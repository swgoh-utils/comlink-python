# coding=utf-8
"""Phase 8 — :meth:`healthcheck`, :meth:`raw_request`,
:meth:`stream_game_data`, :meth:`stream_localization`.

Each ergonomic method tested for sync + async parity. Streaming uses
``httpx.Client.stream`` / ``AsyncClient.stream`` which is a context
manager; we just verify the bytes round-trip without materializing the
body in memory.
"""

from __future__ import annotations

import httpx
import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import RetryPolicy, SwgohComlink, SwgohComlinkAsync
from swgoh_comlink.exceptions import SwgohComlinkClientError, SwgohComlinkException, SwgohComlinkUnavailableError

# ── healthcheck ─────────────────────────────────────────────────────────────


def test_healthcheck_returns_true_on_200(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"x": 1})
    client = SwgohComlink(url="http://comlink.test")
    try:
        assert client.healthcheck() is True
    finally:
        client.close()


def test_healthcheck_returns_false_on_5xx(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=503)
    client = SwgohComlink(url="http://comlink.test")
    try:
        assert client.healthcheck() is False
    finally:
        client.close()


def test_healthcheck_returns_false_on_connect_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(httpx.ConnectError("refused"))
    client = SwgohComlink(url="http://comlink.test")
    try:
        assert client.healthcheck() is False
    finally:
        client.close()


def test_healthcheck_returns_false_on_timeout(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(httpx.TimeoutException("slow"))
    client = SwgohComlink(url="http://comlink.test")
    try:
        assert client.healthcheck(timeout=0.1) is False
    finally:
        client.close()


def test_healthcheck_does_not_retry(httpx_mock: HTTPXMock) -> None:
    """Even with retry=RetryPolicy(backoff=(), jitter=0.0), healthcheck makes exactly one attempt."""
    httpx_mock.add_response(status_code=500)
    client = SwgohComlink(url="http://comlink.test", retry=RetryPolicy(backoff=(), jitter=0.0))
    try:
        assert client.healthcheck() is False
        assert len(httpx_mock.get_requests()) == 1
    finally:
        client.close()


async def test_async_healthcheck_returns_true(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"x": 1})
    client = SwgohComlinkAsync(url="http://comlink.test")
    try:
        assert await client.healthcheck() is True
    finally:
        await client.aclose()


async def test_async_healthcheck_returns_false_on_5xx(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=503)
    client = SwgohComlinkAsync(url="http://comlink.test")
    try:
        assert await client.healthcheck() is False
    finally:
        await client.aclose()


# ── raw_request ─────────────────────────────────────────────────────────────


def test_raw_request_returns_httpx_response_unchanged(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"a": 1, "b": [2, 3]})
    client = SwgohComlink(url="http://comlink.test")
    try:
        r = client.raw_request("POST", "custom-endpoint", payload={"foo": "bar"})
    finally:
        client.close()
    assert isinstance(r, httpx.Response)
    assert r.status_code == 200
    assert r.json() == {"a": 1, "b": [2, 3]}


def test_raw_request_attaches_hmac_headers(httpx_mock: HTTPXMock) -> None:
    """HMAC headers should still ride along the raw path."""
    httpx_mock.add_response(json={})
    client = SwgohComlink(
        url="http://comlink.test",
        access_key="test_access",
        secret_key="test_secret",
    )
    try:
        client.raw_request("POST", "anything", payload={"x": 1})
    finally:
        client.close()
    req = httpx_mock.get_request()
    assert req is not None
    assert "x-date" in req.headers
    assert "authorization" in req.headers


def test_raw_request_bypasses_retry(httpx_mock: HTTPXMock) -> None:
    """503 returns the response object; does NOT retry or raise."""
    httpx_mock.add_response(status_code=503, json={"err": "down"})
    client = SwgohComlink(url="http://comlink.test", retry=RetryPolicy(backoff=(), jitter=0.0))
    try:
        r = client.raw_request("POST", "anything", payload={})
    finally:
        client.close()
    assert r.status_code == 503
    assert len(httpx_mock.get_requests()) == 1


async def test_async_raw_request_returns_response(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"ok": True})
    client = SwgohComlinkAsync(url="http://comlink.test")
    try:
        r = await client.raw_request("POST", "stuff", payload={})
    finally:
        await client.aclose()
    assert isinstance(r, httpx.Response)
    assert r.json() == {"ok": True}


# ── stream_game_data ────────────────────────────────────────────────────────


def test_stream_game_data_yields_bytes(httpx_mock: HTTPXMock) -> None:
    big_body = b'{"units": [' + b'{"id":"x"},' * 1000 + b'{"id":"end"}]}'
    httpx_mock.add_response(content=big_body)
    client = SwgohComlink(url="http://comlink.test")
    try:
        chunks: list[bytes] = []
        with client.stream_game_data(version="known-version") as r:
            r.raise_for_status()
            for chunk in r.iter_bytes():
                chunks.append(chunk)
    finally:
        client.close()
    assert b"".join(chunks) == big_body


def test_stream_game_data_metadata_fallback(httpx_mock: HTTPXMock) -> None:
    """Sync stream resolves version=`""` via a metadata fetch."""
    # First call: metadata; second call: streaming /data
    httpx_mock.add_response(json={"latestGamedataVersion": "v-resolved"})
    httpx_mock.add_response(content=b'{"ok": 1}')
    client = SwgohComlink(url="http://comlink.test")
    try:
        with client.stream_game_data() as r:
            list(r.iter_bytes())
    finally:
        client.close()
    # Verify the metadata call happened
    assert len(httpx_mock.get_requests()) == 2


async def test_async_stream_game_data_yields_bytes(httpx_mock: HTTPXMock) -> None:
    big_body = b'{"data": "abc"}'
    httpx_mock.add_response(content=big_body)
    client = SwgohComlinkAsync(url="http://comlink.test")
    try:
        chunks: list[bytes] = []
        async with client.stream_game_data(version="v1") as r:
            r.raise_for_status()
            async for chunk in r.aiter_bytes():
                chunks.append(chunk)
    finally:
        await client.aclose()
    assert b"".join(chunks) == big_body


async def test_async_stream_game_data_requires_version() -> None:
    """Without an explicit version, the async variant raises (no awaitable fallback)."""
    client = SwgohComlinkAsync(url="http://comlink.test")
    try:
        with pytest.raises(ValueError, match="pass version="):
            client.stream_game_data()  # version="" triggers the guard
    finally:
        await client.aclose()


# ── stream_localization ─────────────────────────────────────────────────────


def test_stream_localization_yields_bytes(httpx_mock: HTTPXMock) -> None:
    body = b'{"strings": {"hello": "Hello"}}'
    httpx_mock.add_response(content=body)
    client = SwgohComlink(url="http://comlink.test")
    try:
        chunks: list[bytes] = []
        with client.stream_localization(localization_id="known", locale="ENG_US") as r:
            for chunk in r.iter_bytes():
                chunks.append(chunk)
    finally:
        client.close()
    assert b"".join(chunks) == body


async def test_async_stream_localization_yields_bytes(httpx_mock: HTTPXMock) -> None:
    body = b'{"x": 1}'
    httpx_mock.add_response(content=body)
    client = SwgohComlinkAsync(url="http://comlink.test")
    try:
        async with client.stream_localization("known", locale="ENG_US") as r:
            chunks = [c async for c in r.aiter_bytes()]
    finally:
        await client.aclose()
    assert b"".join(chunks) == body


# ── streaming error mapping ─────────────────────────────────────────────────


def test_stream_game_data_raises_typed_error_on_error_status(httpx_mock: HTTPXMock) -> None:
    """An error status raises the typed HTTP error on entry, with the comlink error body parsed."""
    httpx_mock.add_response(status_code=503, json={"code": "UNAVAILABLE", "message": "busy"})
    client = SwgohComlink(url="http://comlink.test")
    try:
        with (
            pytest.raises(SwgohComlinkUnavailableError, match="HTTP 503") as exc_info,
            client.stream_game_data(version="v1"),
        ):
            pytest.fail("the stream body must not run for an error response")
    finally:
        client.close()
    assert exc_info.value.detail == "busy"
    assert len(httpx_mock.get_requests()) == 1


def test_stream_localization_maps_transport_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(httpx.ConnectError("refused"))
    client = SwgohComlink(url="http://comlink.test")
    try:
        with (
            pytest.raises(SwgohComlinkException, match="refused"),
            client.stream_localization(localization_id="known"),
        ):
            pytest.fail("the stream body must not run when the connection fails")
    finally:
        client.close()


async def test_async_stream_game_data_raises_typed_error_on_error_status(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=400, json={"code": "BAD_REQUEST", "message": "bad version"})
    client = SwgohComlinkAsync(url="http://comlink.test")
    try:
        with pytest.raises(SwgohComlinkClientError, match="HTTP 400") as exc_info:
            async with client.stream_game_data(version="v1"):
                pytest.fail("the stream body must not run for an error response")
    finally:
        await client.aclose()
    assert exc_info.value.code == "BAD_REQUEST"


async def test_async_stream_localization_maps_transport_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(httpx.ConnectError("refused"))
    client = SwgohComlinkAsync(url="http://comlink.test")
    try:
        with pytest.raises(SwgohComlinkException, match="refused"):
            async with client.stream_localization("known"):
                pytest.fail("the stream body must not run when the connection fails")
    finally:
        await client.aclose()


# ── kwarg + signature shape ─────────────────────────────────────────────────


def test_healthcheck_returns_bool_type(httpx_mock: HTTPXMock) -> None:
    """Documented contract: returns the literal bool, never raises."""
    # Even a malformed response shouldn't raise — healthcheck swallows errors.
    httpx_mock.add_response(status_code=200, content=b"not json")
    client = SwgohComlink(url="http://comlink.test")
    try:
        result = client.healthcheck()
        assert isinstance(result, bool)
        assert result is True  # 200 status; we don't validate body
    finally:
        client.close()
