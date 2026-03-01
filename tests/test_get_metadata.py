from unittest import TestCase, main, mock

from swgoh_comlink import SwgohComlink


def mocked_get_game_metadata(*args, **kwargs):
    return {
        'latestGamedataVersion': '0.33.0:aaaabbbb',
        'latestLocalizationBundleVersion': 'loc_bundle_v1',
        'serverVersion': '21.04.0',
    }


class TestGetMetadata(TestCase):
    @mock.patch.object(SwgohComlink, 'get_game_metadata', side_effect=mocked_get_game_metadata)
    def test_get_metadata(self, mock_metadata):
        """
        Test that game metadata can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        md = comlink.get_game_metadata()
        self.assertTrue('serverVersion' in md.keys())


if __name__ == '__main__':
    main()
