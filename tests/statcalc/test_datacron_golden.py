"""Datacron output against stat values read by hand off the live game.

This is the only evidence that datacron arithmetic is correct. Every other
number `StatCalc` produces is diffed against the JavaScript reference
calculator; datacrons cannot be, because no reference implements them and the
stats service does not calculate them either.

If a test here fails, the implementation is what changes -- not the fixture.
The fixture is a measurement. It has already overturned the implementation
twice: percentages resolve against base and gear, not base, gear and mods; and
the two-decimal percentage the card shows is what gets applied, summed before
it is rounded.

Unlike the parity suite this runs by default and needs nothing external -- the
readings are committed. Putting it behind a marker would leave the feature's
only correctness guard skipped in normal runs.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from swgoh_comlink import StatCalc

_RESOURCES = Path(__file__).resolve().parent.parent / "resources"
_GAME_DATA_FILE = _RESOURCES / "gameData.json"
_GOLDEN_FILE = _RESOURCES / "datacron-golden.json"

# Loaded at import so every asserted reading becomes its own test case, named
# for the datacron it came from.
_GOLDEN: dict[str, Any] = json.loads(_GOLDEN_FILE.read_text())
_ASSERTED: list[dict[str, Any]] = [r for r in _GOLDEN["readings"] if r["asserted"]]


@pytest.fixture(scope="module")
def golden() -> dict[str, Any]:
    return json.loads(_GOLDEN_FILE.read_text())


@pytest.fixture(scope="module")
def calc() -> StatCalc:
    return StatCalc(game_data=json.loads(_GAME_DATA_FILE.read_text())["data"])


def _asserted(golden: dict[str, Any]) -> list[dict[str, Any]]:
    return [r for r in golden["readings"] if r["asserted"]]


def _observed(calc: StatCalc, golden: dict[str, Any], datacron_id: str | None) -> dict[str, float]:
    """Run the hand-authored unit and return `final + datacron` per stat."""
    payload = {
        "rosterUnit": [copy.deepcopy(golden["unit"])],
        "datacron": copy.deepcopy(golden["datacrons"]),
    }
    result = calc.calc_player_stats(payload, datacron_id=datacron_id)
    assert isinstance(result, dict)
    stats = result["rosterUnit"][0]["stats"]
    combined = dict(stats["final"])
    for name, value in stats.get("datacron", {}).items():
        combined[name] = combined.get(name, 0) + value
    return combined


def _as_displayed(name: str, value: float, percent_stats: dict[str, int]) -> float:
    """Express a computed stat the way the game printed it.

    A reading cannot be checked more precisely than it was displayed.
    """
    if name in percent_stats:
        return round(value * 100, percent_stats[name])
    return round(value)


@pytest.mark.parametrize(
    "reading",
    _ASSERTED,
    ids=[r["datacron"] or "no-datacron" for r in _ASSERTED],
)
def test_matches_values_read_from_the_game(calc: StatCalc, golden: dict[str, Any], reading: dict[str, Any]) -> None:
    combined = _observed(calc, golden, reading["datacron"])
    percent_stats = golden["percent_stats"]

    for name, expected in reading["stats"].items():
        assert name in combined, f"{name} missing from calculated output"
        assert _as_displayed(name, combined[name], percent_stats) == expected, (
            f"datacron={reading['datacron']} stat={name}: "
            f"calculated {combined[name]!r} does not match the value read in game. "
            f"Fix the implementation, not this fixture."
        )


def test_every_asserted_reading_is_exercised(golden: dict[str, Any]) -> None:
    """Guards the parametrisation above from silently covering fewer readings."""
    assert len(_asserted(golden)) == 3


def test_unasserted_readings_carry_their_reason(golden: dict[str, Any]) -> None:
    """A reading may be excluded, but never silently."""
    for reading in golden["readings"]:
        if not reading["asserted"]:
            assert reading.get("note"), "an unasserted reading must say why"


def test_fixture_warns_against_regeneration(golden: dict[str, Any]) -> None:
    """The warning is the fixture's only defence against being 'refreshed'."""
    assert "DO NOT REGENERATE" in golden["_warning"]


def test_the_unit_carries_no_account_identifying_fields(golden: dict[str, Any]) -> None:
    """The unit is a hand-authored equivalent, not a copied roster entry."""
    unit = golden["unit"]
    assert not {"id", "currentXp", "unitStat", "promotionRecipeReference"} & set(unit)
    for mod in unit["equippedStatMod"]:
        assert "id" not in mod
