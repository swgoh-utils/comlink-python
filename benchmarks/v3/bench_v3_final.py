# coding=utf-8
"""Phase 9 — Consolidated v3 benchmark roll-up.

Re-runs the headline benchmarks against the current ``v3.0-dev`` HEAD
and compiles a single result JSON at
``benchmarks/v3/results/phase-9-final.json``. The companion
``docs/v3/benchmark-report.md`` reads this plus the historical
per-phase JSONs to produce the v2-vs-v3 comparison table.

Re-runs the things that *move*:
* `bench_baseline.py` — every Phase 0 metric.
* `bench_import_time.py` — cold-import + httpx-on-graph.
* `bench_cache_cold_vs_warm.py` — Phase 7 cache headline.

Skips the heavy ones that don't move with phase 9 changes:
* `bench_decode_speed/memory/object_size.py` (Phase 3/3.5 — code path
  unchanged in Phase 9).
* `bench_retry_overhead/recovery.py` (Phase 2 — code path unchanged).

Run with::

    uv run python -m benchmarks.v3.bench_v3_final
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from benchmarks.v3._harness import (
    RESULTS_DIR,
    Reporter,
    require_python_version,
)


def _run_module(module: str, extra_args: list[str] | None = None) -> int:
    """Spawn a subprocess to run a bench module; return its exit code."""
    args = [sys.executable, "-m", module]
    if extra_args:
        args.extend(extra_args)
    sys.stderr.write(f"→ running {module} {' '.join(extra_args or [])}\n")
    proc = subprocess.run(args, capture_output=False)
    return proc.returncode


def main() -> int:
    require_python_version()
    sys.stderr.write("Phase 9 — re-running headline benches for the final v3 roll-up.\n\n")

    failures: list[str] = []
    for module, args in [
        ("benchmarks.v3.bench_baseline", ["--phase", "phase-9-final-baseline"]),
        ("benchmarks.v3.bench_import_time", []),
        ("benchmarks.v3.bench_cache_cold_vs_warm", []),
    ]:
        rc = _run_module(module, args)
        if rc != 0:
            failures.append(f"{module} (rc={rc})")

    rep = Reporter(phase="phase-9-final")
    rep.add(
        "phase_9_final_bench_run",
        value=0 if not failures else 1,
        unit="status",
        ran=[
            "bench_baseline (--phase=phase-9-final-baseline)",
            "bench_import_time",
            "bench_cache_cold_vs_warm",
        ],
        failures=failures,
    )

    # Headline metrics: read from the per-bench JSONs that just got written.
    final_baseline = RESULTS_DIR / "phase-9-final-baseline.json"
    if final_baseline.exists():
        baseline_data: dict[str, Any] = json.loads(final_baseline.read_text())
        for r in baseline_data["results"]:
            if r["metric"] in {"cold_import_time", "httpx_loaded_on_import"}:
                rep.add(f"final_{r['metric']}", value=r["value"], unit=r["unit"])

    import_time_json = RESULTS_DIR / "phase-5-import-time.json"
    if import_time_json.exists():
        latest = json.loads(import_time_json.read_text())
        for r in latest["results"]:
            if r["metric"] == "import_then_construct_ms":
                rep.add("final_import_then_construct_ms", value=r["value"], unit=r["unit"])

    cache_json = RESULTS_DIR / "phase-7-cache-cold-vs-warm.json"
    if cache_json.exists():
        latest = json.loads(cache_json.read_text())
        for r in latest["results"]:
            if r["metric"] == "inmem_warm_speedup_vs_cold":
                rep.add("final_inmem_warm_speedup_vs_cold", value=r["value"], unit="ratio")

    dest = rep.write()
    sys.stderr.write(f"\nv3 final roll-up: {dest}\n")
    if failures:
        sys.stderr.write(f"WARNINGS: {len(failures)} bench(es) failed.\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
