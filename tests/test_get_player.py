from unittest import TestCase, main, mock

from swgoh_comlink import SwgohComlink


def mocked_get_player(*args, **kwargs):
    return {
        'allyCode': '245866537',
        'level': 85,
        'name': 'Test Player',
        'rosterUnit': [],
    }


class TestGetPlayer(TestCase):
    @mock.patch.object(SwgohComlink, 'get_player', side_effect=mocked_get_player)
    def test_get_player(self, mock_get_player):
        """
        Test that player data can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        ally_code = 245866537
        p = comlink.get_player(allycode=ally_code)
        self.assertTrue('name' in p.keys())


if __name__ == '__main__':
    main()
