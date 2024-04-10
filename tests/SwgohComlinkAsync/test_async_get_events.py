import pytest

from swgoh_comlink import SwgohComlinkAsync


@pytest.mark.asyncio
async def test_async_get_events():
    comlink = SwgohComlinkAsync()
    en = await comlink.get_events()
    assert "gameEvent" in en.keys()
    assert len(en['gameEvent']) > 0
