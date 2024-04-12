# coding=utf-8
"""
Test swgoh_comlink.utils functions
"""
import pytest

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync
from swgoh_comlink.utils import get_guild_members

async_comlink = SwgohComlinkAsync(default_logger_enabled=True)
comlink = SwgohComlink(default_logger_enabled=True)


def test_get_guild_members_by_allycode():
    guild_members = get_guild_members(comlink, allycode=314927874)
    assert isinstance(guild_members, list)
    assert "playerId" in guild_members[0].keys()


def test_get_guild_members_by_allycode_async():
    guild_members = get_guild_members(comlink=SwgohComlinkAsync(default_logger_enabled=True), allycode=314927874)
    assert isinstance(guild_members, list)
    assert "playerId" in guild_members[0].keys()


def test_get_guild_members_by_player_id(player_id):
    guild_members = get_guild_members(comlink, player_id=player_id)
    assert isinstance(guild_members, list)
    assert "playerId" in guild_members[0].keys()


def test_get_guild_members_by_player_id_async(player_id):
    guild_members = get_guild_members(comlink, player_id=player_id)
    assert isinstance(guild_members, list)
    assert "playerId" in guild_members[0].keys()


def test_get_guild_members_none():
    with pytest.raises(ValueError):
        get_guild_members(comlink=comlink)


def test_get_guild_members_none_async():
    with pytest.raises(ValueError):
        get_guild_members(comlink=comlink)


def test_get_guild_members_no_comlink(player_id):
    with pytest.raises(ValueError):
        get_guild_members(player_id=player_id)


def test_get_guild_members_both_allycode_and_player_id(allycode, player_id):
    with pytest.raises(ValueError):
        get_guild_members(comlink=comlink, player_id=player_id, allycode=allycode)
