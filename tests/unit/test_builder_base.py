# coding=utf-8
"""Unit tests for GameDataBuilder transformation logic in _builder_base.py.

All tests use inline fixture data and require no running Comlink service.
"""

from __future__ import annotations

import pytest

from swgoh_comlink.StatCalc.data_builder._builder_base import (
    GameDataBuilderBase,
    _ability_special_gp,
    _build_gear_data,
    _build_mod_set_data,
    _build_relic_data,
    _build_skills_map,
    _build_stat_tables,
    _gear_level_rows,
    _gear_piece_gp_rows,
    _int_rows,
    _mastery_name,
    _mod_cr_rows,
    _mod_gp_rows,
    _num,
    _rarity_rows,
    _relic_rows,
    _resolve_skills,
    _stat_enum_rows,
    _tier_rows,
    _xp_rows,
)


# ===================================================================
# Group A — Utility functions
# ===================================================================


class TestNum:
    """Tests for _num() value coercion."""

    def test_int_passthrough(self):
        assert _num(42) == 42
        assert isinstance(_num(42), int)

    def test_float_passthrough(self):
        assert _num(3.14) == 3.14
        assert isinstance(_num(3.14), float)

    def test_whole_float_normalized_to_int(self):
        assert _num(10.0) == 10
        assert isinstance(_num(10.0), int)

    def test_string_int(self):
        assert _num("100") == 100
        assert isinstance(_num("100"), int)

    def test_string_float(self):
        assert _num("3.14") == 3.14
        assert isinstance(_num("3.14"), float)

    def test_string_whole_float(self):
        assert _num("10.0") == 10
        assert isinstance(_num("10.0"), int)

    def test_none_returns_zero(self):
        assert _num(None) == 0

    def test_empty_string_returns_zero(self):
        assert _num("") == 0

    def test_non_numeric_string_returns_zero(self):
        assert _num("abc") == 0

    def test_negative_int(self):
        assert _num(-5) == -5
        assert isinstance(_num(-5), int)

    def test_negative_float(self):
        assert _num(-3.14) == -3.14
        assert isinstance(_num(-3.14), float)

    def test_zero_int(self):
        assert _num(0) == 0
        assert isinstance(_num(0), int)

    def test_zero_float(self):
        assert _num(0.0) == 0
        assert isinstance(_num(0.0), int)

    def test_large_int_string(self):
        result = _num("52500000000")
        assert result == 52500000000
        assert isinstance(result, int)


class TestResolveSkills:
    """Tests for _resolve_skills() skill reference resolution."""

    def test_empty_refs(self):
        assert _resolve_skills([], {"basic01": {"id": "basic01"}}) == []

    def test_empty_map(self):
        assert _resolve_skills([{"skillId": "x"}], {}) == []

    def test_single_match(self):
        skills_map = {"basic01": {"id": "basic01", "maxTier": 8, "isZeta": False}}
        result = _resolve_skills([{"skillId": "basic01"}], skills_map)
        assert len(result) == 1
        assert result[0]["id"] == "basic01"

    def test_multiple_refs_partial_match(self):
        skills_map = {
            "s1": {"id": "s1"},
            "s2": {"id": "s2"},
        }
        refs = [{"skillId": "s1"}, {"skillId": "missing"}, {"skillId": "s2"}]
        result = _resolve_skills(refs, skills_map)
        assert len(result) == 2
        assert result[0]["id"] == "s1"
        assert result[1]["id"] == "s2"

    def test_returns_copies(self):
        skills_map = {"s1": {"id": "s1", "maxTier": 5}}
        result = _resolve_skills([{"skillId": "s1"}], skills_map)
        result[0]["maxTier"] = 99
        assert skills_map["s1"]["maxTier"] == 5


class TestMasteryName:
    """Tests for _mastery_name() mastery table name derivation."""

    def test_strength_attacker(self):
        assert _mastery_name(2, ["role_attacker"]) == "strength_role_attacker_mastery"

    def test_agility_tank(self):
        assert _mastery_name(3, ["role_tank"]) == "agility_role_tank_mastery"

    def test_intelligence_healer(self):
        assert _mastery_name(4, ["role_healer"]) == "intelligence_role_healer_mastery"

    def test_unknown_stat_defaults_to_strength(self):
        assert _mastery_name(99, ["role_support"]) == "strength_role_support_mastery"

    def test_no_role_defaults_to_attacker(self):
        assert _mastery_name(2, []) == "strength_role_attacker_mastery"

    def test_role_leader_ignored(self):
        assert _mastery_name(2, ["role_leader", "role_support"]) == "strength_role_support_mastery"

    def test_first_matching_role_wins(self):
        assert _mastery_name(3, ["role_tank", "role_attacker"]) == "agility_role_tank_mastery"

    def test_non_role_categories_ignored(self):
        assert _mastery_name(2, ["faction_jedi", "role_healer"]) == "strength_role_healer_mastery"


# ===================================================================
# Group B — Row parsers
# ===================================================================


class TestRarityRows:
    """Tests for _rarity_rows() rarity enum parsing."""

    def test_all_seven_rarities(self):
        rows = [{"key": f"{name}_STAR", "value": i * 10}
                for name, i in [("ONE", 1), ("TWO", 2), ("THREE", 3), ("FOUR", 4),
                                ("FIVE", 5), ("SIX", 6), ("SEVEN", 7)]]
        result = _rarity_rows(rows)
        assert len(result) == 7
        assert result["1"] == 10
        assert result["7"] == 70

    def test_unknown_key_skipped(self):
        assert _rarity_rows([{"key": "UNKNOWN", "value": 100}]) == {}

    def test_empty_rows(self):
        assert _rarity_rows([]) == {}

    def test_subset_of_rarities(self):
        rows = [
            {"key": "THREE_STAR", "value": 30},
            {"key": "FIVE_STAR", "value": 50},
        ]
        result = _rarity_rows(rows)
        assert result == {"3": 30, "5": 50}


class TestTierRows:
    """Tests for _tier_rows() tier key parsing."""

    def test_standard_tiers(self):
        rows = [
            {"key": "TIER_01", "value": 100},
            {"key": "TIER_12", "value": 1200},
        ]
        result = _tier_rows(rows)
        assert result == {"1": 100, "12": 1200}

    def test_leading_zero_stripped(self):
        rows = [{"key": "TIER_01", "value": 5}]
        result = _tier_rows(rows)
        assert "1" in result
        assert "01" not in result

    def test_non_matching_key_skipped(self):
        assert _tier_rows([{"key": "SOMETHING", "value": 5}]) == {}

    def test_empty_rows(self):
        assert _tier_rows([]) == {}


class TestIntRows:
    """Tests for _int_rows() plain key→value parsing."""

    def test_plain_keys(self):
        rows = [
            {"key": "1", "value": 0.37},
            {"key": "2", "value": 0.50},
        ]
        result = _int_rows(rows)
        assert result["1"] == 0.37
        assert result["2"] == 0.50

    def test_empty_rows(self):
        assert _int_rows([]) == {}


class TestRelicRows:
    """Tests for _relic_rows() offset-shifted parsing."""

    def test_offset_applied(self):
        rows = [
            {"key": "0", "value": 100},
            {"key": "1", "value": 200},
        ]
        result = _relic_rows(rows)
        # offset = 2, so 0+2=2, 1+2=3
        assert result == {"2": 100, "3": 200}

    def test_invalid_key_skipped(self):
        assert _relic_rows([{"key": "abc", "value": 100}]) == {}

    def test_empty_rows(self):
        assert _relic_rows([]) == {}


class TestStatEnumRows:
    """Tests for _stat_enum_rows() stat enum string parsing."""

    def test_known_stats(self):
        rows = [
            {"key": "STRENGTH", "value": 3},
            {"key": "MAX_HEALTH", "value": 420},
        ]
        result = _stat_enum_rows(rows)
        assert result == {"2": 3, "1": 420}

    def test_unknown_stat_skipped(self):
        assert _stat_enum_rows([{"key": "NONEXISTENT", "value": 99}]) == {}

    def test_empty_rows(self):
        assert _stat_enum_rows([]) == {}


class TestModCrRows:
    """Tests for _mod_cr_rows() mod CR parsing (pips:level:tier:set)."""

    def test_keeps_tier1_set0(self):
        rows = [
            {"key": "5:10:1:0", "value": 100},
            {"key": "5:10:2:0", "value": 200},  # tier=2, filtered
            {"key": "5:10:1:1", "value": 300},  # set=1, filtered
        ]
        result = _mod_cr_rows(rows)
        assert result == {"5": {"10": 100}}

    def test_nested_structure(self):
        rows = [
            {"key": "5:10:1:0", "value": 100},
            {"key": "5:15:1:0", "value": 150},
            {"key": "6:10:1:0", "value": 200},
        ]
        result = _mod_cr_rows(rows)
        assert result["5"]["10"] == 100
        assert result["5"]["15"] == 150
        assert result["6"]["10"] == 200

    def test_empty_rows(self):
        assert _mod_cr_rows([]) == {}


class TestModGpRows:
    """Tests for _mod_gp_rows() mod GP parsing (pips:level:tier:set)."""

    def test_filters_set0(self):
        rows = [
            {"key": "5:10:1:0", "value": 100},
            {"key": "5:10:1:1", "value": 200},  # set=1, filtered
        ]
        result = _mod_gp_rows(rows)
        assert result == {"5": {"10": {"1": 100}}}

    def test_three_level_nesting(self):
        rows = [
            {"key": "5:10:1:0", "value": 100},
            {"key": "5:10:2:0", "value": 200},
            {"key": "6:15:1:0", "value": 300},
        ]
        result = _mod_gp_rows(rows)
        assert result["5"]["10"]["1"] == 100
        assert result["5"]["10"]["2"] == 200
        assert result["6"]["15"]["1"] == 300

    def test_key_too_short_skipped(self):
        assert _mod_gp_rows([{"key": "1:2:0", "value": 5}]) == {}

    def test_empty_rows(self):
        assert _mod_gp_rows([]) == {}


class TestGearLevelRows:
    """Tests for _gear_level_rows() gear-level-with-increment parsing."""

    def test_initializes_with_gear_1_zero(self):
        result = _gear_level_rows([])
        assert result == {"1": 0}

    def test_tier_incremented(self):
        rows = [{"key": "TIER_01", "value": 42}]
        result = _gear_level_rows(rows)
        assert result == {"1": 0, "2": 42}

    def test_multiple_tiers(self):
        rows = [
            {"key": "TIER_01", "value": 10},
            {"key": "TIER_05", "value": 50},
            {"key": "TIER_13", "value": 130},
        ]
        result = _gear_level_rows(rows)
        assert result["1"] == 0
        assert result["2"] == 10
        assert result["6"] == 50
        assert result["14"] == 130


class TestGearPieceGpRows:
    """Tests for _gear_piece_gp_rows() tier:slot parsing with slot decrement."""

    def test_slot_decremented(self):
        rows = [{"key": "TIER_01:1", "value": 10}]
        result = _gear_piece_gp_rows(rows)
        assert result == {"1": {"0": 10}}

    def test_slot_range(self):
        rows = [
            {"key": "TIER_01:1", "value": 10},
            {"key": "TIER_01:6", "value": 60},
        ]
        result = _gear_piece_gp_rows(rows)
        assert result["1"]["0"] == 10
        assert result["1"]["5"] == 60

    def test_plain_tier_key(self):
        rows = [{"key": "1:2", "value": 20}]
        result = _gear_piece_gp_rows(rows)
        assert result == {"1": {"1": 20}}

    def test_key_without_colon_skipped(self):
        assert _gear_piece_gp_rows([{"key": "TIER_01", "value": 5}]) == {}

    def test_empty_rows(self):
        assert _gear_piece_gp_rows([]) == {}


class TestAbilitySpecialGp:
    """Tests for _ability_special_gp() flat key→value parsing."""

    def test_flat_mapping(self):
        rows = [
            {"key": "zeta", "value": 1500},
            {"key": "omicron", "value": 2000},
        ]
        result = _ability_special_gp(rows)
        assert result == {"zeta": 1500, "omicron": 2000}

    def test_empty_rows(self):
        assert _ability_special_gp([]) == {}


class TestXpRows:
    """Tests for _xp_rows() 0-indexed → 1-indexed conversion."""

    def test_zero_indexed_to_one_indexed(self):
        rows = [
            {"index": 0, "xp": 100},
            {"index": 1, "xp": 200},
            {"index": 2, "xp": 400},
        ]
        result = _xp_rows(rows)
        assert result == {"1": 100, "2": 200, "3": 400}

    def test_empty_rows(self):
        assert _xp_rows([]) == {}


# ===================================================================
# Group C — Intermediate builder functions
# ===================================================================


class TestBuildStatTables:
    """Tests for _build_stat_tables() stat progression parsing."""

    def test_empty_input(self):
        assert _build_stat_tables([]) == {}

    def test_non_stattable_filtered(self):
        entries = [{"id": "other_thing", "stat": {"stat": [{"unitStatId": 1, "unscaledDecimalValue": 5}]}}]
        result = _build_stat_tables(entries)
        assert result == {}

    def test_single_table(self):
        entries = [{
            "id": "stattable_foo",
            "stat": {"stat": [
                {"unitStatId": 2, "unscaledDecimalValue": 100},
                {"unitStatId": 3, "unscaledDecimalValue": "50.0"},
            ]},
        }]
        result = _build_stat_tables(entries)
        assert "stattable_foo" in result
        assert result["stattable_foo"]["2"] == 100
        assert result["stattable_foo"]["3"] == 50
        assert isinstance(result["stattable_foo"]["3"], int)

    def test_multiple_tables(self):
        entries = [
            {"id": "stattable_a", "stat": {"stat": [{"unitStatId": 1, "unscaledDecimalValue": 10}]}},
            {"id": "stattable_b", "stat": {"stat": [{"unitStatId": 2, "unscaledDecimalValue": 20}]}},
        ]
        result = _build_stat_tables(entries)
        assert len(result) == 2


class TestBuildSkillsMap:
    """Tests for _build_skills_map() skill metadata building."""

    def test_empty_input(self):
        assert _build_skills_map([]) == {}

    def test_skill_no_tiers(self):
        skills = [{"id": "basic01", "tier": []}]
        result = _build_skills_map(skills)
        assert result["basic01"]["maxTier"] == 1
        assert result["basic01"]["isZeta"] is False
        assert result["basic01"]["powerOverrideTags"] == {}

    def test_skill_with_zeta(self):
        skills = [{
            "id": "special01",
            "tier": [
                {"powerOverrideTag": ""},
                {"powerOverrideTag": ""},
                {"powerOverrideTag": "zeta"},
            ],
        }]
        result = _build_skills_map(skills)
        assert result["special01"]["isZeta"] is True
        assert result["special01"]["maxTier"] == 4

    def test_power_override_tags_collected(self):
        skills = [{
            "id": "unique01",
            "tier": [
                {"powerOverrideTag": ""},
                {"powerOverrideTag": "zeta"},
                {"powerOverrideTag": ""},
                {"powerOverrideTag": "omicron"},
            ],
        }]
        result = _build_skills_map(skills)
        tags = result["unique01"]["powerOverrideTags"]
        assert tags == {"3": "zeta", "5": "omicron"}


class TestBuildGearData:
    """Tests for _build_gear_data() equipment stat parsing."""

    def test_empty_input(self):
        assert _build_gear_data([]) == {}

    def test_gear_with_stats(self):
        equipment = [{
            "id": "gear001",
            "equipmentStat": {"stat": [
                {"unitStatId": 1, "unscaledDecimalValue": 500},
                {"unitStatId": 6, "unscaledDecimalValue": 25},
            ]},
        }]
        result = _build_gear_data(equipment)
        assert "gear001" in result
        assert result["gear001"]["stats"]["1"] == 500
        assert result["gear001"]["stats"]["6"] == 25

    def test_gear_without_stats_excluded(self):
        equipment = [{"id": "gear_empty", "equipmentStat": {"stat": []}}]
        result = _build_gear_data(equipment)
        assert result == {}

    def test_mixed_gear(self):
        equipment = [
            {"id": "g1", "equipmentStat": {"stat": [{"unitStatId": 1, "unscaledDecimalValue": 10}]}},
            {"id": "g2", "equipmentStat": {"stat": []}},
            {"id": "g3", "equipmentStat": {"stat": [{"unitStatId": 2, "unscaledDecimalValue": 20}]}},
        ]
        result = _build_gear_data(equipment)
        assert len(result) == 2
        assert "g1" in result
        assert "g2" not in result
        assert "g3" in result


class TestBuildModSetData:
    """Tests for _build_mod_set_data() mod set parsing."""

    def test_empty_input(self):
        assert _build_mod_set_data([]) == {}

    def test_single_mod_set(self):
        mod_sets = [{
            "id": "1",
            "setCount": 4,
            "completeBonus": {"stat": {
                "unitStatId": 1,
                "unscaledDecimalValue": "0.05",
            }},
        }]
        result = _build_mod_set_data(mod_sets)
        assert "1" in result
        assert result["1"]["id"] == 1
        assert result["1"]["count"] == 4
        assert result["1"]["value"] == 0.05

    def test_value_coercion(self):
        mod_sets = [{
            "id": "2",
            "setCount": 2,
            "completeBonus": {"stat": {
                "unitStatId": 5,
                "unscaledDecimalValue": "10.0",
            }},
        }]
        result = _build_mod_set_data(mod_sets)
        assert result["2"]["value"] == 10
        assert isinstance(result["2"]["value"], int)


class TestBuildRelicData:
    """Tests for _build_relic_data() relic tier parsing."""

    def test_empty_input(self):
        assert _build_relic_data([], {}) == {}

    def test_relic_with_stats_and_gms(self):
        relic_defs = [{
            "id": "relic_tier_01",
            "stat": {"stat": [
                {"unitStatId": 1, "unscaledDecimalValue": 1000},
            ]},
            "relicStatTable": "stattable_relic_01",
        }]
        stat_tables = {
            "stattable_relic_01": {"2": 50, "3": 30},
        }
        result = _build_relic_data(relic_defs, stat_tables)
        assert "relic_tier_01" in result
        assert result["relic_tier_01"]["stats"]["1"] == 1000
        assert result["relic_tier_01"]["gms"] == {"2": 50, "3": 30}

    def test_relic_missing_stat_table(self):
        relic_defs = [{
            "id": "relic_tier_02",
            "stat": {"stat": []},
            "relicStatTable": "nonexistent_table",
        }]
        result = _build_relic_data(relic_defs, {})
        assert result["relic_tier_02"]["gms"] == {}


class TestBuildCrGpTables:
    """Tests for _build_cr_gp_tables() CR/GP table building."""

    def test_empty_inputs(self):
        from swgoh_comlink.StatCalc.data_builder._builder_base import _build_cr_gp_tables
        cr, gp = _build_cr_gp_tables([], [])
        assert cr == {}
        assert gp == {}

    def test_shared_table_populates_both(self):
        from swgoh_comlink.StatCalc.data_builder._builder_base import _build_cr_gp_tables
        tables = [{
            "id": "crew_rating_per_unit_rarity",
            "row": [
                {"key": "ONE_STAR", "value": 10},
                {"key": "SEVEN_STAR", "value": 70},
            ],
        }]
        cr, gp = _build_cr_gp_tables(tables, [])
        assert "crewRarityCR" in cr
        assert "unitRarityGP" in gp
        assert cr["crewRarityCR"] is gp["unitRarityGP"]

    def test_mastery_table(self):
        from swgoh_comlink.StatCalc.data_builder._builder_base import _build_cr_gp_tables
        tables = [{
            "id": "strength_role_attacker_mastery",
            "row": [{"key": "STRENGTH", "value": 5}],
        }]
        cr, gp = _build_cr_gp_tables(tables, [])
        assert "strength_role_attacker_mastery" in cr
        assert cr["strength_role_attacker_mastery"]["2"] == 5

    def test_xp_tables_shared(self):
        from swgoh_comlink.StatCalc.data_builder._builder_base import _build_cr_gp_tables
        xp_tables = [{
            "id": "crew_rating_per_unit_level",
            "row": [
                {"index": 0, "xp": 100},
                {"index": 1, "xp": 200},
            ],
        }]
        cr, gp = _build_cr_gp_tables([], xp_tables)
        assert "unitLevelCR" in cr
        assert "unitLevelGP" in gp
        assert cr["unitLevelCR"] is gp["unitLevelGP"]
        assert cr["unitLevelCR"]["1"] == 100

    def test_gp_only_tables(self):
        from swgoh_comlink.StatCalc.data_builder._builder_base import _build_cr_gp_tables
        tables = [{
            "id": "galactic_power_modifier_per_ship_crew_size_table",
            "row": [{"key": "1", "value": 0.5}, {"key": "2", "value": 0.75}],
        }]
        cr, gp = _build_cr_gp_tables(tables, [])
        assert "crewSizeFactor" in gp
        assert "crewSizeFactor" not in cr

    def test_gear_level_shared(self):
        from swgoh_comlink.StatCalc.data_builder._builder_base import _build_cr_gp_tables
        tables = [{
            "id": "galactic_power_per_complete_gear_tier_table",
            "row": [{"key": "TIER_01", "value": 42}],
        }]
        cr, gp = _build_cr_gp_tables(tables, [])
        assert "gearLevelGP" in gp
        assert "gearLevelCR" in cr
        assert gp["gearLevelGP"] is cr["gearLevelCR"]
        assert gp["gearLevelGP"]["1"] == 0
        assert gp["gearLevelGP"]["2"] == 42


class TestBuildCharacter:
    """Tests for _build_character() via _build_unit_data()."""

    def test_basic_character_structure(self):
        from swgoh_comlink.StatCalc.data_builder._builder_base import _build_unit_data
        units = [{
            "baseId": "BOSSK",
            "obtainable": True,
            "obtainableTime": "0",
            "rarity": 1,
            "combatType": 1,
            "primaryUnitStat": 2,
            "unitTier": [{
                "tier": 1,
                "baseStat": {"stat": [{"unitStatId": 1, "unscaledDecimalValue": 100}]},
                "equipmentSet": ["eq001"],
            }],
            "skillReference": [],
            "categoryId": ["role_tank"],
            "relicDefinition": {"relicTierDefinitionId": []},
            "statProgressionId": "stattable_bossk",
        }]
        stat_tables = {"stattable_bossk": {"2": 50}}
        result = _build_unit_data(units, stat_tables, {})
        assert "BOSSK" in result
        char = result["BOSSK"]
        assert char["combatType"] == 1
        assert char["primaryStat"] == 2
        assert "gearLvl" in char
        assert "growthModifiers" in char
        assert "skills" in char
        assert "relic" in char
        assert char["masteryModifierID"] == "strength_role_tank_mastery"

    def test_gear_tiers_parsed(self):
        from swgoh_comlink.StatCalc.data_builder._builder_base import _build_unit_data
        units = [{
            "baseId": "VADER",
            "obtainable": True,
            "obtainableTime": "0",
            "rarity": 1,
            "combatType": 1,
            "primaryUnitStat": 2,
            "unitTier": [
                {"tier": 1, "baseStat": {"stat": []}, "equipmentSet": ["a"]},
                {"tier": 2, "baseStat": {"stat": []}, "equipmentSet": ["b"]},
            ],
            "skillReference": [],
            "categoryId": [],
            "relicDefinition": {"relicTierDefinitionId": []},
            "statProgressionId": "",
        }]
        result = _build_unit_data(units, {}, {})
        assert "1" in result["VADER"]["gearLvl"]
        assert "2" in result["VADER"]["gearLvl"]

    def test_relic_tier_ids_offset(self):
        from swgoh_comlink.StatCalc.data_builder._builder_base import _build_unit_data
        units = [{
            "baseId": "CHAR1",
            "obtainable": True,
            "obtainableTime": "0",
            "rarity": 1,
            "combatType": 1,
            "primaryUnitStat": 2,
            "unitTier": [],
            "skillReference": [],
            "categoryId": [],
            "relicDefinition": {
                "relicTierDefinitionId": ["relic_def_01_tier_0", "relic_def_01_tier_1"],
            },
            "statProgressionId": "",
        }]
        result = _build_unit_data(units, {}, {})
        relic = result["CHAR1"]["relic"]
        # tier 0 + offset 2 = key "2", tier 1 + offset 2 = key "3"
        assert "2" in relic
        assert "3" in relic


class TestBuildShip:
    """Tests for _build_ship() via _build_unit_data()."""

    def test_basic_ship_structure(self):
        from swgoh_comlink.StatCalc.data_builder._builder_base import _build_unit_data
        units = [{
            "baseId": "YOURSHIP",
            "obtainable": True,
            "obtainableTime": "0",
            "rarity": 1,
            "combatType": 2,
            "primaryUnitStat": 2,
            "baseStat": {"stat": [
                {"unitStatId": 1, "unscaledDecimalValue": 5000},
            ]},
            "skillReference": [],
            "crewContributionTableId": "",
            "crew": [],
            "statProgressionId": "",
        }]
        result = _build_unit_data(units, {}, {})
        assert "YOURSHIP" in result
        ship = result["YOURSHIP"]
        assert ship["combatType"] == 2
        assert ship["primaryStat"] == 2
        assert "stats" in ship
        assert "growthModifiers" in ship
        assert "skills" in ship
        assert "crewStats" in ship
        assert "crew" in ship

    def test_crew_members_collected(self):
        from swgoh_comlink.StatCalc.data_builder._builder_base import _build_unit_data
        skills_map = {
            "crew_skill_1": {"id": "crew_skill_1", "maxTier": 3, "isZeta": False, "powerOverrideTags": {}},
        }
        units = [{
            "baseId": "SHIP1",
            "obtainable": True,
            "obtainableTime": "0",
            "rarity": 1,
            "combatType": 2,
            "primaryUnitStat": 2,
            "baseStat": {"stat": []},
            "skillReference": [],
            "crewContributionTableId": "",
            "crew": [
                {"unitId": "PILOT_A", "skillReference": [{"skillId": "crew_skill_1"}]},
                {"unitId": "PILOT_B", "skillReference": []},
            ],
            "statProgressionId": "",
        }]
        result = _build_unit_data(units, {}, skills_map)
        ship = result["SHIP1"]
        assert ship["crew"] == ["PILOT_A", "PILOT_B"]
        assert len(ship["skills"]) == 1
        assert ship["skills"][0]["id"] == "crew_skill_1"


class TestBuildGameData:
    """Tests for GameDataBuilderBase._build_game_data() orchestration."""

    def test_empty_raw_has_all_six_keys(self):
        result = GameDataBuilderBase._build_game_data({})
        expected_keys = {"unitData", "gearData", "modSetData", "crTables", "gpTables", "relicData"}
        assert set(result.keys()) == expected_keys

    def test_empty_raw_produces_empty_sections(self):
        result = GameDataBuilderBase._build_game_data({})
        for key in ("unitData", "gearData", "modSetData", "crTables", "gpTables", "relicData"):
            assert isinstance(result[key], dict)

    def test_minimal_raw_produces_nonempty_gear(self):
        raw = {
            "equipment": [{
                "id": "gear001",
                "equipmentStat": {"stat": [
                    {"unitStatId": 1, "unscaledDecimalValue": 100},
                ]},
            }],
        }
        result = GameDataBuilderBase._build_game_data(raw)
        assert len(result["gearData"]) == 1

    def test_growth_modifiers_across_rarities(self):
        """Multiple rarities for the same unit populate growthModifiers."""
        units = [
            {
                "baseId": "UNIT1",
                "obtainable": True,
                "obtainableTime": "0",
                "rarity": 1,
                "combatType": 1,
                "primaryUnitStat": 2,
                "unitTier": [],
                "skillReference": [],
                "categoryId": [],
                "relicDefinition": {"relicTierDefinitionId": []},
                "statProgressionId": "stattable_unit1_r1",
            },
            {
                "baseId": "UNIT1",
                "obtainable": True,
                "obtainableTime": "0",
                "rarity": 7,
                "combatType": 1,
                "primaryUnitStat": 2,
                "statProgressionId": "stattable_unit1_r7",
            },
        ]
        stat_tables_raw = [
            {"id": "stattable_unit1_r1", "stat": {"stat": [{"unitStatId": 2, "unscaledDecimalValue": 10}]}},
            {"id": "stattable_unit1_r7", "stat": {"stat": [{"unitStatId": 2, "unscaledDecimalValue": 70}]}},
        ]
        raw = {"units": units, "statProgression": stat_tables_raw}
        result = GameDataBuilderBase._build_game_data(raw)
        gm = result["unitData"]["UNIT1"]["growthModifiers"]
        assert "1" in gm
        assert "7" in gm
        assert gm["1"]["2"] == 10
        assert gm["7"]["2"] == 70

    def test_non_obtainable_units_excluded(self):
        """Units with obtainable=False or obtainableTime != '0' are skipped."""
        units = [
            {
                "baseId": "PLAYABLE",
                "obtainable": True,
                "obtainableTime": "0",
                "rarity": 1,
                "combatType": 1,
                "primaryUnitStat": 2,
                "unitTier": [],
                "skillReference": [],
                "categoryId": [],
                "relicDefinition": {"relicTierDefinitionId": []},
                "statProgressionId": "",
            },
            {
                "baseId": "NOT_OBTAINABLE",
                "obtainable": False,
                "obtainableTime": "0",
                "rarity": 1,
                "combatType": 1,
                "primaryUnitStat": 2,
                "unitTier": [],
                "skillReference": [],
                "categoryId": [],
                "relicDefinition": {"relicTierDefinitionId": []},
                "statProgressionId": "",
            },
        ]
        raw = {"units": units}
        result = GameDataBuilderBase._build_game_data(raw)
        assert "PLAYABLE" in result["unitData"]
        assert "NOT_OBTAINABLE" not in result["unitData"]
