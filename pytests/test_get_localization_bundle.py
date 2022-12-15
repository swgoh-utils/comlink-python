from unittest import TestCase, main

from ..src import swgoh_comlink


class TestGetLocalizationBundle(TestCase):
    def test_get_localization_bundle(self):
        """
        Test that localization data can be retrieved from game server correctly
        """
        comlink = swgoh_comlink.SwgohComlink()
        game_metadata = comlink.get_game_metadata()
        localization_id = game_metadata['latestLocalizationBundleVersion']
        game_data = comlink.get_localization(id=localization_id, unzip=False)
        self.assertTrue('localizationBundle' in game_data.keys())


if __name__ == '__main__':
    main()
