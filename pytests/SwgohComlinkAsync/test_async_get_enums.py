import pytest
from swgoh_comlink import SwgohComlinkAsync


@pytest.mark.asyncio
async def test_async_get_enums():
    """
    Test that game enums can be retrieved from game server correctly
    """
    comlink = SwgohComlinkAsync()
    en = await comlink.get_enums()
    assert 'CombatType' in en.keys()
