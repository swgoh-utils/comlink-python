import pytest

from swgoh_comlink import SwgohComlink


def test_get_unit_stats(allycode):
    """
    Test stats calculation results for single generic unit
    """
    comlink = SwgohComlink(stats_url="http://192.168.1.167:3223")
    player = comlink.get_player(allycode)
    test_unit = {}
    for unit in player['rosterUnit']:
        if 'police' in unit['definitionId'].lower():
            test_unit = unit

    unit_stats = comlink.get_unit_stats([test_unit], flags=['calcGP', 'gameStyle'])
    assert 'gp' in unit_stats[0]['stats'].keys()


def test_get_unit_stats_no_flags(allycode):
    """
    Test stats calculation results for single generic unit
    """
    comlink = SwgohComlink(stats_url="http://192.168.1.167:3223")
    player = comlink.get_player(allycode)
    test_unit = {}
    for unit in player['rosterUnit']:
        if 'police' in unit['definitionId'].lower():
            test_unit = unit

    unit_stats = comlink.get_unit_stats([test_unit])
    assert 'stats' in unit_stats[0].keys()


def test_get_unit_stats_invalid_flags(allycode):
    comlink = SwgohComlink(stats_url="http://192.168.1.167:3223", default_logger_enabled=True)
    with pytest.raises(ValueError):
        unit_stats = comlink.get_unit_stats(request_payload={}, flags="")


def test_get_unit_stats_single_unit(allycode):
    """
    Test stats calculation results for single generic unit
    """
    comlink = SwgohComlink(stats_url="http://192.168.1.167:3223")
    player = comlink.get_player(allycode)
    test_unit = {}
    for unit in player['rosterUnit']:
        if 'police' in unit['definitionId'].lower():
            test_unit = unit

    unit_stats = comlink.get_unit_stats(test_unit)
    assert 'stats' in unit_stats[0].keys()


def test_get_unit_stats_no_payload(allycode):
    comlink = SwgohComlink(stats_url='http://192.168.1.167:3223', default_logger_enabled=True)
    with pytest.raises(ValueError):
        unit_stats = comlink.get_unit_stats()
