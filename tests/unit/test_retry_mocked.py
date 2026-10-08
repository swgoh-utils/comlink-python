"""Typed HTTP errors, retries and pacing through the sync and async clients (httpx mocked)."""

from __future__ import annotations

import asyncio
import json
import logging
from types import SimpleNamespace

import httpx
import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import RetryPolicy, SwgohComlink, SwgohComlinkAsync
from swgoh_comlink import _base as base_module
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


def test_sync_retry_re_signs_each_attempt(
    httpx_mock: HTTPXMock, waits: list[float], monkeypatch: pytest.MonkeyPatch
) -> None:
    httpx_mock.add_response(status_code=503, json=UNAVAILABLE)
    httpx_mock.add_response(json={"name": "Test Player"})
    # A wall clock that moves on between attempts, so a reused signature would show.
    ticks = iter([1_700_000_000.0, 1_700_000_005.0])
    monkeypatch.setattr(base_module, "time", SimpleNamespace(time=lambda: next(ticks)))

    client = SwgohComlink(url=URL, access_key="access", secret_key="secret", retry=RetryPolicy())
    client.get_player(allycode=123456789)

    first, second = httpx_mock.get_requests()
    assert first.headers["X-Date"] == "1700000000000"
    assert second.headers["X-Date"] == "1700000005000"
    assert first.headers["Authorization"] != second.headers["Authorization"]


# ── Giving up ────────────────────────────────────────────────────────────


def test_sync_logs_when_retries_run_out(
    httpx_mock: HTTPXMock, waits: list[float], caplog: pytest.LogCaptureFixture
) -> None:
    httpx_mock.add_response(status_code=429, is_reusable=True)

    with caplog.at_level(logging.INFO, logger="swgoh_comlink"), pytest.raises(SwgohComlinkRateLimitError):
        SwgohComlink(url=URL, retry=RetryPolicy(attempts=2)).get_player(allycode=123456789)

    assert caplog.messages[-1] == "SwgohComlinkRateLimitError on player; giving up after 2 attempts"


async def test_async_logs_when_retries_run_out(
    httpx_mock: HTTPXMock, waits: list[float], caplog: pytest.LogCaptureFixture
) -> None:
    httpx_mock.add_response(status_code=503, json=UNAVAILABLE, is_reusable=True)

    with caplog.at_level(logging.INFO, logger="swgoh_comlink"):
        async with SwgohComlinkAsync(url=URL, retry=RetryPolicy(attempts=2)) as client:
            with pytest.raises(SwgohComlinkUnavailableError):
                await client.get_player(allycode=123456789)

    assert caplog.messages[-1] == "SwgohComlinkUnavailableError on player; giving up after 2 attempts"


def test_no_give_up_log_without_a_retry(
    httpx_mock: HTTPXMock, waits: list[float], caplog: pytest.LogCaptureFixture
) -> None:
    httpx_mock.add_response(status_code=400, is_reusable=True)

    with caplog.at_level(logging.INFO, logger="swgoh_comlink"):
        for client in (SwgohComlink(url=URL), SwgohComlink(url=URL, retry=RetryPolicy())):
            with pytest.raises(SwgohComlinkClientError):
                client.get_player(allycode=123456789)

    assert not any("giving up" in message for message in caplog.messages)


# ── Pacing ───────────────────────────────────────────────────────────────


def test_sync_paces_calls_to_the_same_endpoint(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_response(json={"name": "Test Player"}, is_reusable=True)

    client = SwgohComlink(url=URL, retry=RetryPolicy(min_interval=0.4, unpaced_endpoints=frozenset({"guild"})))
    for _ in range(3):
        client.get_player(allycode=123456789)
    client.get_guild(guild_id="g1")
    client.get_guild(guild_id="g1")

    assert waits == [pytest.approx(0.4), pytest.approx(0.8)]


async def test_async_paces_concurrent_calls_in_order(
    httpx_mock: HTTPXMock, waits: list[float], monkeypatch: pytest.MonkeyPatch
) -> None:
    httpx_mock.add_response(json={"name": "Test Player"}, is_reusable=True)
    real_sleep = asyncio.sleep

    async def scaled_sleep(seconds: float) -> None:
        # Actually yield, at 1/100 speed, so the tasks can overtake one another.
        waits.append(seconds)
        await real_sleep(seconds / 100)

    monkeypatch.setattr(retry_module, "_async_sleep", scaled_sleep)
    allycodes = [111111111, 222222222, 333333333]

    async with SwgohComlinkAsync(url=URL, retry=RetryPolicy(min_interval=0.4)) as client:
        await asyncio.gather(*(client.get_player(allycode=code) for code in allycodes))

    assert waits == [pytest.approx(0.4), pytest.approx(0.8)]
    sent = [json.loads(request.content)["payload"]["allyCode"] for request in httpx_mock.get_requests()]
    assert sent == [str(code) for code in allycodes]


async def test_async_cancelled_wait_gives_its_slot_back(
    httpx_mock: HTTPXMock, waits: list[float], monkeypatch: pytest.MonkeyPatch
) -> None:
    httpx_mock.add_response(json={"name": "Test Player"}, is_reusable=True)
    parked = asyncio.Event()

    async def blocking_sleep(seconds: float) -> None:
        waits.append(seconds)
        parked.set()
        await asyncio.Event().wait()

    async with SwgohComlinkAsync(url=URL, retry=RetryPolicy(min_interval=0.4)) as client:
        await client.get_player(allycode=123456789)
        monkeypatch.setattr(retry_module, "_async_sleep", blocking_sleep)
        task = asyncio.create_task(client.get_player(allycode=123456789))
        await parked.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        # The cancelled task's slot is free, so the next caller waits one interval, not two.
        assert client._pace_delay("player", stats=False) == pytest.approx(0.4)

    assert waits == [pytest.approx(0.4)]
    assert len(httpx_mock.get_requests()) == 1


def test_sync_pacing_applies_to_retries(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "0"})
    httpx_mock.add_response(json={"name": "Test Player"})

    SwgohComlink(url=URL, retry=RetryPolicy(min_interval=0.4)).get_player(allycode=123456789)

    # Retry-After 0, then the retry still waits its pacing slot on the frozen clock.
    assert waits == [0.0, pytest.approx(0.4)]
