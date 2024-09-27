# coding=utf-8
"""
File containing mock tests configurations for the SwgohComlink class methods
"""
import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(default_logger_enabled=False)


def test_mock_get_localization_bundle(httpx_mock: HTTPXMock):
    """
    Test that localization data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"latestLocalizationBundleVersion": "xyz"}, status_code=200)
    httpx_mock.add_response(json={"localizationBundle": "..."}, status_code=200)
    game_metadata = comlink.get_game_metadata(client_specs={})
    localization_id = game_metadata["latestLocalizationBundleVersion"]
    game_data = comlink.get_localization(id=localization_id)
    assert "localizationBundle" in game_data.keys()


def test_mock_get_localization_language(httpx_mock: HTTPXMock):
    """
    Test that specific language localization data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"latestLocalizationBundleVersion": "xyz"}, status_code=200)
    httpx_mock.add_response(json={"localizationBundle": "..."}, status_code=200)
    game_metadata = comlink.get_game_metadata(client_specs={})
    localization_id = game_metadata["latestLocalizationBundleVersion"]
    game_data = comlink.get_localization(id=localization_id, locale="eng_us")
    assert "localizationBundle" in game_data.keys()


def test_mock_get_localization_language_with_bad_locale():
    with pytest.raises(ValueError):
        comlink.get_localization(locale="xyz_bb")
