"""Integration tests for HMAC authentication against live Comlink services.

Tests use two Comlink instances:
- Port 3000: open access (no HMAC)
- Port 3001: HMAC-protected (requires ACCESS_KEY and SECRET_KEY secrets)
"""

import pytest

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync
from swgoh_comlink.exceptions import SwgohComlinkException

from .conftest import (
    COMLINK_HMAC_URL,
    HMAC_ACCESS_KEY,
    HMAC_SECRET_KEY,
)

pytestmark = pytest.mark.integration

hmac_configured = pytest.mark.skipif(
    not HMAC_ACCESS_KEY or not HMAC_SECRET_KEY,
    reason="HMAC secrets not configured",
)


# ── Sync: valid HMAC ────────────────────────────────────────────────────


@hmac_configured
def test_hmac_sync_request_succeeds(comlink_hmac):
    """Sync client with correct HMAC keys can access the protected endpoint."""
    result = comlink_hmac.get_enums()
    assert isinstance(result, dict)
    assert "CombatType" in result


@hmac_configured
def test_hmac_sync_player_request_succeeds(comlink_hmac):
    """Sync HMAC client can fetch a player profile from the protected endpoint."""
    result = comlink_hmac.get_player(allycode=314927874)
    assert isinstance(result, dict)
    assert "name" in result


# ── Sync: invalid HMAC ──────────────────────────────────────────────────


@hmac_configured
def test_hmac_no_key_rejected():
    """Sync client without HMAC keys is rejected by the protected endpoint."""
    with SwgohComlink(url=COMLINK_HMAC_URL) as client, pytest.raises(SwgohComlinkException):
        client.get_enums()


@hmac_configured
def test_hmac_wrong_key_rejected():
    """Sync client with wrong secret key is rejected by the protected endpoint."""
    with (
        SwgohComlink(
            url=COMLINK_HMAC_URL,
            access_key=HMAC_ACCESS_KEY,
            secret_key="wrong_secret_key",
        ) as client,
        pytest.raises(SwgohComlinkException),
    ):
        client.get_enums()


# ── Async: valid HMAC ───────────────────────────────────────────────────


@hmac_configured
@pytest.mark.asyncio
async def test_hmac_async_request_succeeds(async_comlink_hmac):
    """Async client with correct HMAC keys can access the protected endpoint."""
    result = await async_comlink_hmac.get_enums()
    assert isinstance(result, dict)
    assert "CombatType" in result


@hmac_configured
@pytest.mark.asyncio
async def test_hmac_async_player_request_succeeds(async_comlink_hmac):
    """Async HMAC client can fetch a player profile from the protected endpoint."""
    result = await async_comlink_hmac.get_player(allycode=314927874)
    assert isinstance(result, dict)
    assert "name" in result


# ── Async: invalid HMAC ─────────────────────────────────────────────────


@hmac_configured
@pytest.mark.asyncio
async def test_hmac_no_key_async_rejected():
    """Async client without HMAC keys is rejected by the protected endpoint."""
    async with SwgohComlinkAsync(url=COMLINK_HMAC_URL) as client:
        with pytest.raises(SwgohComlinkException):
            await client.get_enums()


@hmac_configured
@pytest.mark.asyncio
async def test_hmac_wrong_key_async_rejected():
    """Async client with wrong secret key is rejected by the protected endpoint."""
    async with SwgohComlinkAsync(
        url=COMLINK_HMAC_URL,
        access_key=HMAC_ACCESS_KEY,
        secret_key="wrong_secret_key",
    ) as client:
        with pytest.raises(SwgohComlinkException):
            await client.get_enums()


# ── HMAC header verification ────────────────────────────────────────────


@hmac_configured
def test_hmac_headers_present():
    """HMAC client includes Authorization and X-Date headers in requests."""
    client = SwgohComlink(
        url=COMLINK_HMAC_URL,
        access_key=HMAC_ACCESS_KEY,
        secret_key=HMAC_SECRET_KEY,
    )
    headers = client._construct_request_headers("GET", "enums", None)
    assert "Authorization" in headers
    assert "X-Date" in headers
    assert headers["Authorization"].startswith(f"HMAC-SHA256 Credential={HMAC_ACCESS_KEY},Signature=")
    client.close()
