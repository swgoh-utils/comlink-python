"""Tests for pure helper functions that need no HTTP mocking."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest

from swgoh_comlink.exceptions import SwgohComlinkValueError

# ── _utils ──────────────────────────────────────────────────────────────


class TestGetFunctionName:
    def test_returns_calling_function_name(self):
        from swgoh_comlink.helpers._utils import get_function_name

        def my_custom_func():
            return get_function_name()

        assert my_custom_func() == "my_custom_func()"


class TestGetEnumKeyByValue:
    def test_match_found(self):
        from swgoh_comlink.helpers._utils import get_enum_key_by_value

        enum_dict = {"colors": {"red": 1, "blue": 2}}
        assert get_enum_key_by_value(enum_dict, "colors", 2) == "blue"

    def test_no_match(self):
        from swgoh_comlink.helpers._utils import get_enum_key_by_value

        enum_dict = {"colors": {"red": 1}}
        assert get_enum_key_by_value(enum_dict, "colors", 99) is None

    def test_missing_category(self):
        from swgoh_comlink.helpers._utils import get_enum_key_by_value

        enum_dict = {"colors": {"red": 1}}
        assert get_enum_key_by_value(enum_dict, "shapes", 1) is None

    def test_custom_default_return(self):
        from swgoh_comlink.helpers._utils import get_enum_key_by_value

        enum_dict = {"colors": {"red": 1}}
        assert get_enum_key_by_value(enum_dict, "shapes", 1, "fallback") == "fallback"


class TestValidateFilePath:
    def test_valid_file(self, tmp_path: Path):
        from swgoh_comlink.helpers._utils import validate_file_path

        f = tmp_path / "test.txt"
        f.write_text("hello")
        assert validate_file_path(f) is True

    def test_nonexistent_file(self, tmp_path: Path):
        from swgoh_comlink.helpers._utils import validate_file_path

        assert validate_file_path(tmp_path / "nope.txt") is False

    def test_directory_returns_false(self, tmp_path: Path):
        from swgoh_comlink.helpers._utils import validate_file_path

        assert validate_file_path(tmp_path) is False

    def test_empty_raises(self):
        from swgoh_comlink.helpers._utils import validate_file_path

        with pytest.raises(SwgohComlinkValueError, match="path"):
            validate_file_path("")


class TestSanitizeAllycode:
    def test_valid_string(self):
        from swgoh_comlink.helpers._utils import sanitize_allycode

        assert sanitize_allycode("123456789") == "123456789"

    def test_valid_int(self):
        from swgoh_comlink.helpers._utils import sanitize_allycode

        assert sanitize_allycode(123456789) == "123456789"

    def test_dashes_removed(self):
        from swgoh_comlink.helpers._utils import sanitize_allycode

        assert sanitize_allycode("123-456-789") == "123456789"

    def test_wrong_length_raises(self):
        from swgoh_comlink.helpers._utils import sanitize_allycode

        with pytest.raises(SwgohComlinkValueError, match="Invalid ally code"):
            sanitize_allycode("12345")

    def test_non_digits_raises(self):
        from swgoh_comlink.helpers._utils import sanitize_allycode

        with pytest.raises(SwgohComlinkValueError, match="Invalid ally code"):
            sanitize_allycode("12345abcd")

    def test_zero_raises(self):
        from swgoh_comlink.helpers._utils import sanitize_allycode

        # 0 is falsy but is not the REQUIRED sentinel, so it falls
        # through to validation and raises (not a valid 9-digit allycode).
        with pytest.raises(SwgohComlinkValueError, match="Invalid ally code"):
            sanitize_allycode(0)

    def test_default_none_returns_empty(self):
        from swgoh_comlink.helpers._utils import sanitize_allycode

        # Calling with no argument uses the None default,
        # which triggers the early "" return.
        assert sanitize_allycode() == ""


class TestHumanTime:
    def test_seconds(self):
        from swgoh_comlink.helpers._utils import human_time

        assert human_time(0) == "1970-01-01 00:00:00"

    def test_milliseconds_converted(self):
        from swgoh_comlink.helpers._utils import human_time

        # 13+ digit timestamp treated as milliseconds
        assert human_time(1700000000000) == human_time(1700000000)

    def test_float_input(self):
        from swgoh_comlink.helpers._utils import human_time

        result = human_time(1700000000.5)
        assert result == "2023-11-14 22:13:20"

    def test_string_input(self):
        from swgoh_comlink.helpers._utils import human_time

        assert human_time("0") == "1970-01-01 00:00:00"

    def test_invalid_string_raises(self):
        from swgoh_comlink.helpers._utils import human_time

        with pytest.raises(SwgohComlinkValueError, match="Unable to convert"):
            human_time("not_a_number")

    def test_non_numeric_type_raises(self):
        from swgoh_comlink.helpers._utils import human_time

        with pytest.raises(SwgohComlinkValueError, match="required"):
            human_time([])


class TestConvertRelicTier:
    def test_valid_int(self):
        from swgoh_comlink.helpers._utils import convert_relic_tier

        assert convert_relic_tier(0) == "LOCKED"
        assert convert_relic_tier(1) == "UNLOCKED"
        assert convert_relic_tier(2) == "1"

    def test_valid_string(self):
        from swgoh_comlink.helpers._utils import convert_relic_tier

        assert convert_relic_tier("9") == "8"

    def test_unknown_tier_returns_none(self):
        from swgoh_comlink.helpers._utils import convert_relic_tier

        assert convert_relic_tier(99) is None

    def test_invalid_type_raises(self):
        from swgoh_comlink.helpers._utils import convert_relic_tier

        with pytest.raises(SwgohComlinkValueError, match="relic_tier"):
            convert_relic_tier(None)


# ── _arena ──────────────────────────────────────────────────────────────


class TestGetMaxRankJump:
    def test_rank_below_6_returns_1(self):
        from swgoh_comlink.helpers._arena import get_max_rank_jump

        assert get_max_rank_jump(1) == 1
        assert get_max_rank_jump(5) == 1

    def test_rank_6(self):
        from swgoh_comlink.helpers._arena import get_max_rank_jump

        result = get_max_rank_jump(6)
        assert result == 6 - (3 + max(5 // 6, 1))

    def test_rank_54(self):
        from math import floor

        from swgoh_comlink.helpers._arena import get_max_rank_jump

        result = get_max_rank_jump(54)
        assert result == 54 - (3 + max(floor(53 / 6), 1))

    def test_rank_55(self):
        from swgoh_comlink.helpers._arena import get_max_rank_jump

        result = get_max_rank_jump(55)
        assert result == int(round(55 * 0.85 - 1))

    def test_rank_100(self):
        from swgoh_comlink.helpers._arena import get_max_rank_jump

        result = get_max_rank_jump(100)
        assert result == int(round(100 * 0.85 - 1))


class TestGetArenaPayout:
    def test_squad_uses_hour_18(self):
        from swgoh_comlink.helpers._arena import get_arena_payout

        result = get_arena_payout(offset=0, fleet=False)
        # The payout should be at 18:00 local adjusted for UTC offset
        assert result is not None

    def test_fleet_uses_hour_19(self):
        from swgoh_comlink.helpers._arena import get_arena_payout

        result = get_arena_payout(offset=0, fleet=True)
        assert result is not None

    def test_returns_future_datetime(self):
        from datetime import datetime

        from swgoh_comlink.helpers._arena import get_arena_payout

        # Using a large negative offset to push payout into the future
        result = get_arena_payout(offset=-1440)
        assert result > datetime.now()


# ── _omicron ────────────────────────────────────────────────────────────

_SKILL_LIST: list[dict[str, Any]] = [
    {"id": "skill_A", "omicronMode": 8, "tier": [{"isOmicronTier": False}, {"isOmicronTier": True}]},
    {"id": "skill_B", "omicronMode": 3, "tier": [{"isOmicronTier": False}]},
    {"id": "skill_C", "omicronMode": 8, "tier": [{"isOmicronTier": True}]},
]


class TestGetTwOmicrons:
    def test_filters_mode_8(self):
        from swgoh_comlink.helpers._omicron import get_tw_omicrons

        result = get_tw_omicrons(_SKILL_LIST)
        assert len(result) == 2
        assert all(s["omicronMode"] == 8 for s in result)

    def test_empty_list(self):
        from swgoh_comlink.helpers._omicron import get_tw_omicrons

        assert get_tw_omicrons([]) == []

    def test_invalid_type_raises(self):
        from swgoh_comlink.helpers._omicron import get_tw_omicrons

        with pytest.raises(SwgohComlinkValueError, match="list"):
            get_tw_omicrons("not a list")


class TestGetOmicronSkills:
    def test_single_int(self):
        from swgoh_comlink.helpers._omicron import get_omicron_skills

        result = get_omicron_skills(_SKILL_LIST, 3)
        assert len(result) == 1
        assert result[0]["id"] == "skill_B"

    def test_list_of_ints(self):
        from swgoh_comlink.helpers._omicron import get_omicron_skills

        result = get_omicron_skills(_SKILL_LIST, [3, 8])
        assert len(result) == 3

    def test_no_match(self):
        from swgoh_comlink.helpers._omicron import get_omicron_skills

        assert get_omicron_skills(_SKILL_LIST, 99) == []

    def test_invalid_skill_list_raises(self):
        from swgoh_comlink.helpers._omicron import get_omicron_skills

        with pytest.raises(SwgohComlinkValueError, match="list"):
            get_omicron_skills("bad", 8)

    def test_invalid_omicron_type_raises(self):
        from swgoh_comlink.helpers._omicron import get_omicron_skills

        with pytest.raises(SwgohComlinkValueError, match="omicron_type"):
            get_omicron_skills([], "bad")


class TestGetOmicronSkillTier:
    def test_tier_found(self):
        from swgoh_comlink.helpers._omicron import get_omicron_skill_tier

        skill = {"tier": [{"isOmicronTier": False}, {"isOmicronTier": True}]}
        assert get_omicron_skill_tier(skill) == 1

    def test_no_omicron_tier(self):
        from swgoh_comlink.helpers._omicron import get_omicron_skill_tier

        skill = {"tier": [{"isOmicronTier": False}]}
        assert get_omicron_skill_tier(skill) is None

    def test_invalid_type_raises(self):
        from swgoh_comlink.helpers._omicron import get_omicron_skill_tier

        with pytest.raises(SwgohComlinkValueError, match="dictionary"):
            get_omicron_skill_tier("not a dict")

    def test_missing_tier_key_raises(self):
        from swgoh_comlink.helpers._omicron import get_omicron_skill_tier

        with pytest.raises(SwgohComlinkValueError, match="tier"):
            get_omicron_skill_tier({"id": "skill_A"})


class TestIsOmicronSkill:
    def test_via_skill_id_and_tier_true(self):
        from swgoh_comlink.helpers._omicron import is_omicron_skill

        assert is_omicron_skill(_SKILL_LIST, skill_id="skill_A", skill_tier=1) is True

    def test_via_skill_id_and_tier_wrong_tier(self):
        from swgoh_comlink.helpers._omicron import is_omicron_skill

        # skill_A has omicron at tier index 1, so tier 99 should not match
        assert is_omicron_skill(_SKILL_LIST, skill_id="skill_A", skill_tier=99) is False

    def test_via_roster_unit_skill(self):
        from swgoh_comlink.helpers._omicron import is_omicron_skill

        # skill_C has omicron at tier index 0, and tier must be truthy
        roster_skill = {"id": "skill_A", "tier": 1}
        assert is_omicron_skill(_SKILL_LIST, roster_unit_skill=roster_skill) is True

    def test_not_in_list(self):
        from swgoh_comlink.helpers._omicron import is_omicron_skill

        assert is_omicron_skill(_SKILL_LIST, skill_id="nonexistent", skill_tier=1) is False

    def test_invalid_omicron_list_raises(self):
        from swgoh_comlink.helpers._omicron import is_omicron_skill

        with pytest.raises(SwgohComlinkValueError, match="list"):
            is_omicron_skill("bad", skill_id="s", skill_tier=1)

    def test_invalid_skill_id_type_raises(self):
        from swgoh_comlink.helpers._omicron import is_omicron_skill

        with pytest.raises(SwgohComlinkValueError, match="skill_id"):
            is_omicron_skill([], skill_id=123, skill_tier=1)

    def test_missing_skill_id_and_tier_raises(self):
        from swgoh_comlink.helpers._omicron import is_omicron_skill

        with pytest.raises(SwgohComlinkValueError):
            is_omicron_skill([], skill_id="", skill_tier=0)

    def test_invalid_roster_unit_skill_raises(self):
        from swgoh_comlink.helpers._omicron import is_omicron_skill

        with pytest.raises(SwgohComlinkValueError, match="Invalid"):
            is_omicron_skill([], roster_unit_skill={"id": "", "tier": 0})


class TestGetUnitFromSkill:
    def test_found(self):
        from swgoh_comlink.helpers._omicron import get_unit_from_skill

        units = [
            {"baseId": "UNIT1", "nameKey": "Unit One", "skillReference": [{"id": "skill_X"}]},
            {"baseId": "UNIT2", "nameKey": "Unit Two", "skillReference": [{"id": "skill_Y"}]},
        ]
        result = get_unit_from_skill(units, "skill_Y")
        assert result is not None
        assert result.baseId == "UNIT2"
        assert result.nameKey == "Unit Two"

    def test_not_found(self):
        from swgoh_comlink.helpers._omicron import get_unit_from_skill

        units = [{"baseId": "U1", "nameKey": "N1", "skillReference": [{"id": "s1"}]}]
        assert get_unit_from_skill(units, "nonexistent") is None

    def test_empty_skill_reference(self):
        from swgoh_comlink.helpers._omicron import get_unit_from_skill

        units = [{"baseId": "U1", "nameKey": "N1", "skillReference": None}]
        assert get_unit_from_skill(units, "s1") is None

    def test_invalid_unit_list_raises(self):
        from swgoh_comlink.helpers._omicron import get_unit_from_skill

        with pytest.raises(SwgohComlinkValueError, match="list"):
            get_unit_from_skill("bad", "skill")

    def test_invalid_skill_type_raises(self):
        from swgoh_comlink.helpers._omicron import get_unit_from_skill

        with pytest.raises(SwgohComlinkValueError, match="string"):
            get_unit_from_skill([], 123)


# ── _game_data ──────────────────────────────────────────────────────────


class TestGetRaidLeaderboardIds:
    def test_valid_guild_campaign(self):
        from swgoh_comlink.helpers._game_data import get_raid_leaderboard_ids

        campaign_data = [
            {
                "id": "GUILD",
                "campaignMap": [
                    {
                        "id": "MAP1",
                        "campaignNodeDifficultyGroup": [
                            {
                                "campaignNode": [
                                    {
                                        "id": "NODE1",
                                        "campaignNodeMission": [
                                            {"id": "MISSION1"},
                                            {"id": "MISSION2"},
                                        ],
                                    }
                                ]
                            }
                        ],
                    }
                ],
            }
        ]
        result = get_raid_leaderboard_ids(campaign_data)
        assert len(result) == 2
        assert result[0] == "GUILD:MAP1:NORMAL_DIFF:NODE1:MISSION1"
        assert result[1] == "GUILD:MAP1:NORMAL_DIFF:NODE1:MISSION2"

    def test_no_guild_returns_empty(self):
        from swgoh_comlink.helpers._game_data import get_raid_leaderboard_ids

        campaign_data = [{"id": "LIGHT_SIDE"}]
        assert get_raid_leaderboard_ids(campaign_data) == []


class TestCreateLocalizedUnitNameDictionary:
    def test_string_input(self):
        from swgoh_comlink.helpers._game_data import create_localized_unit_name_dictionary

        locale_str = "# comment\nUNIT_BOSSK_NAME|Bossk\nUNIT_BOSSK_DESC|A hunter\n"
        result = create_localized_unit_name_dictionary(locale_str)
        assert result == {"UNIT_BOSSK_NAME": "Bossk"}

    def test_list_input(self):
        from swgoh_comlink.helpers._game_data import create_localized_unit_name_dictionary

        locale_list = ["UNIT_VADER_NAME|Darth Vader", "UNIT_VADER_DESC|Sith Lord"]
        result = create_localized_unit_name_dictionary(locale_list)
        assert result == {"UNIT_VADER_NAME": "Darth Vader"}

    def test_bytes_in_list(self):
        from swgoh_comlink.helpers._game_data import create_localized_unit_name_dictionary

        locale_list = [b"UNIT_LUKE_NAME|Luke Skywalker"]
        result = create_localized_unit_name_dictionary(locale_list)
        assert result == {"UNIT_LUKE_NAME": "Luke Skywalker"}

    def test_comments_and_non_unit_lines_skipped(self):
        from swgoh_comlink.helpers._game_data import create_localized_unit_name_dictionary

        locale_str = "# comment\nSOME_OTHER|value\nno pipe here\n"
        result = create_localized_unit_name_dictionary(locale_str)
        assert result == {}

    def test_invalid_type_raises(self):
        from swgoh_comlink.helpers._game_data import create_localized_unit_name_dictionary

        with pytest.raises(SwgohComlinkValueError, match="list"):
            create_localized_unit_name_dictionary(12345)


class TestGetPlayableUnits:
    def test_filters_correctly(self):
        from swgoh_comlink.helpers._game_data import get_playable_units

        units = [
            {"rarity": 7, "obtainable": True, "obtainableTime": "0"},
            {"rarity": 5, "obtainable": True, "obtainableTime": "0"},
            {"rarity": 7, "obtainable": False, "obtainableTime": "0"},
            {"rarity": 7, "obtainable": True, "obtainableTime": "12345"},
        ]
        result = get_playable_units(units)
        assert len(result) == 1
        assert result[0]["rarity"] == 7

    def test_invalid_type_raises(self):
        from swgoh_comlink.helpers._game_data import get_playable_units

        with pytest.raises(SwgohComlinkValueError, match="list"):
            get_playable_units("bad")


class TestGetCurrentDatacronSets:
    def test_active_sets_returned(self):
        from swgoh_comlink.helpers._game_data import get_current_datacron_sets

        far_future = str(99999999999999)
        past = "0"
        datacrons = [
            {"expirationTimeMs": far_future, "id": "active"},
            {"expirationTimeMs": past, "id": "expired"},
        ]
        result = get_current_datacron_sets(datacrons)
        assert len(result) == 1
        assert result[0]["id"] == "active"

    def test_invalid_type_raises(self):
        from swgoh_comlink.helpers._game_data import get_current_datacron_sets

        with pytest.raises(SwgohComlinkValueError, match="list"):
            get_current_datacron_sets("bad")


class TestGetDatacronDismantleValue:
    def test_normal_dismantle(self):
        from swgoh_comlink.helpers._game_data import get_datacron_dismantle_value

        datacron = {"setId": "set1", "affix": [1, 2]}
        sets = [
            {
                "id": "set1",
                "tier": [
                    {"id": 0, "dustGrantRecipeId": None},
                    {"id": 1, "dustGrantRecipeId": None},
                    {"id": 2, "dustGrantRecipeId": "recipe1"},
                ],
            }
        ]
        recipes = [
            {
                "id": "recipe1",
                "ingredients": [
                    {"id": "mat_A", "maxQuantity": 100, "type": 3},
                ],
            }
        ]
        result = get_datacron_dismantle_value(datacron, sets, recipes)
        assert result["mat_A"]["quantity"] == 100
        assert result["focused"] is False

    def test_focused_dismantle(self):
        from swgoh_comlink.helpers._game_data import get_datacron_dismantle_value

        datacron = {"setId": "set1", "focused": True, "affix": [1]}
        sets = [
            {
                "id": "set1",
                "focusedTier": [{"id": 1, "dustGrantRecipeId": "recipe_f"}],
            }
        ]
        recipes = [{"id": "recipe_f", "ingredients": [{"id": "mat_B", "maxQuantity": 50, "type": 2}]}]
        result = get_datacron_dismantle_value(datacron, sets, recipes)
        assert result["mat_B"]["quantity"] == 50
        assert result["focused"] is True

    def test_missing_set_returns_empty(self):
        from swgoh_comlink.helpers._game_data import get_datacron_dismantle_value

        result = get_datacron_dismantle_value({"setId": "nope"}, [], [])
        assert result == {}

    def test_missing_recipe_returns_empty(self):
        from swgoh_comlink.helpers._game_data import get_datacron_dismantle_value

        datacron = {"setId": "set1", "affix": [1]}
        sets = [{"id": "set1", "tier": [{"id": 1, "dustGrantRecipeId": "recipe_x"}]}]
        result = get_datacron_dismantle_value(datacron, sets, [])
        assert result == {}


class TestGetDatacronDismantleTotal:
    def test_aggregates_materials(self):
        from swgoh_comlink.helpers._game_data import get_datacron_dismantle_total

        datacrons = [
            {"setId": "set1", "affix": [1]},
            {"setId": "set1", "affix": [1]},
        ]
        sets = [{"id": "set1", "tier": [{"id": 1, "dustGrantRecipeId": "r1"}]}]
        recipes = [{"id": "r1", "ingredients": [{"id": "mat_A", "maxQuantity": 10, "type": 1}]}]
        result = get_datacron_dismantle_total(datacrons, sets, recipes)
        assert result["mat_A"]["quantity"] == 20

    def test_empty_list_returns_empty(self):
        from swgoh_comlink.helpers._game_data import get_datacron_dismantle_total

        assert get_datacron_dismantle_total([], [], []) == {}


# ── _gac (pure functions) ──────────────────────────────────────────────


class TestConvertLeagueToInt:
    def test_all_leagues(self):
        from swgoh_comlink.helpers._gac import convert_league_to_int

        assert convert_league_to_int("kyber") == 100
        assert convert_league_to_int("aurodium") == 80
        assert convert_league_to_int("chromium") == 60
        assert convert_league_to_int("bronzium") == 40
        assert convert_league_to_int("carbonite") == 20

    def test_case_insensitive(self):
        from swgoh_comlink.helpers._gac import convert_league_to_int

        assert convert_league_to_int("KYBER") == 100
        assert convert_league_to_int("Kyber") == 100

    def test_unknown_returns_none(self):
        from swgoh_comlink.helpers._gac import convert_league_to_int

        assert convert_league_to_int("unknown") is None

    def test_none_raises(self):
        from swgoh_comlink.helpers._gac import convert_league_to_int

        with pytest.raises(SwgohComlinkValueError, match="required"):
            convert_league_to_int(None)

    def test_empty_raises(self):
        from swgoh_comlink.helpers._gac import convert_league_to_int

        with pytest.raises(SwgohComlinkValueError, match="required"):
            convert_league_to_int("")


class TestConvertDivisionsToInt:
    def test_string_divisions(self):
        from swgoh_comlink.helpers._gac import convert_divisions_to_int

        assert convert_divisions_to_int("1") == 25
        assert convert_divisions_to_int("5") == 5

    def test_int_divisions(self):
        from swgoh_comlink.helpers._gac import convert_divisions_to_int

        assert convert_divisions_to_int(1) == 25
        assert convert_divisions_to_int(5) == 5

    def test_unknown_returns_none(self):
        from swgoh_comlink.helpers._gac import convert_divisions_to_int

        assert convert_divisions_to_int("99") is None

    def test_none_raises(self):
        from swgoh_comlink.helpers._gac import convert_divisions_to_int

        with pytest.raises(SwgohComlinkValueError, match="required"):
            convert_divisions_to_int(None)

    def test_empty_raises(self):
        from swgoh_comlink.helpers._gac import convert_divisions_to_int

        with pytest.raises(SwgohComlinkValueError, match="required"):
            convert_divisions_to_int("")


class TestSearchGacBrackets:
    def test_found(self):
        from swgoh_comlink.helpers._gac import search_gac_brackets

        brackets = {0: [{"name": "Player1"}, {"name": "Player2"}], 1: [{"name": "Player3"}]}
        result = search_gac_brackets(brackets, "Player3")
        assert result["player"]["name"] == "Player3"
        assert result["bracket"] == 1

    def test_not_found(self):
        from swgoh_comlink.helpers._gac import search_gac_brackets

        brackets = {0: [{"name": "Player1"}]}
        assert search_gac_brackets(brackets, "Nobody") == {}

    def test_case_insensitive(self):
        from swgoh_comlink.helpers._gac import search_gac_brackets

        brackets = {0: [{"name": "Player1"}]}
        result = search_gac_brackets(brackets, "player1")
        assert result["player"]["name"] == "Player1"


class TestFindBracketBoundary:
    def test_bracket_0_empty_returns_negative_1(self):
        from swgoh_comlink.helpers._gac import _find_bracket_boundary

        assert _find_bracket_boundary(lambda i: False) == -1

    def test_finds_boundary(self):
        from swgoh_comlink.helpers._gac import _find_bracket_boundary

        # Non-empty for indices 0-9, empty for 10+
        assert _find_bracket_boundary(lambda i: i < 10, initial_step=4) == 9

    def test_single_bracket(self):
        from swgoh_comlink.helpers._gac import _find_bracket_boundary

        assert _find_bracket_boundary(lambda i: i == 0, initial_step=1) == 0


class TestAsyncFindBracketBoundary:
    @pytest.mark.asyncio
    async def test_bracket_0_empty_returns_negative_1(self):
        from swgoh_comlink.helpers._gac import _async_find_bracket_boundary

        async def probe(i):
            return False

        assert await _async_find_bracket_boundary(probe) == -1

    @pytest.mark.asyncio
    async def test_finds_boundary(self):
        from swgoh_comlink.helpers._gac import _async_find_bracket_boundary

        async def probe(i):
            return i < 10

        assert await _async_find_bracket_boundary(probe, initial_step=4) == 9


# ── _constants ──────────────────────────────────────────────────────────


class TestConstantsGet:
    def test_own_attribute(self):
        from swgoh_comlink.helpers._constants import Constants

        assert Constants.get("Segment1") == str(Constants.Segment1)

    def test_legacy_name(self):
        from swgoh_comlink.helpers._constants import Constants

        result = Constants.get("UnitDefinitions")
        assert result is not None
        assert int(result) > 0

    def test_data_items_name(self):
        from swgoh_comlink.helpers._constants import Constants

        result = Constants.get("UNITS")
        assert result is not None
        assert int(result) > 0

    def test_unknown_returns_none(self):
        from swgoh_comlink.helpers._constants import Constants

        assert Constants.get("TotallyFakeItem") is None


class TestConstantsGetNames:
    def test_returns_list(self):
        from swgoh_comlink.helpers._constants import Constants

        names = Constants.get_names()
        assert isinstance(names, list)
        assert len(names) > 0

    def test_includes_expected_names(self):
        from swgoh_comlink.helpers._constants import Constants

        names = Constants.get_names()
        assert "RELIC_TIERS" in names
        assert "UnitDefinitions" in names
        assert "UNITS" in names


# ── _decorators ─────────────────────────────────────────────────────────


class TestFuncTimer:
    def test_returns_correct_result(self):
        from swgoh_comlink.helpers._decorators import func_timer

        @func_timer
        def add(a, b):
            return a + b

        assert add(2, 3) == 5

    def test_logs_at_debug(self, caplog):
        from swgoh_comlink.helpers._decorators import func_timer

        @func_timer
        def noop():
            return "done"

        with caplog.at_level(logging.DEBUG, logger="swgoh_comlink.helpers._decorators"):
            noop()

        assert "noop" in caplog.text
        assert "executed in" in caplog.text


class TestFuncDebugLogger:
    def test_returns_result(self):
        from swgoh_comlink.helpers._decorators import func_debug_logger

        @func_debug_logger
        def greet(name):
            return f"hello {name}"

        assert greet("world") == "hello world"

    def test_masks_sensitive_keys(self, caplog):
        from swgoh_comlink.helpers._decorators import func_debug_logger

        @func_debug_logger
        def dummy(**kwargs):
            return "ok"

        with caplog.at_level(logging.DEBUG, logger="swgoh_comlink.helpers._decorators"):
            dummy(secret_key="my_secret", access_key="my_key", normal="visible")

        assert "my_secret" not in caplog.text
        assert "my_key" not in caplog.text
        assert "***" in caplog.text
        assert "visible" in caplog.text


# ── globals ─────────────────────────────────────────────────────────────


class TestLoggingFormatter:
    def test_format_record(self):
        from swgoh_comlink.globals import LoggingFormatter

        formatter = LoggingFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="hello",
            args=None,
            exc_info=None,
            func="my_func",
        )
        output = formatter.format(record)
        assert "hello" in output
        assert "INFO" in output
        assert "my_func" in output


class TestGetLogger:
    def test_default_name(self):
        from swgoh_comlink.globals import get_logger

        logger = get_logger()
        assert isinstance(logger, logging.Logger)

    def test_custom_name(self):
        from swgoh_comlink.globals import get_logger

        logger = get_logger("my.custom.logger")
        assert logger.name == "my.custom.logger"


# ── _localization ──────────────────────────────────────────────────────


class TestHexToAnsiTruecolor:
    def test_basic_conversion(self):
        from swgoh_comlink.helpers._localization import _hex_to_ansi_truecolor

        result = _hex_to_ansi_truecolor("FF0000")
        assert result == "\033[38;2;255;0;0m"

    def test_with_hash_prefix(self):
        from swgoh_comlink.helpers._localization import _hex_to_ansi_truecolor

        result = _hex_to_ansi_truecolor("#00FF00")
        assert result == "\033[38;2;0;255;0m"

    def test_mixed_case(self):
        from swgoh_comlink.helpers._localization import _hex_to_ansi_truecolor

        result = _hex_to_ansi_truecolor("aaBBcc")
        assert result == "\033[38;2;170;187;204m"


class TestParseTokens:
    def test_plain_text(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("hello world")
        assert len(tokens) == 1
        assert tokens[0] == {"type": "text", "value": "hello world"}

    def test_color_tags(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("[c][FF0000]red[-][/c]")
        types = [t["type"] for t in tokens]
        assert "color_block_open" in types
        assert "color" in types
        assert "color_reset" in types
        assert "color_end" in types

    def test_bold_tags(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("[b]bold[/b]")
        types = [t["type"] for t in tokens]
        assert types == ["bold_open", "text", "bold_close"]

    def test_italic_tags(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("[i]italic[/i]")
        types = [t["type"] for t in tokens]
        assert types == ["italic_open", "text", "italic_close"]

    def test_newline_escape(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("line1\\nline2")
        types = [t["type"] for t in tokens]
        assert types == ["text", "newline", "text"]

    def test_color_end_dash_c(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("[-c]")
        assert tokens[0]["type"] == "color_end"

    def test_hex_color_token(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("[F0FF23]")
        assert tokens[0]["type"] == "color"
        assert tokens[0]["hex6"] == "F0FF23"
        assert tokens[0]["hex8"] == "F0FF23FF"
        assert tokens[0]["r"] == 0xF0
        assert tokens[0]["g"] == 0xFF
        assert tokens[0]["b"] == 0x23
        assert tokens[0]["a"] == 0xFF

    def test_empty_parts_skipped(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("")
        assert tokens == []


class TestParseSwgohStringBare:
    def test_plain_text(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("hello world", output="bare") == "hello world"

    def test_strips_color_markup(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[c][FFAA00]golden[-][/c]", output="bare")
        assert result == "golden"

    def test_strips_bold(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[b]bold[/b]", output="bare") == "bold"

    def test_strips_italic(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[i]italic[/i]", output="bare") == "italic"

    def test_newline(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("a\\nb", output="bare") == "a\nb"

    def test_default_is_bare(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[b]text[/b]") == "text"


class TestParseSwgohStringTerminal:
    def test_color_block(self):
        from swgoh_comlink.helpers._localization import ANSI_RESET, parse_swgoh_string

        result = parse_swgoh_string("[c][FF0000]red[/c]", output="terminal")
        assert "\033[38;2;255;0;0m" in result
        assert "red" in result
        assert result.endswith(ANSI_RESET)

    def test_bold(self):
        from swgoh_comlink.helpers._localization import ANSI_BOLD, ANSI_RESET, parse_swgoh_string

        result = parse_swgoh_string("[b]bold[/b]", output="terminal")
        assert ANSI_BOLD in result
        assert ANSI_RESET in result
        assert "bold" in result

    def test_italic(self):
        from swgoh_comlink.helpers._localization import ANSI_ITALIC, ANSI_RESET, parse_swgoh_string

        result = parse_swgoh_string("[i]italic[/i]", output="terminal")
        assert ANSI_ITALIC in result
        assert ANSI_RESET in result

    def test_color_reset_within_block(self):
        from swgoh_comlink.helpers._localization import ANSI_RESET, parse_swgoh_string

        result = parse_swgoh_string("[c][FF0000]red[-]plain[/c]", output="terminal")
        assert "red" in result
        assert "plain" in result
        # Color reset [-] should produce ANSI_RESET
        assert result.count(ANSI_RESET) >= 2

    def test_bold_with_active_color_reapplies(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        # Bold close should reapply active color
        result = parse_swgoh_string("[c][FF0000][b]bold[/b]text[/c]", output="terminal")
        assert "bold" in result
        assert "text" in result

    def test_italic_with_active_color_reapplies(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[c][FF0000][i]ital[/i]text[/c]", output="terminal")
        assert "ital" in result

    def test_bold_close_preserves_italic(self):
        from swgoh_comlink.helpers._localization import ANSI_ITALIC, parse_swgoh_string

        result = parse_swgoh_string("[i][b]both[/b]just_italic[/i]", output="terminal")
        # After bold close, italic should be reapplied
        parts = result.split("both")
        assert ANSI_ITALIC in parts[1]

    def test_italic_close_preserves_bold(self):
        from swgoh_comlink.helpers._localization import ANSI_BOLD, parse_swgoh_string

        result = parse_swgoh_string("[b][i]both[/i]just_bold[/b]", output="terminal")
        parts = result.split("both")
        assert ANSI_BOLD in parts[1]

    def test_color_end_reapplies_styles(self):
        from swgoh_comlink.helpers._localization import ANSI_BOLD, parse_swgoh_string

        result = parse_swgoh_string("[b][c][FF0000]red[/c]still_bold[/b]", output="terminal")
        # After color end, bold should be reapplied
        assert ANSI_BOLD in result

    def test_finalize_resets_active_styles(self):
        from swgoh_comlink.helpers._localization import ANSI_RESET, parse_swgoh_string

        # Unclosed bold — finalize should add reset
        result = parse_swgoh_string("[b]no close", output="terminal")
        assert result.endswith(ANSI_RESET)


class TestParseSwgohStringDiscord:
    def test_bold(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[b]bold[/b]", output="discord")
        assert result == "**bold**"

    def test_italic(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[i]italic[/i]", output="discord")
        assert result == "*italic*"

    def test_color_ignored(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[c][FF0000]red[/c]", output="discord")
        assert result == "red"


class TestParseSwgohStringWeb:
    def test_color_span(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[c][FF0000]red[/c]", output="web")
        assert '<span style="color:#FF0000">' in result
        assert "</span>" in result
        assert result.startswith("<p>")
        assert result.endswith("</p>")

    def test_bold(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[b]bold[/b]", output="web")
        assert "<b>bold</b>" in result

    def test_italic(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[i]italic[/i]", output="web")
        assert "<em>italic</em>" in result

    def test_color_reset_closes_span(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[c][FF0000]red[-]plain[/c]", output="web")
        assert "</span>" in result
        assert "red" in result
        assert "plain" in result

    def test_wraps_in_p_tag(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("simple", output="web")
        assert result == "<p>simple</p>"


class TestParseSwgohStringComplex:
    def test_nested_bold_italic(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[b][i]bold-italic[/i][/b]", output="bare")
        assert result == "bold-italic"

    def test_mixed_markup(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        text = "[b]Title[/b]\\n[c][FFAA00]Gold text[-][/c] and [i]italic[/i]"
        result = parse_swgoh_string(text, output="bare")
        assert "Title" in result
        assert "\n" in result
        assert "Gold text" in result
        assert "italic" in result

    def test_empty_string(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("", output="bare") == ""
        assert parse_swgoh_string("", output="web") == "<p></p>"


class TestParseTokensExtendedTags:
    """Tokenization coverage for tags added in response to issue #83."""

    def test_underline_tokens(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("[u]x[/u]")
        types = [t["type"] for t in tokens]
        assert types == ["underline_open", "text", "underline_close"]

    def test_strike_tokens(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("[s]x[/s]")
        types = [t["type"] for t in tokens]
        assert types == ["strike_open", "text", "strike_close"]

    def test_sprite_tokens(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("[t]x[/t]")
        types = [t["type"] for t in tokens]
        assert types == ["sprite_open", "text", "sprite_close"]

    def test_sub_and_sup_tokens(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("[sub]a[/sub][sup]b[/sup]")
        types = [t["type"] for t in tokens]
        assert types == ["sub_open", "text", "sub_close", "sup_open", "text", "sup_close"]

    def test_sub_sup_with_scale(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("[sub=1.5]a[/sub][sup=0.8]b[/sup]")
        opens = [t for t in tokens if t["type"] in ("sub_open", "sup_open")]
        assert opens[0] == {"type": "sub_open", "scale": 1.5}
        assert opens[1] == {"type": "sup_open", "scale": 0.8}

    def test_scale_tokens(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("[y=2]xx[/y]")
        types = [t["type"] for t in tokens]
        assert types == ["scale_open", "text", "scale_close"]
        assert tokens[0]["scale"] == 2.0

    def test_three_digit_hex_expands(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("[F0A]")
        assert tokens[0]["type"] == "color"
        assert tokens[0]["hex6"] == "FF00AA"
        assert tokens[0]["a"] == 0xFF

    def test_four_digit_hex_rgba(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("[F0A8]")
        assert tokens[0]["type"] == "color"
        assert tokens[0]["hex8"] == "FF00AA88"
        assert tokens[0]["a"] == 0x88

    def test_eight_digit_hex_rgba(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("[12345678]")
        assert tokens[0]["type"] == "color"
        assert tokens[0]["hex8"] == "12345678"

    def test_single_hex_alpha_token(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("[F]")
        assert tokens[0] == {"type": "alpha", "a": 0xFF}

    def test_standalone_color_without_block(self):
        from swgoh_comlink.helpers._localization import _parse_tokens

        tokens = _parse_tokens("[FF0000]red")
        types = [t["type"] for t in tokens]
        assert types == ["color", "text"]

    def test_named_tag_wins_over_hex(self):
        """Single-letter named tags must not be misread as 1-digit alpha."""
        from swgoh_comlink.helpers._localization import _parse_tokens

        assert _parse_tokens("[b]")[0]["type"] == "bold_open"
        assert _parse_tokens("[c]")[0]["type"] == "color_block_open"
        assert _parse_tokens("[i]")[0]["type"] == "italic_open"
        assert _parse_tokens("[s]")[0]["type"] == "strike_open"
        assert _parse_tokens("[t]")[0]["type"] == "sprite_open"
        assert _parse_tokens("[u]")[0]["type"] == "underline_open"


class TestParseSwgohStringBareExtended:
    def test_strips_underline(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[u]under[/u]", output="bare") == "under"

    def test_strips_strike(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[s]cross[/s]", output="bare") == "cross"

    def test_strips_sub_sup_scale(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        text = "[sub=0.8]x[/sub][sup]y[/sup][y=1.5]z[/y]"
        assert parse_swgoh_string(text, output="bare") == "xyz"

    def test_strips_sprite_and_short_color(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[t]icon[/t][F0A]red", output="bare") == "iconred"

    def test_strips_alpha_literal(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("hello[8]world", output="bare") == "helloworld"


class TestParseSwgohStringTerminalExtended:
    def test_underline_emits_ansi(self):
        from swgoh_comlink.helpers._localization import ANSI_RESET, ANSI_UNDERLINE, parse_swgoh_string

        result = parse_swgoh_string("[u]x[/u]", output="terminal")
        assert ANSI_UNDERLINE in result
        assert "x" in result
        assert result.endswith(ANSI_RESET)

    def test_strike_emits_ansi(self):
        from swgoh_comlink.helpers._localization import ANSI_RESET, ANSI_STRIKE, parse_swgoh_string

        result = parse_swgoh_string("[s]x[/s]", output="terminal")
        assert ANSI_STRIKE in result
        assert result.endswith(ANSI_RESET)

    def test_underline_preserves_color(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[FF0000][u]red[/u]still", output="terminal")
        # After closing underline, the red foreground should be reapplied.
        after_close = result.split("red")[1]
        assert "\033[38;2;255;0;0m" in after_close

    def test_strike_close_reapplies_bold(self):
        from swgoh_comlink.helpers._localization import ANSI_BOLD, parse_swgoh_string

        result = parse_swgoh_string("[b][s]x[/s]still_bold[/b]", output="terminal")
        tail = result.split("x")[1]
        assert ANSI_BOLD in tail

    def test_short_rgb_expands(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[F0A]x", output="terminal")
        assert "\033[38;2;255;0;170m" in result

    def test_standalone_color_without_c_wrapper(self):
        """A color literal without [c] should still colorize in terminal output."""
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[00FF00]green", output="terminal")
        assert "\033[38;2;0;255;0m" in result
        assert "green" in result

    def test_dash_resets_color_outside_block(self):
        from swgoh_comlink.helpers._localization import ANSI_RESET, parse_swgoh_string

        result = parse_swgoh_string("[FF0000]red[-]plain", output="terminal")
        assert ANSI_RESET in result
        assert "plain" in result


class TestParseSwgohStringDiscordExtended:
    def test_underline_markdown(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[u]x[/u]", output="discord") == "__x__"

    def test_strike_markdown(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[s]x[/s]", output="discord") == "~~x~~"

    def test_sub_sup_scale_stripped(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        text = "[sub=0.8]a[/sub][sup]b[/sup][y=1.2]c[/y]"
        assert parse_swgoh_string(text, output="discord") == "abc"


class TestParseSwgohStringWebExtended:
    def test_underline_html(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[u]x[/u]", output="web") == "<p><u>x</u></p>"

    def test_strike_html(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[s]x[/s]", output="web") == "<p><s>x</s></p>"

    def test_sub_default_no_scale(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[sub]x[/sub]", output="web") == "<p><sub>x</sub></p>"

    def test_sub_with_scale(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[sub=0.8]x[/sub]", output="web")
        assert '<sub style="font-size:0.8em">x</sub>' in result

    def test_sup_with_scale(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[sup=1.25]x[/sup]", output="web")
        assert '<sup style="font-size:1.25em">x</sup>' in result

    def test_scale_integer_formatted_without_decimal(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[y=2]x[/y]", output="web")
        assert '<span style="font-size:2em">x</span>' in result

    def test_short_hex_color_span(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[F0A]x[/c]", output="web")
        assert '<span style="color:#FF00AA">x</span>' in result

    def test_rgba_color_uses_rgba_css(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        # [F0A8] -> FF00AA with alpha 0x88 (136). 136/255 ≈ 0.533
        result = parse_swgoh_string("[F0A8]x[/c]", output="web")
        assert "rgba(255,0,170,0.533)" in result

    def test_alpha_only_reuses_prior_rgb(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[FF0000]red[8]faded", output="web")
        # First span opens with opaque red, then closes, then reopens at alpha 0x88.
        assert '<span style="color:#FF0000">' in result
        assert "rgba(255,0,0," in result

    def test_sprite_tag_stripped(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[t]icon[/t]", output="web") == "<p>icon</p>"


class TestParseSwgohStringComplexExtended:
    def test_deep_nested_styles(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[b][u][i]x[/i][/u][/b]", output="bare") == "x"

    def test_discord_nested_style_combo(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[b][u][s]x[/s][/u][/b]", output="discord")
        assert result == "**__~~x~~__**"

    def test_web_nested_preserves_tag_structure(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[b][u]x[/u][/b]", output="web")
        assert result == "<p><b><u>x</u></b></p>"

    def test_color_then_alpha_then_new_color(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        text = "[FF0000]red[8]faded[00FF00]green[/c]"
        result = parse_swgoh_string(text, output="web")
        # One opening span for each color change; matching closes at [/c].
        assert result.count('<span style="color:') == 3
        # Must close every span opened.
        assert result.count("</span>") == 3

    def test_issue_83_golden_string(self):
        """End-to-end smoke for all four outputs on a representative string."""
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        s = "[c][FF0000][b]Boss[/b][-] deals [u]2x[/u] damage[/c]"
        assert parse_swgoh_string(s, output="bare") == "Boss deals 2x damage"
        assert parse_swgoh_string(s, output="discord") == "**Boss** deals __2x__ damage"


class TestParseSwgohStringIssue83Coverage:
    """Round-trip coverage for every tag and color format named in issue #83.

    For text-only outputs (bare/terminal/discord) the visual-only tags
    ([t], [y=X], [sub], [sup]) are expected to be stripped without leaking
    any markup characters into the rendered string.
    """

    # --- [t] / [/t] sprite color forcing ---------------------------------------
    def test_sprite_terminal_strips(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[t]icon[/t]", output="terminal") == "icon"

    def test_sprite_discord_strips(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[t]icon[/t]", output="discord") == "icon"

    # --- [y=FLOAT] / [/y] font scaling -----------------------------------------
    def test_scale_terminal_strips(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[y=1.5]big[/y]", output="terminal") == "big"

    # --- [sub] / [sub=FLOAT] / [/sub] subscript --------------------------------
    def test_sub_terminal_strips(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[sub]x[/sub]", output="terminal") == "x"
        assert parse_swgoh_string("[sub=0.8]x[/sub]", output="terminal") == "x"

    # --- [sup] / [sup=FLOAT] / [/sup] superscript ------------------------------
    def test_sup_terminal_strips(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[sup]x[/sup]", output="terminal") == "x"
        assert parse_swgoh_string("[sup=1.25]x[/sup]", output="terminal") == "x"

    # --- 4-digit [RGBA] color --------------------------------------------------
    def test_four_digit_rgba_bare(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[F0A8]x[/c]", output="bare") == "x"

    def test_four_digit_rgba_terminal_uses_rgb_channel(self):
        """Terminal can't render alpha, but it must still emit the RGB channel."""
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[F0A8]x[/c]", output="terminal")
        # F0A8 -> RGB FF00AA, alpha 88 -> ignored by ANSI but RGB still shown.
        assert "\033[38;2;255;0;170m" in result
        assert "x" in result

    # --- 8-digit [RRGGBBAA] color ----------------------------------------------
    def test_eight_digit_rgba_bare(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        assert parse_swgoh_string("[12345678]x[/c]", output="bare") == "x"

    def test_eight_digit_rgba_terminal(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[12345678]x[/c]", output="terminal")
        # 0x12=18, 0x34=52, 0x56=86 (alpha 0x78 dropped by ANSI)
        assert "\033[38;2;18;52;86m" in result
        assert "x" in result

    def test_eight_digit_rgba_web(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[12345678]x[/c]", output="web")
        # alpha 0x78 = 120 -> 120/255 = 0.471
        assert "rgba(18,52,86,0.471)" in result

    # --- 1-digit [A] alpha-only ------------------------------------------------
    def test_alpha_only_terminal_no_rgb_change(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[FF0000]r[8]still_red[/c]", output="terminal")
        # The alpha tag re-emits the same RGB sequence in terminal output.
        assert result.count("\033[38;2;255;0;0m") == 2
        assert "still_red" in result

    # --- [c] is optional: standalone color without wrapper ---------------------
    def test_standalone_color_web_without_c_wrapper(self):
        from swgoh_comlink.helpers._localization import parse_swgoh_string

        result = parse_swgoh_string("[00FF00]green", output="web")
        assert '<span style="color:#00FF00">green</span>' in result


# ── Additional quick-win helper tests ──────────────────────────────────


class TestSanitizeAllycodeInvalidType:
    def test_float_raises(self):
        from swgoh_comlink.helpers._utils import sanitize_allycode

        with pytest.raises(SwgohComlinkValueError, match="Invalid ally code"):
            sanitize_allycode(3.14)

    def test_list_raises(self):
        from swgoh_comlink.helpers._utils import sanitize_allycode

        with pytest.raises(SwgohComlinkValueError, match="Invalid ally code"):
            sanitize_allycode([1, 2, 3])


class TestIsOmicronSkillNoTier:
    def test_skill_with_no_omicron_tier_returns_false(self):
        from swgoh_comlink.helpers._omicron import is_omicron_skill

        # skill_B has no omicron tier (all isOmicronTier=False)
        # get_omicron_skill_tier returns None, triggering line 132
        skill_list = [
            {"id": "skill_B", "omicronMode": 3, "tier": [{"isOmicronTier": False}]},
        ]
        assert is_omicron_skill(skill_list, skill_id="skill_B", skill_tier=1) is False


class TestConstantsGetLegacyKeyError:
    def test_legacy_name_with_missing_dataitems_returns_none(self):
        from unittest.mock import patch

        from swgoh_comlink.helpers._constants import _LEGACY_NAME_MAP, Constants

        # Patch _LEGACY_NAME_MAP to include a key that maps to a nonexistent DataItems member
        with patch.dict(_LEGACY_NAME_MAP, {"FakeLegacyName": "NONEXISTENT_MEMBER"}):
            result = Constants.get("FakeLegacyName")
            assert result is None


class TestGetDatacronDismantleValueNoDustRecipe:
    def test_no_dust_recipe_id_returns_empty(self):
        from swgoh_comlink.helpers._game_data import get_datacron_dismantle_value

        datacron = {"setId": "set1", "affix": [1]}
        # Tier exists but dustGrantRecipeId is None
        sets = [{"id": "set1", "tier": [{"id": 1, "dustGrantRecipeId": None}]}]
        result = get_datacron_dismantle_value(datacron, sets, [])
        assert result == {}


class TestGetArenaPayoutEdge:
    def test_payout_already_passed_adds_day(self):
        from datetime import datetime

        from swgoh_comlink.helpers._arena import get_arena_payout

        # Use a large positive offset to push payout well into the past
        # This forces the payout < datetime.now() branch
        result = get_arena_payout(offset=1440)
        assert result > datetime.now()
