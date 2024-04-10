import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlinkAsync


@pytest.mark.asyncio
async def test_mock_async_get_enums(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"CombatType": 1}, status_code=200)
    comlink = SwgohComlinkAsync()

    en = await comlink.get_enums()
    assert "CombatType" in en.keys()
