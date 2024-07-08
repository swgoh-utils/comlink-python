# coding=utf-8
"""
Test swgoh_comlink.utils functions
"""
import pytest

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync
from swgoh_comlink.utils import (
    get_async_player,
    get_function_name,
)

comlink = SwgohComlink(default_logger_enabled=True)
async_comlink = SwgohComlinkAsync(default_logger_enabled=True)


@pytest.mark.asyncio
async def test_get_async_player_by_allycode(allycode):
    p = await get_async_player(comlink=async_comlink, allycode=allycode)
    assert "name" in p.keys()


@pytest.mark.asyncio
async def test_get_async_player_by_player_id(player_id):
    p = await get_async_player(comlink=async_comlink, player_id=player_id)
    assert "name" in p.keys()


@pytest.mark.asyncio
async def test_get_async_player_both_player_id_and_allycode(player_id, allycode):
    comlink.logger.debug(f"** Starting {get_function_name()} with {player_id=} and {allycode=}")
    with pytest.raises(ValueError):
        await get_async_player(comlink=async_comlink, player_id=player_id, allycode=allycode)


@pytest.mark.asyncio
async def test_get_async_player_wrong_allycode_type(allycode):
    comlink.logger.debug(f"** Starting {get_function_name()} with {allycode=}")
    with pytest.raises(ValueError):
        await get_async_player(comlink=async_comlink, allycode=str(allycode).encode())


@pytest.mark.asyncio
async def test_get_async_player_both_player_id_and_allycode_wrong_types(player_id, allycode):
    comlink.logger.debug(f"** Starting {get_function_name()} with {player_id=} and {allycode=} as incorrect types.")
    with pytest.raises(ValueError):
        await get_async_player(comlink=async_comlink, player_id=player_id.encode(), allycode=str(allycode).encode())


@pytest.mark.asyncio
async def test_get_async_player_none():
    comlink.logger.debug(f"** Starting {get_function_name()} with only comlink argument.")
    with pytest.raises(ValueError):
        await get_async_player(comlink=async_comlink)


@pytest.mark.asyncio
async def test_get_async_player_no_comlink():
    comlink.logger.debug(f"** Starting {get_function_name()} with no arguments.")
    with pytest.raises(ValueError):
        p = await get_async_player()


@pytest.mark.asyncio
async def test_get_async_player_wrong_comlink():
    comlink.logger.debug(f"** Starting {get_function_name()} with wrong comlink instance type.")
    with pytest.raises(ValueError):
        p = await get_async_player(comlink=comlink)
