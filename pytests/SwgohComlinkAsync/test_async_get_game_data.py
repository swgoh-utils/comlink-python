import pytest

from comlink_python import SwgohComlinkAsync


@pytest.mark.asyncio
async def test_async_get_game_data():
    """
    Test that game data can be retrieved from game server correctly
    """
    comlink = SwgohComlinkAsync()
    game_metadata = await comlink.get_game_metadata()
    game_version = game_metadata['latestGamedataVersion']
    assert 'latestGamedataVersion' in game_metadata.keys()

    game_data = await comlink.get_game_data(version=game_version, include_pve_units=False, request_segment=4)
    assert 'units' in game_data.keys()


async def test_async_get_game_metadata():
    """
    Test that game data can be retrieved from game server correctly
    """
    comlink = SwgohComlinkAsync()
    game_metadata = await comlink.get_game_metadata()
    assert 'latestGamedataVersion' in game_metadata.keys()
