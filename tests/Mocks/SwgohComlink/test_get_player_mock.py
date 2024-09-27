# coding=utf-8
"""
File containing mock tests configurations for the SwgohComlink class methods
"""
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(default_logger_enabled=False)


def test_mock_get_player(httpx_mock: HTTPXMock, allycode):
    """
    Test that player data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"name": 1}, status_code=200)
    p = comlink.get_player(allycode=allycode)
    assert "name" in p.keys()


def test_mock_get_player_arena(httpx_mock: HTTPXMock, allycode):
    """
    Test that player data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"name": 1}, status_code=200)
    p = comlink.get_player_arena(allycode=allycode)
    assert "name" in p.keys()


def test_mock_get_player_arena_details_only(httpx_mock: HTTPXMock, allycode):
    """
    Test that player data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"name": 1}, status_code=200)
    p = comlink.get_player_arena(allycode=allycode, player_details_only=True)
    assert "name" in p.keys()


def test_mock_get_player_arena_details_only_alias(httpx_mock: HTTPXMock, allycode):
    """
    Test that player data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"name": 1}, status_code=200)
    p = comlink.get_player_arena(allycode=allycode, playerDetailsOnly=True)
    assert "name" in p.keys()
