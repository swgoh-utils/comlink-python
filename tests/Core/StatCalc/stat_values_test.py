import pytest

from src.swgoh_comlink.StatCalc.stat_values import StatValues
from src.swgoh_comlink.constants import Constants


def test_stat_values_init_default():
    stat_values = StatValues()
    assert stat_values.unit_type == "char"
    assert stat_values.rarity == Constants.MAX_VALUES['UNIT_RARITY']
    assert stat_values.level == Constants.MAX_VALUES['UNIT_LEVEL']
    assert stat_values.gear == Constants.MAX_VALUES['GEAR_TIER']
    assert stat_values.equipment == "all"
    assert stat_values.skills == "max"
    assert stat_values.relic == Constants.MAX_VALUES['RELIC_TIER']
    assert stat_values.mod_rarity == Constants.MAX_VALUES['MOD_RARITY']
    assert stat_values.mod_level == Constants.MAX_VALUES['MOD_LEVEL']
    assert stat_values.mod_tier == Constants.MAX_VALUES['MOD_TIER']
    assert stat_values.purchase_ability_id is None


def test_stat_values_init_with_params():
    stat_values = StatValues(unit_type="char", rarity=5, level=80, gear=12, equipment=[1, 2, 3],
                             skills="max_no_omicron", relic="locked", mod_rarity=5,
                             mod_level=12, mod_tier=5, purchase_ability_id=['abc'])
    assert stat_values.unit_type == "char"
    assert stat_values.rarity == 5
    assert stat_values.level == 80
    assert stat_values.gear == 12
    assert stat_values.equipment == [1, 2, 3]
    assert stat_values.skills == "max_no_omicron"
    assert stat_values.relic == "locked"
    assert stat_values.mod_rarity == 5
    assert stat_values.mod_level == 12
    assert stat_values.mod_tier == 5
    assert stat_values.purchase_ability_id == ['abc']


def test_setattr():
    stat_values = StatValues()
    with pytest.raises(ValueError):
        stat_values.invalid_attr = "value"


def test_to_dict():
    stat_values = StatValues(unit_type="ship", rarity=5)
    stat_values_dict = stat_values.to_dict()
    assert stat_values_dict["unit_type"] == "ship"
    assert stat_values_dict["rarity"] == 5
