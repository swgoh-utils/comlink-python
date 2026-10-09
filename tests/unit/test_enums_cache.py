"""Tests for the instance-level get_enums() cache, keyed on the game data version."""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync

BASE_URL = "http://localhost:3000"
ENUMS_URL = f"{BASE_URL}/enums"
METADATA_URL = f"{BASE_URL}/metadata"
ENUMS = {"CombatType": {"CombatType_DEFAULT": 0, "CHARACTER": 1, "SHIP": 2}}


def _metadata(game: str) -> dict[str, str]:
    return {"latestGamedataVersion": game, "latestLocalizationBundleVersion": "lang-v1"}


def _requests(httpx_mock: HTTPXMock, url: str) -> int:
    return len(httpx_mock.get_requests(url=url))


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> dict[str, float]:
    """Controllable monotonic clock for version cache expiry."""
    state = {"t": 1000.0}
    monkeypatch.setattr("swgoh_comlink._base._now", lambda: state["t"])
    return state


# ── Sync client ──────────────────────────────────────────────────────────


def test_first_call_populates_the_cache(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v1"))
    httpx_mock.add_response(url=ENUMS_URL, json=ENUMS)
    client = SwgohComlink(url=BASE_URL)
    assert client.enums is None and client.enums_version is None

    result = client.get_enums()

    assert result == ENUMS
    assert client.enums is result
    assert client.enums_version == "game-v1"


def test_repeat_calls_are_served_from_the_cache(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v1"))
    httpx_mock.add_response(url=ENUMS_URL, json=ENUMS)
    client = SwgohComlink(url=BASE_URL)

    first = client.get_enums()
    second = client.get_enums()

    # The version is cached too, so the second call makes no request at all.
    assert second is first
    assert _requests(httpx_mock, METADATA_URL) == 1
    assert _requests(httpx_mock, ENUMS_URL) == 1


def test_a_new_game_data_version_refetches(httpx_mock: HTTPXMock, clock: dict[str, float]):
    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v1"))
    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v2"))
    httpx_mock.add_response(url=ENUMS_URL, json=ENUMS)
    httpx_mock.add_response(url=ENUMS_URL, json={**ENUMS, "NewEnum": {"NewEnum_DEFAULT": 0}})
    client = SwgohComlink(url=BASE_URL, version_cache_ttl=60)

    client.get_enums()
    clock["t"] += 61  # the version cache expires and /metadata reports a new version
    result = client.get_enums()

    assert "NewEnum" in result
    assert client.enums is result
    assert client.enums_version == "game-v2"
    assert _requests(httpx_mock, ENUMS_URL) == 2


def test_an_unchanged_version_does_not_refetch(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v1"), is_reusable=True)
    httpx_mock.add_response(url=ENUMS_URL, json=ENUMS)
    client = SwgohComlink(url=BASE_URL, version_cache_ttl=0)

    first = client.get_enums()
    second = client.get_enums()

    # With the version cache off each call checks /metadata, but the enums are fetched once.
    assert second is first
    assert _requests(httpx_mock, METADATA_URL) == 2
    assert _requests(httpx_mock, ENUMS_URL) == 1


def test_refresh_refetches_version_and_enums(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v1"), is_reusable=True)
    httpx_mock.add_response(url=ENUMS_URL, json=ENUMS, is_reusable=True)
    client = SwgohComlink(url=BASE_URL)

    first = client.get_enums()
    second = client.get_enums(refresh=True)

    assert second == first and second is not first
    assert client.enums is second
    assert _requests(httpx_mock, METADATA_URL) == 2
    assert _requests(httpx_mock, ENUMS_URL) == 2


def test_version_already_cached_by_another_call_is_reused(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v1"))
    httpx_mock.add_response(url=ENUMS_URL, json=ENUMS)
    client = SwgohComlink(url=BASE_URL)
    client.get_latest_game_data_version()

    client.get_enums()

    assert _requests(httpx_mock, METADATA_URL) == 1
    assert client.enums_version == "game-v1"


@pytest.mark.parametrize(
    "metadata_response",
    [
        {"json": {"latestLocalizationBundleVersion": "lang-v1"}},  # no game data version
        {"status_code": 500, "json": {"code": "INTERNAL", "message": "boom"}},
    ],
)
def test_unknown_version_fetches_without_caching(httpx_mock: HTTPXMock, metadata_response: dict):
    httpx_mock.add_response(url=METADATA_URL, is_reusable=True, **metadata_response)
    httpx_mock.add_response(url=ENUMS_URL, json=ENUMS, is_reusable=True)
    client = SwgohComlink(url=BASE_URL)

    assert client.get_enums() == ENUMS
    assert client.get_enums() == ENUMS

    # Without a version to key it on, nothing is cached and each call fetches the enums.
    assert client.enums is None and client.enums_version is None
    assert _requests(httpx_mock, ENUMS_URL) == 2


def test_concurrent_threads_share_one_fetch(httpx_mock: HTTPXMock):
    def slow_enums(request: httpx.Request) -> httpx.Response:
        time.sleep(0.05)  # long enough for every thread to arrive while the first fetch is in flight
        return httpx.Response(200, json=ENUMS)

    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v1"), is_reusable=True)
    httpx_mock.add_callback(slow_enums, url=ENUMS_URL, is_reusable=True)
    client = SwgohComlink(url=BASE_URL)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: client.get_enums(), range(16)))

    assert all(result is results[0] for result in results)
    assert _requests(httpx_mock, METADATA_URL) == 1
    assert _requests(httpx_mock, ENUMS_URL) == 1


# ── Async client ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_cache_and_new_version(httpx_mock: HTTPXMock, clock: dict[str, float]):
    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v1"))
    httpx_mock.add_response(url=METADATA_URL, json=_metadata("game-v2"))
    httpx_mock.add_response(url=ENUMS_URL, json=ENUMS, is_reusable=True)

    async with SwgohComlinkAsync(url=BASE_URL, version_cache_ttl=60) as client:
        first = await client.get_enums()
        assert await client.get_enums() is first
        assert client.enums_version == "game-v1"

        clock["t"] += 61
        second = await client.get_enums()

    assert second is not first
    assert client.enums is second and client.enums_version == "game-v2"
    assert _requests(httpx_mock, ENUMS_URL) == 2


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_async_unknown_version_fetches_without_caching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=METADATA_URL, json={}, is_reusable=True)
    httpx_mock.add_response(url=ENUMS_URL, json=ENUMS, is_reusable=True)

    async with SwgohComlinkAsync(url=BASE_URL) as client:
        assert await client.get_enums() == ENUMS
        assert client.enums is None

    assert _requests(httpx_mock, ENUMS_URL) == 1
