# coding=utf-8
"""
File containing mock tests configurations for the SwgohComlink class methods
"""
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(default_logger_enabled=False)


def test_mock_get_game_data_segment(httpx_mock: HTTPXMock):
    """
    Test that game data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"latestGamedataVersion": "x"}, status_code=200)
    httpx_mock.add_response(json={"units": "x"}, status_code=200)
    game_data = comlink.get_game_data(
        include_pve_units=False,
        request_segment=4
    )
    assert "units" in game_data.keys()


def test_mock_get_game_data_items(httpx_mock: HTTPXMock):
    """
    Test that game data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"latestGamedataVersion": "x"}, status_code=200)
    httpx_mock.add_response(json={"modRecommendation": "x"}, status_code=200)
    game_data = comlink.get_game_data(
        include_pve_units=False,
        items="ModRecommendations"
    )
    assert "modRecommendation" in game_data.keys()
