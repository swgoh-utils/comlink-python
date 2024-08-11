import pytest

from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(default_logger_enabled=False)


def test_get_game_metadata():
    game_metadata = comlink.get_game_metadata()
    assert "latestGamedataVersion" in game_metadata.keys()


def test_get_game_metadata_no_client_specs():
    game_metadata = comlink.get_game_metadata(client_specs={})
    assert "latestGamedataVersion" in game_metadata.keys()


def test_get_game_metadata_with_client_specs():
    game_metadata = comlink.get_game_metadata(client_specs={"bundleId": "390bljwoSWCqK5VeoRPs3Q"})
    assert "latestGamedataVersion" in game_metadata.keys()


def test_get_game_data():
    game_data = comlink.get_game_data(include_pve_units=False, request_segment=1)
    assert 'effect' in game_data.keys()


def test_get_game_data_with_version():
    versions = comlink.get_latest_game_data_version()
    game_data = comlink.get_game_data(version=versions['game'], include_pve_units=False, request_segment=1)
    assert 'effect' in game_data.keys()


def test_get_game_data_with_items():
    game_data = comlink.get_game_data(include_pve_units=False, items="ModRecommendations")
    assert 'modRecommendation' in game_data.keys()


def test_get_game_data_with_request_segment_and_items():
    with pytest.raises(ValueError):
        p = comlink.get_game_data(request_segment=4, items="ModRecommendations")


def test_get_latest_game_data_version():
    game_data = comlink.get_latest_game_data_version()
    assert 'game' in game_data.keys()
    assert 'language' in game_data.keys()


def test_get_latest_game_data_version_with_version():
    gd = comlink.get_latest_game_data_version()
    assert 'game' in gd.keys()
    game_data = comlink.get_latest_game_data_version(game_version=gd['game'])
    assert 'language' in game_data.keys()
