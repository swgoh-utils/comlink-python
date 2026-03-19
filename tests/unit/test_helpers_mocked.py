"""Tests for helper functions that require mocked HTTP calls."""

from __future__ import annotations

import pytest
from unittest.mock import patch
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync
from swgoh_comlink.exceptions import SwgohComlinkValueError

# ── Shared fixtures ─────────────────────────────────────────────────────

_GAC_EVENT = {
    "id": "CHAMPIONSHIPS_GRAND_ARENA_GA2_EVENT_SEASON_55",
    "type": 10,
    "instance": [{"id": "SEASON_55_INSTANCE"}],
}


@pytest.fixture
def sync_client(httpx_mock: HTTPXMock) -> SwgohComlink:
    client = SwgohComlink(url="http://localhost:3000")
    yield client
    client.close()


@pytest.fixture
def async_client(httpx_mock: HTTPXMock) -> SwgohComlinkAsync:
    client = SwgohComlinkAsync(url="http://localhost:3000")
    yield client


# ── _gac: get_current_gac_event (sync) ──────────────────────────────────


class TestGetCurrentGacEvent:
    def test_returns_gac_event(self, httpx_mock: HTTPXMock, sync_client):
        from swgoh_comlink.helpers._gac import get_current_gac_event

        httpx_mock.add_response(json={"gameEvent": [_GAC_EVENT, {"type": 5}]})
        result = get_current_gac_event(sync_client)
        assert result["type"] == 10
        assert result["id"] == _GAC_EVENT["id"]

    def test_no_gac_event_raises(self, httpx_mock: HTTPXMock, sync_client):
        from swgoh_comlink.helpers._gac import get_current_gac_event

        httpx_mock.add_response(json={"gameEvent": [{"type": 5}]})
        with pytest.raises(SwgohComlinkValueError, match="No active GAC"):
            get_current_gac_event(sync_client)

    def test_missing_comlink_raises(self):
        from swgoh_comlink.helpers._gac import get_current_gac_event

        with pytest.raises(SwgohComlinkValueError, match="comlink"):
            get_current_gac_event(None)

    def test_no_comlink_type_raises(self):
        from swgoh_comlink.helpers._gac import get_current_gac_event

        # Object without __comlink_type__
        with pytest.raises(SwgohComlinkValueError, match="comlink"):
            get_current_gac_event(object())


# ── _gac: async_get_current_gac_event ────────────────────────────────────


class TestAsyncGetCurrentGacEvent:
    @pytest.mark.asyncio
    async def test_returns_gac_event(self, httpx_mock: HTTPXMock, async_client):
        from swgoh_comlink.helpers._gac import async_get_current_gac_event

        httpx_mock.add_response(json={"gameEvent": [_GAC_EVENT]})
        result = await async_get_current_gac_event(async_client)
        assert result["type"] == 10
        await async_client.aclose()

    @pytest.mark.asyncio
    async def test_no_gac_event_raises(self, httpx_mock: HTTPXMock, async_client):
        from swgoh_comlink.helpers._gac import async_get_current_gac_event

        httpx_mock.add_response(json={"gameEvent": []})
        with pytest.raises(SwgohComlinkValueError, match="No active GAC"):
            await async_get_current_gac_event(async_client)
        await async_client.aclose()

    @pytest.mark.asyncio
    async def test_missing_comlink_raises(self):
        from swgoh_comlink.helpers._gac import async_get_current_gac_event

        with pytest.raises(SwgohComlinkValueError, match="comlink"):
            await async_get_current_gac_event(None)


# ── _gac: get_gac_brackets (sync) ──────────────────────────────────────


class TestGetGacBrackets:
    def test_wrong_comlink_type_raises(self):
        from swgoh_comlink.helpers._gac import get_gac_brackets

        with pytest.raises(SwgohComlinkValueError, match="Invalid comlink"):
            get_gac_brackets(None, league="kyber")

    def test_missing_league_raises(self, sync_client):
        from swgoh_comlink.helpers._gac import get_gac_brackets

        with pytest.raises(SwgohComlinkValueError, match="league"):
            get_gac_brackets(sync_client, league=None)

    def test_non_string_league_raises(self, sync_client):
        from swgoh_comlink.helpers._gac import get_gac_brackets

        with pytest.raises(SwgohComlinkValueError, match="league"):
            get_gac_brackets(sync_client, league=123)

    def test_async_comlink_rejected(self, httpx_mock: HTTPXMock):
        from swgoh_comlink.helpers._gac import get_gac_brackets

        async_client = SwgohComlinkAsync(url="http://localhost:3000")
        with pytest.raises(SwgohComlinkValueError, match="Invalid comlink"):
            get_gac_brackets(async_client, league="kyber")

    def test_scans_brackets(self, httpx_mock: HTTPXMock, sync_client):
        from swgoh_comlink.helpers._gac import get_gac_brackets

        # First: get_events for current GAC event
        httpx_mock.add_response(json={"gameEvent": [_GAC_EVENT]})
        # Probing phase: bracket 0 has players, bracket 1024 empty
        httpx_mock.add_response(json={"player": [{"name": "P1"}]})  # probe(0)
        httpx_mock.add_response(json={"player": []})  # probe(1024) → empty
        # Binary search narrows: probe(512)→empty
        httpx_mock.add_response(json={"player": []})
        # Binary search: probe(256)→empty
        httpx_mock.add_response(json={"player": []})
        # Binary search: probe(128)→empty
        httpx_mock.add_response(json={"player": []})
        # Binary search: probe(64)→empty
        httpx_mock.add_response(json={"player": []})
        # Binary search: probe(32)→empty
        httpx_mock.add_response(json={"player": []})
        # Binary search: probe(16)→empty
        httpx_mock.add_response(json={"player": []})
        # Binary search: probe(8)→empty
        httpx_mock.add_response(json={"player": []})
        # Binary search: probe(4)→empty
        httpx_mock.add_response(json={"player": []})
        # Binary search: probe(2)→empty
        httpx_mock.add_response(json={"player": []})
        # Binary search: probe(1)→empty → boundary is 0
        httpx_mock.add_response(json={"player": []})
        # Fetch bracket 0
        httpx_mock.add_response(json={"player": [{"name": "P1"}]})

        result = get_gac_brackets(sync_client, league="kyber")
        assert isinstance(result, dict)
        assert 0 in result

    def test_empty_bracket_0_returns_empty_dict(self, httpx_mock: HTTPXMock, sync_client):
        from swgoh_comlink.helpers._gac import get_gac_brackets

        httpx_mock.add_response(json={"gameEvent": [_GAC_EVENT]})
        httpx_mock.add_response(json={"player": []})  # probe(0) → empty
        result = get_gac_brackets(sync_client, league="kyber")
        assert result == {}


# ── _gac: async_get_gac_brackets ───────────────────────────────────────


class TestAsyncGetGacBrackets:
    @pytest.mark.asyncio
    async def test_wrong_comlink_type_raises(self):
        from swgoh_comlink.helpers._gac import async_get_gac_brackets

        with pytest.raises(SwgohComlinkValueError, match="Invalid comlink"):
            await async_get_gac_brackets(None, league="kyber")

    @pytest.mark.asyncio
    async def test_missing_league_raises(self, async_client):
        from swgoh_comlink.helpers._gac import async_get_gac_brackets

        with pytest.raises(SwgohComlinkValueError, match="league"):
            await async_get_gac_brackets(async_client, league=None)
        await async_client.aclose()

    @pytest.mark.asyncio
    async def test_sync_comlink_rejected(self, httpx_mock: HTTPXMock):
        from swgoh_comlink.helpers._gac import async_get_gac_brackets

        sync_client = SwgohComlink(url="http://localhost:3000")
        with pytest.raises(SwgohComlinkValueError, match="Invalid comlink"):
            await async_get_gac_brackets(sync_client, league="kyber")
        sync_client.close()

    @pytest.mark.asyncio
    async def test_empty_bracket_0_returns_empty_dict(self, httpx_mock: HTTPXMock, async_client):
        from swgoh_comlink.helpers._gac import async_get_gac_brackets

        httpx_mock.add_response(json={"gameEvent": [_GAC_EVENT]})
        httpx_mock.add_response(json={"player": []})  # probe(0) → empty
        result = await async_get_gac_brackets(async_client, league="kyber")
        assert result == {}
        await async_client.aclose()


# ── _guild: get_guild_members (sync) ────────────────────────────────────


class TestGetGuildMembers:
    def test_via_player_id(self, httpx_mock: HTTPXMock, sync_client):
        from swgoh_comlink.helpers._guild import get_guild_members

        httpx_mock.add_response(json={"guildId": "guild_abc"})
        httpx_mock.add_response(json={"member": [{"id": "m1"}, {"id": "m2"}]})
        result = get_guild_members(sync_client, player_id="pid_123")
        assert len(result) == 2

    def test_via_allycode(self, httpx_mock: HTTPXMock, sync_client):
        from swgoh_comlink.helpers._guild import get_guild_members

        httpx_mock.add_response(json={"guildId": "guild_abc"})
        httpx_mock.add_response(json={"member": [{"id": "m1"}]})
        result = get_guild_members(sync_client, allycode=123456789)
        assert len(result) == 1

    def test_both_provided_raises(self, sync_client):
        from swgoh_comlink.helpers._guild import get_guild_members

        with pytest.raises(SwgohComlinkValueError, match="not both"):
            get_guild_members(sync_client, player_id="pid", allycode=123456789)

    def test_neither_provided_raises(self, sync_client):
        from swgoh_comlink.helpers._guild import get_guild_members

        with pytest.raises(SwgohComlinkValueError, match="required"):
            get_guild_members(sync_client)

    def test_wrong_comlink_type_raises(self):
        from swgoh_comlink.helpers._guild import get_guild_members

        with pytest.raises(SwgohComlinkValueError, match="SwgohComlink"):
            get_guild_members(None, player_id="pid")

    def test_async_comlink_rejected(self, httpx_mock: HTTPXMock):
        from swgoh_comlink.helpers._guild import get_guild_members

        async_client = SwgohComlinkAsync(url="http://localhost:3000")
        with pytest.raises(SwgohComlinkValueError, match="SwgohComlink"):
            get_guild_members(async_client, player_id="pid")


# ── _guild: async_get_guild_members ─────────────────────────────────────


class TestAsyncGetGuildMembers:
    @pytest.mark.asyncio
    async def test_via_player_id(self, httpx_mock: HTTPXMock, async_client):
        from swgoh_comlink.helpers._guild import async_get_guild_members

        httpx_mock.add_response(json={"guildId": "guild_abc"})
        httpx_mock.add_response(json={"member": [{"id": "m1"}]})
        result = await async_get_guild_members(async_client, player_id="pid_123")
        assert len(result) == 1
        await async_client.aclose()

    @pytest.mark.asyncio
    async def test_via_allycode(self, httpx_mock: HTTPXMock, async_client):
        from swgoh_comlink.helpers._guild import async_get_guild_members

        httpx_mock.add_response(json={"guildId": "guild_abc"})
        httpx_mock.add_response(json={"member": [{"id": "m1"}]})
        result = await async_get_guild_members(async_client, allycode=123456789)
        assert len(result) == 1
        await async_client.aclose()

    @pytest.mark.asyncio
    async def test_both_provided_raises(self, async_client):
        from swgoh_comlink.helpers._guild import async_get_guild_members

        with pytest.raises(SwgohComlinkValueError, match="not both"):
            await async_get_guild_members(async_client, player_id="pid", allycode=123456789)
        await async_client.aclose()

    @pytest.mark.asyncio
    async def test_neither_provided_raises(self, async_client):
        from swgoh_comlink.helpers._guild import async_get_guild_members

        with pytest.raises(SwgohComlinkValueError, match="required"):
            await async_get_guild_members(async_client)
        await async_client.aclose()

    @pytest.mark.asyncio
    async def test_wrong_comlink_type_raises(self):
        from swgoh_comlink.helpers._guild import async_get_guild_members

        with pytest.raises(SwgohComlinkValueError, match="SwgohComlinkAsync"):
            await async_get_guild_members(None, player_id="pid")

    @pytest.mark.asyncio
    async def test_sync_comlink_rejected(self, httpx_mock: HTTPXMock):
        from swgoh_comlink.helpers._guild import async_get_guild_members

        sync_client = SwgohComlink(url="http://localhost:3000")
        with pytest.raises(SwgohComlinkValueError, match="SwgohComlinkAsync"):
            await async_get_guild_members(sync_client, player_id="pid")
        sync_client.close()


# ── _conquest: calc_current_stamina ──────────────────────────────────────

_FROZEN_TIME = 1773793698

_CONQUEST_UNIT = {
    "lastRefreshTime": str(_FROZEN_TIME - 7200),  # 120 minutes ago
    "remainingStamina": 87,
    "unitId": "2rJUF0DJRyWBTFrXRbTvhA",
}


class TestCalcCurrentStamina:
    @patch("swgoh_comlink.helpers._conquest.time.time", return_value=_FROZEN_TIME)
    def test_stamina_without_pass_plus(self, mock_time):
        from swgoh_comlink.helpers._conquest import calc_current_stamina

        result = calc_current_stamina(_CONQUEST_UNIT)
        assert result == 4  # floor(120 / 30 * 1.0)

    @patch("swgoh_comlink.helpers._conquest.time.time", return_value=_FROZEN_TIME)
    def test_stamina_with_pass_plus(self, mock_time):
        from swgoh_comlink.helpers._conquest import calc_current_stamina

        result = calc_current_stamina(_CONQUEST_UNIT, pass_plus=True)
        assert result == 5  # floor(120 / 30 * 1.33)

    def test_non_dict_raises(self):
        from swgoh_comlink.helpers._conquest import calc_current_stamina

        with pytest.raises(SwgohComlinkValueError, match="dict"):
            calc_current_stamina("not a dict")

    def test_missing_remaining_stamina_raises(self):
        from swgoh_comlink.helpers._conquest import calc_current_stamina

        with pytest.raises((SwgohComlinkValueError, TypeError)):
            calc_current_stamina({"lastRefreshTime": "123"})

    def test_missing_last_refresh_time_raises(self):
        from swgoh_comlink.helpers._conquest import calc_current_stamina

        with pytest.raises((SwgohComlinkValueError, TypeError)):
            calc_current_stamina({"remainingStamina": 87})

    @patch("swgoh_comlink.helpers._conquest.time.time", return_value=_FROZEN_TIME)
    def test_stamina_capped_at_100(self, mock_time):
        from swgoh_comlink.helpers._conquest import calc_current_stamina

        old_unit = {
            "lastRefreshTime": str(_FROZEN_TIME - 360000),  # 6000 minutes ago
            "remainingStamina": 50,
            "unitId": "test",
        }
        result = calc_current_stamina(old_unit)
        assert result == 100
