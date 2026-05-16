# coding=utf-8
"""Phase 2 — Retry overhead on the happy path.

1000 successful (200 OK) calls through a mock transport, comparing:

* ``max_retries=0`` — bare ``client.request(...)`` + classify + decode
* ``max_retries=3`` — same, wrapped in the retry loop (which never trips)

Per the Phase 2 plan: the overhead of the retry wrapping on the happy
path must be **<2%**. Higher overhead means the per-attempt closure
construction is unexpectedly expensive and we should investigate.

Writes results to ``benchmarks/v3/results/phase-2-retry-overhead.json``.
"""

from __future__ import annotations

import sys
from typing import Any

import httpx

from benchmarks.v3._harness import (
    Reporter,
    load_cassette,
    measure,
    require_python_version,
)


def _client_with_mock(max_retries: int) -> Any:
    """Construct SwgohComlink wired to a mock transport returning 200 + small body."""
    from swgoh_comlink import SwgohComlink

    body = load_cassette("metadata")  # small (~10 KiB gzipped, ~50 KiB decoded)
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            content=body,
            headers={"content-type": "application/json"},
        ),
    )
    sdk = SwgohComlink(url="http://bench.local", max_retries=max_retries)
    sdk.client.close()
    sdk.client = httpx.Client(base_url=sdk.url_base, transport=transport)
    return sdk


def _run_one(max_retries: int) -> Any:
    """Run the measure loop for one max_retries setting. Factored out so the
    closure captures only its own *sdk* (avoids the ruff B023 loop-variable
    capture gotcha you get when the body is inlined in ``main``)."""
    sdk = _client_with_mock(max_retries)
    try:
        # warmup 10, iters 50 — happy-path call is ~10s of microseconds; many iters smooth noise.
        return measure(lambda: sdk.get_game_metadata(), warmup=10, iters=50)
    finally:
        sdk.close()


def main() -> int:
    require_python_version()
    rep = Reporter(phase="phase-2-retry-overhead")

    for max_retries in (0, 3):
        result = _run_one(max_retries)
        rep.add_measure(
            f"retry_overhead_max_retries_{max_retries}",
            result,
            unit="ns",
            max_retries=max_retries,
        )

    dest = rep.write()
    # Compute the overhead percentage for the operator.
    no_retry = next(r for r in rep.results if r["metric"] == "retry_overhead_max_retries_0")["value"]
    with_retry = next(r for r in rep.results if r["metric"] == "retry_overhead_max_retries_3")["value"]
    overhead = (with_retry - no_retry) / no_retry
    sys.stderr.write(
        f"\nmax_retries=0: {no_retry / 1e6:.3f} ms  |  "
        f"max_retries=3: {with_retry / 1e6:.3f} ms  |  "
        f"overhead: {overhead * 100:+.2f}%  (target <2%)\n",
    )
    sys.stderr.write(f"Wrote {dest}\n")
    return 0 if overhead < 0.02 else 1


if __name__ == "__main__":
    sys.exit(main())
