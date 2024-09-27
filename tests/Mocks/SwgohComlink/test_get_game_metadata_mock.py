# coding=utf-8
"""
File containing mock tests configurations for the SwgohComlink class methods
"""
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(default_logger_enabled=False)


def test_mock_get_metadata(httpx_mock: HTTPXMock):
    """
    Test that game metadata can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"serverVersion": 1}, status_code=200)
    md = comlink.get_game_metadata(client_specs={})
    assert "serverVersion" in md.keys()
