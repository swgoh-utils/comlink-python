import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlinkAsync


@pytest.mark.asyncio
async def test_mock_async_get_player_by_allycode(httpx_mock: HTTPXMock, allycode):
    httpx_mock.add_response(json={"name": 1}, status_code=200)
    comlink = SwgohComlinkAsync()
    p = await comlink.get_player(allycode=allycode)
    assert "name" in p.keys()


@pytest.mark.asyncio
async def test_mock_async_get_player_by_player_id(httpx_mock: HTTPXMock, player_id):
    httpx_mock.add_response(json={"name": 1}, status_code=200)
    comlink = SwgohComlinkAsync()
    p = await comlink.get_player(player_id=player_id)
    assert "name" in p.keys()


@pytest.mark.asyncio
async def test_mock_async_get_player_arena_by_allycode(httpx_mock: HTTPXMock, allycode):
    httpx_mock.add_response(json={"pvpProfile": 1}, status_code=200)
    comlink = SwgohComlinkAsync()
    p = await comlink.get_player(allycode=allycode)
    assert "pvpProfile" in p.keys()


@pytest.mark.asyncio
async def test_mock_async_get_player_arena_by_player_id(httpx_mock: HTTPXMock, player_id):
    httpx_mock.add_response(json={"pvpProfile": 1}, status_code=200)
    comlink = SwgohComlinkAsync()
    p = await comlink.get_player(player_id=player_id)
    assert "pvpProfile" in p.keys()


@pytest.mark.asyncio
async def test_async_get_player_by_allycode(allycode):
    comlink = SwgohComlinkAsync()
    p = await comlink.get_player(allycode=allycode)
    assert "name" in p.keys()


@pytest.mark.asyncio
async def test_async_get_player_by_player_id(player_id):
    comlink = SwgohComlinkAsync()
    p = await comlink.get_player(player_id=player_id)
    assert "name" in p.keys()


@pytest.mark.asyncio
async def test_async_get_player_both_player_id_and_allycode(allycode, player_id):
    comlink = SwgohComlinkAsync()
    with pytest.raises(ValueError):
        await comlink.get_player(player_id=player_id, allycode=allycode)


@pytest.mark.asyncio
async def test_async_get_player_no_params():
    comlink = SwgohComlinkAsync()
    with pytest.raises(ValueError):
        await comlink.get_player()


@pytest.mark.asyncio
async def test_async_get_player_arena_by_allycode(allycode):
    comlink = SwgohComlinkAsync()
    p = await comlink.get_player_arena(allycode=allycode)
    assert "pvpProfile" in p.keys()


@pytest.mark.asyncio
async def test_async_get_player_arena_by_player_id(player_id):
    comlink = SwgohComlinkAsync()
    p = await comlink.get_player_arena(player_id=player_id)
    assert "pvpProfile" in p.keys()


@pytest.mark.asyncio
async def test_async_get_player_arena_both_player_id_and_allycode(allycode, player_id):
    comlink = SwgohComlinkAsync()
    with pytest.raises(ValueError):
        await comlink.get_player_arena(player_id=player_id, allycode=allycode)


@pytest.mark.asyncio
async def test_async_get_player_arena_no_params():
    comlink = SwgohComlinkAsync()
    with pytest.raises(ValueError):
        await comlink.get_player_arena()
