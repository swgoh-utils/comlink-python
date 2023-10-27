import pytest
from swgoh_comlink import SwgohComlinkAsync


@pytest.mark.asyncio
async def test_async_get_unit_stats():
    comlink = SwgohComlinkAsync()
    p = await comlink.get_player(245866537)
    assert 'name' in p.keys()
    unit_stats = await comlink.get_unit_stats(p['rosterUnit'], flags=['calcGP', 'gameStyle'])
    assert 'gp' in unit_stats['stats'].keys()
