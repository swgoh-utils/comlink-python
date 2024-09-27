# coding=utf-8
"""
File containing mock tests configurations for the SwgohComlink class methods
"""
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(default_logger_enabled=False)


def test_mock_get_guild_by_criteria(httpx_mock: HTTPXMock):
    """
    Test that guild data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"guild": 1}, status_code=200)
    p = comlink.get_guilds_by_criteria({"minGuildGalacticPower": 490000000})
    assert "guild" in p.keys()


def test_mock_get_guild_by_name(httpx_mock: HTTPXMock):
    """
    Test that guild data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"guild": 1}, status_code=200)
    p = comlink.get_guilds_by_name("dead")
    assert "guild" in p.keys()
