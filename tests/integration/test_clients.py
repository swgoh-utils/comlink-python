"""Integration tests for SwgohComlink and SwgohComlinkAsync against a live Comlink service.

Every test runs once per client through the ``comlink`` and ``call`` fixtures in conftest.py.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync

from .conftest import COMLINK_URL, TEST_ALLYCODE, Client

pytestmark = pytest.mark.integration

Call = Callable[..., Awaitable[Any]]


async def test_get_enums(comlink: Client, call: Call):
    """GET /enums returns game enum definitions."""
    result = await call(comlink, "get_enums")
    assert isinstance(result, dict)
    assert "CombatType" in result


async def test_get_game_metadata(comlink: Client, call: Call):
    """POST /metadata returns game metadata with a populated version string."""
    result = await call(comlink, "get_game_metadata")
    assert isinstance(result, dict)
    assert result.get("latestGamedataVersion"), "version must be present and non-empty"


async def test_get_latest_game_data_version(comlink: Client, call: Call):
    """Helper returns dict with non-empty 'game' and 'language' version strings.

    Asserting the type alone would pass on empty strings, which is the shape a
    broken version lookup returns.
    """
    result = await call(comlink, "get_latest_game_data_version")
    assert isinstance(result, dict)
    assert isinstance(result["game"], str) and result["game"], "game version must be non-empty"
    assert isinstance(result["language"], str) and result["language"], "language version must be non-empty"


async def test_get_events(comlink: Client, call: Call):
    """POST /getEvents returns a populated event list."""
    result = await call(comlink, "get_events")
    assert isinstance(result, dict)
    assert isinstance(result["gameEvent"], list)
    assert result["gameEvent"], "a live Comlink instance always has scheduled events"


async def test_get_player(comlink: Client, call: Call):
    """POST /player returns full player profile."""
    result = await call(comlink, "get_player", allycode=TEST_ALLYCODE)
    assert isinstance(result, dict)
    assert "name" in result
    assert "allyCode" in result
    assert "rosterUnit" in result
    assert isinstance(result["rosterUnit"], list)
    assert len(result["rosterUnit"]) > 0


async def test_get_player_arena(comlink: Client, call: Call):
    """POST /playerArena returns an arena profile with populated squads."""
    result = await call(comlink, "get_player_arena", allycode=TEST_ALLYCODE)
    assert isinstance(result, dict)
    assert result["name"]
    assert result["pvpProfile"], "arena profile must list at least one arena tab"
    assert any(entry.get("squad") for entry in result["pvpProfile"]), "full response includes squad rosters"


async def test_get_player_arena_details_only(comlink: Client, call: Call):
    """player_details_only=True keeps the arena tabs but drops the squad rosters."""
    result = await call(comlink, "get_player_arena", allycode=TEST_ALLYCODE, player_details_only=True)
    assert result["pvpProfile"], "arena tabs are still returned"
    assert all(entry.get("squad") is None for entry in result["pvpProfile"]), "squads must be omitted"


async def test_get_guilds_by_name(comlink: Client, call: Call):
    """POST /getGuilds returns guild search results."""
    result = await call(comlink, "get_guilds_by_name", name="guild", count=1)
    assert isinstance(result, dict)
    assert "guild" in result
    assert isinstance(result["guild"], list)
    assert len(result["guild"]) > 0


async def test_get_game_data_filtered(comlink: Client, call: Call):
    """POST /data with a single items collection populates that collection and no other.

    /data always returns the same full set of collection keys regardless of what was
    requested — the ones not asked for come back empty. So asserting on len(result)
    would pass even if the filter matched nothing; assert on which keys are populated.

    The value comes from the server's own GameDataItemsEnum rather than the client-side
    DataItems constants, which are a hand-maintained copy that can drift. A single
    collection is used rather than a Segment aggregate: it isolates the filter exactly,
    and it returns in well under a second where an aggregate takes ~10s and has been
    seen to fail upstream against a cold service container.
    """
    equipment_only = (await call(comlink, "get_enums"))["GameDataItemsEnum"]["EquipmentDefinitions"]
    result = await call(comlink, "get_game_data", items=equipment_only)
    assert isinstance(result, dict)
    assert result["equipment"], "the requested collection should be populated"
    assert not result["units"], "every unrequested collection should be empty"


@pytest.mark.parametrize("client_type", [SwgohComlink, SwgohComlinkAsync], ids=["sync", "async"])
async def test_context_manager_closes_the_http_client(client_type: type[Client]):
    """Exiting the context manager closes the underlying HTTP client.

    Closure is the whole point of the context manager, so assert on it — a test
    that only calls an endpoint inside the block would pass without it.
    """
    if client_type is SwgohComlinkAsync:
        async with SwgohComlinkAsync(url=COMLINK_URL) as client:
            inner = client.client
            assert not inner.is_closed
            assert "CombatType" in await client.get_enums()
    else:
        with SwgohComlink(url=COMLINK_URL) as client:
            inner = client.client
            assert not inner.is_closed
            assert "CombatType" in client.get_enums()
    assert inner.is_closed, "exiting the context manager must close the HTTP client"
