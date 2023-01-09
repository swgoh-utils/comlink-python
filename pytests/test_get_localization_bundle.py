from unittest import TestCase, main
from swgoh_comlink import SwgohComlink


class TestGetLocalizationBundle(TestCase):
    def test_get_localization_bundle(self):
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
