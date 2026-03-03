"""Tests for the asynchronous SwgohComlinkAsync client."""
from __future__ import annotations

import json

import httpx
import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlinkAsync
from swgoh_comlink.exceptions import SwgohComlinkException

# ── Core request tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_player_posts_expected_payload(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"name": "Test Player"})

    client = SwgohComlinkAsync(url="http://localhost:3000", verify_ssl=False)
    out = await client.get_player(allycode=123456789)

    assert out["name"] == "Test Player"

    request = httpx_mock.get_request()
    assert request.method == "POST"
    assert str(request.url) == "http://localhost:3000/player"
    body = json.loads(request.content)
    assert body == {"payload": {"allyCode": "123456789"}, "enums": False}
    await client.aclose()


@pytest.mark.asyncio
async def test_get_player_with_player_id(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"name": "Test Player"})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    await client.get_player(player_id="abc-123")

    body = json.loads(httpx_mock.get_request().content)
    assert body == {"payload": {"playerId": "abc-123"}, "enums": False}
    await client.aclose()


@pytest.mark.asyncio
async def test_get_game_data_posts_expected_payload(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"units": []})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    out = await client.get_game_data(
        version="1.2.3",
        include_pve_units=False,
        request_segment=4,
        enums=True,
    )

    assert out == {"units": []}

    request = httpx_mock.get_request()
    assert request.method == "POST"
    assert str(request.url) == "http://localhost:3000/data"
    body = json.loads(request.content)
    assert body == {
        "payload": {
            "version": "1.2.3",
            "devicePlatform": "Android",
            "includePveUnits": False,
            "requestSegment": 4,
        },
        "enums": True,
    }
    await client.aclose()


@pytest.mark.asyncio
async def test_get_game_data_auto_version(httpx_mock: HTTPXMock):
    """When no version is provided, get_game_data fetches metadata first."""
    httpx_mock.add_response(json={"latestGamedataVersion": "auto-1.0"})
    httpx_mock.add_response(json={"data": []})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    await client.get_game_data()

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert str(requests[0].url) == "http://localhost:3000/metadata"
    assert str(requests[1].url) == "http://localhost:3000/data"
    body = json.loads(requests[1].content)
    assert body["payload"]["version"] == "auto-1.0"
    await client.aclose()


@pytest.mark.asyncio
async def test_get_guild_unwraps_guild_key(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"guild": {"profile": {"name": "Guild Name"}}})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    out = await client.get_guild(guild_id="guild-1", include_recent_guild_activity_info=True)

    assert out == {"profile": {"name": "Guild Name"}}

    request = httpx_mock.get_request()
    assert request.method == "POST"
    assert str(request.url) == "http://localhost:3000/guild"
    body = json.loads(request.content)
    assert body == {
        "payload": {
            "guildId": "guild-1",
            "includeRecentGuildActivityInfo": True,
        },
        "enums": False,
    }
    await client.aclose()


@pytest.mark.asyncio
async def test_get_guild_no_unwrap_when_key_missing(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"profile": {"name": "Direct Guild"}})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    out = await client.get_guild(guild_id="guild-2")
    assert out == {"profile": {"name": "Direct Guild"}}
    await client.aclose()


@pytest.mark.asyncio
async def test_get_guild_with_alias(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"guild": {"name": "Test"}})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    await client.get_guild(guild_id="guild-1", includeRecent=True)

    body = json.loads(httpx_mock.get_request().content)
    assert body["payload"]["includeRecentGuildActivityInfo"] is True
    await client.aclose()


@pytest.mark.asyncio
async def test_get_enums_uses_get_method(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"CombatType": 1})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    out = await client.get_enums()

    assert "CombatType" in out
    request = httpx_mock.get_request()
    assert request.method == "GET"
    assert str(request.url) == "http://localhost:3000/enums"
    await client.aclose()


@pytest.mark.asyncio
async def test_request_error_raises_comlink_exception(httpx_mock: HTTPXMock):
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))

    client = SwgohComlinkAsync(url="http://localhost:3000")
    with pytest.raises(SwgohComlinkException):
        await client.get_enums()
    await client.aclose()


@pytest.mark.asyncio
async def test_async_context_manager(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"CombatType": 1})

    async with SwgohComlinkAsync(url="http://localhost:3000") as client:
        out = await client.get_enums()
        assert "CombatType" in out


# ── Events ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_events(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"events": [{"id": "event1"}]})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    await client.get_events(enums=True)

    body = json.loads(httpx_mock.get_request().content)
    assert body == {"payload": {}, "enums": True}
    assert str(httpx_mock.get_request().url) == "http://localhost:3000/getEvents"
    await client.aclose()


# ── Localization ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_localization_with_id(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"localization": {}})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    await client.get_localization(localization_id="loc-v1")

    body = json.loads(httpx_mock.get_request().content)
    assert body == {"unzip": False, "enums": False, "payload": {"id": "loc-v1"}}
    await client.aclose()


@pytest.mark.asyncio
async def test_get_localization_with_locale(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"localization": {}})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    await client.get_localization(localization_id="loc-v1", locale="fra_fr")

    body = json.loads(httpx_mock.get_request().content)
    assert body["payload"]["id"] == "loc-v1:FRA_FR"
    await client.aclose()


@pytest.mark.asyncio
async def test_get_localization_auto_version(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={
        "latestGamedataVersion": "game-v1",
        "latestLocalizationBundleVersion": "lang-v1",
    })
    httpx_mock.add_response(json={"localization": {}})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    await client.get_localization()

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    body = json.loads(requests[1].content)
    assert body["payload"]["id"] == "lang-v1"
    await client.aclose()


# ── Game Metadata ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_game_metadata_default(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"latestGamedataVersion": "v1"})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    out = await client.get_game_metadata()

    body = json.loads(httpx_mock.get_request().content)
    assert body == {}
    assert out["latestGamedataVersion"] == "v1"
    await client.aclose()


@pytest.mark.asyncio
async def test_get_game_metadata_with_client_specs(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"latestGamedataVersion": "v1"})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    specs = {"platform": "Android", "bundleId": "com.ea.game"}
    await client.get_game_metadata(client_specs=specs, enums=True)

    body = json.loads(httpx_mock.get_request().content)
    assert body == {"payload": {"client_specs": specs}, "enums": True}
    await client.aclose()


# ── Player Arena ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_player_arena(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"arena": {}})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    await client.get_player_arena(allycode=123, player_details_only=True)

    body = json.loads(httpx_mock.get_request().content)
    assert body["payload"]["playerDetailsOnly"] is True
    assert str(httpx_mock.get_request().url) == "http://localhost:3000/playerArena"
    await client.aclose()


@pytest.mark.asyncio
async def test_get_player_arena_camel_case_alias(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"arena": {}})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    await client.get_player_arena(allycode=123, playerDetailsOnly=True)

    body = json.loads(httpx_mock.get_request().content)
    assert body["payload"]["playerDetailsOnly"] is True
    await client.aclose()


# ── Guilds by name/criteria ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_guilds_by_name(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"guilds": []})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    await client.get_guilds_by_name(name="Test Guild", start_index=5, count=20)

    body = json.loads(httpx_mock.get_request().content)
    assert body == {
        "payload": {"name": "Test Guild", "filterType": 4, "startIndex": 5, "count": 20},
        "enums": False,
    }
    await client.aclose()


@pytest.mark.asyncio
async def test_get_guilds_by_criteria(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"guilds": []})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    criteria = {"minMemberCount": 40}
    await client.get_guilds_by_criteria(search_criteria=criteria)

    body = json.loads(httpx_mock.get_request().content)
    assert body == {
        "payload": {"searchCriteria": criteria, "filterType": 5, "startIndex": 0, "count": 10},
        "enums": False,
    }
    await client.aclose()


# ── Leaderboard ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_leaderboard_type_4(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"leaderboard": []})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    await client.get_leaderboard(
        leaderboard_type=4, event_instance_id="event1", group_id="group1"
    )

    body = json.loads(httpx_mock.get_request().content)
    assert body["payload"]["leaderboardType"] == 4
    assert body["payload"]["eventInstanceId"] == "event1"
    assert body["payload"]["groupId"] == "group1"
    await client.aclose()


@pytest.mark.asyncio
async def test_get_leaderboard_type_6_with_string_league_division(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"leaderboard": []})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    await client.get_leaderboard(leaderboard_type=6, league="kyber", division="1")

    body = json.loads(httpx_mock.get_request().content)
    assert body["payload"]["leaderboardType"] == 6
    assert body["payload"]["league"] == 100  # kyber
    assert body["payload"]["division"] == 25  # division 1
    await client.aclose()


@pytest.mark.asyncio
async def test_get_leaderboard_type_6_with_int_division(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"leaderboard": []})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    await client.get_leaderboard(leaderboard_type=6, league="carbonite", division=3)

    body = json.loads(httpx_mock.get_request().content)
    assert body["payload"]["league"] == 20  # carbonite
    assert body["payload"]["division"] == 15  # division 3
    await client.aclose()


# ── Guild Leaderboard ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_guild_leaderboard(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"leaderboard": []})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    await client.get_guild_leaderboard(leaderboard_id=[{"id": "lb1"}], count=50)

    body = json.loads(httpx_mock.get_request().content)
    assert body == {
        "payload": {"leaderboardId": [{"id": "lb1"}], "count": 50},
        "enums": False,
    }
    assert str(httpx_mock.get_request().url) == "http://localhost:3000/getGuildLeaderboard"
    await client.aclose()


# ── Namespaces & Segmented Content ───────────────────────────────────────

@pytest.mark.asyncio
async def test_get_name_spaces(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"namespaces": []})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    await client.get_name_spaces(only_compatible=True)

    body = json.loads(httpx_mock.get_request().content)
    assert body == {"payload": {"onlyCompatible": True}, "enums": False}
    await client.aclose()


@pytest.mark.asyncio
async def test_get_segmented_content(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"content": {}})

    client = SwgohComlinkAsync(url="http://localhost:3000")
    await client.get_segmented_content(content_name_space="test", accept_language="FRA_FR")

    body = json.loads(httpx_mock.get_request().content)
    assert body == {
        "payload": {"contentNameSpace": "test", "acceptLanguage": "FRA_FR"},
        "enums": False,
    }
    await client.aclose()


# ── Unit Stats ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_unit_stats_with_dict(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json=[{"stats": {}}])

    client = SwgohComlinkAsync(url="http://localhost:3000", stats_url="http://localhost:3223")
    await client.get_unit_stats(request_payload={"unit": "data"})

    request = httpx_mock.get_request()
    assert str(request.url) == "http://localhost:3223/api"
    body = json.loads(request.content)
    assert body == [{"unit": "data"}]
    await client.aclose()


@pytest.mark.asyncio
async def test_get_unit_stats_with_list(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json=[{"stats": {}}])

    client = SwgohComlinkAsync(url="http://localhost:3000", stats_url="http://localhost:3223")
    await client.get_unit_stats(request_payload=[{"unit": "data"}])

    body = json.loads(httpx_mock.get_request().content)
    assert body == [{"unit": "data"}]
    await client.aclose()


@pytest.mark.asyncio
async def test_get_unit_stats_with_flags(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json=[{}])

    client = SwgohComlinkAsync(url="http://localhost:3000", stats_url="http://localhost:3223")
    await client.get_unit_stats(
        request_payload=[{"unit": "data"}], flags=["calcGP"], language="eng_us"
    )

    request = httpx_mock.get_request()
    assert "flags=calcGP" in str(request.url)
    assert "language=eng_us" in str(request.url)
    await client.aclose()


# ── Latest Version ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_latest_game_data_version(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={
        "latestGamedataVersion": "game-v2",
        "latestLocalizationBundleVersion": "lang-v2",
    })

    client = SwgohComlinkAsync(url="http://localhost:3000")
    out = await client.get_latest_game_data_version()

    assert out == {"game": "game-v2", "language": "lang-v2"}
    await client.aclose()


# ── HMAC integration test ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hmac_headers_sent_on_request(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"CombatType": 1})

    client = SwgohComlinkAsync(
        url="http://localhost:3000", access_key="pub", secret_key="priv"
    )
    await client.get_enums()

    request = httpx_mock.get_request()
    assert "Authorization" in request.headers
    assert request.headers["Authorization"].startswith("HMAC-SHA256 Credential=pub,Signature=")
    assert "X-Date" in request.headers
    await client.aclose()
