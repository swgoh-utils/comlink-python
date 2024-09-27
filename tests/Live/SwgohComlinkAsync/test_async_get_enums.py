import pytest

from swgoh_comlink import SwgohComlinkAsync


@pytest.mark.asyncio
async def test_async_get_enums():
    comlink = SwgohComlinkAsync()
    en = await comlink.get_enums()
    assert "CombatType" in en.keys()
    assert en["CombatType"] == {'CHARACTER': 1, 'CombatType_DEFAULT': 0, 'SHIP': 2}
