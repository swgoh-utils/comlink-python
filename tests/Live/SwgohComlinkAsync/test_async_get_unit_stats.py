import pytest

from swgoh_comlink import SwgohComlinkAsync


@pytest.mark.asyncio
async def test_async_get_unit_stats(allycode):
    """
    Test stats calculation results for single generic unit
    """
    comlink = SwgohComlinkAsync(stats_url="http://192.168.1.167:3223")
    player = await comlink.get_player(allycode)
    test_unit = {}
    for unit in player['rosterUnit']:
        if 'police' in unit['definitionId'].lower():
            test_unit = unit

    unit_stats = await comlink.get_unit_stats([test_unit], flags=['calcGP', 'gameStyle'])
    assert 'gp' in unit_stats[0]['stats'].keys()


@pytest.mark.asyncio
async def test_async_get_unit_stats_no_flags(allycode):
    """
    Test stats calculation results for single generic unit
    """
    comlink = SwgohComlinkAsync(stats_url="http://192.168.1.167:3223")
    player = await comlink.get_player(allycode)
    test_unit = {}
    for unit in player['rosterUnit']:
        if 'police' in unit['definitionId'].lower():
            test_unit = unit

    unit_stats = await comlink.get_unit_stats([test_unit])
    assert 'stats' in unit_stats[0].keys()


@pytest.mark.asyncio
async def test_async_get_unit_stats_invalid_flags(allycode):
    comlink = SwgohComlinkAsync(stats_url="http://192.168.1.167:3223", default_logger_enabled=True)
    with pytest.raises(ValueError):
        unit_stats = await comlink.get_unit_stats(request_payload={}, flags="")


@pytest.mark.asyncio
async def test_async_get_unit_stats_single_unit(allycode):
    """
    Test stats calculation results for single generic unit
    """
    comlink = SwgohComlinkAsync(stats_url="http://192.168.1.167:3223")
    player = await comlink.get_player(allycode)
    test_unit = {}
    for unit in player['rosterUnit']:
        if 'police' in unit['definitionId'].lower():
            test_unit = unit

    unit_stats = await comlink.get_unit_stats(test_unit)
    assert 'stats' in unit_stats[0].keys()


@pytest.mark.asyncio
async def test_async_get_unit_stats_no_payload(allycode):
    comlink = SwgohComlinkAsync(stats_url='http://192.168.1.167:3223', default_logger_enabled=True)
    with pytest.raises(ValueError):
        unit_stats = await comlink.get_unit_stats()
