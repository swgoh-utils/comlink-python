# coding=utf-8
"""Phase 3 memory regression guards.

Asserts peak memory for decoding load-bearing cassettes stays under a
fixed budget. Catches a future phase silently bloating the parser.

Budgets are intentionally generous (~1.5x the measured Phase 3
baseline) so normal phase churn doesn't trip them — only an honest
regression would.

If a budget needs to move up, update the constant *and* document the
reason in the corresponding phase report. Don't bump silently.
"""

from __future__ import annotations

import gc
import tracemalloc

import pytest
from tests.v3.conftest import load_cassette_bytes

from swgoh_comlink._models import PLAYER_DECODER, UNTYPED_DECODER


def _peak_memory_for(decode, body: bytes) -> int:
    """Peak allocation in bytes for one decode call."""
    gc.collect()
    tracemalloc.start()
    try:
        decoded = decode(body)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    del decoded
    gc.collect()
    return int(peak)


# Budgets measured at the Phase 3 introduction commit and padded ~1.5x:
#
#   typed Player decode of player_large (358 KiB gzipped, 397 units):  budget 35 MiB
#   untyped /data decode (15 MiB gzipped, 80 MiB JSON):                budget 1.6 GiB
#
# The /data budget is intentionally close to the Phase 0 baseline since
# /data is a passthrough endpoint (no Struct typing yet) — Phase 3 does
# not move that number meaningfully. Phase 7 (GameDataCache) will.

_PLAYER_LARGE_BUDGET_BYTES = 35 * 1024 * 1024
_DATA_BUDGET_BYTES = 1_600 * 1024 * 1024


@pytest.mark.skipif(
    not __import__("pathlib")
    .Path(
        __file__,
    )
    .parent.parent.parent.joinpath("benchmarks/v3/fixtures/player_large.json.gz")
    .exists(),
    reason="cassette player_large missing — run benchmarks/v3/_record.py",
)
def test_player_large_typed_decode_under_budget() -> None:
    """Typed Player decode of the 397-unit cassette must stay under 35 MiB peak."""
    body = load_cassette_bytes("player_large")
    peak = _peak_memory_for(PLAYER_DECODER.decode, body)
    assert peak < _PLAYER_LARGE_BUDGET_BYTES, (
        f"Player typed-decode peak memory regressed: {peak / 1024 / 1024:.1f} MiB > "
        f"{_PLAYER_LARGE_BUDGET_BYTES / 1024 / 1024:.0f} MiB budget. "
        f"Either the Struct grew unintentionally, or a future phase added "
        f"allocations. If the regression is intentional, bump the budget and "
        f"document it in the phase report."
    )


@pytest.mark.skipif(
    not __import__("pathlib")
    .Path(
        __file__,
    )
    .parent.parent.parent.joinpath("benchmarks/v3/fixtures/data.json.gz")
    .exists(),
    reason="cassette data missing — run benchmarks/v3/_record.py",
)
def test_data_passthrough_decode_under_budget() -> None:
    """Untyped /data decode must stay under 1.6 GiB peak.

    /data is a passthrough endpoint (returns dict, not Struct) — this
    test guards against accidental double-decoding or eager re-allocation
    on the path. Phase 7's GameDataCache will be the channel that moves
    this number; until then, watch for regressions.
    """
    body = load_cassette_bytes("data")
    peak = _peak_memory_for(UNTYPED_DECODER.decode, body)
    assert peak < _DATA_BUDGET_BYTES, (
        f"/data untyped-decode peak memory regressed: {peak / 1024 / 1024:.1f} MiB > "
        f"{_DATA_BUDGET_BYTES / 1024 / 1024:.0f} MiB budget."
    )
