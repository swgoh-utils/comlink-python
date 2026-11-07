"""The opt-in ``max_response_bytes`` / ``max_game_data_bytes`` caps on response bodies, in both clients."""

from __future__ import annotations

import gzip
import json
from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest
from pytest_httpx import HTTPXMock, IteratorStream

from swgoh_comlink import RetryPolicy, SwgohComlink, SwgohComlinkAsync
from swgoh_comlink import retry as retry_module
from swgoh_comlink._base import GAME_DATA_TIMEOUT
from swgoh_comlink.exceptions import (
    SwgohComlinkHTTPError,
    SwgohComlinkRateLimitError,
    SwgohComlinkTypeError,
    SwgohComlinkValueError,
)

Client = SwgohComlink | SwgohComlinkAsync
CAP_ARGS = ("max_response_bytes", "max_game_data_bytes")


class Chunks:
    """A response body served in fixed chunks that records how many chunks the client pulled."""

    def __init__(self, body: bytes, size: int) -> None:
        self.parts = [body[i : i + size] for i in range(0, len(body), size)]
        self.served = 0

    def __iter__(self) -> Iterator[bytes]:
        for part in self.parts:
            self.served += 1
            yield part


def padded_json(size: int) -> bytes:
    """A JSON array of exactly *size* bytes."""
    return b"[" + b" " * (size - 2) + b"]"


@pytest.fixture
def no_stream(monkeypatch: pytest.MonkeyPatch) -> Callable[[Client], None]:
    """Make ``client.stream`` fail, to prove a request did not take the streaming path."""

    def patch(comlink: Client) -> None:
        def boom(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("client.stream() must not be used without a cap")

        for http_client in (comlink.client, comlink.stats_client):
            monkeypatch.setattr(http_client, "stream", boom)

    return patch


# ── Constructor ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("arg", CAP_ARGS)
async def test_caps_default_to_none(comlink: Client, arg: str) -> None:
    assert getattr(comlink, arg) is None


@pytest.mark.parametrize("arg", CAP_ARGS)
async def test_caps_are_stored(make_comlink: Callable[..., Client], arg: str) -> None:
    assert getattr(make_comlink(**{arg: 1024}), arg) == 1024


@pytest.mark.parametrize("arg", CAP_ARGS)
@pytest.mark.parametrize("value", [0, -1])
async def test_caps_must_be_positive(make_comlink: Callable[..., Client], arg: str, value: int) -> None:
    with pytest.raises(SwgohComlinkValueError, match=arg):
        make_comlink(**{arg: value})


@pytest.mark.parametrize("arg", CAP_ARGS)
@pytest.mark.parametrize("value", ["1024", 1024.0, True])
async def test_caps_must_be_int(make_comlink: Callable[..., Client], arg: str, value: object) -> None:
    with pytest.raises(SwgohComlinkTypeError, match=arg):
        make_comlink(**{arg: value})


# ── Default path is unchanged ────────────────────────────────────────────


async def test_no_cap_does_not_stream(comlink: Client, call, httpx_mock: HTTPXMock, no_stream) -> None:
    no_stream(comlink)
    httpx_mock.add_response(json={"latestGamedataVersion": "g"})
    httpx_mock.add_response(json={"units": []})
    assert await call(comlink, "get_game_metadata") == {"latestGamedataVersion": "g"}
    assert await call(comlink, "get_game_data", version="g") == {"units": []}


async def test_game_data_cap_alone_leaves_other_endpoints_unstreamed(
    make_comlink: Callable[..., Client], call, httpx_mock: HTTPXMock, no_stream
) -> None:
    comlink = make_comlink(max_game_data_bytes=10)
    no_stream(comlink)
    httpx_mock.add_response(content=padded_json(100))
    assert await call(comlink, "get_game_metadata") == []


async def test_response_cap_alone_leaves_game_data_unstreamed(
    make_comlink: Callable[..., Client], call, httpx_mock: HTTPXMock, no_stream
) -> None:
    comlink = make_comlink(max_response_bytes=10)
    no_stream(comlink)
    httpx_mock.add_response(content=b'{"units": []' + b" " * 100 + b"}")
    assert await call(comlink, "get_game_data", version="g") == {"units": []}


# ── Oversized bodies ─────────────────────────────────────────────────────


async def test_oversized_body_raises_and_stops_reading(
    make_comlink: Callable[..., Client], call, httpx_mock: HTTPXMock
) -> None:
    comlink = make_comlink(max_response_bytes=100)
    body = Chunks(padded_json(500), 50)
    httpx_mock.add_response(stream=IteratorStream(body))
    with pytest.raises(SwgohComlinkValueError, match=r"/metadata.*max_response_bytes.*100"):
        await call(comlink, "get_game_metadata")
    assert body.served == 3  # stopped at the first chunk past the cap


async def test_body_at_cap_is_accepted(make_comlink: Callable[..., Client], call, httpx_mock: HTTPXMock) -> None:
    comlink = make_comlink(max_response_bytes=100)
    httpx_mock.add_response(stream=IteratorStream(Chunks(padded_json(100), 30)))
    assert await call(comlink, "get_game_metadata") == []


async def test_content_length_over_cap_fails_before_reading(
    make_comlink: Callable[..., Client], call, httpx_mock: HTTPXMock
) -> None:
    comlink = make_comlink(max_response_bytes=100)
    body = Chunks(padded_json(500), 50)
    httpx_mock.add_response(headers={"Content-Length": "500"}, stream=IteratorStream(body))
    with pytest.raises(SwgohComlinkValueError, match=r"500 bytes.*max_response_bytes.*100"):
        await call(comlink, "get_game_metadata")
    assert body.served == 0


async def test_decompressed_size_is_what_counts(
    make_comlink: Callable[..., Client], call, httpx_mock: HTTPXMock
) -> None:
    """A small gzip body that inflates past the cap is stopped: Content-Length gives only the compressed size."""
    compressed = gzip.compress(padded_json(1_000_000))
    assert len(compressed) < 10_000
    comlink = make_comlink(max_response_bytes=10_000)
    httpx_mock.add_response(
        headers={"Content-Encoding": "gzip", "Content-Length": str(len(compressed))},
        stream=IteratorStream(Chunks(compressed, 512)),
    )
    with pytest.raises(SwgohComlinkValueError, match="max_response_bytes"):
        await call(comlink, "get_game_metadata")


async def test_game_data_uses_its_own_cap(make_comlink: Callable[..., Client], call, httpx_mock: HTTPXMock) -> None:
    comlink = make_comlink(max_response_bytes=10, max_game_data_bytes=1_000)
    httpx_mock.add_response(content=padded_json(500))
    assert await call(comlink, "get_game_data", version="g") == []
    httpx_mock.add_response(content=padded_json(2_000))
    with pytest.raises(SwgohComlinkValueError, match=r"/data.*max_game_data_bytes.*1000"):
        await call(comlink, "get_game_data", version="g")


async def test_stats_service_uses_response_cap(
    make_comlink: Callable[..., Client], call, httpx_mock: HTTPXMock
) -> None:
    comlink = make_comlink(max_response_bytes=10, max_game_data_bytes=1_000)
    httpx_mock.add_response(content=padded_json(100))
    with pytest.raises(SwgohComlinkValueError, match="max_response_bytes"):
        await call(comlink, "get_unit_stats", request_payload=[])


# ── The request itself is unchanged ──────────────────────────────────────


@pytest.mark.parametrize("caps", [{}, {"max_response_bytes": 10**6, "max_game_data_bytes": 10**6}])
async def test_streamed_request_matches_buffered_request(
    make_comlink: Callable[..., Client], call, httpx_mock: HTTPXMock, caps: dict[str, int]
) -> None:
    comlink = make_comlink(access_key="access", secret_key="secret", **caps)
    httpx_mock.add_response(json={})
    await call(comlink, "get_game_data", version="g", items=1)
    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert request.url == "http://localhost:3000/data"
    assert json.loads(request.content)["payload"]["version"] == "g"
    assert request.headers["Authorization"].startswith("HMAC-SHA256 ")
    assert request.extensions["timeout"]["read"] == GAME_DATA_TIMEOUT


# ── Error statuses ───────────────────────────────────────────────────────

RATE_LIMIT_BODY = b'{"code": "RATE_LIMITED", "message": "slow down"}'


async def test_error_within_cap_matches_uncapped_error(
    make_comlink: Callable[..., Client], call, httpx_mock: HTTPXMock
) -> None:
    errors = []
    for caps in ({}, {"max_response_bytes": 1_000}):
        httpx_mock.add_response(status_code=429, headers={"Retry-After": "3"}, content=RATE_LIMIT_BODY)
        with pytest.raises(SwgohComlinkRateLimitError) as caught:
            await call(make_comlink(**caps), "get_game_metadata")
        errors.append(caught.value)
    uncapped, capped = errors
    assert str(capped) == str(uncapped)
    assert (capped.status, capped.code, capped.detail, capped.retry_after) == (429, "RATE_LIMITED", "slow down", 3.0)
    assert capped.response is not None
    assert capped.response.content == RATE_LIMIT_BODY
    assert capped.response.headers["Retry-After"] == "3"
    assert isinstance(capped.__cause__, httpx.HTTPStatusError)


async def test_error_body_over_cap_is_cut_to_cap(
    make_comlink: Callable[..., Client], call, httpx_mock: HTTPXMock
) -> None:
    """An error body is read only up to the cap; the status still decides the exception class."""
    comlink = make_comlink(max_response_bytes=100)
    body = Chunks(b'{"code": "GAME_6", "message": "Rate exceeded!"}' + b" " * 10_000, 64)
    httpx_mock.add_response(status_code=502, headers={"Content-Length": "10047"}, stream=IteratorStream(body))
    with pytest.raises(SwgohComlinkRateLimitError) as caught:
        await call(comlink, "get_game_metadata")
    assert caught.value.status == 502
    assert caught.value.response is not None
    assert len(caught.value.response.content) == 100
    assert body.served == 2


async def test_gzip_error_body_is_decoded(make_comlink: Callable[..., Client], call, httpx_mock: HTTPXMock) -> None:
    comlink = make_comlink(max_response_bytes=1_000)
    httpx_mock.add_response(
        status_code=400, headers={"Content-Encoding": "gzip"}, stream=IteratorStream([gzip.compress(b"bad")])
    )
    with pytest.raises(SwgohComlinkHTTPError, match="HTTP 400: bad") as caught:
        await call(comlink, "get_game_metadata")
    assert caught.value.response is not None
    assert "content-encoding" not in caught.value.response.headers


async def test_retry_policy_still_retries_with_a_cap(
    make_comlink: Callable[..., Client], call, httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def no_wait(seconds: float) -> None:
        return None

    monkeypatch.setattr(retry_module, "_sleep", lambda seconds: None)
    monkeypatch.setattr(retry_module, "_async_sleep", no_wait)
    comlink = make_comlink(max_response_bytes=1_000, retry=RetryPolicy(attempts=2))
    httpx_mock.add_response(status_code=503, headers={"Retry-After": "0"})
    httpx_mock.add_response(json={"ok": True})
    assert await call(comlink, "get_game_metadata") == {"ok": True}
