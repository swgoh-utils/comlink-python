from unittest import TestCase, main, mock

from swgoh_comlink import SwgohComlink


def mocked_get_guilds_by_criteria(*args, **kwargs):
    return {
        'guild': [{'id': 'GUILD_001', 'name': 'Test Guild'}],
    }


class TestGetGuildByCriteria(TestCase):
    @mock.patch.object(SwgohComlink, 'get_guilds_by_criteria', side_effect=mocked_get_guilds_by_criteria)
    def test_get_guild_by_criteria(self, mock_get_guilds):
        """
        Test that guild data can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        p = comlink.get_guilds_by_criteria(search_criteria={"minGuildGalacticPower": 490000000})
        self.assertTrue('guild' in p.keys())


if __name__ == '__main__':
    main()
