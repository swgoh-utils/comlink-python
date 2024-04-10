import pytest

from swgoh_comlink import SwgohComlink


def test_get_player_by_allycode(allycode):
    comlink = SwgohComlink()
    p = comlink.get_player(allycode=allycode)
    assert "name" in p.keys()


def test_get_player_by_player_id(player_id):
    comlink = SwgohComlink()
    p = comlink.get_player(player_id=player_id)
    assert "name" in p.keys()


def test_get_player_no_params():
    comlink = SwgohComlink()
    with pytest.raises(ValueError):
        comlink.get_player()


def test_get_player_arena_by_allycode(allycode):
    comlink = SwgohComlink()
    p = comlink.get_player_arena(allycode=allycode)
    assert "pvpProfile" in p.keys()


def test_get_player_arena_by_player_id(player_id):
    comlink = SwgohComlink()
    p = comlink.get_player_arena(player_id=player_id)
    assert "pvpProfile" in p.keys()


def test_get_player_arena_no_params():
    comlink = SwgohComlink()
    with pytest.raises(ValueError):
        comlink.get_player_arena()
