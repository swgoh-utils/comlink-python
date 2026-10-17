"""Integration tests for HMAC authentication against live Comlink services.

Tests use two Comlink instances:
- Port 3000: open access (no HMAC)
- Port 3001: HMAC-protected (requires ACCESS_KEY and SECRET_KEY secrets)

Each request test runs once per client through the ``make_comlink`` and ``call`` fixtures in
conftest.py.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from swgoh_comlink import SwgohComlink
from swgoh_comlink.exceptions import SwgohComlinkException

from .conftest import (
    COMLINK_HMAC_URL,
    HMAC_ACCESS_KEY,
    HMAC_SECRET_KEY,
    TEST_ALLYCODE,
    Client,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not HMAC_ACCESS_KEY or not HMAC_SECRET_KEY, reason="HMAC secrets not configured"),
]

# SwgohComlinkException wraps transport failures as well as HTTP status errors, so a
# bare `pytest.raises(SwgohComlinkException)` is satisfied by "connection refused" —
# the rejection tests would pass if the HMAC service never came up. Matching the HTTP
# status text asserts the server actually saw the request and turned it away.
REJECTED = r"HTTP 4\d{2}"


@pytest.mark.parametrize(
    ("method", "kwargs", "populated_key"),
    [
        # `metadata` rather than `enums`: HMAC is only enforced on POST, so a GET
        # endpoint would pass whether or not request signing works at all.
        pytest.param("get_game_metadata", {}, "latestGamedataVersion", id="metadata"),
        pytest.param("get_player", {"allycode": TEST_ALLYCODE}, "name", id="player"),
    ],
)
async def test_signed_request_succeeds(
    make_comlink: Callable[..., Client],
    call: Callable[..., Awaitable[Any]],
    method: str,
    kwargs: dict[str, Any],
    populated_key: str,
):
    """A client with correct HMAC keys can reach a signed POST endpoint."""
    client = make_comlink(url=COMLINK_HMAC_URL, access_key=HMAC_ACCESS_KEY, secret_key=HMAC_SECRET_KEY)
    result = await call(client, method, **kwargs)
    assert isinstance(result, dict)
    assert result.get(populated_key), f"signed POST must return a populated {populated_key!r}"


@pytest.mark.parametrize(
    "credentials",
    [
        pytest.param({}, id="no-key"),
        pytest.param({"access_key": HMAC_ACCESS_KEY, "secret_key": "wrong_secret_key"}, id="wrong-key"),
    ],
)
async def test_unsigned_or_badly_signed_request_is_rejected(
    make_comlink: Callable[..., Client], call: Callable[..., Awaitable[Any]], credentials: dict[str, str]
):
    """A client without HMAC keys, or with the wrong secret, is rejected by the protected endpoint.

    Uses a POST endpoint (`playerArena`) because the Comlink HMAC service only enforces HMAC
    on POST; GET endpoints like `/enums` are unauthenticated.
    """
    client = make_comlink(url=COMLINK_HMAC_URL, **credentials)
    with pytest.raises(SwgohComlinkException, match=REJECTED):
        await call(client, "get_player_arena", allycode=TEST_ALLYCODE, player_details_only=True)


def test_hmac_headers_present():
    """HMAC client includes Authorization and X-Date headers in requests."""
    with SwgohComlink(url=COMLINK_HMAC_URL, access_key=HMAC_ACCESS_KEY, secret_key=HMAC_SECRET_KEY) as client:
        headers = client._construct_request_headers("GET", "enums", None)
    assert "Authorization" in headers
    assert "X-Date" in headers
    assert headers["Authorization"].startswith(f"HMAC-SHA256 Credential={HMAC_ACCESS_KEY},Signature=")
