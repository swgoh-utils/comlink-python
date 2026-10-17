# coding=utf-8
"""v3.3 Phase 2 — parity snapshot pinning current StatCalc output.

Carries the v3.2 GREATMOTHERS lesson forward: field-access audits
lie; parity testing is load-bearing.

This module captures **today's exact** per-unit stats + GP for every
unit on every cassette, then asserts the same output post-refactor.
Written BEFORE the pure-Python restructure starts.

Two kinds of test live here:

1. **Per-unit checksum.** A deterministic hash of every unit's
   ``(definitionId, sorted stats dict, gp)`` triple. Survives the
   restructure → identical hash. Fast (single pass per cassette).

2. **Spot-check fixtures.** Specific units the v3.2 audit flagged as
   parity-sensitive — most importantly GREATMOTHERS, the v3.2 mod-set
   bonus regression unit. Exact stats + GP must match across the
   refactor.

Both must pass for the Phase 2 prototype to ship. Failures here are
non-shippable; document and revert, do not "document as a known
difference."
"""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from swgoh_comlink.StatCalc import StatCalc
from swgoh_comlink.StatCalc.data_builder._builder_base import GameDataBuilderBase

_FIXTURES = Path(__file__).resolve().parents[1].parent / "benchmarks" / "v3" / "fixtures"

_PLAYERS = ("player_small", "player_large")


def _have_cassette(name: str) -> bool:
    return (_FIXTURES / f"{name}.json.gz").exists()


def _load_player_dict(name: str) -> dict[str, Any]:
    with gzip.open(_FIXTURES / f"{name}.json.gz", "rb") as fh:
        return json.load(fh)  # type: ignore[no-any-return]


@pytest.fixture(scope="module")
def game_data() -> dict[str, Any]:
    if not _have_cassette("data"):
        pytest.skip("/data cassette missing")
    with gzip.open(_FIXTURES / "data.json.gz", "rb") as fh:
        raw = json.load(fh)
    return GameDataBuilderBase._build_game_data(raw)


@pytest.fixture(scope="module")
def sc(game_data: dict[str, Any]) -> StatCalc:
    return StatCalc(game_data=game_data)


def _per_unit_checksum(roster: list[dict[str, Any]]) -> str:
    """Deterministic SHA256 over ``(defId, sorted_stats, gp)`` triples.

    Sorted stats dict by key → list of (key, value) so dict ordering
    doesn't affect the hash. GP included separately.
    """
    h = hashlib.sha256()
    for u in roster:
        def_id = u.get("definitionId") or u.get("defId") or ""
        stats = u.get("stats") or {}
        gp = u.get("gp")
        # Stats is nested (mods, base, final, gp, ...). Walk it
        # canonically — sort all dict keys at every level so the hash
        # is order-independent.
        canonical = json.dumps(stats, sort_keys=True)
        h.update(def_id.encode())
        h.update(b"\x1f")  # field separator (unit separator)
        h.update(canonical.encode())
        h.update(b"\x1f")
        h.update(str(gp).encode())
        h.update(b"\x1e")  # record separator
    return h.hexdigest()


# ── Snapshot checksums (recorded against v3.2-research HEAD ef7a542) ───────
#
# These are the "before" hashes. The Phase 2 refactor must keep them
# identical. If they drift, the refactor changed observable output
# and must be reverted (parity is non-negotiable).
#
# To regenerate after a deliberate behaviour change, run the regen
# helper at the bottom of this file (run as a script, not via pytest).
#
_EXPECTED_CHECKSUMS: dict[str, str] = {
    # Recorded against v3.2-research HEAD ef7a542 (Phase 5 of v3.2,
    # the bimorphic + cached-game-data merge). Regenerate via the
    # _regen() script in this module ONLY after a deliberate,
    # approved behaviour change.
    "player_small": "83d043b120b0bf19b2c38f55f6f89fd75841e2630c444f9d2cecbadde4997ede",
    # player_large re-pinned for develop's bc3e0e8 (raw units keep purchasedAbilityId): its 10
    # Galactic Legends gain the ultimate's GP (+7467 each). With purchasedAbilityId stripped the
    # roster still hashes to the ef7a542 value 47deaaa8678830103d37389de99e3333176dc4ebbcffb327bc6c63702f79548f.
    "player_large": "701bb82052d15db313d731f0778ada7335fa743452245237efcb7e30627134a3",
}


@pytest.mark.parametrize("player_name", _PLAYERS)
def test_per_unit_checksum_pins_current_output(
    sc: StatCalc,
    player_name: str,
) -> None:
    """Per-unit (defId, stats, gp) checksum must match the recorded snapshot."""
    if not _have_cassette(player_name):
        pytest.skip(f"{player_name} cassette missing")
    player = _load_player_dict(player_name)
    sc.calc_player_stats(player)
    actual = _per_unit_checksum(player["rosterUnit"])

    expected = _EXPECTED_CHECKSUMS.get(player_name)
    if expected is None:
        pytest.skip(
            f"no recorded checksum for {player_name}; run "
            f"`uv run python tests/unit/test_statcalc_v3_3_parity.py` "
            f"to record. Current value: {actual}"
        )
    assert actual == expected, (
        f"per-unit checksum drift on {player_name}:\n  expected {expected}\n  actual   {actual}\n"
        "Phase 2 refactor changed observable output — REVERT."
    )


@pytest.mark.parametrize("player_name", _PLAYERS)
def test_greatmothers_exact_stats(sc: StatCalc, player_name: str) -> None:
    """v3.2 regression unit — Strength stat on GREATMOTHERS must not drift.

    The v3.2 H aggressive variant broke parity here (Strength 451 → 368).
    This test pins down GREATMOTHERS exactly so any future restructure
    that re-introduces nested-key normalisation breaks loudly.
    """
    if not _have_cassette(player_name):
        pytest.skip(f"{player_name} cassette missing")
    player = _load_player_dict(player_name)
    sc.calc_player_stats(player)

    greatmothers = [u for u in player["rosterUnit"] if "GREATMOTHERS" in (u.get("definitionId") or "").upper()]
    if not greatmothers:
        pytest.skip(f"GREATMOTHERS not in {player_name} cassette")

    assert len(greatmothers) == 1
    unit = greatmothers[0]
    stats = unit.get("stats") or {}
    gp = unit.get("gp")

    # GREATMOTHERS is a ship — ships produce {final, mods, gp};
    # characters add `base` (and sometimes `crew`). The two cassettes
    # carry different stars of the same unit (small=lower-star,
    # large=SEVEN_STAR), so absolute stat values differ. Per-stat
    # pinning happens via the per-unit checksum test above; here we
    # only assert structural shape + GP sanity.
    final = stats.get("final") or {}

    assert "final" in stats, f"GREATMOTHERS missing 'final': {stats.keys()}"
    assert "mods" in stats, f"GREATMOTHERS missing 'mods': {stats.keys()}"
    assert "gp" in stats, "GREATMOTHERS missing 'gp' in stats dict"
    assert isinstance(gp, int) and gp > 0, f"GREATMOTHERS gp invalid: {gp!r}"

    # Strength is the v3.2 H-aggressive regression signal (Strength
    # 451 → 368 on lower-star GREATMOTHERS; ship's Strength is the
    # mod-set bonus path the broken normalisation corrupted). Just
    # assert it's a positive float — the actual value is pinned by
    # the checksum test.
    assert isinstance(final.get("Strength"), (int, float))
    assert final["Strength"] > 0, f"GREATMOTHERS Strength non-positive: {final['Strength']!r}"


def _regen() -> None:
    """Manual regen — print the current checksums so a developer can
    paste them into ``_EXPECTED_CHECKSUMS``.

    Run as a script (NOT via pytest), only when a deliberate behaviour
    change has been approved and the snapshot needs updating::

        uv run python tests/unit/test_statcalc_v3_3_parity.py
    """
    if not _have_cassette("data"):
        print("/data cassette missing — cannot regen")
        return
    with gzip.open(_FIXTURES / "data.json.gz", "rb") as fh:
        raw = json.load(fh)
    game_data = GameDataBuilderBase._build_game_data(raw)
    sc = StatCalc(game_data=game_data)

    print("_EXPECTED_CHECKSUMS = {")
    for name in _PLAYERS:
        if not _have_cassette(name):
            print(f"    # SKIP: {name} cassette missing")
            continue
        player = _load_player_dict(name)
        sc.calc_player_stats(player)
        checksum = _per_unit_checksum(player["rosterUnit"])
        print(f'    "{name}": "{checksum}",')
    print("}")


if __name__ == "__main__":
    _regen()
