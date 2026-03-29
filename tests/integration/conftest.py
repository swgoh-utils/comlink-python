"""Shared fixtures for integration tests against a live Comlink service."""

import os

import pytest

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync

COMLINK_URL = "http://localhost:3000"
COMLINK_HMAC_URL = "http://localhost:3001"
HMAC_ACCESS_KEY = os.environ.get("HMAC_ACCESS_KEY", "")
HMAC_SECRET_KEY = os.environ.get("HMAC_SECRET_KEY", "")

# Known public allycode used in example scripts
TEST_ALLYCODE = 314927874

pytestmark = pytest.mark.integration


@pytest.fixture
def comlink():
    """Sync client connected to the open Comlink instance."""
    with SwgohComlink(url=COMLINK_URL) as client:
        yield client


@pytest.fixture
def comlink_hmac():
    """Sync client connected to the HMAC-protected Comlink instance."""
    with SwgohComlink(
        url=COMLINK_HMAC_URL,
        access_key=HMAC_ACCESS_KEY,
        secret_key=HMAC_SECRET_KEY,
    ) as client:
        yield client


@pytest.fixture
async def async_comlink():
    """Async client connected to the open Comlink instance."""
    async with SwgohComlinkAsync(url=COMLINK_URL) as client:
        yield client


@pytest.fixture
async def async_comlink_hmac():
    """Async client connected to the HMAC-protected Comlink instance."""
    async with SwgohComlinkAsync(
        url=COMLINK_HMAC_URL,
        access_key=HMAC_ACCESS_KEY,
        secret_key=HMAC_SECRET_KEY,
    ) as client:
        yield client
