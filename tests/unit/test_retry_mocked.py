"""Typed HTTP errors, retries and pacing through the sync and async clients (httpx mocked)."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
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
# get_enums() reads the game data version from /metadata before fetching /enums.
METADATA = {"latestGamedataVersion": "game-v1", "latestLocalizationBundleVersion": "lang-v1"}


@pytest.fixture
def waits(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Record every sleep the clients ask for instead of sleeping, on a frozen clock and without jitter."""
    recorded: list[float] = []

    async def async_sleep(seconds: float) -> None:
        recorded.append(seconds)

    monkeypatch.setattr(retry_module, "_sleep", recorded.append)
    monkeypatch.setattr(retry_module, "_async_sleep", async_sleep)
    monkeypatch.setattr(retry_module, "_clock", lambda: 1000.0)
    monkeypatch.setattr(retry_module, "_random", lambda: 0.0)
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
    httpx_mock.add_response(url=f"{URL}/metadata", json=METADATA)
    httpx_mock.add_response(url=f"{URL}/enums", status_code=500, text="Internal Server Error")

    with pytest.raises(SwgohComlinkException, match=r"^HTTP 500: Internal Server Error$"):
        SwgohComlink(url=URL).get_enums()


async def test_async_message_is_unchanged(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=f"{URL}/metadata", json=METADATA)
    httpx_mock.add_response(url=f"{URL}/enums", status_code=500, text="Internal Server Error")

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
    httpx_mock.add_response(url=f"{URL}/metadata", json=METADATA)
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"), url=f"{URL}/enums")

    with pytest.raises(SwgohComlinkException) as exc_info:
        SwgohComlink(url=URL, retry=RetryPolicy()).get_enums()

    assert not isinstance(exc_info.value, SwgohComlinkHTTPError)
    assert waits == []


async def test_async_no_retry_on_transport_error(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_response(url=f"{URL}/metadata", json=METADATA)
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"), url=f"{URL}/enums")

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

    # Retry-After 0, so the retry's only wait is its pacing slot on the frozen clock.
    assert waits == [pytest.approx(0.4)]


# ── Concurrency: cancelled batches, refusals together, endpoint holds ───


async def test_async_cancelled_batch_leaves_no_phantom_slots(
    httpx_mock: HTTPXMock, waits: list[float], monkeypatch: pytest.MonkeyPatch
) -> None:
    httpx_mock.add_response(json={"name": "Test Player"})
    parked: list[float] = []
    all_parked = asyncio.Event()

    async def blocking_sleep(seconds: float) -> None:
        parked.append(seconds)
        if len(parked) == 10:
            all_parked.set()
        await asyncio.Event().wait()

    async with SwgohComlinkAsync(url=URL, retry=RetryPolicy(min_interval=0.4)) as client:
        await client.get_player(allycode=123456789)
        monkeypatch.setattr(retry_module, "_async_sleep", blocking_sleep)
        batch = asyncio.gather(*(client.get_player(allycode=123456789) for _ in range(10)))
        await all_parked.wait()
        batch.cancel()
        with pytest.raises(asyncio.CancelledError):
            await batch

        # Only the call that ran still spaces the queue: one interval, not the 4.0 s the batch had queued.
        assert client._pace_delay("player", stats=False) == pytest.approx(0.4)

    assert parked == [pytest.approx(0.4 * n) for n in range(1, 11)]


def _refuse_first(count: int) -> Callable[[httpx.Request], httpx.Response]:
    """A callback refusing the first *count* requests with 'Rate exceeded!', then answering every request."""
    seen = [0]

    def callback(request: httpx.Request) -> httpx.Response:
        seen[0] += 1
        if seen[0] <= count:
            return httpx.Response(502, json=RATE_EXCEEDED)
        return httpx.Response(200, json={"name": "Test Player"})

    return callback


def _refuse_together(count: int) -> Callable[[httpx.Request], Awaitable[httpx.Response]]:
    """An async callback that holds the first *count* requests until all have arrived, then refuses them all."""
    arrived = [0]
    everyone_in = asyncio.Event()

    async def callback(request: httpx.Request) -> httpx.Response:
        arrived[0] += 1
        if arrived[0] > count:
            return httpx.Response(200, json={"name": "Test Player"})
        if arrived[0] == count:
            everyone_in.set()
        await everyone_in.wait()
        return httpx.Response(502, json=RATE_EXCEEDED)

    return callback


@pytest.mark.parametrize(("jitter", "spread"), [(0.0, False), (0.2, True)])
async def test_async_refusals_together_retry_spread_out(
    httpx_mock: HTTPXMock, waits: list[float], monkeypatch: pytest.MonkeyPatch, jitter: float, spread: bool
) -> None:
    httpx_mock.add_callback(_refuse_together(20), is_reusable=True)
    draws = iter(n / 20 for n in range(20))
    monkeypatch.setattr(retry_module, "_random", lambda: next(draws))

    async with SwgohComlinkAsync(url=URL, retry=RetryPolicy(jitter=jitter)) as client:
        await asyncio.gather(*(client.get_player(allycode=100000000 + n) for n in range(20)))

    # Twenty requests refused at the same moment, then one retry wait each.
    assert len(httpx_mock.get_requests()) == 40 and len(waits) == 20
    # Every retry waits at least the backoff; jitter only ever adds time.
    assert min(waits) == pytest.approx(5.0)
    if spread:
        assert len(set(waits)) == 20
        assert max(waits) - min(waits) == pytest.approx(0.95)
    else:
        # Without jitter all twenty retries are due at the same instant.
        assert set(waits) == {5.0}


def test_sync_rate_refusal_holds_back_later_calls_to_the_endpoint(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_callback(_refuse_first(1), is_reusable=True)
    client = SwgohComlink(url=URL, retry=RetryPolicy())

    client.get_player(allycode=123456789)  # refused once, retried after 5 s
    client.get_player(allycode=987654321)  # never refused, but the endpoint is still held

    assert waits == [5.0, 5.0]
    client.close()


def test_sync_rate_refusal_does_not_hold_unpaced_endpoints(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_callback(_refuse_first(1), is_reusable=True)
    client = SwgohComlink(url=URL, retry=RetryPolicy(unpaced_endpoints=frozenset({"player"})))

    client.get_player(allycode=123456789)
    client.get_player(allycode=987654321)

    # The refused call waits out its own retry; the next call is not held.
    assert waits == [5.0]
    client.close()


async def test_async_rate_refusal_holds_back_concurrent_callers(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_callback(_refuse_first(1), is_reusable=True)

    async with SwgohComlinkAsync(url=URL, retry=RetryPolicy()) as client:
        await client.get_player(allycode=123456789)
        await asyncio.gather(*(client.get_player(allycode=123456789) for _ in range(3)))

    # The refusal's 5 s hold covers the retry and the three calls that followed it on the same endpoint.
    assert waits == [5.0, 5.0, 5.0, 5.0]


def test_unavailable_is_not_held(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    httpx_mock.add_response(status_code=503, json=UNAVAILABLE)
    httpx_mock.add_response(json={"name": "Test Player"}, is_reusable=True)
    client = SwgohComlink(url=URL, retry=RetryPolicy())

    client.get_player(allycode=123456789)
    client.get_player(allycode=123456789)

    # A 503 says the service is busy, not that this endpoint is over its rate: only the retry waits.
    assert waits == [5.0]
    client.close()
