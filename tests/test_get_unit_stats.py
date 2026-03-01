from unittest import TestCase, main, mock

from swgoh_comlink import SwgohComlink


def mocked_get_player(*args, **kwargs):
    return {
        'allyCode': '245866537',
        'level': 85,
        'name': 'Test Player',
        'rosterUnit': [{'id': 'UNIT_001', 'defId': 'DARTHMALGUS'}],
    }


def mocked_get_unit_stats(*args, **kwargs):
    return {
        'stats': {'gp': 12345},
    }


class TestGetUnitStats(TestCase):
    @mock.patch.object(SwgohComlink, 'get_unit_stats', side_effect=mocked_get_unit_stats)
    @mock.patch.object(SwgohComlink, 'get_player', side_effect=mocked_get_player)
    def test_get_unit_stats(self, mock_get_player, mock_get_unit_stats):
        """
        Test that player data can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        ally_code = 245866537
        p = comlink.get_player(allycode=ally_code)
        unit_stats = comlink.get_unit_stats(p['rosterUnit'], flags=['calcGP', 'gameStyle'])
        self.assertTrue('gp' in unit_stats['stats'].keys())


if __name__ == '__main__':
    main()
