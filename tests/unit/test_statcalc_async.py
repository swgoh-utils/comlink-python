"""Tests for StatCalcAsync and GameDataBuilder/Async."""

from __future__ import annotations

import asyncio
import copy
import gc
import inspect
import json
import os
import time
from pathlib import Path
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
    async def fetch(url: str | None = None, expected_sha256: str | None = None) -> dict[str, Any]:
        return game_data

    monkeypatch.setattr(StatCalcAsync, "_async_fetch_game_data_from_github", staticmethod(fetch))

    calc = await StatCalcAsync.create()

    assert isinstance(calc, StatCalcAsync)
    assert calc._unit_data is game_data["unitData"]


# ── StatCalcAsync off-loop calculation ─────────────────────────────────

_PLAYER_FILE = Path(__file__).resolve().parent.parent / "resources" / "example-player.json"

# Ticks requested every 10 ms may run this late while acalc_* computes. A worker thread gives up
# the GIL every sys.getswitchinterval() (5 ms), so a tick normally lands well inside 50 ms. Shared
# CI runners stall for reasons unrelated to the code, so the bound is relaxed there.
_TICK_INTERVAL = 0.01
_MAX_TICK_LATENESS = 0.25 if os.environ.get("CI") else 0.05


@pytest.fixture(scope="module")
def player() -> dict[str, Any]:
    """The 386-unit fixture player. Do not mutate; deep-copy it first."""
    return json.loads(_PLAYER_FILE.read_text())


@pytest.fixture(scope="module")
def calc(game_data: dict[str, Any]) -> StatCalcAsync:
    return StatCalcAsync(game_data=game_data)


def _def_id(unit: dict[str, Any]) -> str:
    return unit["definitionId"].split(":")[0]


async def test_acalc_player_stats_matches_sync(calc: StatCalcAsync, player: dict[str, Any]) -> None:
    expected = calc.calc_player_stats(copy.deepcopy(player))

    assert await calc.acalc_player_stats(copy.deepcopy(player)) == expected


async def test_acalc_player_stats_accepts_a_list(calc: StatCalcAsync, player: dict[str, Any]) -> None:
    players = [copy.deepcopy(player), copy.deepcopy(player)]

    result = await calc.acalc_player_stats(players)

    assert result is players
    assert result == [calc.calc_player_stats(copy.deepcopy(player))] * 2


async def test_acalc_roster_stats_matches_sync(calc: StatCalcAsync, player: dict[str, Any]) -> None:
    expected = calc.calc_roster_stats(copy.deepcopy(player["rosterUnit"]))

    assert await calc.acalc_roster_stats(copy.deepcopy(player["rosterUnit"])) == expected


async def test_acalc_char_stats_matches_sync(
    calc: StatCalcAsync, player: dict[str, Any], game_data: dict[str, Any]
) -> None:
    unit = next(u for u in player["rosterUnit"] if game_data["unitData"][_def_id(u)]["combatType"] == 1)
    expected = calc.calc_char_stats(copy.deepcopy(unit))

    assert "stats" in expected
    assert await calc.acalc_char_stats(copy.deepcopy(unit)) == expected


async def test_acalc_ship_stats_matches_sync(
    calc: StatCalcAsync, player: dict[str, Any], game_data: dict[str, Any]
) -> None:
    roster = calc.calc_player_stats(copy.deepcopy(player))["rosterUnit"]
    by_id = {_def_id(u): u for u in roster}
    ship, crew = next(
        (u, [by_id[c] for c in meta["crew"]])
        for u in roster
        if (meta := game_data["unitData"][_def_id(u)])["combatType"] == 2
        and meta["crew"]
        and all(c in by_id for c in meta["crew"])
    )
    expected = calc.calc_ship_stats(copy.deepcopy(ship), copy.deepcopy(crew))

    assert "stats" in expected
    assert await calc.acalc_ship_stats(copy.deepcopy(ship), copy.deepcopy(crew)) == expected


async def test_acalc_errors_propagate(calc: StatCalcAsync) -> None:
    not_a_player: Any = "not a player"

    with pytest.raises(TypeError, match="Expected a list or dict"):
        await calc.acalc_player_stats(not_a_player)


async def test_calculation_leaves_game_data_unchanged(calc: StatCalcAsync, player: dict[str, Any]) -> None:
    """acalc_* share the game data tables across threads, which is safe only while they are read-only."""
    tables = [calc._unit_data, calc._gear_data, calc._mod_set_data, calc._cr_tables, calc._gp_tables, calc._relic_data]
    snapshot = json.dumps(tables, sort_keys=True)

    await calc.acalc_player_stats(copy.deepcopy(player))

    assert json.dumps(tables, sort_keys=True) == snapshot


async def test_acalc_player_stats_keeps_the_event_loop_responsive(calc: StatCalcAsync, player: dict[str, Any]) -> None:
    # Several rosters so the calculation spans many ticks (tens of ms per roster).
    players = [copy.deepcopy(player) for _ in range(6)]
    lateness: list[float] = []
    stop = asyncio.Event()

    async def ticker() -> None:
        while not stop.is_set():
            due = time.perf_counter() + _TICK_INTERVAL
            await asyncio.sleep(_TICK_INTERVAL)
            lateness.append(time.perf_counter() - due)

    # A full GC pass holds the GIL; over the whole test session's heap it can stall the loop for
    # tens of ms. That is not what this test measures, so keep existing objects out of collection.
    gc.collect()
    gc.freeze()
    task = asyncio.create_task(ticker())
    await asyncio.sleep(0)  # let the ticker start before the calculation
    try:
        await calc.acalc_player_stats(players)
    finally:
        stop.set()
        await task
        gc.unfreeze()

    assert any("stats" in u for u in players[-1]["rosterUnit"])
    assert len(lateness) >= 3, "calculation finished before the ticker could measure anything"
    assert max(lateness) < _MAX_TICK_LATENESS, f"tick late by {max(lateness) * 1000:.1f} ms"


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
