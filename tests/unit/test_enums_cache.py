"""Tests for the instance-level get_enums() cache, keyed on the game data version.

The deterministic cache rules run against both clients via the ``comlink``/``make_comlink``
and ``call`` fixtures in tests/unit/conftest.py. The concurrency tests stay per client:
threads and ``asyncio.gather`` exercise different single-flight mechanisms.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx
import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync

Client = SwgohComlink | SwgohComlinkAsync
Call = Callable[..., Awaitable[Any]]

BASE_URL = "http://localhost:3000"
ENUMS_URL = f"{BASE_URL}/enums"
METADATA_URL = f"{BASE_URL}/metadata"
ENUMS = {"CombatType": {"CombatType_DEFAULT": 0, "CHARACTER": 1, "SHIP": 2}}


def _metadata(game: str) -> dict[str, str]:
    return {"latestGamedataVersion": game, "latestLocalizationBundleVersion": "lang-v1"}


def _requests(httpx_mock: HTTPXMock, url: str) -> int:
    return len(httpx_mock.get_requests(url=url))


# ── Cache rules (both clients) ───────────────────────────────────────────


async def test_first_call_populates_the_cache(comlink: Client, call: Call, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v1"))
    httpx_mock.add_response(url=ENUMS_URL, json=ENUMS)
    assert comlink.enums is None and comlink.enums_version is None

    result = await call(comlink, "get_enums")

    assert result == ENUMS
    assert comlink.enums is result
    assert comlink.enums_version == "game-v1"


async def test_repeat_calls_are_served_from_the_cache(comlink: Client, call: Call, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v1"))
    httpx_mock.add_response(url=ENUMS_URL, json=ENUMS)

    first = await call(comlink, "get_enums")
    second = await call(comlink, "get_enums")

    # The version is cached too, so the second call makes no request at all.
    assert second is first
    assert _requests(httpx_mock, METADATA_URL) == 1
    assert _requests(httpx_mock, ENUMS_URL) == 1


async def test_a_new_game_data_version_refetches(
    make_comlink: Callable[..., Client], call: Call, httpx_mock: HTTPXMock, clock: dict[str, float]
):
    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v1"))
    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v2"))
    httpx_mock.add_response(url=ENUMS_URL, json=ENUMS)
    httpx_mock.add_response(url=ENUMS_URL, json={**ENUMS, "NewEnum": {"NewEnum_DEFAULT": 0}})
    client = make_comlink(version_cache_ttl=60)

    first = await call(client, "get_enums")
    clock["t"] += 61  # the version cache expires and /metadata reports a new version
    result = await call(client, "get_enums")

    assert result is not first
    assert "NewEnum" in result
    assert client.enums is result
    assert client.enums_version == "game-v2"
    assert _requests(httpx_mock, ENUMS_URL) == 2


async def test_an_unchanged_version_does_not_refetch(
    make_comlink: Callable[..., Client], call: Call, httpx_mock: HTTPXMock
):
    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v1"), is_reusable=True)
    httpx_mock.add_response(url=ENUMS_URL, json=ENUMS)
    client = make_comlink(version_cache_ttl=0)

    first = await call(client, "get_enums")
    second = await call(client, "get_enums")

    # With the version cache off each call checks /metadata, but the enums are fetched once.
    assert second is first
    assert _requests(httpx_mock, METADATA_URL) == 2
    assert _requests(httpx_mock, ENUMS_URL) == 1


async def test_refresh_refetches_version_and_enums(comlink: Client, call: Call, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v1"), is_reusable=True)
    httpx_mock.add_response(url=ENUMS_URL, json=ENUMS, is_reusable=True)

    first = await call(comlink, "get_enums")
    second = await call(comlink, "get_enums", refresh=True)

    assert second == first and second is not first
    assert comlink.enums is second
    assert _requests(httpx_mock, METADATA_URL) == 2
    assert _requests(httpx_mock, ENUMS_URL) == 2


async def test_version_already_cached_by_another_call_is_reused(comlink: Client, call: Call, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v1"))
    httpx_mock.add_response(url=ENUMS_URL, json=ENUMS)
    await call(comlink, "get_latest_game_data_version")

    await call(comlink, "get_enums")

    assert _requests(httpx_mock, METADATA_URL) == 1
    assert comlink.enums_version == "game-v1"


@pytest.mark.parametrize(
    "metadata_response",
    [
        pytest.param({"json": {"latestLocalizationBundleVersion": "lang-v1"}}, id="no-game-data-version"),
        pytest.param({"status_code": 500, "json": {"code": "INTERNAL", "message": "boom"}}, id="metadata-error"),
    ],
)
async def test_unknown_version_fetches_without_caching(
    comlink: Client, call: Call, httpx_mock: HTTPXMock, metadata_response: dict
):
    httpx_mock.add_response(url=METADATA_URL, is_reusable=True, **metadata_response)
    httpx_mock.add_response(url=ENUMS_URL, json=ENUMS, is_reusable=True)

    assert await call(comlink, "get_enums") == ENUMS
    assert await call(comlink, "get_enums") == ENUMS

    # Without a version to key it on, nothing is cached and each call fetches the enums.
    assert comlink.enums is None and comlink.enums_version is None
    assert _requests(httpx_mock, ENUMS_URL) == 2


# ── Concurrency (per client) ─────────────────────────────────────────────


def test_concurrent_threads_share_one_fetch(httpx_mock: HTTPXMock):
    def slow_enums(request: httpx.Request) -> httpx.Response:
        time.sleep(0.05)  # long enough for every thread to arrive while the first fetch is in flight
        return httpx.Response(200, json=ENUMS)

    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v1"), is_reusable=True)
    httpx_mock.add_callback(slow_enums, url=ENUMS_URL, is_reusable=True)

    with SwgohComlink(url=BASE_URL) as client, ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: client.get_enums(), range(16)))

    assert all(result is results[0] for result in results)
    assert _requests(httpx_mock, METADATA_URL) == 1
    assert _requests(httpx_mock, ENUMS_URL) == 1


async def test_async_concurrent_calls_share_one_fetch(httpx_mock: HTTPXMock):
    async def slow_enums(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.01)  # yield so the other tasks reach get_enums() while this fetch is in flight
        return httpx.Response(200, json=ENUMS)

    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v1"), is_reusable=True)
    httpx_mock.add_callback(slow_enums, url=ENUMS_URL, is_reusable=True)

    async with SwgohComlinkAsync(url=BASE_URL) as client:
        results = await asyncio.gather(*(client.get_enums() for _ in range(16)))

    assert all(result is results[0] for result in results)
    assert _requests(httpx_mock, METADATA_URL) == 1
    assert _requests(httpx_mock, ENUMS_URL) == 1
