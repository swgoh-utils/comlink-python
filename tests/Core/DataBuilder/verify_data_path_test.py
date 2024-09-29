import os
import tempfile
from pathlib import Path

import pytest

from src.swgoh_comlink.data_builder import _verify_data_path


def test_verify_data_path_for_existing_directory():
    with tempfile.TemporaryDirectory() as temp_dir:
        _verify_data_path(temp_dir)
        assert Path(temp_dir).exists()


def test_verify_data_path_for_non_existing_directory():
    with tempfile.TemporaryDirectory() as temp_dir:
        non_existing_path = Path(temp_dir) / "non_existing_dir"
        _verify_data_path(non_existing_path)
        assert Path(non_existing_path).exists()


def test_verify_data_path_for_nested_non_existing_directory():
    with tempfile.TemporaryDirectory() as temp_dir:
        nested_non_existing_path = Path(temp_dir) / "nested" / "non_existing_dir"
        _verify_data_path(nested_non_existing_path)
        assert Path(nested_non_existing_path).exists()


def test_verify_data_path_with_string_input():
    with tempfile.TemporaryDirectory() as temp_dir:
        nested_non_existing_path_str = os.path.join(temp_dir, "nested", "non_existing_dir")
        _verify_data_path(nested_non_existing_path_str)
        assert Path(nested_non_existing_path_str).exists()


def test_verify_data_path_with_path_input():
    with tempfile.TemporaryDirectory() as temp_dir:
        nested_non_existing_path = Path(temp_dir) / "nested" / "non_existing_dir"
        _verify_data_path(nested_non_existing_path)
        assert nested_non_existing_path.exists()


@pytest.mark.parametrize("invalid_data_path", [123, [], {}, None])
def test_verify_data_path_for_invalid_input(invalid_data_path):
    with pytest.raises(TypeError):
        _verify_data_path(invalid_data_path)
