from unittest import TestCase, main
from swgoh_comlink import SwgohComlink


class TestGetUnitStats(TestCase):
    def test_get_unit_stats(self):
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
