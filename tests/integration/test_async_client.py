"""Integration tests for the asynchronous SwgohComlinkAsync client."""

import pytest

from swgoh_comlink import SwgohComlinkAsync
from swgoh_comlink.helpers import DataItems

from .conftest import COMLINK_URL, TEST_ALLYCODE

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_get_enums(async_comlink):
    """GET /enums returns game enum definitions."""
    result = await async_comlink.get_enums()
    assert isinstance(result, dict)
    assert "CombatType" in result


async def test_get_game_metadata(async_comlink):
    """POST /metadata returns game metadata with version info."""
    result = await async_comlink.get_game_metadata()
    assert isinstance(result, dict)
    assert "latestGamedataVersion" in result


async def test_get_latest_game_data_version(async_comlink):
    """Helper returns dict with 'game' and 'language' version strings."""
    result = await async_comlink.get_latest_game_data_version()
    assert isinstance(result, dict)
    assert "game" in result
    assert "language" in result
    assert isinstance(result["game"], str)
    assert isinstance(result["language"], str)


async def test_get_events(async_comlink):
    """POST /getEvents returns event data."""
    result = await async_comlink.get_events()
    assert isinstance(result, dict)
    assert "gameEvent" in result
    assert isinstance(result["gameEvent"], list)


async def test_get_player(async_comlink):
    """POST /player returns full player profile."""
    result = await async_comlink.get_player(allycode=TEST_ALLYCODE)
    assert isinstance(result, dict)
    assert "name" in result
    assert "allyCode" in result
    assert "rosterUnit" in result
    assert isinstance(result["rosterUnit"], list)
    assert len(result["rosterUnit"]) > 0


async def test_get_player_arena(async_comlink):
    """POST /playerArena returns arena profile."""
    result = await async_comlink.get_player_arena(allycode=TEST_ALLYCODE)
    assert isinstance(result, dict)
    assert "name" in result
    assert "pvpProfile" in result


async def test_get_guilds_by_name(async_comlink):
    """POST /getGuilds returns guild search results."""
    result = await async_comlink.get_guilds_by_name(name="guild", count=1)
    assert isinstance(result, dict)
    assert "guild" in result
    assert isinstance(result["guild"], list)
    assert len(result["guild"]) > 0


async def test_get_game_data_filtered(async_comlink):
    """POST /data with DataItems filter returns game data subset."""
    result = await async_comlink.get_game_data(items=DataItems.UNITS)
    assert isinstance(result, dict)
    assert len(result) > 0


async def test_async_context_manager():
    """Async client works correctly as an async context manager."""
    async with SwgohComlinkAsync(url=COMLINK_URL) as client:
        result = await client.get_enums()
        assert isinstance(result, dict)
