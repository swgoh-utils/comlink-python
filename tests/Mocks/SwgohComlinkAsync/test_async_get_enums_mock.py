import httpx
import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlinkAsync

comlink = SwgohComlinkAsync()


@pytest.mark.asyncio
async def test_mock_async_get_enums(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"CombatType": 1}, status_code=200)
    en = await comlink.get_enums()
    assert "CombatType" in en.keys()


@pytest.mark.asyncio
async def test_mock_async_get_enums_exception(httpx_mock: HTTPXMock):
    httpx_mock.add_exception(httpx.RequestError("Request error"))
    with pytest.raises(httpx.RequestError):
        en = await comlink.get_enums()
