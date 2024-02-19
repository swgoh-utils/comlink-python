from comlink_python import SwgohComlink
from comlink_python import get_guild_members


class TestGetGuildMembers:
    def test_get_guild_members_by_allycode(self):
        """
        Test that game enums can be retrieved from game server correctly
        """
        comlink = SwgohComlink(url='http://192.168.1.167:3200')
        allycode = 314927874
        guild_members = get_guild_members(comlink, allycode=allycode)
        assert isinstance(guild_members, list)
        assert 'playerId' in guild_members[0].keys()

    def test_get_guild_members_by_player_id(self):
        """
        Test that game enums can be retrieved from game server correctly
        """
        comlink = SwgohComlink(url='http://192.168.1.167:3200')
        player_id = 'cRdX7yGvS-eKfyDxAAgaYw'
        guild_members = get_guild_members(comlink, player_id=player_id)
        assert isinstance(guild_members, list)
        assert 'playerId' in guild_members[0].keys()
