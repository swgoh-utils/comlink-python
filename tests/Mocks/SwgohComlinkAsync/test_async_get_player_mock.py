import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlinkAsync

comlink = SwgohComlinkAsync()


@pytest.mark.asyncio
async def test_mock_async_get_player(httpx_mock: HTTPXMock, allycode):
    httpx_mock.add_response(json={"name": 1}, status_code=200)
    p = await comlink.get_player(allycode=allycode)
    assert "name" in p.keys()
