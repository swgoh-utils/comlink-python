import pytest

from comlink_python import SwgohComlinkAsync


@pytest.mark.asyncio
async def test_async_get_guild_by_criteria():
    comlink = SwgohComlinkAsync()
    p = await comlink.get_guilds_by_criteria(search_criteria={"minGuildGalacticPower": 490000000})
    assert 'guild' in p.keys()


@pytest.mark.asyncio
async def test_async_get_guild_by_name():
    comlink = SwgohComlinkAsync()
    p = await comlink.get_guilds_by_name("dead")
    assert 'guild' in p.keys()
