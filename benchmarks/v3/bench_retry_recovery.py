# coding=utf-8
"""Phase 2 — Retry recovery timing.

Two scenarios:

1. **429 + Retry-After: 1 → 200.** Mock first returns 429 with a
   ``Retry-After: 1`` header; second call returns 200. Total wall time
   should be ``1.0 s + base_latency ± 0.1 s`` (the SDK honors the
   header verbatim and the second call is fast).

2. **503 (no Retry-After) → 200.** First call returns 503 with no
   header; second returns 200. Total wall time should be roughly
   ``compute_backoff(0)`` worth of exponential-jitter wait — for
   default backoff (``base=0.5``) the expected mean is ~0.25 s
   (uniform ``[0, 0.5)``). Test asserts the wait is bounded below
   the next-bucket cap.

Writes results to ``benchmarks/v3/results/phase-2-retry-recovery.json``.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

import httpx

from benchmarks.v3._harness import (
    Reporter,
    require_python_version,
)


def _scenario_mock(scenario: str) -> Callable[[httpx.Request], httpx.Response]:
    """Return a stateful handler that produces the requested scenario.

    Each handler is single-use per SDK instance (it counts calls) — caller
    should construct a fresh SDK for each measure() iteration via the
    ``setup`` callable.
    """
    if scenario == "429+1s":
        state = {"calls": 0}

        def h(req: httpx.Request) -> httpx.Response:
            state["calls"] += 1
            if state["calls"] == 1:
                return httpx.Response(429, headers={"Retry-After": "1"})
            return httpx.Response(200, content=b'{"ok": true}')

        return h

    if scenario == "503_backoff":
        state = {"calls": 0}

        def h(req: httpx.Request) -> httpx.Response:
            state["calls"] += 1
            if state["calls"] == 1:
                return httpx.Response(503)
            return httpx.Response(200, content=b'{"ok": true}')

        return h

    raise ValueError(f"unknown scenario {scenario!r}")


def _fresh_sdk(handler: Callable[[httpx.Request], httpx.Response]) -> Any:
    """SwgohComlink wired to *handler*."""
    from swgoh_comlink import SwgohComlink

    transport = httpx.MockTransport(handler)
    sdk = SwgohComlink(url="http://bench.local", max_retries=3)
    sdk.client.close()
    sdk.client = httpx.Client(base_url=sdk.url_base, transport=transport)
    return sdk


def _time_one(scenario: str) -> float:
    """Run *scenario* once end-to-end. Returns wall seconds."""
    import time

    sdk = _fresh_sdk(_scenario_mock(scenario))
    start = time.perf_counter()
    try:
        sdk.get_game_metadata()
    finally:
        sdk.close()
    return time.perf_counter() - start


def main() -> int:
    require_python_version()
    rep = Reporter(phase="phase-2-retry-recovery")

    # ── Scenario 1: 429 + Retry-After: 1 ──
    sys.stderr.write("[1/2] 429 + Retry-After: 1 → 200 ...\n")
    samples_1s = [_time_one("429+1s") for _ in range(5)]
    median_1s = sorted(samples_1s)[len(samples_1s) // 2]
    rep.add(
        "retry_after_1s_total_wall",
        value=median_1s,
        unit="s",
        samples=samples_1s,
        scenario="429 + Retry-After: 1 -> 200",
        expected_range_s=[0.95, 1.5],
    )
    sys.stderr.write(f"  median: {median_1s:.3f}s  (expected ~1.0–1.3s)\n")

    # ── Scenario 2: 503 (no header) → backoff → 200 ──
    sys.stderr.write("[2/2] 503 (no Retry-After) → backoff → 200 ...\n")
    samples_bo = [_time_one("503_backoff") for _ in range(10)]
    median_bo = sorted(samples_bo)[len(samples_bo) // 2]
    rep.add(
        "exponential_backoff_first_retry",
        value=median_bo,
        unit="s",
        samples=samples_bo,
        scenario="503 -> exp jitter wait -> 200",
        expected_range_s=[0.0, 0.6],  # uniform [0, 0.5) + tiny overhead
    )
    sys.stderr.write(f"  median: {median_bo:.3f}s  (expected ~0.1–0.4s, uniform in [0,0.5))\n")

    dest = rep.write()
    sys.stderr.write(f"\nWrote {dest}\n")
    # Loose health check (pass/fail isn't useful for jitter-based timing).
    ok = 0.95 <= median_1s <= 1.5 and 0.0 <= median_bo <= 0.6
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
