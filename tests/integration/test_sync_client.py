"""Integration tests for the synchronous SwgohComlink client."""

import pytest

from swgoh_comlink import SwgohComlink

from .conftest import COMLINK_URL, TEST_ALLYCODE

pytestmark = pytest.mark.integration


def test_get_enums(comlink):
    """GET /enums returns game enum definitions."""
    result = comlink.get_enums()
    assert isinstance(result, dict)
    assert "CombatType" in result


def test_get_game_metadata(comlink):
    """POST /metadata returns game metadata with a populated version string."""
    result = comlink.get_game_metadata()
    assert isinstance(result, dict)
    assert result.get("latestGamedataVersion"), "version must be present and non-empty"


def test_get_latest_game_data_version(comlink):
    """Helper returns dict with non-empty 'game' and 'language' version strings.

    Asserting the type alone would pass on empty strings, which is the shape a
    broken version lookup returns.
    """
    result = comlink.get_latest_game_data_version()
    assert isinstance(result, dict)
    assert isinstance(result["game"], str) and result["game"], "game version must be non-empty"
    assert isinstance(result["language"], str) and result["language"], "language version must be non-empty"


def test_get_events(comlink):
    """POST /getEvents returns a populated event list."""
    result = comlink.get_events()
    assert isinstance(result, dict)
    assert isinstance(result["gameEvent"], list)
    assert result["gameEvent"], "a live Comlink instance always has scheduled events"


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
    """POST /playerArena returns an arena profile with populated squads."""
    result = comlink.get_player_arena(allycode=TEST_ALLYCODE)
    assert isinstance(result, dict)
    assert result["name"]
    assert result["pvpProfile"], "arena profile must list at least one arena tab"
    assert any(entry.get("squad") for entry in result["pvpProfile"]), "full response includes squad rosters"


def test_get_player_arena_details_only(comlink):
    """player_details_only=True keeps the arena tabs but drops the squad rosters."""
    result = comlink.get_player_arena(allycode=TEST_ALLYCODE, player_details_only=True)
    assert result["pvpProfile"], "arena tabs are still returned"
    assert all(entry.get("squad") is None for entry in result["pvpProfile"]), "squads must be omitted"


def test_get_guilds_by_name(comlink):
    """POST /getGuilds returns guild search results."""
    result = comlink.get_guilds_by_name(name="guild", count=1)
    assert isinstance(result, dict)
    assert "guild" in result
    assert isinstance(result["guild"], list)
    assert len(result["guild"]) > 0


def test_get_game_data_filtered(comlink):
    """POST /data with the Segment1 items value populates only the Segment1 collections.

    /data always returns the same full set of collection keys regardless of what was
    requested — the ones not asked for come back empty. So asserting on len(result)
    would pass even if the filter matched nothing; assert on which keys are populated.

    The items value is read from the server's own GameDataItemsEnum rather than from
    the client-side DataItems constants. Segment values are aggregate bitmasks, so they
    shift whenever a collection is added to a segment, and a stale local copy is
    rejected outright (HTTP 400) by newer Comlink builds.
    """
    segment1 = comlink.get_enums()["GameDataItemsEnum"]["Segment1"]
    result = comlink.get_game_data(items=segment1)
    assert isinstance(result, dict)
    assert result["equipment"], "requested SEGMENT1 collection should be populated"
    assert not result["units"], "unrequested SEGMENT3 collection should be empty"


def test_context_manager():
    """Exiting the context manager closes the underlying HTTP client.

    Closure is the whole point of the context manager, so assert on it — a test
    that only calls an endpoint inside the block would pass without it.
    """
    with SwgohComlink(url=COMLINK_URL) as client:
        inner = client.client
        assert not inner.is_closed
        result = client.get_enums()
        assert "CombatType" in result
    assert inner.is_closed, "exiting the context manager must close the HTTP client"
