import pytest

from src.swgoh_comlink import data_builder


def test_compare_game_data_versions_same():
    current_version = {"game": 3, "language": "English", "otherkey": "value"}
    server_version = {"game": 3, "language": "English"}
    result = data_builder._compare_game_data_versions(current_version, server_version)
    assert result is True, f"Error: Expected True, but got {result}"


def test_compare_game_data_versions_different_game():
    current_version = {"game": 3, "language": "English", "otherkey": "value"}
    server_version = {"game": 4, "language": "English"}
    result = data_builder._compare_game_data_versions(current_version, server_version)
    assert result is False, f"Error: Expected False, but got {result}"


def test_compare_game_data_versions_different_language():
    current_version = {"game": 3, "language": "English", "otherkey": "value"}
    server_version = {"game": 3, "language": "French"}
    result = data_builder._compare_game_data_versions(current_version, server_version)
    assert result is False, f"Error: Expected False, but got {result}"


def test_compare_game_data_versions_additional_keys():
    current_version = {"game": 3, "language": "English", "otherkey": "value"}
    server_version = {"game": 3, "language": "English", "extra": "info"}
    result = data_builder._compare_game_data_versions(current_version, server_version)
    assert result is True, f"Error: Expected True, but got {result}"


def test_compare_game_data_versions_no_keys():
    current_version = {"otherkey": "value"}
    server_version = {"extra": "info"}
    with pytest.raises(KeyError):
        data_builder._compare_game_data_versions(current_version, server_version)
