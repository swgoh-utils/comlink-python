from unittest import TestCase, main
import swgoh_comlink


class TestGetMetadata(TestCase):
    def test_get_metadata(self):
        """
        Test that game metadata can be retrieved from game server correctly
        """
        comlink = swgoh_comlink.SwgohComlink()
        md = comlink.get_game_metadata()
        self.assertTrue('serverVersion' in md.keys())


if __name__ == '__main__':
    main()
