# coding=utf-8
"""Version cache, enums cache and typed HTTP errors on the typed clients.

The dict clients are covered by ``tests/unit/test_version_cache.py``,
``test_enums_cache.py`` and ``test_retry_mocked.py``. The typed clients share
the generated pipeline but decode ``/metadata`` into a :class:`Metadata`
Struct, so the version extraction runs down a different path; these tests
pin that path for both the sync and async typed variants.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import RetryPolicy
from swgoh_comlink._models import Metadata
from swgoh_comlink.exceptions import SwgohComlinkRateLimitError
from swgoh_comlink.typed import SwgohComlink as TypedSwgohComlink
from swgoh_comlink.typed import SwgohComlinkAsync as TypedSwgohComlinkAsync

TypedClient = TypedSwgohComlink | TypedSwgohComlinkAsync

URL = "http://comlink.test"
METADATA = {"latestGamedataVersion": "game-v1", "latestLocalizationBundleVersion": "lang-v1"}

pytestmark = [pytest.mark.httpx_mock(assert_all_responses_were_requested=False)]


@pytest.fixture(params=[TypedSwgohComlink, TypedSwgohComlinkAsync], ids=["typed-sync", "typed-async"])
async def make_client(request: pytest.FixtureRequest) -> AsyncIterator[Callable[..., TypedClient]]:
    clients: list[TypedClient] = []

    def factory(**kwargs: Any) -> TypedClient:
        client = request.param(url=URL, **kwargs)
        clients.append(client)
        return client

    yield factory
    for client in clients:
        if isinstance(client, TypedSwgohComlinkAsync):
            await client.aclose()
        else:
            client.close()


async def call(client: TypedClient, method: str, /, *args: Any, **kwargs: Any) -> Any:
    result = getattr(client, method)(*args, **kwargs)
    return await result if inspect.isawaitable(result) else result


def _requests_to(httpx_mock: HTTPXMock, path: str) -> int:
    return sum(1 for r in httpx_mock.get_requests() if r.url.path == path)


def _mock(httpx_mock: HTTPXMock, metadata: dict[str, str] | None = None) -> None:
    httpx_mock.add_response(url=f"{URL}/metadata", json=metadata or METADATA, is_reusable=True)
    httpx_mock.add_response(url=f"{URL}/enums", json={"CombatType": {"CHARACTER": 1}}, is_reusable=True)
    httpx_mock.add_response(url=f"{URL}/data", json={"units": []}, is_reusable=True)
    httpx_mock.add_response(url=f"{URL}/localization", json={"localizationBundle": ""}, is_reusable=True)


async def test_typed_metadata_populates_the_version_cache(
    make_client: Callable[..., TypedClient], httpx_mock: HTTPXMock
) -> None:
    _mock(httpx_mock)
    client = make_client()

    metadata = await call(client, "get_game_metadata")
    assert isinstance(metadata, Metadata)
    # The Struct response stored the versions, so neither call below re-fetches /metadata.
    await call(client, "get_game_data")
    await call(client, "get_localization")
    assert await call(client, "get_latest_game_data_version") == {"game": "game-v1", "language": "lang-v1"}

    assert _requests_to(httpx_mock, "/metadata") == 1
    data_body = json.loads(next(r for r in httpx_mock.get_requests() if r.url.path == "/data").content)
    assert data_body["payload"]["version"] == "game-v1"


async def test_typed_cold_cache_fetches_metadata_once(
    make_client: Callable[..., TypedClient], httpx_mock: HTTPXMock
) -> None:
    _mock(httpx_mock)
    client = make_client()

    await call(client, "get_game_data")
    await call(client, "get_game_data")
    assert _requests_to(httpx_mock, "/metadata") == 1

    assert await call(client, "get_latest_game_data_version", refresh=True) == {
        "game": "game-v1",
        "language": "lang-v1",
    }
    assert _requests_to(httpx_mock, "/metadata") == 2


async def test_typed_get_enums_is_cached_per_game_data_version(
    make_client: Callable[..., TypedClient], httpx_mock: HTTPXMock
) -> None:
    _mock(httpx_mock)
    client = make_client()

    first = await call(client, "get_enums")
    second = await call(client, "get_enums")
    assert first is second is client.enums
    assert client.enums_version == "game-v1"
    assert _requests_to(httpx_mock, "/enums") == 1

    await call(client, "get_enums", refresh=True)
    assert _requests_to(httpx_mock, "/enums") == 2


async def test_typed_enums_metadata_response_is_not_cached(
    make_client: Callable[..., TypedClient], httpx_mock: HTTPXMock
) -> None:
    """``enums=True`` responses may carry translated values, so they never feed the cache."""
    _mock(httpx_mock)
    client = make_client()

    await call(client, "get_game_metadata", enums=True)
    await call(client, "get_game_data")
    assert _requests_to(httpx_mock, "/metadata") == 2


async def test_typed_client_specs_use_camel_case(
    make_client: Callable[..., TypedClient], httpx_mock: HTTPXMock
) -> None:
    _mock(httpx_mock)
    client = make_client()
    specs = {"platform": "Android"}

    await call(client, "get_game_metadata", client_specs=specs, raw=True)

    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body == {"payload": {"clientSpecs": specs}, "enums": False}


async def test_typed_endpoint_raises_typed_error_and_retries(
    make_client: Callable[..., TypedClient], httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    from swgoh_comlink import retry as retry_module

    waits: list[float] = []

    async def async_sleep(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr(retry_module, "_sleep", waits.append)
    monkeypatch.setattr(retry_module, "_async_sleep", async_sleep)
    monkeypatch.setattr(retry_module, "_clock", lambda: 1000.0)

    rate_exceeded = {"code": "GAME_6", "message": "Rate exceeded!"}
    httpx_mock.add_response(url=f"{URL}/player", status_code=502, json=rate_exceeded)
    httpx_mock.add_response(url=f"{URL}/player", status_code=502, json=rate_exceeded)

    client = make_client(retry=RetryPolicy(attempts=2, backoff=(3.0,), jitter=0.0))
    with pytest.raises(SwgohComlinkRateLimitError) as exc_info:
        await call(client, "get_player", allycode=123456789)

    assert exc_info.value.status == 502
    assert _requests_to(httpx_mock, "/player") == 2
    assert waits == [3.0]
