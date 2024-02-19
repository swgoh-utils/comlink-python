import pytest

from comlink_python import SwgohComlinkAsync


@pytest.mark.asyncio
async def test_async_get_localization_bundle():
    comlink = SwgohComlinkAsync()
    game_metadata = await comlink.get_game_metadata()
    localization_id = game_metadata['latestLocalizationBundleVersion']
    game_data = await comlink.get_localization(id=localization_id)
    assert 'localizationBundle' in game_data.keys()
