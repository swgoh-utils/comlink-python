import base64
import io
import zipfile

import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlinkAsync


@pytest.mark.asyncio
async def test_mock_async_get_localization_bundle(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"latestLocalizationBundleVersion": "xyz"}, status_code=200)
    httpx_mock.add_response(json={"localizationBundle": "..."}, status_code=200)
    comlink = SwgohComlinkAsync()
    game_metadata = await comlink.get_game_metadata(client_specs={})
    localization_id = game_metadata["latestLocalizationBundleVersion"]
    game_data = await comlink.get_localization(id=localization_id)
    assert "localizationBundle" in game_data.keys()


@pytest.mark.asyncio
async def test_async_get_localization_bundle():
    comlink = SwgohComlinkAsync()
    game_data_versions = await comlink.get_latest_game_data_version()
    location_bundle = await comlink.get_localization_bundle(
        id=game_data_versions["language"]
    )
    loc_bundle_decoded = base64.b64decode(location_bundle["localizationBundle"])
    zip_obj = zipfile.ZipFile(io.BytesIO(loc_bundle_decoded))
    assert 'Loc_ENG_US.txt' in zip_obj.namelist()


@pytest.mark.asyncio
async def test_async_get_localization_bundle_no_id():
    comlink = SwgohComlinkAsync()
    location_bundle = await comlink.get_localization_bundle()
    assert isinstance(location_bundle, dict)
