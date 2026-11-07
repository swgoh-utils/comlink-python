"""StatCalc table lookups and input copying (REF-2).

The calculator normalises game data tables to ``str`` keys once in ``set_game_data`` and
copies caller units only as deeply as it needs. These tests pin the results and prove the
caller's game data and units are never modified.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from swgoh_comlink import StatCalc

_PLAYER_FILE = Path(__file__).resolve().parent.parent / "resources" / "example-player.json"
_RESULT_KEYS = ("stats", "gp")


@pytest.fixture(scope="module")
def player() -> dict[str, Any]:
    return json.loads(_PLAYER_FILE.read_text())


@pytest.fixture(scope="module")
def calc(game_data: dict[str, Any]) -> StatCalc:
    return StatCalc(game_data=game_data)


def _int_keyed(value: Any) -> Any:
    """Copy of *value* with every digit-only dict key turned into an ``int``."""
    if isinstance(value, dict):
        return {int(k) if isinstance(k, str) and k.isdigit() else k: _int_keyed(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_int_keyed(v) for v in value]
    return value


def _def_id(unit: dict[str, Any]) -> str:
    return unit["definitionId"].split(":")[0]


def _normalized(raw: dict[str, Any]) -> dict[str, Any]:
    """The normalized (``defId``) form of a raw Comlink roster unit."""
    return {
        "defId": _def_id(raw),
        "rarity": raw["currentRarity"],
        "level": raw["currentLevel"],
        "gear": raw.get("currentTier"),
        "equipped": copy.deepcopy(raw.get("equipment", [])),
        "relic": copy.deepcopy(raw.get("relic")),
        "skills": [{"id": s["id"], "tier": s["tier"] + 2} for s in raw.get("skill", [])],
        "purchasedAbilityId": list(raw.get("purchasedAbilityId", [])),
        "equippedStatMod": copy.deepcopy(raw.get("equippedStatMod")),
    }


def _without_results(unit: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in unit.items() if k not in _RESULT_KEYS}


def _crewed_ship(game_data: dict[str, Any], player: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    roster = {_def_id(u): u for u in player["rosterUnit"]}
    for def_id, unit in roster.items():
        meta = game_data["unitData"].get(def_id, {})
        if meta.get("combatType") == 2 and meta.get("crew") and all(c in roster for c in meta["crew"]):
            return copy.deepcopy(unit), [copy.deepcopy(roster[c]) for c in meta["crew"]]
    raise AssertionError("fixture roster has no fully crewed ship")


class TestGameDataKeys:
    def test_int_keyed_tables_are_normalised_to_str_keys(self, game_data):
        calc = StatCalc(game_data=_int_keyed(game_data))
        assert calc._gp_tables is not None
        assert calc._unit_data is not None
        assert all(isinstance(k, str) for k in calc._gp_tables["unitLevelGP"])
        assert all(isinstance(k, str) for k in calc._gp_tables["gearPieceGP"]["1"])
        assert all(isinstance(k, str) for k in calc._unit_data["CINTA"]["growthModifiers"]["7"])

    def test_int_keyed_game_data_gives_identical_results(self, calc, game_data, player):
        expected = calc.calc_player_stats(copy.deepcopy(player))
        actual = StatCalc(game_data=_int_keyed(game_data)).calc_player_stats(copy.deepcopy(player))
        assert actual == expected

    def test_caller_game_data_is_not_modified(self, game_data, player):
        int_keyed = _int_keyed(game_data)
        snapshot = copy.deepcopy(int_keyed)
        StatCalc(game_data=int_keyed).calc_player_stats(copy.deepcopy(player))
        assert int_keyed == snapshot
        assert isinstance(next(iter(int_keyed["gpTables"]["unitLevelGP"])), int)

    def test_str_keyed_tables_are_used_without_copying(self, calc, game_data):
        # JSON game data already has str keys, so nothing is duplicated in memory.
        assert calc._unit_data is game_data["unitData"]
        assert calc._gp_tables is game_data["gpTables"]


class TestCallerUnitsUnchanged:
    def test_calc_char_stats_only_adds_results(self, calc, player):
        char = _normalized(player["rosterUnit"][0])
        snapshot = copy.deepcopy(char)
        calc.calc_char_stats(char)
        assert _without_results(char) == snapshot
        assert set(char) - set(snapshot) == set(_RESULT_KEYS)

    def test_calc_char_gp_leaves_unit_unchanged(self, calc, player):
        char = _normalized(player["rosterUnit"][0])
        char.pop("equipped")  # setdefault() on the copy must not reach the caller
        snapshot = copy.deepcopy(char)
        calc.calc_char_gp(char)
        assert char == snapshot

    def test_calc_ship_stats_only_adds_results(self, calc, game_data, player):
        raw_ship, raw_crew = _crewed_ship(game_data, player)
        crew = [_normalized(c) for c in raw_crew]
        for member, raw in zip(crew, raw_crew, strict=True):
            member["gp"] = calc.calc_char_gp(raw)
        ship = _normalized(raw_ship)
        ship_snapshot, crew_snapshot = copy.deepcopy(ship), copy.deepcopy(crew)
        calc.calc_ship_stats(ship, crew)
        assert _without_results(ship) == ship_snapshot
        assert crew == crew_snapshot

    def test_calc_ship_gp_leaves_ship_and_crew_unchanged(self, calc, game_data, player):
        raw_ship, raw_crew = _crewed_ship(game_data, player)
        ship, crew = _normalized(raw_ship), [_normalized(c) for c in raw_crew]
        ship_snapshot, crew_snapshot = copy.deepcopy(ship), copy.deepcopy(crew)
        calc.calc_ship_gp(ship, crew)
        assert (ship, crew) == (ship_snapshot, crew_snapshot)
