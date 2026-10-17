# coding=utf-8
"""Phase 2 — Retry overhead on the happy path.

1000 successful (200 OK) calls through a mock transport, comparing:

* ``retry=None`` — one attempt: ``client.request(...)`` + classify + decode
* ``retry=RetryPolicy()`` — same, through the retry/pacing loop (which never trips)

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


def _client_with_mock(with_policy: bool) -> Any:
    """Construct SwgohComlink wired to a mock transport returning 200 + small body."""
    from swgoh_comlink import RetryPolicy, SwgohComlink

    body = load_cassette("metadata")  # small (~10 KiB gzipped, ~50 KiB decoded)
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            content=body,
            headers={"content-type": "application/json"},
        ),
    )
    sdk = SwgohComlink(url="http://bench.local", retry=RetryPolicy() if with_policy else None)
    sdk.client.close()
    sdk.client = httpx.Client(base_url=sdk.url_base, transport=transport)
    return sdk


def _run_one(with_policy: bool) -> Any:
    """Run the measure loop for one retry setting. Factored out so the
    closure captures only its own *sdk* (avoids the ruff B023 loop-variable
    capture gotcha you get when the body is inlined in ``main``)."""
    sdk = _client_with_mock(with_policy)
    try:
        # warmup 10, iters 50 — happy-path call is ~10s of microseconds; many iters smooth noise.
        return measure(lambda: sdk.get_game_metadata(), warmup=10, iters=50)
    finally:
        sdk.close()


def main() -> int:
    require_python_version()
    rep = Reporter(phase="phase-2-retry-overhead")

    for with_policy in (False, True):
        result = _run_one(with_policy)
        rep.add_measure(
            f"retry_overhead_policy_{'default' if with_policy else 'none'}",
            result,
            unit="ns",
            retry_policy="RetryPolicy()" if with_policy else None,
        )

    dest = rep.write()
    # Compute the overhead percentage for the operator.
    no_retry = next(r for r in rep.results if r["metric"] == "retry_overhead_policy_none")["value"]
    with_retry = next(r for r in rep.results if r["metric"] == "retry_overhead_policy_default")["value"]
    overhead = (with_retry - no_retry) / no_retry
    sys.stderr.write(
        f"\nretry=None: {no_retry / 1e6:.3f} ms  |  "
        f"retry=RetryPolicy(): {with_retry / 1e6:.3f} ms  |  "
        f"overhead: {overhead * 100:+.2f}%  (target <2%)\n",
    )
    sys.stderr.write(f"Wrote {dest}\n")
    return 0 if overhead < 0.02 else 1


if __name__ == "__main__":
    sys.exit(main())
