from unittest import TestCase, main
import swgoh_comlink


class TestGetLocalizationBundle(TestCase):
    def test_get_localization_bundle(self):
        """
        Test that localization data can be retrieved from game server correctly
        """
        comlink = swgoh_comlink.SwgohComlink()
        game_metadata = comlink.get_game_metadata()
        localization_id = game_metadata['latestLocalizationBundleVersion']
        print(f'local id: {localization_id}')
        game_data = comlink.get_localization(id=localization_id, unzip=False)
        if 'message' in game_data.keys():
            print(game_data['message'])
        self.assertTrue('localizationBundle' in game_data.keys())


if __name__ == '__main__':
    main()
