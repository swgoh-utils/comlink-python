from unittest import TestCase, main
from swgoh_comlink import SwgohComlink


class TestGetMetadata(TestCase):
    def test_get_metadata(self):
        """
        Test that game metadata can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        md = comlink.get_game_metadata()
        self.assertTrue('serverVersion' in md.keys())


if __name__ == '__main__':
    main()
