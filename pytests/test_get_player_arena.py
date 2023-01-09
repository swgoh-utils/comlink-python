from unittest import TestCase, main
from swgoh_comlink import SwgohComlink


class TestGetPlayerArena(TestCase):
    def test_get_player_arena(self):
        """
        Test that player data can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        allyCode = 245866537
        p = comlink.get_player_arena(allycode=allyCode)
        self.assertTrue('name' in p.keys())

    def test_get_arena(self):
        """
        Test that player data can be retrieved from game server correctly
        """
        comlink = swgoh_comlink.SwgohComlink()
        allyCode = 245866537
        p = comlink.get_arena(allycode=allyCode)
        self.assertTrue('name' in p.keys())


if __name__ == '__main__':
    main()
