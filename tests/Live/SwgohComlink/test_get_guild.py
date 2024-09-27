import pytest

from swgoh_comlink import SwgohComlink


def test_get_guild_by_criteria():
    comlink = SwgohComlink()
    p = comlink.get_guilds_by_criteria(
        search_criteria={"minGuildGalacticPower": 490000000}
    )
    assert "guild" in p.keys()


def test_get_guild_by_name():
    comlink = SwgohComlink()
    p = comlink.get_guilds_by_name("dead")
    assert "guild" in p.keys()


def test_get_guild_by_id(guild_id):
    comlink = SwgohComlink()
    p = comlink.get_guild(guild_id=guild_id)
    assert "profile" in p.keys()


def test_get_guild_no_id():
    comlink = SwgohComlink()
    with pytest.raises(ValueError):
        comlink.get_guild()


def test_get_guild_invalid_id():
    comlink = SwgohComlink()
    p = comlink.get_guild(guild_id=".")
    assert p == {}
