import pytest

from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(default_logger_enabled=True)


def test_get_player_by_allycode(allycode):
    p = comlink.get_player(allycode=allycode)
    assert "name" in p.keys()


def test_get_player_by_player_id(player_id):
    p = comlink.get_player(player_id=player_id)
    assert "name" in p.keys()


def test_get_player_no_params():
    with pytest.raises(ValueError):
        comlink.get_player()


def test_mock_get_player_both_allycode_and_player_id(allycode, player_id):
    with pytest.raises(ValueError):
        p = comlink.get_player(allycode=allycode, player_id=player_id)


def test_get_player_arena_by_allycode(allycode):
    p = comlink.get_player_arena(allycode=allycode)
    assert "pvpProfile" in p.keys()


def test_get_player_arena_by_player_id(player_id):
    p = comlink.get_player_arena(player_id=player_id)
    assert "pvpProfile" in p.keys()


def test_get_player_arena_no_params():
    with pytest.raises(ValueError):
        comlink.get_player_arena()


def test_mock_get_player_arena_both_allycode_and_player_id(allycode, player_id):
    with pytest.raises(ValueError):
        p = comlink.get_player_arena(allycode=allycode, player_id=player_id)
