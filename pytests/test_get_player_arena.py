import os
import sys

sys.path.append(os.path.join(os.path.split(os.getcwd())[0], 'src'))
from unittest import TestCase, main, mock
from swgoh_comlink import SwgohComlink


def mocked_player_arena(*args, **kwargs):
    possible_params = ['allycode', 'player_id:', 'player_details_only', 'playerDetailsOnly', 'enums']

    for kw in kwargs:
        if kw not in possible_params:
            raise AttributeError(f'Invalid argument {kw}')

    sample_resp = {
        'allyCode': '314927874',
        'level': 85,
        'name': 'Mar Trepodi',
        'playerRating': {},
        'pvpProfile': []
    }
    return sample_resp


class TestGetPlayerArena(TestCase):
    @mock.patch('swgoh_comlink.SwgohComlink.get_player_arena', side_effect=mocked_player_arena)
    def test_get_player_arena(self, mock_post):
        """
        Test that player data can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        ally_code = 245866537
        p = comlink.get_player_arena(allycode=ally_code)
        self.assertTrue('name' in p.keys())

    @mock.patch('swgoh_comlink.SwgohComlink.get_player_arena', side_effect=mocked_player_arena)
    def test_get_player_arena_details_only(self, mock_post):
        """
        Test that player data can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        ally_code = 245866537
        p = comlink.get_player_arena(allycode=ally_code, player_details_only=True)
        self.assertTrue('name' in p.keys())

    @mock.patch('swgoh_comlink.SwgohComlink.get_player_arena', side_effect=mocked_player_arena)
    def test_get_player_arena_details_only_alias(self, mock_post):
        """
        Test that player data can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        ally_code = 245866537
        p = comlink.get_player_arena(allycode=ally_code, playerDetailsOnly=True)
        self.assertTrue('name' in p.keys())

    @mock.patch('swgoh_comlink.SwgohComlink.get_player_arena', side_effect=mocked_player_arena)
    def test_get_player_arena_details_only_alias_neg(self, mock_post):
        """
        Test that player data can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        ally_code = 245866537
        p = comlink.get_player_arena(allycode=ally_code, playerDetailsOnly=True)
        self.assertTrue('name' in p.keys())

    @mock.patch('swgoh_comlink.SwgohComlink.get_arena', side_effect=mocked_player_arena)
    def test_get_arena(self, mock_post):
        """
        Test that player data can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        ally_code = 245866537
        p = comlink.get_arena(allycode=ally_code)
        self.assertTrue('name' in p.keys())


if __name__ == '__main__':
    main()
