from unittest import TestCase, main
import swgoh_comlink


class TestGetGuildByName(TestCase):
    def test_get_guild_by_name(self):
        """
        Test that guild data can be retrieved from game server correctly
        """
        comlink = swgoh_comlink.SwgohComlink()
        p = comlink.get_guilds_by_name("dead")
        self.assertTrue('guild' in p.keys())


if __name__ == '__main__':
    main()
