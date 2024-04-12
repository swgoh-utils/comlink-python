import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlinkAsync

comlink = SwgohComlinkAsync()


@pytest.mark.asyncio
async def test_mock_async_get_unit_stats(httpx_mock: HTTPXMock, allycode):
    httpx_mock.add_response(json={"name": 1,
                                  "rosterUnit": [{}, {}],
                                  }, status_code=200)
    p = await comlink.get_player(allycode)
    assert 'name' in p.keys()
    httpx_mock.add_response(json={"stats": {"gp": 1}}, status_code=200)
    unit_stats = await comlink.get_unit_stats(p['rosterUnit'], flags=['calcGP', 'gameStyle'])
    assert 'gp' in unit_stats['stats'].keys()
