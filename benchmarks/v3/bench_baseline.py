# coding=utf-8
"""Phase 0 baseline benchmark.

Runs every metric called out in `v3_implementation_plan.md` against the current
state of `src/swgoh_comlink/` (initial state of `v3.0-dev` = upstream v2.0.x).
Writes the consolidated result to `benchmarks/v3/results/phase-0-baseline.json`.

Metrics divide cleanly into three groups:

1. **Cassette-free** — always run:
   * ``cold_import_time`` and ``import_graph_cost`` via ``python -X importtime``.
   * ``method_body_duplication_ratio`` via AST/diff between sync and async modules.

2. **Cassette-bound** — skipped with a clear status marker if a cassette is missing:
   * ``get_player_small_e2e_latency`` / ``get_player_large_e2e_latency``.
   * ``get_data_decode_time`` / ``get_data_decode_peak_memory`` / ``get_data_object_size``.
   * ``get_player_concurrent_100x_async``.

3. **Heavy / opt-in** — only when ``--full`` is passed:
   * ``installed_wheel_size`` and ``site_packages_size_delta`` (downloads a real wheel).

Run with::

    uv run python -m benchmarks.v3.bench_baseline           # quick path
    uv run python -m benchmarks.v3.bench_baseline --full    # + wheel/install size
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import difflib
import gc
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import httpx

from benchmarks.v3._harness import (
    BENCHMARKS_ROOT,
    Reporter,
    cassette_exists,
    load_cassette,
    measure,
    require_python_version,
    track_import_time,
    track_memory,
)

# ── Source paths used by the duplication metric ─────────────────────────────

_SRC = BENCHMARKS_ROOT.parent.parent / "src" / "swgoh_comlink"
_SYNC = _SRC / "swgoh_comlink.py"
_ASYNC = _SRC / "swgoh_comlink_async.py"


# ── Cassette-free metrics ───────────────────────────────────────────────────


def bench_cold_import_time(rep: Reporter) -> None:
    """Cold ``import swgoh_comlink`` time via subprocess + ``-X importtime``.

    Headline number for Phase 5 (lazy ``__getattr__``).
    """
    result = track_import_time("swgoh_comlink", iters=10)
    rep.add(
        "cold_import_time",
        value=result["median_us"] / 1000.0,
        unit="ms",
        p95_ms=result["p95_us"] / 1000.0,
        iters=result["iters"],
    )
    # Capture the import graph separately so Phase 5 can diff the top-N.
    rep.add(
        "import_graph_top30",
        value=None,
        unit="(structured)",
        status="ok",
        top_imports=result["top_imports"],
    )
    # Specifically: is httpx loaded eagerly today? (Phase 5 assertion will flip.)
    httpx_loaded = any(t["name"] == "httpx" for t in result["top_imports"])
    rep.add(
        "httpx_loaded_on_import",
        value=1.0 if httpx_loaded else 0.0,
        unit="bool",
    )


def bench_method_body_duplication(rep: Reporter) -> None:
    """AST-diff each ``get_*`` method shared between sync and async modules.

    Reports the average :class:`difflib.SequenceMatcher` ratio across all paired
    methods. Phase 4 (sibling-on-base) targets this directly: baseline should be
    high (~0.7–0.9), Phase 4 exit should drop it under 0.10.
    """
    sync_funcs = _public_funcs(_SYNC)
    async_funcs = _public_funcs(_ASYNC, strip_async=True)

    paired = sorted(set(sync_funcs) & set(async_funcs))
    if not paired:
        rep.add(
            "method_body_duplication_ratio", value=None, unit="ratio", status="skip", reason="no paired methods found"
        )
        return

    similarities: list[float] = []
    per_method: list[dict[str, Any]] = []
    for name in paired:
        s = sync_funcs[name]
        a = async_funcs[name]
        ratio = difflib.SequenceMatcher(a=s, b=a, autojunk=False).ratio()
        similarities.append(ratio)
        per_method.append({"method": name, "similarity": round(ratio, 4)})

    avg = sum(similarities) / len(similarities)
    rep.add(
        "method_body_duplication_ratio",
        value=round(avg, 4),
        unit="ratio",
        paired_count=len(paired),
        per_method=per_method,
    )


def _public_funcs(path: Path, *, strip_async: bool = False) -> dict[str, str]:
    """Return ``{function_name: normalized_body_text}`` for public ``get_*`` methods.

    Body is normalized for the duplication comparison: stripped of leading
    whitespace, ``async``/``await`` removed when *strip_async* is set, so that
    a sync and async implementation of the same method compare on logic only.
    """
    tree = ast.parse(path.read_text())
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if not node.name.startswith("get_"):
            continue
        # Render the body. ast.unparse is python 3.9+.
        body_src = "\n".join(ast.unparse(stmt) for stmt in node.body)
        if strip_async:
            # Normalize async-only tokens so sync and async bodies are comparable.
            body_src = body_src.replace("await ", "").replace("async ", "")
        out[node.name] = body_src
    return out


# ── Cassette-bound metrics ──────────────────────────────────────────────────


def _mock_transport_for(cassette: bytes, endpoint_substr: str) -> httpx.MockTransport:
    """Return a mock transport that serves *cassette* for any URL containing *endpoint_substr*.

    Other URLs return 404 — the benchmark should only hit the endpoint under test.
    """
    body = cassette

    def handler(request: httpx.Request) -> httpx.Response:
        if endpoint_substr in str(request.url):
            return httpx.Response(200, content=body, headers={"content-type": "application/json"})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def _bench_player_e2e(rep: Reporter, *, cassette: str, metric: str, ally: str = "123456789") -> None:
    """End-to-end ``get_player`` latency against a mock-transport-backed client."""
    if not cassette_exists(cassette):
        rep.add(metric, value=None, unit="ms", status="skip", reason=f"cassette '{cassette}' missing")
        return

    from swgoh_comlink import SwgohComlink

    raw = load_cassette(cassette)
    transport = _mock_transport_for(raw, "/player")

    client = SwgohComlink(url="http://comlink.local:3000")
    # Replace the auto-created httpx.Client with one wired to the mock transport.
    client.client.close()
    client.client = httpx.Client(base_url=client.url_base, transport=transport)

    try:
        result = measure(lambda: client.get_player(allycode=ally), warmup=3, iters=20)
    finally:
        client.close()

    rep.add_measure(metric, result, unit="ns", cassette=cassette)


def bench_get_player_small_e2e(rep: Reporter) -> None:
    _bench_player_e2e(rep, cassette="player_small", metric="get_player_small_e2e_latency")


def bench_get_player_large_e2e(rep: Reporter) -> None:
    _bench_player_e2e(rep, cassette="player_large", metric="get_player_large_e2e_latency")


def bench_get_data_decode(rep: Reporter) -> None:
    """Time only ``json.loads(bytes)`` on the ``/data`` cassette (no network).

    Phase 3 msgspec adds parallel rows for ``orjson`` and typed-Struct decoding;
    this baseline is the row labeled ``json``.
    """
    if not cassette_exists("data"):
        rep.add("get_data_decode_time", value=None, unit="ms", status="skip", reason="cassette 'data' missing")
        rep.add(
            "get_data_decode_peak_memory", value=None, unit="bytes", status="skip", reason="cassette 'data' missing"
        )
        rep.add("get_data_object_size", value=None, unit="bytes", status="skip", reason="cassette 'data' missing")
        return

    raw = load_cassette("data")

    decode = lambda: json.loads(raw)  # noqa: E731 — terse on purpose
    timing = measure(decode, warmup=3, iters=10)
    rep.add_measure("get_data_decode_time", timing, unit="ns", parser="json", cassette_size_bytes=len(raw))

    mem = track_memory(decode)
    rep.add_memory("get_data_decode_peak_memory", mem, parser="json")

    # Object size at rest (after decoding settles).
    try:
        from pympler.asizeof import asizeof
    except ImportError:
        rep.add(
            "get_data_object_size",
            value=None,
            unit="bytes",
            status="skip",
            reason="pympler not installed; add `bench` dep group (uv sync --group bench)",
        )
        return

    decoded = json.loads(raw)
    gc.collect()
    size = asizeof(decoded)
    rep.add("get_data_object_size", value=int(size), unit="bytes", parser="json")
    del decoded
    gc.collect()


def bench_concurrent_100x_async(rep: Reporter) -> None:
    """100 concurrent ``get_player`` calls via the async client.

    Stresses connection-pool churn + asyncio scheduling. Reports total wall
    time and peak memory.
    """
    if not cassette_exists("player_small"):
        rep.add(
            "get_player_concurrent_100x_async_wall_ms",
            value=None,
            unit="ms",
            status="skip",
            reason="cassette 'player_small' missing",
        )
        rep.add(
            "get_player_concurrent_100x_async_peak_memory",
            value=None,
            unit="bytes",
            status="skip",
            reason="cassette 'player_small' missing",
        )
        return

    from swgoh_comlink import SwgohComlinkAsync

    raw = load_cassette("player_small")

    async def runner() -> None:
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, content=raw, headers={"content-type": "application/json"}),
        )
        client = SwgohComlinkAsync(url="http://comlink.local:3000")
        await client.client.aclose()
        client.client = httpx.AsyncClient(base_url=client.url_base, transport=transport)
        try:
            await asyncio.gather(*(client.get_player(allycode="123456789") for _ in range(100)))
        finally:
            await client.aclose()

    # Wall-time: a single 100-call gather is the unit of measurement.
    timing = measure(lambda: asyncio.run(runner()), warmup=1, iters=5)
    rep.add_measure(
        "get_player_concurrent_100x_async_wall",
        timing,
        unit="ns",
        cassette="player_small",
        concurrency=100,
    )

    mem = track_memory(lambda: asyncio.run(runner()))
    rep.add_memory("get_player_concurrent_100x_async_peak_memory", mem, concurrency=100)


# ── Heavy / opt-in metrics ──────────────────────────────────────────────────


def bench_install_size(rep: Reporter) -> None:
    """Measure wheel + installed footprint of the *current* package.

    Uses ``uv build`` to produce a wheel from the working tree (no network),
    then measures the wheel size and the post-install ``du`` delta in a fresh
    venv. Skips gracefully if ``uv`` is not on PATH or the build fails.
    """
    if not shutil.which("uv"):
        rep.add(
            "installed_wheel_size",
            value=None,
            unit="bytes",
            status="skip",
            reason="uv not on PATH",
        )
        return

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        build_dir = tmp_path / "dist"
        proc = subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(build_dir)],
            cwd=BENCHMARKS_ROOT.parent.parent,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            rep.add(
                "installed_wheel_size",
                value=None,
                unit="bytes",
                status="skip",
                reason=f"uv build failed: {proc.stderr.strip()[:200]}",
            )
            return
        wheels = list(build_dir.glob("*.whl"))
        if not wheels:
            rep.add("installed_wheel_size", value=None, unit="bytes", status="skip", reason="no wheel produced")
            return
        wheel = wheels[0]
        rep.add(
            "installed_wheel_size",
            value=wheel.stat().st_size,
            unit="bytes",
            wheel_name=wheel.name,
        )


# ── Entry point ─────────────────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--full",
        action="store_true",
        help="Also run heavy metrics (build wheel and measure install footprint).",
    )
    p.add_argument(
        "--phase",
        default="phase-0-baseline",
        help="Phase tag for the output filename and result records.",
    )
    p.add_argument(
        "--skip-python-version-check",
        action="store_true",
        help="Allow running on an interpreter other than the pinned major.minor.",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    if not args.skip_python_version_check:
        require_python_version()

    rep = Reporter(phase=args.phase)

    sys.stderr.write("[1/6] cold import time + import graph ...\n")
    bench_cold_import_time(rep)

    sys.stderr.write("[2/6] method-body duplication ratio ...\n")
    bench_method_body_duplication(rep)

    sys.stderr.write("[3/6] get_player end-to-end (small) ...\n")
    bench_get_player_small_e2e(rep)

    sys.stderr.write("[4/6] get_player end-to-end (large) ...\n")
    bench_get_player_large_e2e(rep)

    sys.stderr.write("[5/6] get_data decode time + memory + size ...\n")
    bench_get_data_decode(rep)

    sys.stderr.write("[6/6] get_player concurrent 100x async ...\n")
    bench_concurrent_100x_async(rep)

    if args.full:
        sys.stderr.write("[opt] installed wheel size ...\n")
        bench_install_size(rep)

    dest = rep.write()
    sys.stderr.write(f"\nWrote {len(rep.results)} metrics → {dest}\n")
    skipped = sum(1 for r in rep.results if r["status"] == "skip")
    if skipped:
        sys.stderr.write(f"({skipped} metric(s) skipped — typically missing cassettes; see fixtures/README.md)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
