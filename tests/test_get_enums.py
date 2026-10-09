"""Tests for get_enums() endpoint."""

import httpx
import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink
from swgoh_comlink.exceptions import SwgohComlinkException

# get_enums() first reads the game data version through /metadata, then fetches /enums.
ENUMS_URL = "http://localhost:3000/enums"
METADATA_URL = "http://localhost:3000/metadata"
METADATA = {"latestGamedataVersion": "game-v1", "latestLocalizationBundleVersion": "lang-v1"}


def test_get_enums(httpx_mock: HTTPXMock):
    """Test that get_enums() makes a GET request and returns parsed JSON."""
    httpx_mock.add_response(url=METADATA_URL, json=METADATA)
    httpx_mock.add_response(url=ENUMS_URL, json={"CombatType": {"1": "CHARACTER", "2": "SHIP"}})

    client = SwgohComlink(url="http://localhost:3000")
    result = client.get_enums()

    request = httpx_mock.get_request(url=ENUMS_URL)
    assert request.method == "GET"
    assert str(request.url) == "http://localhost:3000/enums"
    assert "CombatType" in result


def test_get_enums_with_hmac(httpx_mock: HTTPXMock):
    """Test that get_enums() applies HMAC authentication when keys are set."""
    httpx_mock.add_response(url=METADATA_URL, json=METADATA)
    httpx_mock.add_response(url=ENUMS_URL, json={"CombatType": {"1": "CHARACTER"}})

    client = SwgohComlink(
        url="http://localhost:3000",
        access_key="test_access",
        secret_key="test_secret",
    )
    client.get_enums()

    request = httpx_mock.get_request(url=ENUMS_URL)
    assert request.method == "GET"
    assert str(request.url) == "http://localhost:3000/enums"
    assert "x-date" in request.headers
    assert "authorization" in request.headers
    assert request.headers["authorization"].startswith("HMAC-SHA256 Credential=test_access,Signature=")


def test_get_enums_respects_verify_ssl(httpx_mock: HTTPXMock):
    """Test that get_enums() works with verify_ssl=False."""
    httpx_mock.add_response(url=METADATA_URL, json=METADATA)
    httpx_mock.add_response(url=ENUMS_URL, json={})

    client = SwgohComlink(url="http://localhost:3000", verify_ssl=False)
    result = client.get_enums()

    request = httpx_mock.get_request(url=ENUMS_URL)
    assert request.method == "GET"
    assert result == {}


def test_get_enums_connection_error(httpx_mock: HTTPXMock):
    """Test that get_enums() wraps connection errors in SwgohComlinkException."""
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"), is_reusable=True)

    client = SwgohComlink(url="http://localhost:3000")
    with pytest.raises(SwgohComlinkException):
        client.get_enums()


def test_get_enums_no_json_body_for_get(httpx_mock: HTTPXMock):
    """Test that GET requests do not include a JSON body."""
    httpx_mock.add_response(url=METADATA_URL, json=METADATA)
    httpx_mock.add_response(url=ENUMS_URL, json={})

    client = SwgohComlink(url="http://localhost:3000")
    client.get_enums()

    request = httpx_mock.get_request(url=ENUMS_URL)
    assert request.content == b""
