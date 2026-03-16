"""Tests for StatCalcAsync and GameDataBuilder/Async."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

_GAME_DATA_PATH = Path(__file__).parent.parent / "resources" / "gameData.json"


@pytest.fixture(scope="module")
def game_data() -> dict:
    return json.loads(_GAME_DATA_PATH.read_text())["data"]


# ── StatCalcAsync ──────────────────────────────────────────────────────


class TestStatCalcAsyncInit:
    def test_init_with_game_data(self, game_data):
        from swgoh_comlink.StatCalc.calculator_async import StatCalcAsync

        calc = StatCalcAsync(game_data=game_data)
        assert calc._unit_data is not None
        assert len(calc._unit_data) > 0

    def test_inherits_calc_methods(self, game_data):
        from swgoh_comlink.StatCalc.calculator import StatCalc
        from swgoh_comlink.StatCalc.calculator_async import StatCalcAsync

        calc = StatCalcAsync(game_data=game_data)
        # Verify it inherits from StatCalc
        assert isinstance(calc, StatCalc)
        assert hasattr(calc, "calc_char_stats")
        assert hasattr(calc, "calc_ship_stats")
        assert hasattr(calc, "calc_player_stats")


class TestStatCalcAsyncCreate:
    @pytest.mark.asyncio
    async def test_create_with_game_data(self, game_data):
        from swgoh_comlink.StatCalc.calculator_async import StatCalcAsync

        calc = await StatCalcAsync.create(game_data=game_data)
        assert calc._unit_data is not None

    @pytest.mark.asyncio
    async def test_create_without_game_data_fetches(self, monkeypatch, game_data):
        from swgoh_comlink.StatCalc.calculator_async import StatCalcAsync

        async def mock_fetch():
            return game_data

        monkeypatch.setattr(StatCalcAsync, "_async_fetch_game_data_from_github", staticmethod(mock_fetch))
        calc = await StatCalcAsync.create()
        assert calc._unit_data is not None


# ── GameDataBuilder (sync) ─────────────────────────────────────────────


class TestGameDataBuilder:
    def test_build_calls_get_game_data(self):
        from swgoh_comlink.StatCalc.data_builder.builder import GameDataBuilder

        raw_data = json.loads(_GAME_DATA_PATH.read_text())
        mock_client = MagicMock()
        mock_client.get_game_data.return_value = raw_data

        builder = GameDataBuilder(mock_client)
        result = builder.build()

        mock_client.get_game_data.assert_called_once()
        assert "unitData" in result
        assert "gearData" in result
        assert "modSetData" in result
        assert "crTables" in result
        assert "gpTables" in result
        assert "relicData" in result

    def test_build_output_has_expected_keys(self):
        from swgoh_comlink.StatCalc.data_builder.builder import GameDataBuilder

        raw_data = json.loads(_GAME_DATA_PATH.read_text())
        mock_client = MagicMock()
        mock_client.get_game_data.return_value = raw_data

        result = GameDataBuilder(mock_client).build()
        assert isinstance(result["unitData"], dict)
        assert isinstance(result["gearData"], dict)
        assert isinstance(result["modSetData"], dict)


# ── GameDataBuilderAsync ───────────────────────────────────────────────


class TestGameDataBuilderAsync:
    @pytest.mark.asyncio
    async def test_build_calls_get_game_data(self):
        from swgoh_comlink.StatCalc.data_builder.builder_async import GameDataBuilderAsync

        raw_data = json.loads(_GAME_DATA_PATH.read_text())
        mock_client = AsyncMock()
        mock_client.get_game_data.return_value = raw_data

        builder = GameDataBuilderAsync(mock_client)
        result = await builder.build()

        mock_client.get_game_data.assert_called_once()
        assert "unitData" in result
        assert "gearData" in result

    @pytest.mark.asyncio
    async def test_build_output_matches_sync(self):
        from swgoh_comlink.StatCalc.data_builder.builder import GameDataBuilder
        from swgoh_comlink.StatCalc.data_builder.builder_async import GameDataBuilderAsync

        raw_data = json.loads(_GAME_DATA_PATH.read_text())

        sync_client = MagicMock()
        sync_client.get_game_data.return_value = raw_data
        sync_result = GameDataBuilder(sync_client).build()

        async_client = AsyncMock()
        async_client.get_game_data.return_value = raw_data
        async_result = await GameDataBuilderAsync(async_client).build()

        assert sync_result.keys() == async_result.keys()
        assert len(sync_result["unitData"]) == len(async_result["unitData"])
