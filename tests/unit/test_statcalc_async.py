"""Tests for StatCalcAsync and GameDataBuilder/Async."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock

import pytest

from swgoh_comlink.StatCalc.data_builder import builder, builder_async

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


# ── GameDataBuilder / GameDataBuilderAsync ─────────────────────────────
#
# The builders only fetch raw Comlink data and hand it to the shared transform, which
# test_builder_base.py covers in depth. These tests pin that wiring: the exact fetch
# arguments, and that the transform's output is returned for a raw payload that
# actually produces data (gameData.json is already-built StatCalc data, not a raw
# Comlink response, so feeding it in yields six empty sections).

_RAW_GAME_DATA = {
    "equipment": [
        {"id": "gear001", "equipmentStat": {"stat": [{"unitStatId": 1, "unscaledDecimalValue": 100}]}},
    ],
}


@pytest.mark.parametrize(
    ("module", "builder_class", "client_mock"),
    [
        pytest.param(builder, builder.GameDataBuilder, MagicMock, id="sync"),
        pytest.param(builder_async, builder_async.GameDataBuilderAsync, AsyncMock, id="async"),
    ],
)
async def test_builder_fetches_required_items_and_transforms_them(
    module: ModuleType, builder_class: type, client_mock: type
) -> None:
    client = client_mock()
    client.get_game_data.return_value = _RAW_GAME_DATA

    result = builder_class(client).build()
    if inspect.isawaitable(result):
        result = await result

    client.get_game_data.assert_called_once_with(items=str(int(module._REQUIRED_ITEMS)), include_pve_units=False)
    assert result == {
        "unitData": {},
        "gearData": {"gear001": {"stats": {"1": 100}}},
        "modSetData": {},
        "crTables": {},
        "gpTables": {},
        "relicData": {},
    }


# ── StatCalcAsync GitHub fetch error handling ──────────────────────────


class TestStatCalcAsyncFetchErrors:
    @pytest.mark.asyncio
    async def test_network_error_raises_runtime(self, monkeypatch):
        import httpx

        from swgoh_comlink.StatCalc.calculator_async import StatCalcAsync

        async def mock_get(self, url, **kwargs):
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        with pytest.raises(RuntimeError, match="Unable to retrieve game data"):
            await StatCalcAsync._async_fetch_game_data_from_github()

    @pytest.mark.asyncio
    async def test_http_error_raises_runtime(self, monkeypatch):
        import httpx

        from swgoh_comlink.StatCalc.calculator_async import StatCalcAsync

        async def mock_get(self, url, **kwargs):
            response = httpx.Response(500, request=httpx.Request("GET", url))
            return response

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        with pytest.raises(RuntimeError, match="Unable to retrieve game data"):
            await StatCalcAsync._async_fetch_game_data_from_github()

    @pytest.mark.asyncio
    async def test_timeout_raises_runtime(self, monkeypatch):
        import httpx

        from swgoh_comlink.StatCalc.calculator_async import StatCalcAsync

        async def mock_get(self, url, **kwargs):
            raise httpx.ReadTimeout("Timeout")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
        with pytest.raises(RuntimeError, match="Unable to retrieve game data"):
            await StatCalcAsync._async_fetch_game_data_from_github()
