from unittest import TestCase, main, mock

from swgoh_comlink import SwgohComlink


def mocked_get_guilds_by_name(*args, **kwargs):
    return {
        'guild': [{'id': 'GUILD_001', 'name': 'dead'}],
    }


class TestGetGuildByName(TestCase):
    @mock.patch.object(SwgohComlink, 'get_guilds_by_name', side_effect=mocked_get_guilds_by_name)
    def test_get_guild_by_name(self, mock_get_guilds):
        """
        Test that guild data can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        p = comlink.get_guilds_by_name("dead")
        self.assertTrue('guild' in p.keys())


if __name__ == '__main__':
    main()
