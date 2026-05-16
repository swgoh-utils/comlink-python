# coding=utf-8
"""Shared benchmark harness for v3.

Public surface:

* :func:`measure` — time a callable; returns median / p95 / stdev.
* :func:`track_memory` — peak / current allocation footprint via :mod:`tracemalloc`.
* :func:`track_import_time` — cold-import cost in milliseconds via ``python -X importtime``.
* :func:`load_cassette` — read a gzipped fixture as ``bytes``.
* :class:`Reporter` — append benchmark results to a JSON file under ``results/``.

The harness has **no dependency on swgoh_comlink itself** so it can be imported
and stay cheap even from Phase 5 onward when the SDK gets the lazy ``__getattr__``
treatment — we don't want the harness to perturb import-time measurements.

Per [v3_implementation_plan.md](../../v3_implementation_plan.md) cross-cutting
principles: report median + p95, not mean; default to 3 warmup runs + 20 iters;
capture git SHA in every result.
"""

from __future__ import annotations

import gzip
import json
import os
import re
import statistics
import subprocess
import sys
import tracemalloc
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter_ns
from typing import Any

__all__ = [
    "BENCHMARKS_ROOT",
    "FIXTURES_DIR",
    "RESULTS_DIR",
    "MeasureResult",
    "MemoryResult",
    "Reporter",
    "PythonVersionMismatch",
    "git_sha",
    "load_cassette",
    "measure",
    "require_python_version",
    "track_import_time",
    "track_memory",
]


# ── Paths ────────────────────────────────────────────────────────────────────

BENCHMARKS_ROOT: Path = Path(__file__).resolve().parent
"""Absolute path to ``benchmarks/v3/``."""

FIXTURES_DIR: Path = BENCHMARKS_ROOT / "fixtures"
"""Where cassettes live."""

RESULTS_DIR: Path = BENCHMARKS_ROOT / "results"
"""Where per-phase result JSON files go."""

_PYTHON_VERSION_FILE: Path = BENCHMARKS_ROOT / "python-version"


# ── Python version gate ──────────────────────────────────────────────────────


class PythonVersionMismatch(RuntimeError):
    """Raised by :func:`require_python_version` when the running interpreter
    does not match the pinned version in ``benchmarks/v3/python-version``."""


def require_python_version() -> None:
    """Refuse to benchmark on an interpreter other than the pinned major.minor.

    The version pin lives in ``benchmarks/v3/python-version`` (e.g. ``3.11``).
    Phase-to-phase comparisons are only valid if the interpreter is held
    constant — different CPython versions have meaningfully different timing
    characteristics (3.11 alone is ~10-15% faster startup than 3.10).
    """
    pinned = _PYTHON_VERSION_FILE.read_text().strip()
    actual = f"{sys.version_info.major}.{sys.version_info.minor}"
    if actual != pinned:
        raise PythonVersionMismatch(
            f"benchmarks/v3 require Python {pinned}; running on {actual}. "
            f"Use `uv run --python {pinned} ...` or activate a matching venv."
        )


# ── Measurement primitives ──────────────────────────────────────────────────


@dataclass(frozen=True)
class MeasureResult:
    """Outcome of a :func:`measure` call.

    All durations are in nanoseconds; convert at presentation time.
    """

    iters: int
    warmup: int
    median_ns: float
    p95_ns: float
    stdev_ns: float
    min_ns: float
    max_ns: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def measure(
    callable_: Callable[[], Any],
    *,
    warmup: int = 3,
    iters: int = 20,
) -> MeasureResult:
    """Time *callable_* and return median / p95 / stdev / min / max in nanoseconds.

    Args:
        callable_: A no-arg callable. Wrap argument-bearing calls in a
            ``lambda`` or ``functools.partial``.
        warmup: Number of throwaway iterations before measurement begins.
            Three is the minimum; bump to 10+ for anything touching
            connection pools, TLS handshakes, or import caches.
        iters: Number of measured iterations.

    Returns:
        :class:`MeasureResult`. Median is the headline; p95 catches tail
        behavior; stdev is for sanity-checking that the sample is stable.

    Notes:
        Uses :func:`time.perf_counter_ns` — monotonic, highest resolution,
        not affected by NTP adjustments. Each iteration's timing excludes
        the loop overhead, which is negligible at this scale.
    """
    if iters < 1:
        raise ValueError(f"iters must be >= 1, got {iters}")
    if warmup < 0:
        raise ValueError(f"warmup must be >= 0, got {warmup}")

    for _ in range(warmup):
        callable_()

    samples: list[int] = []
    for _ in range(iters):
        start = perf_counter_ns()
        callable_()
        samples.append(perf_counter_ns() - start)

    samples.sort()
    p95_idx = max(0, int(round(0.95 * (len(samples) - 1))))
    return MeasureResult(
        iters=iters,
        warmup=warmup,
        median_ns=float(statistics.median(samples)),
        p95_ns=float(samples[p95_idx]),
        stdev_ns=float(statistics.stdev(samples)) if len(samples) > 1 else 0.0,
        min_ns=float(samples[0]),
        max_ns=float(samples[-1]),
    )


@dataclass(frozen=True)
class MemoryResult:
    """Outcome of a :func:`track_memory` call.

    Both numbers are in bytes. ``peak`` is the headline figure — the largest
    allocation footprint observed at any point during *callable_*. ``current``
    is the allocation alive at the moment *callable_* returned.
    """

    peak_bytes: int
    current_bytes: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def track_memory(callable_: Callable[[], Any]) -> MemoryResult:
    """Run *callable_* under :mod:`tracemalloc` and report peak + current bytes.

    Stops tracemalloc on every call so repeated invocations are independent.
    """
    tracemalloc.start()
    try:
        callable_()
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return MemoryResult(peak_bytes=int(peak), current_bytes=int(current))


# ── Import-time measurement ─────────────────────────────────────────────────


_IMPORTTIME_LINE = re.compile(
    r"^import time:\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(.+?)\s*$",
)


def track_import_time(
    module: str,
    *,
    iters: int = 10,
    python: str | None = None,
) -> dict[str, Any]:
    """Measure cold-import cost of *module* via ``python -X importtime``.

    Each iteration spawns a fresh interpreter subprocess (no warm cache from
    the parent), runs ``import <module>``, and parses the ``-X importtime``
    output for the total cumulative milliseconds.

    Returns a dict with the median total (microseconds, matching importtime's
    native unit), the import graph (list of ``(name, cumulative_us)`` for the
    top-30 most expensive imports from the median run), and the raw total per
    iteration so callers can compute their own statistics.
    """
    py = python or sys.executable
    totals_us: list[int] = []
    graphs: list[list[tuple[str, int]]] = []

    for _ in range(iters):
        proc = subprocess.run(
            [py, "-X", "importtime", "-c", f"import {module}"],
            capture_output=True,
            text=True,
            check=False,
        )
        # -X importtime writes to stderr.
        lines = proc.stderr.splitlines()
        graph: list[tuple[str, int]] = []
        total = 0
        for line in lines:
            match = _IMPORTTIME_LINE.match(line)
            if not match:
                continue
            _self_us, cum_us, name = match.groups()
            cum = int(cum_us)
            graph.append((name, cum))
            # The package's own line carries the cumulative cost we care about.
            if name == module:
                total = cum
        if total == 0 and graph:
            # Fallback: top of the call tree (deepest cumulative entry).
            total = max(cum for _, cum in graph)
        totals_us.append(total)
        graphs.append(graph)

    totals_us.sort()
    median_us = float(statistics.median(totals_us))
    median_index = len(totals_us) // 2
    # Use the graph from a representative run for top-N reporting.
    representative = graphs[median_index] if graphs else []
    representative.sort(key=lambda x: x[1], reverse=True)
    top30 = representative[:30]

    return {
        "module": module,
        "iters": iters,
        "median_us": median_us,
        "p95_us": float(totals_us[max(0, int(round(0.95 * (len(totals_us) - 1))))]),
        "all_totals_us": totals_us,
        "top_imports": [{"name": n, "cumulative_us": cum} for n, cum in top30],
    }


# ── Cassette loading ────────────────────────────────────────────────────────


def load_cassette(name: str) -> bytes:
    """Return the raw decompressed bytes for cassette *name* (without ``.json.gz``).

    Raises :class:`FileNotFoundError` with a helpful message — most baseline
    benchmarks need cassettes, and the failure mode for a brand-new clone is
    "you haven't run ``_record.py`` yet."
    """
    path = FIXTURES_DIR / f"{name}.json.gz"
    if not path.exists():
        raise FileNotFoundError(
            f"Cassette '{name}' not found at {path}. "
            f"Run `uv run python -m benchmarks.v3._record` to populate fixtures. "
            f"See benchmarks/v3/fixtures/README.md for required environment variables."
        )
    with gzip.open(path, "rb") as fh:
        return fh.read()


def cassette_exists(name: str) -> bool:
    """Cheap check for whether cassette *name* is available on disk."""
    return (FIXTURES_DIR / f"{name}.json.gz").exists()


# ── Result reporting ────────────────────────────────────────────────────────


def git_sha() -> str:
    """Return ``HEAD`` SHA of the repo this file lives in, or ``"unknown"``."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=BENCHMARKS_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


@dataclass
class Reporter:
    """Collect benchmark results and serialize to a per-phase JSON file.

    Usage::

        rep = Reporter(phase="phase-0-baseline")
        rep.add("cold_import_time_ms", value=12.3, unit="ms")
        rep.add("get_data_decode_ms", value=145.0, unit="ms", parser="json")
        rep.write()  # → benchmarks/v3/results/phase-0-baseline.json
    """

    phase: str
    results: list[dict[str, Any]] = field(default_factory=list)
    sha: str = field(default_factory=git_sha)
    python_version: str = field(
        default_factory=lambda: f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    )

    def add(
        self,
        metric: str,
        *,
        value: float | int | None = None,
        unit: str = "",
        status: str = "ok",
        **extra: Any,
    ) -> None:
        """Record one metric.

        ``status="skip"`` marks a metric as deliberately not measured (e.g.
        cassette-dependent metrics on a fresh clone) — still appears in the
        JSON so report tooling can flag the gap.
        """
        entry: dict[str, Any] = {
            "phase": self.phase,
            "metric": metric,
            "value": value,
            "unit": unit,
            "status": status,
            "git_sha": self.sha,
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        if extra:
            entry["meta"] = extra
        self.results.append(entry)

    def add_measure(self, metric: str, result: MeasureResult, *, unit: str = "ns", **extra: Any) -> None:
        """Convenience wrapper: record a :class:`MeasureResult` as one entry."""
        self.add(
            metric,
            value=result.median_ns,
            unit=unit,
            p95=result.p95_ns,
            stdev=result.stdev_ns,
            iters=result.iters,
            warmup=result.warmup,
            **extra,
        )

    def add_memory(self, metric: str, result: MemoryResult, **extra: Any) -> None:
        """Convenience wrapper: record a :class:`MemoryResult` as one entry."""
        self.add(
            metric,
            value=result.peak_bytes,
            unit="bytes",
            current_bytes=result.current_bytes,
            **extra,
        )

    def write(self, *, dest: Path | None = None) -> Path:
        """Serialize collected results to JSON. Returns the file path."""
        out = dest or (RESULTS_DIR / f"{self.phase}.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "phase": self.phase,
            "git_sha": self.sha,
            "python_version": self.python_version,
            "platform": sys.platform,
            "env": {
                "comlink_url": os.environ.get("COMLINK_URL", "(unset)"),
            },
            "results": self.results,
        }
        out.write_text(json.dumps(payload, indent=2, sort_keys=False))
        return out
