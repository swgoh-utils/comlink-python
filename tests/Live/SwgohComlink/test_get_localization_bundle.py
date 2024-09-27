from swgoh_comlink import SwgohComlink


def test_get_localization_bundle():
    comlink = SwgohComlink()
    game_data_versions = comlink.get_latest_game_data_version()
    location_bundle = comlink.get_localization_bundle(
        id=game_data_versions["language"]
    )
    assert isinstance(location_bundle, dict)


def test_get_localization_bundle_no_id():
    comlink = SwgohComlink()
    location_bundle = comlink.get_localization_bundle()
    assert isinstance(location_bundle, dict)
