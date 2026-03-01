from unittest import TestCase, main, mock

from swgoh_comlink import SwgohComlink


def mocked_get_game_metadata(*args, **kwargs):
    return {
        'latestGamedataVersion': '0.33.0:aaaabbbb',
        'latestLocalizationBundleVersion': 'loc_bundle_v1',
        'serverVersion': '21.04.0',
    }


def mocked_get_localization(*args, **kwargs):
    return {
        'localizationBundle': {'en': {'KEY_001': 'Test Value'}},
    }


class TestGetLocalizationBundle(TestCase):
    @mock.patch.object(SwgohComlink, 'get_localization', side_effect=mocked_get_localization)
    @mock.patch.object(SwgohComlink, 'get_game_metadata', side_effect=mocked_get_game_metadata)
    def test_get_localization_bundle(self, mock_metadata, mock_localization):
        """
        Test that localization data can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        game_metadata = comlink.get_game_metadata()
        localization_id = game_metadata['latestLocalizationBundleVersion']
        game_data = comlink.get_localization(id=localization_id)
        self.assertTrue('localizationBundle' in game_data.keys())


if __name__ == '__main__':
    main()
