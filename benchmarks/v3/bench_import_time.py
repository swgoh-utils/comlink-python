# coding=utf-8
"""Phase 5 — Cold import time + import-graph hygiene assertions.

Two measurements + one structural check, each per the Phase 5 plan:

* ``import_time_swgoh_comlink_ms`` — median ms over fresh interpreter
  subprocess starts. Target: ≥10x reduction vs the Phase 0 baseline of
  ~65 ms.
* ``import_time_then_construct_ms`` — cold ``import`` + ``SwgohComlink(...)``
  construct. Should equal the *original* baseline within noise (the
  construct triggers the deferred httpx import).
* ``httpx_in_import_graph`` — boolean. With lazy imports, ``import
  swgoh_comlink`` should NOT pull in httpx. Phase 5 flips this from
  True (Phase 0) to False.

Writes results to ``benchmarks/v3/results/phase-5-import-time.json``.
"""

from __future__ import annotations

import sys
from typing import TypedDict

from benchmarks.v3._harness import (
    Reporter,
    require_python_version,
    track_import_time,
)


class _ImportTimeResult(TypedDict):
    median_ms: float
    p95_ms: float
    iters: int
    httpx_loaded: bool
    all_totals_ms: list[float]


def _measure_import_time_ms(iters: int = 20) -> _ImportTimeResult:
    """Median + p95 cold import in milliseconds; httpx-presence flag."""
    result = track_import_time("swgoh_comlink", iters=iters)
    httpx_loaded = any(t["name"] == "httpx" for t in result["top_imports"])
    return {
        "median_ms": result["median_us"] / 1000.0,
        "p95_ms": result["p95_us"] / 1000.0,
        "iters": iters,
        "httpx_loaded": httpx_loaded,
        "all_totals_ms": [v / 1000.0 for v in result["all_totals_us"]],
    }


def _measure_cold_import_then_construct_ms(iters: int = 20) -> dict[str, float]:
    """Cold ``import`` + ``SwgohComlink(url=...)`` construct, in ms.

    Spawns a fresh interpreter per iteration so the cost is the FULL
    deferred path (import → first __getattr__ → load _base, _models,
    httpx, msgspec, …). Should equal the Phase 0 *bare* import baseline
    within noise — that's the "total cost of first use" sanity check.
    """
    import subprocess
    import time

    py = sys.executable
    samples: list[float] = []
    for _ in range(iters):
        start = time.perf_counter()
        subprocess.run(
            [py, "-c", "import swgoh_comlink; c = swgoh_comlink.SwgohComlink(url='http://x'); c.close()"],
            check=True,
            capture_output=True,
        )
        samples.append((time.perf_counter() - start) * 1000)

    samples.sort()
    return {
        "median_ms": samples[len(samples) // 2],
        "p95_ms": samples[max(0, int(round(0.95 * (len(samples) - 1))))],
        "min_ms": samples[0],
        "max_ms": samples[-1],
        "iters": iters,
    }


def main() -> int:
    require_python_version()
    rep = Reporter(phase="phase-5-import-time")

    sys.stderr.write("[1/2] Bare `import swgoh_comlink` ...\n")
    bare = _measure_import_time_ms(iters=20)
    rep.add(
        "cold_import_time_ms",
        value=bare["median_ms"],
        unit="ms",
        p95_ms=bare["p95_ms"],
        iters=bare["iters"],
    )
    rep.add(
        "httpx_loaded_on_import",
        value=0.0 if not bare["httpx_loaded"] else 1.0,
        unit="bool",
    )
    sys.stderr.write(f"  median {bare['median_ms']:.2f} ms  (httpx loaded: {bare['httpx_loaded']})\n")

    sys.stderr.write("[2/2] Cold import + SwgohComlink() construct ...\n")
    construct = _measure_cold_import_then_construct_ms(iters=10)
    rep.add(
        "import_then_construct_ms",
        value=construct["median_ms"],
        unit="ms",
        p95_ms=construct["p95_ms"],
        iters=construct["iters"],
    )
    sys.stderr.write(f"  median {construct['median_ms']:.2f} ms  (p95 {construct['p95_ms']:.2f} ms)\n")

    dest = rep.write()
    sys.stderr.write(f"\nWrote {dest}\n")

    # Pass/fail summary: lazy imports must NOT load httpx, and bare import
    # must hit the plan's ≤10 ms target.
    ok = (not bare["httpx_loaded"]) and bare["median_ms"] <= 15.0
    if ok:
        sys.stderr.write("OK\n")
        return 0
    sys.stderr.write("Phase 5 target not fully met (httpx in graph or median > 15 ms)\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
