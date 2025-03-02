from unittest import TestCase, main
from swgoh_comlink import SwgohComlink


class TestGetPlayer(TestCase):
    def test_get_player(self):
        """
        Test that player data can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        allyCode = 245866537
        p = comlink.get_player(allycode=allyCode)
        self.assertTrue('name' in p.keys())


if __name__ == '__main__':
    main()
