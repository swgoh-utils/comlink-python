"""Tests for get_unit_stats() endpoint."""

import json

import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink
from swgoh_comlink.exceptions import SwgohComlinkValueError


def test_get_unit_stats_with_list(httpx_mock: HTTPXMock):
    """Test that get_unit_stats() posts to the stats endpoint with correct payload."""
    httpx_mock.add_response(json={"stats": {"gp": 12345}})

    client = SwgohComlink(
        url="http://localhost:3000", stats_url="http://localhost:3223"
    )
    roster = [{"id": "UNIT_001", "defId": "DARTHMALGUS"}]
    result = client.get_unit_stats(roster, flags=["calcGP", "gameStyle"])

    request = httpx_mock.get_request()
    assert str(request.url).startswith("http://localhost:3223/")
    assert "calcGP" in str(request.url)
    assert "gp" in result["stats"]


def test_get_unit_stats_dict_wrapped_as_list(httpx_mock: HTTPXMock):
    """Test that a dict payload is automatically wrapped in a list."""
    httpx_mock.add_response(json={})

    client = SwgohComlink(
        url="http://localhost:3000", stats_url="http://localhost:3223"
    )
    client.get_unit_stats({"id": "UNIT_001"})

    request = httpx_mock.get_request()
    body = json.loads(request.content)
    assert isinstance(body, list)


def test_get_unit_stats_invalid_flags():
    """Test that invalid flags raise SwgohComlinkValueError."""
    client = SwgohComlink(url="http://localhost:3000")
    with pytest.raises(SwgohComlinkValueError):
        client.get_unit_stats([{}], flags=["invalidFlag"])
