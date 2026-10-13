"""Tests for the instance-level game/localization version cache.

The cache rules run against both clients via the ``comlink``/``make_comlink`` and ``call``
fixtures in tests/unit/conftest.py. The lock tests are written per client, since a thread
lock and an asyncio lock are driven differently.
"""

from __future__ import annotations

import asyncio
import math
import threading
from collections.abc import Awaitable, Callable
from typing import Any, cast

import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync
from swgoh_comlink.exceptions import SwgohComlinkException, SwgohComlinkValueError

Client = SwgohComlink | SwgohComlinkAsync
Call = Callable[..., Awaitable[Any]]

# Not every test exercises all three mocked endpoints.
pytestmark = [pytest.mark.httpx_mock(assert_all_responses_were_requested=False)]

BASE_URL = "http://localhost:3000"
METADATA = {
    "latestGamedataVersion": "game-v1",
    "latestLocalizationBundleVersion": "lang-v1",
}


def _metadata_requests(httpx_mock: HTTPXMock) -> list:
    return [r for r in httpx_mock.get_requests() if r.url.path == "/metadata"]


def _mock_endpoints(httpx_mock: HTTPXMock, metadata: dict | None = None) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}/metadata", json=metadata or METADATA, is_reusable=True)
    httpx_mock.add_response(url=f"{BASE_URL}/data", json={"units": []}, is_reusable=True)
    httpx_mock.add_response(url=f"{BASE_URL}/localization", json={"localizationBundle": ""}, is_reusable=True)


# ── Cache rules (both clients) ───────────────────────────────────────────


async def test_repeated_game_data_calls_hit_metadata_once(comlink: Client, call: Call, httpx_mock: HTTPXMock):
    _mock_endpoints(httpx_mock)

    await call(comlink, "get_game_data")
    await call(comlink, "get_game_data")

    assert len(_metadata_requests(httpx_mock)) == 1


async def test_cache_shared_between_game_data_and_localization(comlink: Client, call: Call, httpx_mock: HTTPXMock):
    _mock_endpoints(httpx_mock)

    await call(comlink, "get_game_data")
    await call(comlink, "get_localization")

    assert len(_metadata_requests(httpx_mock)) == 1


async def test_ttl_expiry_triggers_refetch(
    make_comlink: Callable[..., Client], call: Call, httpx_mock: HTTPXMock, clock: dict[str, float]
):
    _mock_endpoints(httpx_mock)
    client = make_comlink(version_cache_ttl=60.0)

    await call(client, "get_game_data")
    clock["t"] += 59.0
    await call(client, "get_game_data")
    assert len(_metadata_requests(httpx_mock)) == 1

    clock["t"] += 2.0  # past the 60s TTL
    await call(client, "get_game_data")
    assert len(_metadata_requests(httpx_mock)) == 2


async def test_ttl_zero_disables_caching(make_comlink: Callable[..., Client], call: Call, httpx_mock: HTTPXMock):
    _mock_endpoints(httpx_mock)
    client = make_comlink(version_cache_ttl=0)

    await call(client, "get_game_data")
    await call(client, "get_game_data")

    assert len(_metadata_requests(httpx_mock)) == 2


async def test_infinite_ttl_caches_forever(
    make_comlink: Callable[..., Client], call: Call, httpx_mock: HTTPXMock, clock: dict[str, float]
):
    _mock_endpoints(httpx_mock)
    client = make_comlink(version_cache_ttl=math.inf)

    await call(client, "get_game_data")
    clock["t"] += 10**9
    await call(client, "get_game_data")

    assert len(_metadata_requests(httpx_mock)) == 1


async def test_invalidate_version_cache_forces_refetch(comlink: Client, call: Call, httpx_mock: HTTPXMock):
    _mock_endpoints(httpx_mock)

    await call(comlink, "get_game_data")
    comlink.invalidate_version_cache()
    await call(comlink, "get_game_data")

    assert len(_metadata_requests(httpx_mock)) == 2


async def test_get_latest_game_data_version_refresh_bypasses_cache(comlink: Client, call: Call, httpx_mock: HTTPXMock):
    _mock_endpoints(httpx_mock)

    versions = await call(comlink, "get_latest_game_data_version")
    assert versions == {"game": "game-v1", "language": "lang-v1"}
    assert await call(comlink, "get_latest_game_data_version") == versions
    assert len(_metadata_requests(httpx_mock)) == 1

    await call(comlink, "get_latest_game_data_version", refresh=True)
    assert len(_metadata_requests(httpx_mock)) == 2


@pytest.mark.parametrize(
    ("enums", "metadata_requests"),
    [
        pytest.param(False, 1, id="populates-cache"),
        # An enums=True response is not the plain version payload, so it must not be cached.
        pytest.param(True, 2, id="with-enums-does-not-populate-cache"),
    ],
)
async def test_get_game_metadata_and_the_cache(
    comlink: Client, call: Call, httpx_mock: HTTPXMock, enums: bool, metadata_requests: int
):
    _mock_endpoints(httpx_mock)

    await call(comlink, "get_game_metadata", enums=enums)
    await call(comlink, "get_game_data")

    assert len(_metadata_requests(httpx_mock)) == metadata_requests


async def test_explicit_version_skips_metadata_entirely(comlink: Client, call: Call, httpx_mock: HTTPXMock):
    _mock_endpoints(httpx_mock)

    await call(comlink, "get_game_data", version="explicit-version")
    await call(comlink, "get_localization", localization_id="explicit-loc-id")

    assert len(_metadata_requests(httpx_mock)) == 0


async def test_partial_metadata_supports_game_data_only(comlink: Client, call: Call, httpx_mock: HTTPXMock):
    """A /metadata response missing the localization key still serves get_game_data."""
    _mock_endpoints(httpx_mock, metadata={"latestGamedataVersion": "game-only"})

    await call(comlink, "get_game_data")

    with pytest.raises(SwgohComlinkException, match="latestLocalizationBundleVersion"):
        await call(comlink, "get_localization")


def test_negative_ttl_rejected(make_comlink: Callable[..., Client]):
    with pytest.raises(SwgohComlinkValueError):
        make_comlink(version_cache_ttl=-1)


# ── Concurrency: a caller waiting on the version lock ────────────────────
#
# Each test holds the version lock as if a first caller were fetching /metadata, starts a second
# caller that finds the cache cold and waits for the lock, fills the cache, then releases the lock.
# The second caller must use the stored versions instead of fetching /metadata again. No response
# is mocked, so any request fails the test.


def test_sync_caller_waiting_on_the_version_lock_uses_the_stored_versions(httpx_mock: HTTPXMock):
    lock = threading.Lock()
    waiting = threading.Event()

    class SignalingLock:
        def __enter__(self) -> None:
            waiting.set()
            lock.acquire()

        def __exit__(self, *exc: object) -> None:
            lock.release()

    client = SwgohComlink(url=BASE_URL)
    cast(Any, client)._version_lock = SignalingLock()
    result: dict[str, Any] = {}
    lock.acquire()
    second = threading.Thread(target=lambda: result.update(versions=client._get_versions()))
    second.start()
    try:
        assert waiting.wait(timeout=5), "the second caller never reached the lock"
        client._store_versions("game-v1", "lang-v1")
    finally:
        lock.release()
        second.join(timeout=5)
        client.close()

    assert (result["versions"].game, result["versions"].language) == ("game-v1", "lang-v1")
    assert httpx_mock.get_requests() == []


async def test_async_caller_waiting_on_the_version_lock_uses_the_stored_versions(httpx_mock: HTTPXMock):
    lock = asyncio.Lock()
    waiting = asyncio.Event()

    class SignalingLock:
        async def __aenter__(self) -> None:
            waiting.set()
            await lock.acquire()

        async def __aexit__(self, *exc: object) -> None:
            lock.release()

    async with SwgohComlinkAsync(url=BASE_URL) as client:
        cast(Any, client)._version_lock = SignalingLock()
        await lock.acquire()
        second = asyncio.create_task(client._get_versions())
        try:
            await asyncio.wait_for(waiting.wait(), timeout=5)
            client._store_versions("game-v1", "lang-v1")
        finally:
            lock.release()
        versions = await second

    assert (versions.game, versions.language) == ("game-v1", "lang-v1")
    assert httpx_mock.get_requests() == []
