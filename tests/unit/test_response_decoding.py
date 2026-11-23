"""Both transports expose one documented exception family for invalid responses."""

import json

import pytest

from swgoh_comlink.exceptions import SwgohComlinkDecodeError, SwgohComlinkException


@pytest.mark.parametrize(
    ("body", "cause"),
    [(b"<html>error</html>", json.JSONDecodeError), (b"\xff", UnicodeDecodeError), (b"", json.JSONDecodeError)],
)
async def test_decode_errors_preserve_cause(comlink, call, httpx_mock, body, cause):
    httpx_mock.add_response(content=body)
    with pytest.raises(SwgohComlinkException) as caught:
        await call(comlink, "get_game_metadata")
    assert isinstance(caught.value, SwgohComlinkDecodeError)
    assert isinstance(caught.value.__cause__, cause)
    # Compatible with handlers written for the json.JSONDecodeError raised before.
    assert isinstance(caught.value, ValueError)
    # The response body is not echoed into the message.
    if body:
        assert body.decode("utf-8", errors="replace") not in str(caught.value)


@pytest.mark.parametrize("body", ["null", "true", "42", '"text"'])
async def test_scalar_json_is_rejected(comlink, call, httpx_mock, body):
    httpx_mock.add_response(content=body)
    with pytest.raises(SwgohComlinkDecodeError, match="object or array"):
        await call(comlink, "get_game_metadata")


@pytest.mark.parametrize("body", [{}, []])
async def test_supported_response_shapes(comlink, call, httpx_mock, body):
    httpx_mock.add_response(json=body)
    assert await call(comlink, "_post", endpoint="test") == body


@pytest.mark.parametrize("caps", [{}, {"max_response_bytes": 1_000}], ids=["buffered", "capped"])
async def test_utf8_bom_is_rejected(make_comlink, call, httpx_mock, caps):
    """Regression guard: a BOM-prefixed body stays a decode error, as ``json.loads(str)`` rejects the BOM."""
    httpx_mock.add_response(content=b'\xef\xbb\xbf{"latestGamedataVersion": "g"}')
    with pytest.raises(SwgohComlinkDecodeError) as caught:
        await call(make_comlink(**caps), "get_game_metadata")
    assert isinstance(caught.value.__cause__, json.JSONDecodeError)
