"""Typed HTTP errors, retries and pacing through the sync and async clients (httpx mocked)."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import RetryPolicy, SwgohComlink, SwgohComlinkAsync
from swgoh_comlink import retry as retry_module
from swgoh_comlink.exceptions import (
    SwgohComlinkClientError,
    SwgohComlinkException,
    SwgohComlinkHTTPError,
    SwgohComlinkRateLimitError,
    SwgohComlinkUnavailableError,
)

URL = "http://localhost:3000"
RATE_EXCEEDED = {"code": "GAME_6", "message": "Rate exceeded!"}
UNAVAILABLE = {"code": "UNAVAILABLE", "message": "server is at capacity"}


@pytest.fixture
def waits(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Record every sleep the clients ask for instead of sleeping, on a frozen clock."""
    recorded: list[float] = []

    async def async_sleep(seconds: float) -> None:
        recorded.append(seconds)

    monkeypatch.setattr(retry_module, "_sleep", recorded.append)
    monkeypatch.setattr(retry_module, "_async_sleep", async_sleep)
    monkeypatch.setattr(retry_module, "_clock", lambda: 1000.0)
    return recorded


# ── Typed errors ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (429, {"code": "RATE_LIMITED", "message": "too many requests"}, SwgohComlinkRateLimitError),
        (502, RATE_EXCEEDED, SwgohComlinkRateLimitError),
        (503, UNAVAILABLE, SwgohComlinkUnavailableError),
        (400, {"code": "BAD_REQUEST", "message": "missing allyCode"}, SwgohComlinkClientError),
        (500, {"code": "INTERNAL", "message": "boom"}, SwgohComlinkHTTPError),
    ],
)
def test_sync_raises_typed_error(
    httpx_mock: HTTPXMock, status: int, body: dict[str, str], expected: type[SwgohComlinkHTTPError]
) -> None:
    httpx_mock.add_response(status_code=status, json=body, headers={"Retry-After": "2"})

    with pytest.raises(expected) as exc_info:
        SwgohComlink(url=URL).get_player(allycode=123456789)

    error = exc_info.value
    assert type(error) is expected
    assert error.response is not None
    assert str(error) == f"HTTP {status}: {error.response.text}"
    assert error.status == status
    assert error.code == body["code"]
    assert error.detail == body["message"]
    assert error.retry_after == 2.0
    assert isinstance(error.__cause__, httpx.HTTPStatusError)


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (429, {"code": "RATE_LIMITED", "message": "too many requests"}, SwgohComlinkRateLimitError),
        (502, RATE_EXCEEDED, SwgohComlinkRateLimitError),
        (503, UNAVAILABLE, SwgohComlinkUnavailableError),
        (400, {"code": "BAD_REQUEST", "message": "missing allyCode"}, SwgohComlinkClientError),
        (500, {"code": "INTERNAL", "message": "boom"}, SwgohComlinkHTTPError),
    ],
)
async def test_async_raises_typed_error(
    httpx_mock: HTTPXMock, status: int, body: dict[str, str], expected: type[SwgohComlinkHTTPError]
) -> None:
    httpx_mock.add_response(status_code=status, json=body, headers={"Retry-After": "2"})

    async with SwgohComlinkAsync(url=URL) as client:
        with pytest.raises(expected) as exc_info:
            await client.get_player(allycode=123456789)

    error = exc_info.value
    assert type(error) is expected
    assert error.status == status
    assert error.code == body["code"]
    assert error.detail == body["message"]
    assert error.retry_after == 2.0
    assert isinstance(error.__cause__, httpx.HTTPStatusError)


def test_sync_message_is_unchanged(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=500, text="Internal Server Error")

    with pytest.raises(SwgohComlinkException, match=r"^HTTP 500: Internal Server Error$"):
        SwgohComlink(url=URL).get_enums()


async def test_async_message_is_unchanged(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=500, text="Internal Server Error")

    async with SwgohComlinkAsync(url=URL) as client:
        with pytest.raises(SwgohComlinkException, match=r"^HTTP 500: Internal Server Error$"):
            await client.get_enums()


# ── Retry is off by default ──────────────────────────────────────────────


def test_sync_no_retry_by_default(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "1"})

    with pytest.raises(SwgohComlinkRateLimitError):
        SwgohComlink(url=URL).get_player(allycode=123456789)

    assert len(httpx_mock.get_requests()) == 1
    assert waits == []


async def test_async_no_retry_by_default(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_response(status_code=503, json=UNAVAILABLE, headers={"Retry-After": "1"})

    async with SwgohComlinkAsync(url=URL) as client:
        with pytest.raises(SwgohComlinkUnavailableError):
            await client.get_player(allycode=123456789)

    assert len(httpx_mock.get_requests()) == 1
    assert waits == []


# ── Retrying ─────────────────────────────────────────────────────────────


def test_sync_retries_429_then_succeeds(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_response(status_code=429)
    httpx_mock.add_response(json={"name": "Test Player"})

    out = SwgohComlink(url=URL, retry=RetryPolicy()).get_player(allycode=123456789)

    assert out == {"name": "Test Player"}
    assert len(httpx_mock.get_requests()) == 2
    assert waits == [5.0]


async def test_async_retries_429_then_succeeds(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_response(status_code=429)
    httpx_mock.add_response(json={"name": "Test Player"})

    async with SwgohComlinkAsync(url=URL, retry=RetryPolicy()) as client:
        out = await client.get_player(allycode=123456789)

    assert out == {"name": "Test Player"}
    assert len(httpx_mock.get_requests()) == 2
    assert waits == [5.0]


def test_sync_honours_and_clamps_retry_after(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_response(status_code=503, json=UNAVAILABLE, headers={"Retry-After": "1"})
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "3600"})
    httpx_mock.add_response(json={"latestGamedataVersion": "1"})

    SwgohComlink(url=URL, retry=RetryPolicy(max_retry_after=30.0)).get_game_metadata()

    assert waits == [1.0, 30.0]


async def test_async_honours_and_clamps_retry_after(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_response(status_code=503, json=UNAVAILABLE, headers={"Retry-After": "1"})
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "3600"})
    httpx_mock.add_response(json={"latestGamedataVersion": "1"})

    async with SwgohComlinkAsync(url=URL, retry=RetryPolicy(max_retry_after=30.0)) as client:
        await client.get_game_metadata()

    assert waits == [1.0, 30.0]


def test_sync_rate_refusal_backs_off_then_stands(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    for _ in range(3):
        httpx_mock.add_response(status_code=502, json=RATE_EXCEEDED)

    with pytest.raises(SwgohComlinkRateLimitError) as exc_info:
        SwgohComlink(url=URL, retry=RetryPolicy(attempts=3)).get_player(allycode=123456789)

    assert len(httpx_mock.get_requests()) == 3
    assert waits == [5.0, 10.0]
    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)


async def test_async_rate_refusal_backs_off_then_stands(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    for _ in range(3):
        httpx_mock.add_response(status_code=502, json=RATE_EXCEEDED)

    async with SwgohComlinkAsync(url=URL, retry=RetryPolicy(attempts=3)) as client:
        with pytest.raises(SwgohComlinkRateLimitError):
            await client.get_player(allycode=123456789)

    assert len(httpx_mock.get_requests()) == 3
    assert waits == [5.0, 10.0]


@pytest.mark.parametrize(("status", "expected"), [(400, SwgohComlinkClientError), (500, SwgohComlinkHTTPError)])
def test_sync_no_retry_on_client_or_server_error(
    httpx_mock: HTTPXMock, waits: list[float], status: int, expected: type[SwgohComlinkHTTPError]
) -> None:
    httpx_mock.add_response(status_code=status, json={"code": "X", "message": "no"})

    with pytest.raises(expected):
        SwgohComlink(url=URL, retry=RetryPolicy()).get_player(allycode=123456789)

    assert len(httpx_mock.get_requests()) == 1
    assert waits == []


@pytest.mark.parametrize(("status", "expected"), [(400, SwgohComlinkClientError), (500, SwgohComlinkHTTPError)])
async def test_async_no_retry_on_client_or_server_error(
    httpx_mock: HTTPXMock, waits: list[float], status: int, expected: type[SwgohComlinkHTTPError]
) -> None:
    httpx_mock.add_response(status_code=status, json={"code": "X", "message": "no"})

    async with SwgohComlinkAsync(url=URL, retry=RetryPolicy()) as client:
        with pytest.raises(expected):
            await client.get_player(allycode=123456789)

    assert len(httpx_mock.get_requests()) == 1
    assert waits == []


def test_sync_no_retry_on_transport_error(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))

    with pytest.raises(SwgohComlinkException) as exc_info:
        SwgohComlink(url=URL, retry=RetryPolicy()).get_enums()

    assert not isinstance(exc_info.value, SwgohComlinkHTTPError)
    assert waits == []


async def test_async_no_retry_on_transport_error(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))

    async with SwgohComlinkAsync(url=URL, retry=RetryPolicy()) as client:
        with pytest.raises(SwgohComlinkException) as exc_info:
            await client.get_enums()

    assert not isinstance(exc_info.value, SwgohComlinkHTTPError)
    assert waits == []


def test_sync_retry_re_signs_each_attempt(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_response(status_code=503, json=UNAVAILABLE)
    httpx_mock.add_response(json={"name": "Test Player"})

    client = SwgohComlink(url=URL, access_key="access", secret_key="secret", retry=RetryPolicy())
    client.get_player(allycode=123456789)

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert all("Authorization" in request.headers and "X-Date" in request.headers for request in requests)


# ── Pacing ───────────────────────────────────────────────────────────────


def test_sync_paces_calls_to_the_same_endpoint(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_response(json={"name": "Test Player"}, is_reusable=True)

    client = SwgohComlink(url=URL, retry=RetryPolicy(min_interval=0.4, unpaced_endpoints=frozenset({"guild"})))
    for _ in range(3):
        client.get_player(allycode=123456789)
    client.get_guild(guild_id="g1")
    client.get_guild(guild_id="g1")

    assert waits == [pytest.approx(0.4), pytest.approx(0.8)]


async def test_async_paces_concurrent_calls_in_order(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_response(json={"name": "Test Player"}, is_reusable=True)

    async with SwgohComlinkAsync(url=URL, retry=RetryPolicy(min_interval=0.4)) as client:
        await asyncio.gather(*(client.get_player(allycode=123456789) for _ in range(3)))

    assert sorted(waits) == [pytest.approx(0.4), pytest.approx(0.8)]


def test_sync_pacing_applies_to_retries(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "0"})
    httpx_mock.add_response(json={"name": "Test Player"})

    SwgohComlink(url=URL, retry=RetryPolicy(min_interval=0.4)).get_player(allycode=123456789)

    # Retry-After 0, then the retry still waits its pacing slot on the frozen clock.
    assert waits == [0.0, pytest.approx(0.4)]
