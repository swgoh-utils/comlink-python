"""Integration tests for the synchronous SwgohComlink client."""

import pytest

from swgoh_comlink import SwgohComlink
from swgoh_comlink.helpers import DataItems

from .conftest import COMLINK_URL, TEST_ALLYCODE

pytestmark = pytest.mark.integration


def test_get_enums(comlink):
    """GET /enums returns game enum definitions."""
    result = comlink.get_enums()
    assert isinstance(result, dict)
    assert "CombatType" in result


def test_get_game_metadata(comlink):
    """POST /metadata returns game metadata with version info."""
    result = comlink.get_game_metadata()
    assert isinstance(result, dict)
    assert "latestGamedataVersion" in result


def test_get_latest_game_data_version(comlink):
    """Helper returns dict with 'game' and 'language' version strings."""
    result = comlink.get_latest_game_data_version()
    assert isinstance(result, dict)
    assert "game" in result
    assert "language" in result
    assert isinstance(result["game"], str)
    assert isinstance(result["language"], str)


def test_get_events(comlink):
    """POST /getEvents returns event data."""
    result = comlink.get_events()
    assert isinstance(result, dict)
    assert "gameEvent" in result
    assert isinstance(result["gameEvent"], list)


def test_get_player(comlink):
    """POST /player returns full player profile."""
    result = comlink.get_player(allycode=TEST_ALLYCODE)
    assert isinstance(result, dict)
    assert "name" in result
    assert "allyCode" in result
    assert "rosterUnit" in result
    assert isinstance(result["rosterUnit"], list)
    assert len(result["rosterUnit"]) > 0


def test_get_player_arena(comlink):
    """POST /playerArena returns arena profile."""
    result = comlink.get_player_arena(allycode=TEST_ALLYCODE)
    assert isinstance(result, dict)
    assert "name" in result
    assert "pvpProfile" in result


def test_get_guilds_by_name(comlink):
    """POST /getGuilds returns guild search results."""
    result = comlink.get_guilds_by_name(name="guild", count=1)
    assert isinstance(result, dict)
    assert "guild" in result
    assert isinstance(result["guild"], list)
    assert len(result["guild"]) > 0


def test_get_game_data_filtered(comlink):
    """POST /data with DataItems filter returns game data subset."""
    result = comlink.get_game_data(items=DataItems.UNITS)
    assert isinstance(result, dict)
    assert len(result) > 0


def test_context_manager():
    """Client works correctly as a context manager."""
    with SwgohComlink(url=COMLINK_URL) as client:
        result = client.get_enums()
        assert isinstance(result, dict)
