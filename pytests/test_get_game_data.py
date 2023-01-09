import os
from unittest import TestCase, main
from swgoh_comlink import SwgohComlink


class TestGetGameData(TestCase):
    def test_get_game_data(self):
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
