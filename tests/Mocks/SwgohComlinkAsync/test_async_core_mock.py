import httpx
import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlinkAsync

comlink = SwgohComlinkAsync()


@pytest.mark.asyncio
async def test_mock_post_exception(httpx_mock: HTTPXMock):
    httpx_mock.add_exception(httpx.RequestError("Request error"))
    with pytest.raises(httpx.RequestError):
        en = await comlink._post(endpoint="/enums", payload={"test": True})
