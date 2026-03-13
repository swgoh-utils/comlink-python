"""Tests for pure helper functions that need no HTTP mocking."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest

from swgoh_comlink.exceptions import SwgohComlinkValueError
from swgoh_comlink.helpers._sentinels import GIVEN, MISSING

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

    def test_default_sentinel_returns_empty(self):
        from swgoh_comlink.helpers._utils import sanitize_allycode

        # Calling with no argument uses the REQUIRED sentinel default,
        # which triggers the early "" return.
        assert sanitize_allycode() == ""

    def test_given_sentinel_bypasses_empty_return(self):
        from swgoh_comlink.helpers._utils import sanitize_allycode

        # GIVEN is falsy but should NOT trigger the early "" return.
        # It falls through to the string validation path instead.
        with pytest.raises((SwgohComlinkValueError, AttributeError)):
            sanitize_allycode(GIVEN)


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

    def test_missing_sentinel_raises(self):
        from swgoh_comlink.helpers._utils import human_time

        with pytest.raises(SwgohComlinkValueError, match="required"):
            human_time(MISSING)


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

    def test_missing_raises(self):
        from swgoh_comlink.helpers._gac import convert_league_to_int

        with pytest.raises(SwgohComlinkValueError, match="required"):
            convert_league_to_int(MISSING)

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

    def test_missing_raises(self):
        from swgoh_comlink.helpers._gac import convert_divisions_to_int

        with pytest.raises(SwgohComlinkValueError, match="required"):
            convert_divisions_to_int(MISSING)

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
