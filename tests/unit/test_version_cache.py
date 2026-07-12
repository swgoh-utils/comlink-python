"""Tests for the instance-level game/localization version cache."""

from __future__ import annotations

import asyncio
import math

import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync
from swgoh_comlink.exceptions import SwgohComlinkException, SwgohComlinkValueError

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


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> dict[str, float]:
    """Controllable monotonic clock for cache expiry."""
    state = {"t": 1000.0}
    monkeypatch.setattr("swgoh_comlink._base._now", lambda: state["t"])
    return state


# ── Sync client ──────────────────────────────────────────────────────────


def test_repeated_game_data_calls_hit_metadata_once(httpx_mock: HTTPXMock):
    _mock_endpoints(httpx_mock)
    client = SwgohComlink(url=BASE_URL)

    client.get_game_data()
    client.get_game_data()

    assert len(_metadata_requests(httpx_mock)) == 1


def test_cache_shared_between_game_data_and_localization(httpx_mock: HTTPXMock):
    _mock_endpoints(httpx_mock)
    client = SwgohComlink(url=BASE_URL)

    client.get_game_data()
    client.get_localization()

    assert len(_metadata_requests(httpx_mock)) == 1


def test_ttl_expiry_triggers_refetch(httpx_mock: HTTPXMock, clock: dict[str, float]):
    _mock_endpoints(httpx_mock)
    client = SwgohComlink(url=BASE_URL, version_cache_ttl=60.0)

    client.get_game_data()
    clock["t"] += 59.0
    client.get_game_data()
    assert len(_metadata_requests(httpx_mock)) == 1

    clock["t"] += 2.0  # past the 60s TTL
    client.get_game_data()
    assert len(_metadata_requests(httpx_mock)) == 2


def test_ttl_zero_disables_caching(httpx_mock: HTTPXMock):
    _mock_endpoints(httpx_mock)
    client = SwgohComlink(url=BASE_URL, version_cache_ttl=0)

    client.get_game_data()
    client.get_game_data()

    assert len(_metadata_requests(httpx_mock)) == 2


def test_infinite_ttl_caches_forever(httpx_mock: HTTPXMock, clock: dict[str, float]):
    _mock_endpoints(httpx_mock)
    client = SwgohComlink(url=BASE_URL, version_cache_ttl=math.inf)

    client.get_game_data()
    clock["t"] += 10**9
    client.get_game_data()

    assert len(_metadata_requests(httpx_mock)) == 1


def test_invalidate_version_cache_forces_refetch(httpx_mock: HTTPXMock):
    _mock_endpoints(httpx_mock)
    client = SwgohComlink(url=BASE_URL)

    client.get_game_data()
    client.invalidate_version_cache()
    client.get_game_data()

    assert len(_metadata_requests(httpx_mock)) == 2


def test_get_latest_game_data_version_refresh_bypasses_cache(httpx_mock: HTTPXMock):
    _mock_endpoints(httpx_mock)
    client = SwgohComlink(url=BASE_URL)

    versions = client.get_latest_game_data_version()
    assert versions == {"game": "game-v1", "language": "lang-v1"}
    assert client.get_latest_game_data_version() == versions
    assert len(_metadata_requests(httpx_mock)) == 1

    client.get_latest_game_data_version(refresh=True)
    assert len(_metadata_requests(httpx_mock)) == 2


def test_get_game_metadata_populates_cache(httpx_mock: HTTPXMock):
    _mock_endpoints(httpx_mock)
    client = SwgohComlink(url=BASE_URL)

    client.get_game_metadata()
    client.get_game_data()

    assert len(_metadata_requests(httpx_mock)) == 1


def test_get_game_metadata_with_enums_does_not_populate_cache(httpx_mock: HTTPXMock):
    _mock_endpoints(httpx_mock)
    client = SwgohComlink(url=BASE_URL)

    client.get_game_metadata(enums=True)
    client.get_game_data()

    assert len(_metadata_requests(httpx_mock)) == 2


def test_explicit_version_skips_metadata_entirely(httpx_mock: HTTPXMock):
    _mock_endpoints(httpx_mock)
    client = SwgohComlink(url=BASE_URL)

    client.get_game_data(version="explicit-version")
    client.get_localization(localization_id="explicit-loc-id")

    assert len(_metadata_requests(httpx_mock)) == 0


def test_partial_metadata_supports_game_data_only(httpx_mock: HTTPXMock):
    """A /metadata response missing the localization key still serves get_game_data."""
    _mock_endpoints(httpx_mock, metadata={"latestGamedataVersion": "game-only"})
    client = SwgohComlink(url=BASE_URL)

    client.get_game_data()

    with pytest.raises(SwgohComlinkException, match="latestLocalizationBundleVersion"):
        client.get_localization()


def test_negative_ttl_rejected():
    with pytest.raises(SwgohComlinkValueError):
        SwgohComlink(url=BASE_URL, version_cache_ttl=-1)


# ── Async client ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_repeated_game_data_calls_hit_metadata_once(httpx_mock: HTTPXMock):
    _mock_endpoints(httpx_mock)
    async with SwgohComlinkAsync(url=BASE_URL) as client:
        await client.get_game_data()
        await client.get_game_data()

    assert len(_metadata_requests(httpx_mock)) == 1


@pytest.mark.asyncio
async def test_async_concurrent_cold_calls_single_flight(httpx_mock: HTTPXMock):
    _mock_endpoints(httpx_mock)
    async with SwgohComlinkAsync(url=BASE_URL) as client:
        await asyncio.gather(client.get_game_data(), client.get_game_data(), client.get_localization())

    assert len(_metadata_requests(httpx_mock)) == 1


@pytest.mark.asyncio
async def test_async_ttl_zero_disables_caching(httpx_mock: HTTPXMock):
    _mock_endpoints(httpx_mock)
    async with SwgohComlinkAsync(url=BASE_URL, version_cache_ttl=0) as client:
        await client.get_game_data()
        await client.get_game_data()

    assert len(_metadata_requests(httpx_mock)) == 2


@pytest.mark.asyncio
async def test_async_invalidate_and_refresh(httpx_mock: HTTPXMock, clock: dict[str, float]):
    _mock_endpoints(httpx_mock)
    async with SwgohComlinkAsync(url=BASE_URL, version_cache_ttl=60.0) as client:
        await client.get_game_data()
        client.invalidate_version_cache()
        await client.get_game_data()
        assert len(_metadata_requests(httpx_mock)) == 2

        clock["t"] += 61.0
        versions = await client.get_latest_game_data_version()
        assert versions == {"game": "game-v1", "language": "lang-v1"}
        assert len(_metadata_requests(httpx_mock)) == 3
