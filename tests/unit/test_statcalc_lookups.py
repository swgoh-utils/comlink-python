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
