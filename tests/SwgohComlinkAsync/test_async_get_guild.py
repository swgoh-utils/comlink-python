import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlinkAsync


@pytest.mark.asyncio
async def test_mock_async_get_guild_by_criteria(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"guild": 1}, status_code=200)

    comlink = SwgohComlinkAsync()
    p = await comlink.get_guilds_by_criteria(
        search_criteria={"minGuildGalacticPower": 490000000}
    )
    assert "guild" in p.keys()


@pytest.mark.asyncio
async def test_mock_async_get_guild_by_name(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"guild": 1}, status_code=200)

    comlink = SwgohComlinkAsync()
    p = await comlink.get_guilds_by_name("dead")
    assert "guild" in p.keys()


@pytest.mark.asyncio
async def test_async_get_guild_by_criteria():
    comlink = SwgohComlinkAsync()
    p = await comlink.get_guilds_by_criteria(
        search_criteria={"minGuildGalacticPower": 490000000}
    )
    assert "guild" in p.keys()


@pytest.mark.asyncio
async def test_async_get_guild_by_name():
    comlink = SwgohComlinkAsync()
    p = await comlink.get_guilds_by_name("dead")
    assert "guild" in p.keys()


@pytest.mark.asyncio
async def test_async_get_guild_by_id(guild_id):
    comlink = SwgohComlinkAsync()
    p = await comlink.get_guild(guild_id=guild_id)
    assert "profile" in p.keys()


@pytest.mark.asyncio
async def test_async_get_guild_no_id():
    comlink = SwgohComlinkAsync()
    with pytest.raises(ValueError):
        await comlink.get_guild()


@pytest.mark.asyncio
async def test_async_get_guild_invalid_id():
    comlink = SwgohComlinkAsync()
    p = await comlink.get_guild(guild_id=".")
    assert p == {}
