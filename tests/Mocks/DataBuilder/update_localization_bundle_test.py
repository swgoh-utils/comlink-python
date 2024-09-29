import tempfile
from collections import defaultdict
from unittest.mock import Mock, patch

import pytest

from src.swgoh_comlink.data_builder import DataBuilder


@pytest.fixture
def setup_databuilder():
    with tempfile.TemporaryDirectory() as temp_dir:
        DataBuilder._INITIALIZED = True
        DataBuilder._USE_UNZIP = True
        DataBuilder._COMLINK = Mock()
        DataBuilder._DATA_PATH = temp_dir
        DataBuilder._DATA_VERSION_FILE = 'mockDataVersion'
        DataBuilder._LOCALIZATION_MAP = defaultdict(str)


@pytest.mark.usefixtures("setup_databuilder")
def test_update_localization_bundle_specific_lang_no_force_update():
    mock_server_versions = {'language': 'eng_us'}

    # Mock responses
    DataBuilder._COMLINK.get_latest_game_data_version.return_value = mock_server_versions
    DataBuilder._get_data_versions_from_file = Mock(return_value=mock_server_versions)

    # Test
    assert DataBuilder.update_localization_bundle('eng_us', False) is False


@pytest.mark.usefixtures("setup_databuilder")
def test_update_localization_bundle_specific_lang_with_force_update():
    mock_server_versions = {'game': '1', 'language': 'eng_us'}

    # Mock responses
    DataBuilder._COMLINK.get_latest_game_data_version.return_value = mock_server_versions
    DataBuilder._get_data_versions_from_file = Mock(return_value=mock_server_versions)
    DataBuilder._validate_data_file_paths = Mock()
    DataBuilder._COMLINK.get_localization_bundle.return_value = {
        'Loc_eng_us.txt': ['mock_data']
    }
    DataBuilder._process_file_contents_by_line = Mock(
        return_value=(defaultdict(str), defaultdict(str), defaultdict(str)))

    # Mocking OS path join that is being used while writing JSON File
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch('os.path.join', return_value=f'{temp_dir}/eng_us.json'):
            with patch('os.path.join', return_value=f'{temp_dir}/eng_us_unit_name_keys.json'):
                with patch('os.path.join', return_value=f'{temp_dir}/eng_us_master.json'):
                    with patch('os.path.join', return_value=f'{temp_dir}/mockDataVersion.json'):
                        with patch('json.dump', return_value=True):
                            # Test
                            assert DataBuilder.update_localization_bundle('eng_us', True)


@pytest.mark.usefixtures("setup_databuilder")
def test_update_localization_bundle_all_languages():
    mock_server_versions = {'game': '1', 'language': 'All'}

    # Mock responses
    DataBuilder._COMLINK.get_latest_game_data_version.return_value = mock_server_versions
    DataBuilder._get_data_versions_from_file = Mock(return_value={'game': '1', 'language': 'eng_us'})
    DataBuilder._validate_data_file_paths = Mock()
    DataBuilder._COMLINK.get_localization_bundle.return_value = {
        'Loc_eng_us.txt': ['mock_data'],
        'Loc_fre_fr.txt': ['mock_data']
    }
    DataBuilder._process_file_contents_by_line = Mock(
        return_value=(defaultdict(str), defaultdict(str), defaultdict(str)))

    # Mocking OS path join that is being used while writing JSON File
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch('os.path.join', return_value=f'{temp_dir}/eng_us.json'):
            with patch('os.path.join', return_value=f'{temp_dir}/eng_us_unit_name_keys.json'):
                with patch('os.path.join', return_value=f'{temp_dir}/eng_us_master.json'):
                    with patch('os.path.join', return_value=f'{temp_dir}/fre_fr.json'):
                        with patch('os.path.join', return_value=f'{temp_dir}/fre_fr_unit_name_keys.json'):
                            with patch('os.path.join', return_value=f'{temp_dir}/fre_fr_master.json'):
                                with patch('os.path.join', return_value=f'{temp_dir}/mockDataVersion.json'):
                                    with patch('json.dump', return_value=True):
                                        # Test
                                        assert DataBuilder.update_localization_bundle('eng_us', True)
                                        assert 'eng_us' in DataBuilder._VERSION["languages"]
                                        assert 'fre_fr' in DataBuilder._VERSION["languages"]
