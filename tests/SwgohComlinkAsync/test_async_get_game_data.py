import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlinkAsync


@pytest.mark.asyncio
async def test_mock_async_get_game_data(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"latestGamedataVersion": 1,
                                  "units": 1}, status_code=200)

    comlink = SwgohComlinkAsync()
    game_metadata = await comlink.get_game_metadata()
    game_version = game_metadata["latestGamedataVersion"]
    assert "latestGamedataVersion" in game_metadata.keys()

    game_data = await comlink.get_game_data(
        version=game_version, include_pve_units=False, request_segment=4
    )
    assert "units" in game_data.keys()


@pytest.mark.asyncio
async def test_mock_async_get_game_metadata(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"latestGamedataVersion": 1}, status_code=200)
    comlink = SwgohComlinkAsync()
    game_metadata = await comlink.get_game_metadata()
    assert "latestGamedataVersion" in game_metadata.keys()


@pytest.mark.asyncio
async def test_async_get_game_metadata():
    comlink = SwgohComlinkAsync()
    game_metadata = await comlink.get_game_metadata()
    assert "latestGamedataVersion" in game_metadata.keys()


@pytest.mark.asyncio
async def test_get_game_metadata_no_client_specs():
    comlink = SwgohComlinkAsync(default_logger_enabled=True)
    game_metadata = await comlink.get_game_metadata(client_specs={})
    assert "latestGamedataVersion" in game_metadata.keys()


@pytest.mark.asyncio
async def test_get_game_metadata_with_client_specs():
    comlink = SwgohComlinkAsync(default_logger_enabled=True)
    game_metadata = await comlink.get_game_metadata(client_specs={"bundleId": "390bljwoSWCqK5VeoRPs3Q"})
    assert "latestGamedataVersion" in game_metadata.keys()


@pytest.mark.asyncio
async def test_async_get_game_data():
    comlink = SwgohComlinkAsync()
    game_data = await comlink.get_game_data(include_pve_units=False, request_segment=1)
    assert 'effect' in game_data.keys()


@pytest.mark.asyncio
async def test_get_game_data_with_version():
    comlink = SwgohComlinkAsync(default_logger_enabled=True)
    versions = await comlink.get_latest_game_data_version()
    game_data = await comlink.get_game_data(version=versions['game'], include_pve_units=False, request_segment=1)
    assert 'effect' in game_data.keys()


@pytest.mark.asyncio
async def test_get_latest_game_data_version():
    comlink = SwgohComlinkAsync()
    game_data = await comlink.get_latest_game_data_version()
    assert 'game' in game_data.keys()
    assert 'language' in game_data.keys()


@pytest.mark.asyncio
async def test_get_latest_game_data_version_with_version():
    comlink = SwgohComlinkAsync(default_logger_enabled=True)
    gd = await comlink.get_latest_game_data_version()
    assert 'game' in gd.keys()
    game_data = await comlink.get_latest_game_data_version(game_version=gd['game'])
    assert 'language' in game_data.keys()
