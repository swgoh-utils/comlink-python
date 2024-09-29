from src.swgoh_comlink import data_builder
from src.swgoh_comlink.constants import Constants


def test_load_stat_enums_map_dict():
    stat_enums, localization_map = data_builder._load_stat_enums_map_dict()

    assert stat_enums["TAUNT"] == "59"
    assert stat_enums["STRENGTH"] == "2"
    assert stat_enums["MASTERY"] == "61"

    assert localization_map["UnitStat_MaxShieldPercentAdditive"] == "56"
    assert localization_map["UNIT_STAT_STAT_VIEW_MASTERY"] == "61"
    assert "name_key3" not in localization_map


def test_load_stat_enums_map_dict_empty_map():
    Constants.UNIT_STAT_ENUMS_MAP = {}

    stat_enums, localization_map = data_builder._load_stat_enums_map_dict()

    assert len(stat_enums) != 0
    assert len(localization_map) != 0
