import pytest

from comlink_python import SwgohComlinkAsync


@pytest.mark.asyncio
async def test_async_get_player():
    comlink = SwgohComlinkAsync()
    p = await comlink.get_player(245866537)
    assert 'name' in p.keys()


@pytest.mark.asyncio
async def test_async_get_player_arena():
    comlink = SwgohComlinkAsync()
    p = await comlink.get_player(245866537)
    assert 'pvpProfile' in p.keys()
