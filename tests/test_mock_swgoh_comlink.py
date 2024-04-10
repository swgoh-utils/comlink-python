# coding=utf-8
"""
File containing test configurations for the SwgohComlink class methods
"""
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink


def test_get_enums(httpx_mock: HTTPXMock):
    """
    Test that game enums can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"CombatType": 1}, status_code=200)
    comlink = SwgohComlink()
    en = comlink.get_enums()
    assert "CombatType" in en.keys()


def test_get_game_data(httpx_mock: HTTPXMock):
    """
    Test that game data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"latestGamedataVersion": "x"}, status_code=200)
    httpx_mock.add_response(json={"units": "x"}, status_code=200)
    comlink = SwgohComlink()
    game_data = comlink.get_game_data(
        include_pve_units=False,
        request_segment=4
    )
    assert "units" in game_data.keys()


def test_get_guild_by_criteria(httpx_mock: HTTPXMock):
    """
    Test that guild data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"guild": 1}, status_code=200)
    comlink = SwgohComlink()
    p = comlink.get_guilds_by_criteria({"minGuildGalacticPower": 490000000})
    assert "guild" in p.keys()


def test_get_guild_by_name(httpx_mock: HTTPXMock):
    """
    Test that guild data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"guild": 1}, status_code=200)
    comlink = SwgohComlink()
    p = comlink.get_guilds_by_name("dead")
    assert "guild" in p.keys()


def test_get_localization_bundle(httpx_mock: HTTPXMock):
    """
    Test that localization data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"latestLocalizationBundleVersion": "xyz"}, status_code=200)
    httpx_mock.add_response(json={"localizationBundle": "..."}, status_code=200)
    comlink = SwgohComlink()
    game_metadata = comlink.get_game_metadata(client_specs={})
    localization_id = game_metadata["latestLocalizationBundleVersion"]
    game_data = comlink.get_localization(id=localization_id)
    assert "localizationBundle" in game_data.keys()


def test_get_metadata(httpx_mock: HTTPXMock):
    """
    Test that game metadata can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"serverVersion": 1}, status_code=200)
    comlink = SwgohComlink()
    md = comlink.get_game_metadata(client_specs={})
    assert "serverVersion" in md.keys()


def test_get_player(httpx_mock: HTTPXMock, allycode):
    """
    Test that player data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"name": 1}, status_code=200)
    comlink = SwgohComlink()
    p = comlink.get_player(allycode=allycode)
    assert "name" in p.keys()


def test_get_player_arena(httpx_mock: HTTPXMock, allycode):
    """
    Test that player data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"name": 1}, status_code=200)
    comlink = SwgohComlink()
    p = comlink.get_player_arena(allycode=allycode)
    assert "name" in p.keys()


def test_get_player_arena_details_only(httpx_mock: HTTPXMock, allycode):
    """
    Test that player data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"name": 1}, status_code=200)
    comlink = SwgohComlink()
    p = comlink.get_player_arena(allycode=allycode, player_details_only=True)
    assert "name" in p.keys()


def test_get_player_arena_details_only_alias(httpx_mock: HTTPXMock, allycode):
    """
    Test that player data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"name": 1}, status_code=200)
    comlink = SwgohComlink()
    p = comlink.get_player_arena(allycode=allycode, playerDetailsOnly=True)
    assert "name" in p.keys()


def test_get_unit_stats(httpx_mock: HTTPXMock, allycode):
    """
    Test that player data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"name": 1,
                                  "rosterUnit": [{}, {}],
                                  "stats": {"gp": 1}
                                  }, status_code=200)
    comlink = SwgohComlink()
    p = comlink.get_player(allycode)
    assert 'name' in p.keys()
    unit_stats = comlink.get_unit_stats(p['rosterUnit'], flags=['calcGP', 'gameStyle'])
    assert 'gp' in unit_stats['stats'].keys()
