# coding=utf-8
"""Typed-client coverage for the dict-passthrough endpoints and plumbing.

The four typed endpoints (``get_player``, ``get_guild``, ``get_game_metadata``,
``get_leaderboard``) are exercised by the golden/shape suites. This module
covers the rest of the generated typed clients — the endpoints that stay
dict-shaped even on the typed surface (per the codegen manifest), plus the
client lifecycle (injected ``http_client``, context manager) and the error /
decode-failure paths of ``_request``.

Every response is served from the ``metadata`` cassette: these endpoints
bypass Struct decoding, so any valid JSON object exercises the passthrough.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink.exceptions import SwgohComlinkException
from swgoh_comlink.typed import SwgohComlink, SwgohComlinkAsync

from .conftest import CassetteServer

#: Endpoint paths that return dicts even on the typed surface. ``api`` is the
#: swgoh-stats sub-service path used by ``get_unit_stats``.
_PASSTHROUGH_ENDPOINTS = (
    "enums",
    "getEvents",
    "playerArena",
    "getGuilds",
    "getGuildLeaderboard",
    "getNameSpaces",
    "getSegmentedContent",
    "api",
    "data",
    "localization",
)


def _bind_passthrough(cassette_server: CassetteServer) -> None:
    for endpoint in _PASSTHROUGH_ENDPOINTS:
        cassette_server.use(endpoint, "metadata")


# ── Sync client ──────────────────────────────────────────────────────────────


def test_sync_passthrough_endpoints_return_dicts(cassette_server: CassetteServer, recorded_comlink_typed: Any) -> None:
    _bind_passthrough(cassette_server)
    client = recorded_comlink_typed

    assert isinstance(client.get_enums(), dict)
    assert isinstance(client.get_events(), dict)
    assert isinstance(client.get_player_arena(allycode=314927874), dict)
    assert isinstance(client.get_guilds_by_name("guild"), dict)
    assert isinstance(client.get_guilds_by_criteria({"minGuildGalacticPower": 1}), dict)
    assert isinstance(client.get_guild_leaderboard([{"leaderboardType": 0, "monthOffset": 0}]), dict)
    assert isinstance(client.get_name_spaces(), dict)
    assert isinstance(client.get_segmented_content(), dict)


def test_sync_get_unit_stats_wraps_single_dict_payload(
    cassette_server: CassetteServer, recorded_comlink_typed: Any
) -> None:
    _bind_passthrough(cassette_server)
    result = recorded_comlink_typed.get_unit_stats({"defId": "JEDIKNIGHTLUKE"})
    assert isinstance(result, dict)


def test_sync_game_data_resolves_latest_version(cassette_server: CassetteServer, recorded_comlink_typed: Any) -> None:
    # version="" forces the metadata fetch in _get_game_version.
    _bind_passthrough(cassette_server)
    assert isinstance(recorded_comlink_typed.get_game_data(), dict)


def test_sync_localization_resolves_bundle_id(cassette_server: CassetteServer, recorded_comlink_typed: Any) -> None:
    # localization_id=None resolves the bundle version from current metadata.
    _bind_passthrough(cassette_server)
    assert isinstance(recorded_comlink_typed.get_localization(), dict)


def test_sync_context_manager(cassette_server: CassetteServer) -> None:
    _bind_passthrough(cassette_server)
    with SwgohComlink(url="http://comlink.test") as client:
        assert isinstance(client.get_enums(), dict)


def test_sync_injected_client_is_not_closed() -> None:
    injected = httpx.Client(base_url="http://comlink.test")
    client = SwgohComlink(url="http://comlink.test", http_client=injected)
    client.close()
    assert not injected.is_closed
    injected.close()


def test_sync_http_error_maps_to_exception(cassette_server: CassetteServer) -> None:
    cassette_server.fail("enums", status_code=503)
    with (
        SwgohComlink(url="http://comlink.test", max_retries=0) as client,
        pytest.raises(SwgohComlinkException, match=r"HTTP 503"),
    ):
        client.get_enums()


def test_sync_decode_failure_raises(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(content=b"{not json")
    with (
        SwgohComlink(url="http://comlink.test") as client,
        pytest.raises(SwgohComlinkException, match="failed to decode"),
    ):
        client.get_enums()


# ── Async client ─────────────────────────────────────────────────────────────


async def test_async_passthrough_endpoints_return_dicts(
    cassette_server: CassetteServer, recorded_comlink_async_typed: Any
) -> None:
    _bind_passthrough(cassette_server)
    client = recorded_comlink_async_typed

    assert isinstance(await client.get_enums(), dict)
    assert isinstance(await client.get_events(), dict)
    assert isinstance(await client.get_player_arena(allycode=314927874), dict)
    assert isinstance(await client.get_guilds_by_name("guild"), dict)
    assert isinstance(await client.get_guilds_by_criteria({"minGuildGalacticPower": 1}), dict)
    assert isinstance(await client.get_guild_leaderboard([{"leaderboardType": 0, "monthOffset": 0}]), dict)
    assert isinstance(await client.get_name_spaces(), dict)
    assert isinstance(await client.get_segmented_content(), dict)


async def test_async_get_unit_stats_wraps_single_dict_payload(
    cassette_server: CassetteServer, recorded_comlink_async_typed: Any
) -> None:
    _bind_passthrough(cassette_server)
    result = await recorded_comlink_async_typed.get_unit_stats({"defId": "JEDIKNIGHTLUKE"})
    assert isinstance(result, dict)


async def test_async_game_data_resolves_latest_version(
    cassette_server: CassetteServer, recorded_comlink_async_typed: Any
) -> None:
    _bind_passthrough(cassette_server)
    assert isinstance(await recorded_comlink_async_typed.get_game_data(), dict)


async def test_async_localization_resolves_bundle_id(
    cassette_server: CassetteServer, recorded_comlink_async_typed: Any
) -> None:
    _bind_passthrough(cassette_server)
    assert isinstance(await recorded_comlink_async_typed.get_localization(), dict)


async def test_async_context_manager(cassette_server: CassetteServer) -> None:
    _bind_passthrough(cassette_server)
    async with SwgohComlinkAsync(url="http://comlink.test") as client:
        assert isinstance(await client.get_enums(), dict)


async def test_async_injected_client_is_not_closed() -> None:
    injected = httpx.AsyncClient(base_url="http://comlink.test")
    client = SwgohComlinkAsync(url="http://comlink.test", http_client=injected)
    await client.aclose()
    assert not injected.is_closed
    await injected.aclose()


async def test_async_http_error_maps_to_exception(cassette_server: CassetteServer) -> None:
    cassette_server.fail("enums", status_code=503)
    async with SwgohComlinkAsync(url="http://comlink.test", max_retries=0) as client:
        with pytest.raises(SwgohComlinkException, match=r"HTTP 503"):
            await client.get_enums()


async def test_async_decode_failure_raises(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(content=b"{not json")
    async with SwgohComlinkAsync(url="http://comlink.test") as client:
        with pytest.raises(SwgohComlinkException, match="failed to decode"):
            await client.get_enums()
