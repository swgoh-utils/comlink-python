from src.swgoh_comlink import data_builder
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(default_logger_enabled=False)


def test_initialize():
    result = data_builder.DataBuilder.initialize(
        comlink=comlink,
        data_path="./test_data",
        data_version_file="test_dataVersion.json",
        game_data_path_sub_folder="test_game",
        zip_game_data=True,
        use_segments=True,
        use_unzip=True
    )

    assert result is True
    assert data_builder.DataBuilder._COMLINK is comlink
    assert data_builder.DataBuilder._DATA_PATH == "./test_data"
    assert data_builder.DataBuilder._DATA_VERSION_FILE == "test_dataVersion"
    assert data_builder.DataBuilder._GAME_DATA_PATH_SUB_FOLDER == "test_game"
    assert data_builder.DataBuilder._ZIP_GAME_DATA is True
    assert data_builder.DataBuilder._USE_SEGMENTS is True
    assert data_builder.DataBuilder._USE_UNZIP is True


def test_initialize_without_optional_params():
    result = data_builder.DataBuilder.initialize(comlink=comlink)

    assert result is True
    assert data_builder.DataBuilder._COMLINK is comlink


def test_initialize_without_comlink():
    result = data_builder.DataBuilder.initialize()

    assert result is False
    assert data_builder.DataBuilder._INITIALIZED is False


def test_initialize_with_unexpected_param():
    result = data_builder.DataBuilder.initialize(
        comlink=comlink,
        unexpected_param="value"
    )

    assert result is True
    assert data_builder.DataBuilder._COMLINK is comlink
    assert getattr(data_builder.DataBuilder, "_UNEXPECTED_PARAM", None) is None
