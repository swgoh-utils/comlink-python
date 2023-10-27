from unittest import TestCase, main
from swgoh_comlink import SwgohComlink


class TestGetGuildByCriteria(TestCase):
    def test_get_guild_by_criteria(self):
        """
        Test that guild data can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        p = comlink.get_guilds_by_criteria(search_criteria={"minGuildGalacticPower": 490000000})
        self.assertTrue('guild' in p.keys())


if __name__ == '__main__':
    main()
