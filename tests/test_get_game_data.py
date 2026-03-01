from unittest import TestCase, main, mock

from swgoh_comlink import SwgohComlink


def mocked_get_game_metadata(*args, **kwargs):
    return {
        'latestGamedataVersion': '0.33.0:aaaabbbb',
        'latestLocalizationBundleVersion': 'loc_bundle_v1',
        'serverVersion': '21.04.0',
    }


def mocked_get_game_data(*args, **kwargs):
    return {
        'units': [{'id': 'UNIT_001', 'name': 'Test Unit'}],
    }


class TestGetGameData(TestCase):
    @mock.patch.object(SwgohComlink, 'get_game_data', side_effect=mocked_get_game_data)
    @mock.patch.object(SwgohComlink, 'get_game_metadata', side_effect=mocked_get_game_metadata)
    def test_get_game_data(self, mock_metadata, mock_game_data):
        """
        Test that game data can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        game_metadata = comlink.get_game_metadata()
        game_version = game_metadata['latestGamedataVersion']
        game_data = comlink.get_game_data(version=game_version, include_pve_units=False, request_segment=4)
        self.assertTrue('units' in game_data.keys())


if __name__ == '__main__':
    main()
