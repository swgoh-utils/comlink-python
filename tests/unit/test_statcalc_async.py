"""Tests for StatCalcAsync and GameDataBuilder/Async."""

from __future__ import annotations

import inspect
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink.StatCalc.calculator import StatCalc
from swgoh_comlink.StatCalc.calculator_async import StatCalcAsync
from swgoh_comlink.StatCalc.data_builder import builder, builder_async

# ── StatCalcAsync ──────────────────────────────────────────────────────


async def test_create_with_game_data(game_data):
    calc = await StatCalcAsync.create(game_data=game_data)

    assert isinstance(calc, StatCalc)
    assert calc._unit_data is game_data["unitData"]
    assert calc.calc_char_gp({"defId": "BOSSK", "rarity": 7, "level": 85, "gear": 13}) > 0


async def test_create_without_game_data_fetches_it(monkeypatch, game_data):
    async def fetch() -> dict[str, Any]:
        return game_data

    monkeypatch.setattr(StatCalcAsync, "_async_fetch_game_data_from_github", staticmethod(fetch))

    calc = await StatCalcAsync.create()

    assert isinstance(calc, StatCalcAsync)
    assert calc._unit_data is game_data["unitData"]


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


# ── StatCalcAsync GitHub fetch ─────────────────────────────────────────

_GITHUB_URL = StatCalcAsync._DEFAULT_GAMEDATA_URL


async def test_fetch_unwraps_the_data_key(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=_GITHUB_URL, json={"data": {"unitData": {"X": {}}}})

    assert await StatCalcAsync._async_fetch_game_data_from_github() == {"unitData": {"X": {}}}


async def test_fetch_rejects_an_unsupported_payload(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=_GITHUB_URL, json={"bad": 1})

    with pytest.raises(RuntimeError, match="Unsupported"):
        await StatCalcAsync._async_fetch_game_data_from_github()


@pytest.mark.parametrize(
    ("mock_response", "cause"),
    [
        pytest.param(lambda m: m.add_exception(httpx.ConnectError("refused")), httpx.ConnectError, id="connect"),
        pytest.param(lambda m: m.add_exception(httpx.ReadTimeout("timeout")), httpx.ReadTimeout, id="timeout"),
        pytest.param(lambda m: m.add_response(status_code=500), httpx.HTTPStatusError, id="http-500"),
        pytest.param(lambda m: m.add_response(text="not json"), ValueError, id="not-json"),
    ],
)
async def test_fetch_failures_raise_runtime_error(httpx_mock: HTTPXMock, mock_response, cause: type[Exception]):
    mock_response(httpx_mock)

    with pytest.raises(RuntimeError, match="Unable to retrieve game data") as excinfo:
        await StatCalcAsync._async_fetch_game_data_from_github()
    assert isinstance(excinfo.value.__cause__, cause)
