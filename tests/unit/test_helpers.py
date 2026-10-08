"""Tests for pure helper functions that need no HTTP mocking."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
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
    # The game's RelicTier enum: RelicTier_DEFAULT = 0, RELIC_LOCKED = 1, RELIC_UNLOCKED = 2, RELIC_TIER_01 = 3
    def test_valid_int(self):
        from swgoh_comlink.helpers._utils import convert_relic_tier

        assert convert_relic_tier(0) == "LOCKED"
        assert convert_relic_tier(1) == "LOCKED"
        assert convert_relic_tier(2) == "UNLOCKED"
        assert convert_relic_tier(3) == "1"
        assert convert_relic_tier(12) == "10"

    def test_valid_string(self):
        from swgoh_comlink.helpers._utils import convert_relic_tier

        assert convert_relic_tier("9") == "7"

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("RelicTier_DEFAULT", "LOCKED"),
            ("RELIC_LOCKED", "LOCKED"),
            ("RELIC_UNLOCKED", "UNLOCKED"),
            ("RELIC_TIER_01", "1"),
            ("RELIC_TIER_10", "10"),
            ("RELIC_TIER_11", None),
            ("RELIC_TIER_", None),
            ("NOT_A_TIER", None),
        ],
    )
    def test_enum_names(self, name: str, expected: str | None):
        from swgoh_comlink.helpers._utils import convert_relic_tier

        assert convert_relic_tier(name) == expected

    def test_every_relic_in_example_player_converts(self):
        import json

        from swgoh_comlink.helpers._utils import convert_relic_tier

        player = json.loads((Path(__file__).parent.parent / "resources" / "example-player.json").read_text())
        tiers = {unit["relic"]["currentTier"] for unit in player["rosterUnit"] if unit.get("relic")}
        assert 12 in tiers  # relic 10, the maximum
        assert all(convert_relic_tier(tier) is not None for tier in tiers)

    def test_unknown_tier_returns_none(self):
        from swgoh_comlink.helpers._utils import convert_relic_tier

        assert convert_relic_tier(99) is None

    @pytest.mark.parametrize("value", [None, True, 1.0])
    def test_invalid_type_raises(self, value: Any):
        from swgoh_comlink.helpers._utils import convert_relic_tier

        with pytest.raises(SwgohComlinkValueError, match="relic_tier"):
            convert_relic_tier(value)


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
    # localTimeZoneOffsetMinutes: payout is 18:00 (squad) / 19:00 (fleet) UTC moved back by the offset
    @staticmethod
    def _at(hour: int, minute: int = 0, day: int = 8):
        from datetime import datetime, timezone

        return datetime(2026, 10, day, hour, minute, tzinfo=timezone.utc)

    def test_squad_and_fleet_anchor_hours(self):
        from swgoh_comlink.helpers._arena import get_arena_payout

        assert get_arena_payout(0, now=self._at(12)) == self._at(18)
        assert get_arena_payout(0, fleet=True, now=self._at(12)) == self._at(19)

    def test_returns_aware_utc(self):
        from datetime import timezone

        from swgoh_comlink.helpers._arena import get_arena_payout

        assert get_arena_payout(0).tzinfo == timezone.utc

    def test_offset_moves_payout(self):
        from swgoh_comlink.helpers._arena import get_arena_payout

        # UTC+10: 19:00 local is 09:00 UTC
        assert get_arena_payout(600, fleet=True, now=self._at(8)) == self._at(9)

    def test_passed_payout_rolls_to_next_day(self):
        from swgoh_comlink.helpers._arena import get_arena_payout

        assert get_arena_payout(0, now=self._at(18)) == self._at(18, day=9)
        assert get_arena_payout(0, now=self._at(20)) == self._at(18, day=9)

    def test_payout_on_the_next_utc_day_is_not_skipped(self):
        from swgoh_comlink.helpers._arena import get_arena_payout

        # US Pacific (UTC-7) fleet pays at 02:00 UTC. At 01:00 UTC the next payout is an hour away,
        # not the one 25 hours later.
        assert get_arena_payout(-420, fleet=True, now=self._at(1)) == self._at(2)

    def test_naive_now_is_local_time(self):
        from datetime import datetime, timedelta

        from swgoh_comlink.helpers._arena import get_arena_payout

        now = datetime.now()
        payout = get_arena_payout(0, now=now)
        assert timedelta(0) < payout - now.astimezone() <= timedelta(days=1)


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

    def test_name_variant_suffixes_included(self):
        from swgoh_comlink.helpers._game_data import create_localized_unit_name_dictionary

        locale_list = [
            "UNIT_JEDIKNIGHTREVAN_NAME_V2|Jedi Knight Revan",
            "UNIT_BOSSK_NAME|Bossk",
            "UNIT_BOSSK_DESC|A hunter",
        ]
        result = create_localized_unit_name_dictionary(locale_list)
        assert result == {
            "UNIT_JEDIKNIGHTREVAN_NAME_V2": "Jedi Knight Revan",
            "UNIT_BOSSK_NAME": "Bossk",
        }

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

    def test_tolerates_missing_fields_and_enum_rarity(self):
        from swgoh_comlink.helpers._game_data import get_playable_units

        units = [
            {"baseId": "OLD_DUMP", "rarity": 7, "obtainable": True},  # predates obtainableTime
            {"baseId": "ENUMS", "rarity": "SEVEN_STAR", "obtainable": True, "obtainableTime": "0"},
            {"baseId": "INT_TIME", "rarity": 7, "obtainable": True, "obtainableTime": 0},
            {"baseId": "NO_RARITY", "obtainable": True, "obtainableTime": "0"},
            {"baseId": "NO_OBTAINABLE", "rarity": 7, "obtainableTime": "0"},
            {"baseId": "GL_TEMPLATE", "rarity": 7, "obtainable": True, "obtainableTime": "4102444800000"},
        ]
        assert [u["baseId"] for u in get_playable_units(units)] == ["OLD_DUMP", "ENUMS", "INT_TIME"]

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


# ── _conquest ──────────────────────────────────────────────────────────


def _feat(challenge_id: str, keycards: int = 1, artifact: str | None = None, reward_type: Any = 22) -> dict[str, Any]:
    rewards = [{"id": "", "type": reward_type, "maxQuantity": keycards}]
    if artifact:
        rewards.append({"id": artifact, "type": 23, "maxQuantity": 1})
    return {"id": challenge_id, "nameKey": f"{challenge_id}_NAME", "descKey": f"{challenge_id}_DESC", "reward": rewards}


_CONQUEST_DEFS = [
    {"id": "CONQUEST_VOL1", "conquestDifficulty": []},
    {
        "id": "CONQUEST_VOL2",
        "conquestDifficulty": [
            {"sector": [{"id": "S0", "titleKey": "SECTOR_1"}, {"id": "S1", "titleKey": "SECTOR_2"}]}
        ],
    },
]
_CHALLENGES = [
    _feat("CONQUEST_VOL2_BOSS_KILL_III_DIFF_S1", keycards=5),
    _feat("CONQUEST_VOL2_SECTOR_WIN_III_DIFF_S0", keycards=3),
    _feat("CONQUEST_VOL2_EVENT_BOMBS_III_DIFF", keycards=15, artifact="artifact_x"),
    _feat("CONQUEST_VOL2_EVENT_BOMBS_I_DIFF", keycards=10),
    _feat("CONQUEST_VOL2_MINIBOSS_HIT_II_DIFF_S0", reward_type="CONQUEST_POINT"),
    _feat("CONQUEST_VOL1_EVENT_OLD_III_DIFF"),
    _feat("CONQUEST_VOL2_NOT_A_FEAT"),
]
_LOC = {
    "SECTOR_1": "[c][FFFF00]SECTOR 1[-][/c]",
    "SECTOR_2": "SECTOR 2",
    "CONQUEST_VOL2_EVENT_BOMBS_III_DIFF_NAME": "[b]Bombs Away[/b]",
    "ARTIFACT_X_NAME": "Thermal Kit",
}
_ARTIFACTS = [{"id": "artifact_x", "nameKey": "ARTIFACT_X_NAME"}]


class TestGetConquestFeats:
    def test_defaults_to_newest_conquest_and_orders_feats(self):
        from swgoh_comlink.helpers import get_conquest_feats

        feats = get_conquest_feats(_CONQUEST_DEFS, _CHALLENGES)
        assert [f["challenge_id"] for f in feats] == [
            "CONQUEST_VOL2_EVENT_BOMBS_I_DIFF",
            "CONQUEST_VOL2_MINIBOSS_HIT_II_DIFF_S0",
            "CONQUEST_VOL2_EVENT_BOMBS_III_DIFF",
            "CONQUEST_VOL2_SECTOR_WIN_III_DIFF_S0",
            "CONQUEST_VOL2_BOSS_KILL_III_DIFF_S1",
        ]
        assert [f["difficulty"] for f in feats] == ["Easy", "Normal", "Hard", "Hard", "Hard"]
        assert [f["kind"] for f in feats] == ["Global", "Mini-Boss", "Global", "Sector", "Boss"]

    def test_localizes_names_sectors_and_artifacts(self):
        from swgoh_comlink.helpers import get_conquest_feats

        feats = get_conquest_feats(_CONQUEST_DEFS, _CHALLENGES, _LOC, _ARTIFACTS, difficulty="hard")
        bombs, sector, boss = feats
        assert bombs["name"] == "Bombs Away"
        assert bombs["scope"] == "Global" and bombs["sector_id"] is None
        assert bombs["keycards"] == 15
        assert bombs["reward_artifact_id"] == "artifact_x"
        assert bombs["reward_artifact"] == "Thermal Kit"
        assert sector["scope"] == "Sector 1" and sector["sector_id"] == "S0"
        assert boss["scope"] == "Sector 2"
        # Unresolved keys fall back to the localization key
        assert sector["name"] == "CONQUEST_VOL2_SECTOR_WIN_III_DIFF_S0_NAME"

    def test_without_localization_uses_ids(self):
        from swgoh_comlink.helpers import get_conquest_feats

        feats = get_conquest_feats(_CONQUEST_DEFS, _CHALLENGES, difficulty="Hard")
        assert feats[0]["reward_artifact"] == "artifact_x"
        assert feats[1]["scope"] == "S0"

    def test_enum_name_reward_types(self):
        from swgoh_comlink.helpers import get_conquest_feats

        (feat,) = get_conquest_feats(_CONQUEST_DEFS, _CHALLENGES, difficulty="normal")
        assert feat["keycards"] == 1

    def test_feats_without_a_kind_token(self):
        from swgoh_comlink.helpers import get_conquest_feats

        challenges = [
            _feat("CONQUEST_VOL2_SILVO_VANE_III_DIFF_S0", keycards=5),
            _feat("CONQUEST_VOL2_NO_TANKS_I_DIFF"),
            # A longer volume id must not be read as this volume's feat
            _feat("CONQUEST_VOL24_SECTOR_WIN_III_DIFF_S0"),
        ]
        feats = get_conquest_feats(_CONQUEST_DEFS, challenges)
        assert [(f["challenge_id"], f["kind"], f["scope"]) for f in feats] == [
            ("CONQUEST_VOL2_NO_TANKS_I_DIFF", "Global", "Global"),
            ("CONQUEST_VOL2_SILVO_VANE_III_DIFF_S0", "Sector", "S0"),
        ]
        assert feats[1]["keycards"] == 5

    def test_explicit_conquest_id_is_case_insensitive(self):
        from swgoh_comlink.helpers import get_conquest_feats

        feats = get_conquest_feats(_CONQUEST_DEFS, _CHALLENGES, conquest_id="conquest_vol1")
        assert [f["challenge_id"] for f in feats] == ["CONQUEST_VOL1_EVENT_OLD_III_DIFF"]

    @pytest.mark.parametrize(
        ("args", "kwargs"),
        [
            ((_CONQUEST_DEFS, _CHALLENGES), {"conquest_id": "CONQUEST_VOL99"}),
            ((_CONQUEST_DEFS, _CHALLENGES), {"difficulty": "nightmare"}),
            (({"id": "x"}, _CHALLENGES), {}),
            ((_CONQUEST_DEFS, None), {}),
            (([], _CHALLENGES), {}),
        ],
    )
    def test_invalid_input_raises(self, args: tuple[Any, ...], kwargs: dict[str, Any]):
        from swgoh_comlink.helpers import get_conquest_feats

        with pytest.raises(SwgohComlinkValueError):
            get_conquest_feats(*args, **kwargs)


# ── _abilities ─────────────────────────────────────────────────────────


def _skill(skill_id: str, ability_id: str, zeta: int | None = None, omicron: int | None = None, mode: Any = 1):
    """A 'skill' record with seven upgrade tiers; zeta/omicron are tier indexes."""
    tiers = [{"isZetaTier": i == zeta, "isOmicronTier": i == omicron} for i in range(7)]
    return {
        "id": skill_id,
        "abilityReference": ability_id,
        "nameKey": "DEFENSE_UP_NAME_KEY",
        "omicronMode": mode,
        "tier": tiers,
    }


def _ability(ability_id: str, tier_desc_keys: list[str], upgrade_keys: list[str] | None = None) -> dict[str, Any]:
    upgrades = upgrade_keys or [""] * len(tier_desc_keys)
    stem = ability_id.upper()
    return {
        "id": ability_id,
        "nameKey": f"{stem}_NAME",
        "descKey": f"{stem}_DESC",
        "tier": [{"descKey": d, "upgradeDescKey": u} for d, u in zip(tier_desc_keys, upgrades, strict=True)],
    }


_ABILITY_SKILLS = [
    # Trench's basic: a TW omicron at the last tier, text keyed under _OBTAINABLE_TIER_<nn>_DESC.
    _skill("basicskill_TRENCH", "basicability_trench", omicron=6, mode=8),
    # Ackbar's special: reworked, so every key the record names carries _V2.
    _skill("specialskill_ADMIRALACKBAR02", "specialability_admiralackbar02", zeta=6),
    # The game data spells one prefix with a capital letter.
    _skill("Contractskill_TRENCH", "contractability_trench"),
    # A ship's own ability, and a crew member's ability attached to the ship.
    _skill("basicskill_CAPITALEXECUTOR", "basicability_capitalexecutor"),
    _skill("uniqueskill_CAPITALEXECUTOR01", "uniqueability_capitalexecutor01", omicron=6, mode=9),
]
_ABILITIES = [
    _ability(
        "basicability_trench",
        ["BASICABILITY_TRENCH_OBTAINABLE_DESC"] * 3
        + [f"BASICABILITY_TRENCH_OBTAINABLE_TIER_0{i}_DESC" for i in range(4, 8)],
        ["ABILITYUPGRADE_STAT_DAMAGE05PCT_DESC"] * 6 + ["ABILITYUPGRADE_BASICABILITY_TRENCH_TIER_07_DESC"],
    ),
    {
        **_ability(
            "specialability_admiralackbar02",
            [f"SPECIALABILITY_ADMIRALACKBAR02_TIER0{i}_DESC_V2" for i in range(1, 8)],
        ),
        "descKey": "SPECIALABILITY_ADMIRALACKBAR02_DESC_V2",
    },
    # Fewer text tiers than the skill has upgrades: the last known text carries forward.
    _ability("contractability_trench", ["CONTRACT_TIER01_DESC"]),
    _ability("basicability_capitalexecutor", ["X_DESC"] * 7),
    _ability("uniqueability_capitalexecutor01", ["Y_DESC"] * 7),
]
_ABILITY_UNITS = [
    {"baseId": "TRENCH", "nameKey": "UNIT_TRENCH_NAME", "rarity": 1,
     "skillReference": [{"skillId": "basicskill_TRENCH"}, {"skillId": "Contractskill_TRENCH"}, {"skillId": "missing"}]},
    # A second rarity row for the same unit is not listed again.
    {"baseId": "TRENCH", "nameKey": "UNIT_TRENCH_NAME", "rarity": 7, "skillReference": [{"skillId": "basicskill_TRENCH"}]},
    {"baseId": "ADMIRALACKBAR", "nameKey": "UNIT_ACKBAR_NAME", "skillReference": [{"skillId": "specialskill_ADMIRALACKBAR02"}]},
    {"baseId": "CAPITALEXECUTOR", "nameKey": "UNIT_EXECUTOR_NAME",
     "skillReference": [{"skillId": "basicskill_CAPITALEXECUTOR"}],
     "crew": [{"unitId": "ADMIRALPIETT", "skillReference": [{"skillId": "uniqueskill_CAPITALEXECUTOR01"}]}]},
]  # fmt: skip
_ABILITY_LOC = {
    "UNIT_TRENCH_NAME": "Admiral Trench",
    "BASICABILITY_TRENCH_NAME": "Unfinished Business ",
    "BASICABILITY_TRENCH_DESC": "base text",
    "BASICABILITY_TRENCH_OBTAINABLE_DESC": "early text",
    "BASICABILITY_TRENCH_OBTAINABLE_TIER_07_DESC": "[c][ffff33]final[-][/c] text",
    "ABILITYUPGRADE_STAT_DAMAGE05PCT_DESC": "+5% Damage",
    "ABILITYUPGRADE_BASICABILITY_TRENCH_TIER_07_DESC": "[c][e7e7e7]While in Territory Wars:[-][/c] Ability Block",
    "SPECIALABILITY_ADMIRALACKBAR02_NAME": "Tactical Genius",
    "SPECIALABILITY_ADMIRALACKBAR02_DESC": "pre-rework text",
    "SPECIALABILITY_ADMIRALACKBAR02_DESC_V2": "current text",
    "SPECIALABILITY_ADMIRALACKBAR02_TIER07_DESC": "pre-rework L8",
    "SPECIALABILITY_ADMIRALACKBAR02_TIER07_DESC_V2": "current L8",
    "DEFENSE_UP_NAME_KEY": "DEFENSE UP",
}


class TestGetUnitAbilities:
    def _get(self, **kwargs: Any) -> list[Any]:
        from swgoh_comlink.helpers import get_unit_abilities

        return get_unit_abilities(_ABILITY_UNITS, _ABILITY_SKILLS, _ABILITIES, _ABILITY_LOC, **kwargs)

    def test_lists_each_unit_once_with_crew_abilities_last(self):
        abilities = self._get()
        assert [(a["base_id"], a["skill_id"], a["crew_base_id"]) for a in abilities] == [
            ("TRENCH", "basicskill_TRENCH", None),
            ("TRENCH", "Contractskill_TRENCH", None),
            ("ADMIRALACKBAR", "specialskill_ADMIRALACKBAR02", None),
            ("CAPITALEXECUTOR", "basicskill_CAPITALEXECUTOR", None),
            ("CAPITALEXECUTOR", "uniqueskill_CAPITALEXECUTOR01", "ADMIRALPIETT"),
        ]
        assert [a["kind"] for a in abilities] == ["basic", "contract", "special", "basic", "unique"]

    def test_reads_text_through_the_ability_records_keys(self):
        trench = self._get(base_id="trench")[0]
        assert trench["unit_name"] == "Admiral Trench"
        # ability.nameKey, not the skill's placeholder, and trimmed
        assert trench["name"] == "Unfinished Business"
        assert trench["description"] == "base text"
        assert [t["level"] for t in trench["tiers"]] == [2, 3, 4, 5, 6, 7, 8]
        assert trench["tiers"][0]["description"] == "early text"
        assert trench["tiers"][0]["upgrade"] == "+5% Damage"
        assert trench["tiers"][-1]["description"] == "final text"
        assert trench["tiers"][-1]["upgrade"] == "While in Territory Wars: Ability Block"

        (ackbar,) = self._get(base_id="ADMIRALACKBAR")
        assert ackbar["description"] == "current text"
        assert ackbar["tiers"][-1]["description"] == "current L8"

        # Keys missing from the dictionary fall back to the key itself
        executor = self._get(base_id="CAPITALEXECUTOR")[0]
        assert executor["unit_name"] == "UNIT_EXECUTOR_NAME"
        assert executor["tiers"][0]["description"] == "X_DESC"

    def test_zeta_and_omicron_levels(self):
        trench, contract = self._get(base_id=["TRENCH"])
        assert trench["max_level"] == 8
        assert (trench["zeta_level"], trench["omicron_level"], trench["omicron_mode"]) == (None, 8, 8)
        assert [t["is_omicron"] for t in trench["tiers"]] == [False] * 6 + [True]
        # A skill without an omicron tier reports mode 1, the unset default; that is not surfaced.
        assert (contract["omicron_level"], contract["omicron_mode"]) == (None, None)
        (ackbar,) = self._get(base_id="ADMIRALACKBAR")
        assert (ackbar["zeta_level"], ackbar["omicron_mode"]) == (8, None)

    def test_missing_ability_tiers_carry_text_forward(self):
        contract = self._get(base_id="TRENCH")[1]
        assert {t["description"] for t in contract["tiers"]} == {"CONTRACT_TIER01_DESC"}
        assert contract["max_level"] == 8

    def test_omicron_mode_filter(self):
        assert [a["skill_id"] for a in self._get(omicron_mode=8)] == ["basicskill_TRENCH"]
        assert len(self._get(omicron_mode=[8, 9])) == 2
        # Mode 1 is the default on every skill without an omicron, so it matches nothing here.
        assert self._get(omicron_mode=1) == []

    def test_without_localization_returns_keys(self):
        from swgoh_comlink.helpers import get_unit_abilities

        (ackbar,) = get_unit_abilities(_ABILITY_UNITS, _ABILITY_SKILLS, _ABILITIES, base_id="ADMIRALACKBAR")
        assert ackbar["unit_name"] == "UNIT_ACKBAR_NAME"
        assert ackbar["name"] == "SPECIALABILITY_ADMIRALACKBAR02_NAME"

    @pytest.mark.parametrize(
        ("args", "kwargs"),
        [
            (({}, _ABILITY_SKILLS, _ABILITIES), {}),
            ((_ABILITY_UNITS, None, _ABILITIES), {}),
            ((_ABILITY_UNITS, _ABILITY_SKILLS, "ability"), {}),
            ((_ABILITY_UNITS, _ABILITY_SKILLS, _ABILITIES, ["not", "a", "dict"]), {}),
            ((_ABILITY_UNITS, _ABILITY_SKILLS, _ABILITIES), {"base_id": 5}),
            ((_ABILITY_UNITS, _ABILITY_SKILLS, _ABILITIES), {"omicron_mode": [8, None]}),
        ],
    )
    def test_invalid_input_raises(self, args: tuple[Any, ...], kwargs: dict[str, Any]):
        from swgoh_comlink.helpers import get_unit_abilities

        with pytest.raises(SwgohComlinkValueError):
            get_unit_abilities(*args, **kwargs)


_EFFECT_LOC = {
    "BattleEffect_PotencyUp": "[c][ffff33]Potency Up:[-][/c] Increased chance to apply detrimental effects",
    # Colon after the closing tags
    "BattleEffect_Overcharge": "[c][F0FF23]Overcharge[-][/c]: Protection Temporarily Increased",
    # Whitespace before the closing tags
    "BattleEffect_Provoked": "[c][ffff33]Provoked: [-][/c]old wording",
    "BattleEffect_Provoked_V2": "[c][ffff33]Provoked: [-][/c]+100% counter chance\\nnext line",
    # 'Vulnerable' starts with V; only a trailing _V<n> is a version
    "BattleEffect_Vulnerable": "[c][ffff33]Vulnerable:[-][/c] old",
    "BattleEffect_Vulnerable_V2": "[c][ffff33]Vulnerable:[-][/c] current",
    "Battleeffect_ConcussionMine": "[c][ffff33]Concussion Mine:[-][/c] Deals damage",
    "FEAR_DEBUFF_DESC": "[c][ffff33]Fear:[-][/c] Miss the next turn",
    "DEMORALIZED_DEBUFF_TIER1": "[c][ffff33]Demoralized:[-][/c] tier 1",
    "DEMORALIZED_DEBUFF_TIER0": "[c][ffff33]Demoralized:[-][/c] tier 0",
    "MOFFGIDEON_INSIGHT_V2": "[c][ffff33]Insight:[-][/c] additional effects",
    "50RT_VIP_ALLY": "[c][ffff33]VIP:[-][/c] gain bonuses",
    # Generic key, but BattleEffect_ wins for the same name
    "OVERCHARGE_BUFF_DESC": "[c][ffff33]Overcharge:[-][/c] generic wording",
    # Not named effects
    "BattleEffect_AccuracyUp_Stat": "[c][ffff33]+15% Accuracy:[-][/c] stat line",
    "BattleEffect_Mission": "Inflict 10 stacks of Distract to obtain victory!",
    "SPECIALABILITY_X_DESC": "[c][ffff33]Expose:[-][/c] ability text is not an effect key",
}


class TestGetNamedEffects:
    def test_reads_every_key_family(self):
        from swgoh_comlink.helpers import get_named_effects

        effects = get_named_effects(_EFFECT_LOC)
        assert list(effects) == sorted(
            ["Concussion Mine", "Demoralized", "Fear", "Insight", "Overcharge", "Potency Up", "Provoked", "VIP",
             "Vulnerable"]
        )  # fmt: skip
        assert effects["Potency Up"] == {
            "name": "Potency Up",
            "description": "Increased chance to apply detrimental effects",
            "key": "BattleEffect_PotencyUp",
        }

    def test_picks_the_authoritative_definition(self):
        from swgoh_comlink.helpers import get_named_effects

        effects = get_named_effects(_EFFECT_LOC)
        assert effects["Overcharge"]["key"] == "BattleEffect_Overcharge"
        assert effects["Overcharge"]["description"] == "Protection Temporarily Increased"
        assert effects["Provoked"]["description"] == "+100% counter chance\nnext line"
        assert effects["Vulnerable"]["description"] == "current"
        assert effects["Demoralized"]["key"] == "DEMORALIZED_DEBUFF_TIER0"

    def test_invalid_input_raises(self):
        from swgoh_comlink.helpers import get_named_effects

        not_a_dict: Any = []
        with pytest.raises(SwgohComlinkValueError):
            get_named_effects(not_a_dict)


# ── _wire ──────────────────────────────────────────────────────────────

# An excerpt of get_enums()["CurrencyType"], plus one enum without a <Type>_DEFAULT member.
_CURRENCY = {
    "CurrencyType_DEFAULT": 0,
    "GRIND": 1,
    "PVP_CURRENCY": 10,
    "SHARD_CURRENCY": 16,
    "GUILD_RAID_CURRENCY_01": 20,
}
_DIFFICULTY = {"NOT_SET": 0, "NORMAL_DIFF": 4, "HARD_DIFF": 5}


class TestAsInt:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (42, 42),
            ("1655938556", 1655938556),
            ("-3", -3),
            (" 7 ", 7),
            (1.9, 1),
            ("9223372036854775807", 9223372036854775807),
            (0, 0),
            ("0", 0),
        ],
    )
    def test_reads_numbers(self, value: Any, expected: int):
        from swgoh_comlink.helpers import as_int

        assert as_int(value) == expected

    @pytest.mark.parametrize("value", [None, "", "abc", "1.5", True, False, [], {}, float("inf"), float("nan")])
    def test_unreadable_returns_default(self, value: Any):
        from swgoh_comlink.helpers import as_int

        assert as_int(value) == 0
        assert as_int(value, default=-1) == -1


class TestAsStr:
    @pytest.mark.parametrize(("value", "expected"), [("Rebels", "Rebels"), ("", ""), (42, ""), (None, ""), ([], "")])
    def test_only_strings_pass(self, value: Any, expected: str):
        from swgoh_comlink.helpers import as_str

        assert as_str(value) == expected

    def test_custom_default(self):
        from swgoh_comlink.helpers import as_str

        assert as_str(None, default="?") == "?"


class TestAsId:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [("O1700000000000:1", "O1700000000000:1"), (2, "2"), (0, "0"), ("", ""), (None, ""), (True, ""), (1.5, "")],
    )
    def test_reads_string_or_int(self, value: Any, expected: str):
        from swgoh_comlink.helpers import as_id

        assert as_id(value) == expected

    def test_custom_default(self):
        from swgoh_comlink.helpers import as_id

        assert as_id(None, default="none") == "none"


class TestAsScalar:
    @pytest.mark.parametrize(
        ("value", "expected"), [(3, 3), (0, 0), ("CHARACTER", "CHARACTER"), (True, None), (None, None), (1.5, None)]
    )
    def test_keeps_int_or_str(self, value: Any, expected: int | str | None):
        from swgoh_comlink.helpers import as_scalar

        assert as_scalar(value) == expected


class TestAsEpoch:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            # guildJoinTime / Conquest lastRefreshTime: seconds
            (1655938556, datetime(2022, 6, 22, 22, 55, 56, tzinfo=timezone.utc)),
            ("1655938556", datetime(2022, 6, 22, 22, 55, 56, tzinfo=timezone.utc)),
            # lastActivityTime: milliseconds, kept to the millisecond
            ("1770515437123", datetime(2026, 2, 8, 1, 50, 37, 123000, tzinfo=timezone.utc)),
            (1700000000000, datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc)),
            # Either side of the 1e11 boundary
            (99_999_999_999, datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=99_999_999_999)),
            (100_000_000_000, datetime(1973, 3, 3, 9, 46, 40, tzinfo=timezone.utc)),
        ],
    )
    def test_seconds_and_milliseconds(self, value: Any, expected: datetime):
        from swgoh_comlink.helpers import as_epoch

        assert as_epoch(value) == expected

    @pytest.mark.parametrize("value", [None, 0, "0", "", "-5", -1, "abc", True, "99999999999999999999"])
    def test_no_time_returns_none(self, value: Any):
        from swgoh_comlink.helpers import as_epoch

        assert as_epoch(value) is None

    def test_result_is_aware_utc(self):
        from swgoh_comlink.helpers import as_epoch

        moment = as_epoch("1770515437000")
        assert moment is not None
        assert moment.tzinfo == timezone.utc

    def test_example_player_times(self):
        import json

        from swgoh_comlink.helpers import as_epoch

        player = json.loads((Path(__file__).parent.parent / "resources" / "example-player.json").read_text())
        assert as_epoch(player["lastActivityTime"]) == datetime(2026, 2, 8, 1, 50, 37, tzinfo=timezone.utc)
        assert all(as_epoch(season["joinTime"]) for season in player["seasonStatus"])


class TestAsList:
    def test_list_is_returned_as_is(self):
        from swgoh_comlink.helpers import as_list

        rows = [{"id": "a"}, {"id": "b"}]
        assert as_list(rows) is rows

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ({"id": "a"}, [{"id": "a"}]),
            (None, []),
            ((1, 2), [1, 2]),
            ("abc", ["abc"]),
            (0, [0]),
            ([], []),
        ],
    )
    def test_wraps_other_values(self, value: Any, expected: list[Any]):
        from swgoh_comlink.helpers import as_list

        assert as_list(value) == expected


class TestBaseId:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("GENERALSKYWALKER:SEVEN_STAR", "GENERALSKYWALKER"),
            ("BOUSHH", "BOUSHH"),
            ("A:B:C", "A"),
            ("", ""),
            (None, ""),
            (42, ""),
        ],
    )
    def test_strips_rarity(self, value: Any, expected: str):
        from swgoh_comlink.helpers import base_id

        assert base_id(value) == expected

    def test_example_player_roster(self):
        import json

        from swgoh_comlink.helpers import base_id

        player = json.loads((Path(__file__).parent.parent / "resources" / "example-player.json").read_text())
        ids = {base_id(unit["definitionId"]) for unit in player["rosterUnit"]}
        assert "MAGMATROOPER" in ids
        assert not any(":" in unit_id for unit_id in ids)


class TestParseEnum:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (16, "SHARD_CURRENCY"),
            ("16", "SHARD_CURRENCY"),
            (" 16 ", "SHARD_CURRENCY"),
            (0, "CurrencyType_DEFAULT"),
            ("SHARD_CURRENCY", "SHARD_CURRENCY"),
            ("shard_currency", "SHARD_CURRENCY"),
            ("SHARDCURRENCY", "SHARD_CURRENCY"),
            ("CURRENCYTYPE_SHARDCURRENCY", "SHARD_CURRENCY"),
            ("CURRENCYTYPE_GUILDRAIDCURRENCY01", "GUILD_RAID_CURRENCY_01"),
            ("CURRENCYTYPE_CURRENCYTYPEDEFAULT", "CurrencyType_DEFAULT"),
            ("CurrencyType_DEFAULT", "CurrencyType_DEFAULT"),
        ],
    )
    def test_every_spelling(self, value: Any, expected: str):
        from swgoh_comlink.helpers import parse_enum

        assert parse_enum(value, _CURRENCY) == expected

    @pytest.mark.parametrize(
        "value",
        [
            99,
            "99",
            "UNKNOWN",
            "",
            None,
            True,
            False,
            16.0,
            [],
            # An unknown member from a newer game version is not read as "GRIND"
            "NEW_GRIND",
            # Wrong type name in a decoder-style spelling
            "ITEMTYPE_SHARDCURRENCY",
            # Decoder-style names have no underscore in the member half
            "CURRENCYTYPE_SHARD_CURRENCY_X",
            # Not plain ASCII whole numbers
            "--16",
            "¹⁶",
            # Past the interpreter's limit on digits in an int string
            "1" * 5000,
        ],
    )
    def test_unknown_returns_none(self, value: Any):
        from swgoh_comlink.helpers import parse_enum

        assert parse_enum(value, _CURRENCY) is None

    def test_decoder_name_without_known_type(self):
        from swgoh_comlink.helpers import parse_enum

        # No <Type>_DEFAULT member, so any type half is accepted unless enum_name is given.
        assert parse_enum("CAMPAIGNNODEDIFFICULTY_NORMALDIFF", _DIFFICULTY) == "NORMAL_DIFF"
        assert parse_enum("OTHER_NORMALDIFF", _DIFFICULTY) == "NORMAL_DIFF"
        assert (
            parse_enum("CAMPAIGNNODEDIFFICULTY_NORMALDIFF", _DIFFICULTY, enum_name="CampaignNodeDifficulty")
            == "NORMAL_DIFF"
        )
        assert parse_enum("OTHER_NORMALDIFF", _DIFFICULTY, enum_name="CampaignNodeDifficulty") is None

    def test_ambiguous_spelling_returns_none(self):
        from swgoh_comlink.helpers import parse_enum

        members = {"MetadataRequestType_DEFAULT": 0, "DEFAULT": 1, "CLIENT_PARAMS": 2}
        assert parse_enum("METADATAREQUESTTYPE_DEFAULT", members) is None
        assert parse_enum("DEFAULT", members) == "DEFAULT"
        assert parse_enum("METADATAREQUESTTYPE_CLIENTPARAMS", members) == "CLIENT_PARAMS"

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("server_error", "SERVER_ERROR"),
            ("Server_Error", "SERVER_ERROR"),
            ("SERVER_ERROR", "SERVER_ERROR"),
            ("error", "ERROR"),
            ("feature_suspended", "FEATURE_SUSPENDED"),
            # Upper-case with one underscore is still read as a decoder-style name
            ("RESPONSECODE_SUSPENDED", "SUSPENDED"),
        ],
    )
    def test_case_variant_without_known_type(self, value: str, expected: str):
        from swgoh_comlink.helpers import parse_enum

        # No <Type>_DEFAULT member, and one member is another's last word: a lower-case member
        # name must not also be read as a decoder-style name for that last word.
        members = {"OK": 0, "SERVER_ERROR": 1, "ERROR": 2, "FEATURE_SUSPENDED": 3, "SUSPENDED": 4}
        assert parse_enum(value, members) == expected

    def test_lower_case_type_default_member(self):
        from swgoh_comlink.helpers import parse_enum

        members = {"MetadataRequestType_DEFAULT": 0, "DEFAULT": 1, "CLIENT_PARAMS": 2}
        assert parse_enum("metadatarequesttype_default", members) == "MetadataRequestType_DEFAULT"

    def test_alias_value_returns_first_name(self):
        from swgoh_comlink.helpers import parse_enum

        assert parse_enum(1, {"OLD_NAME": 1, "NEW_NAME": 1}) == "OLD_NAME"

    def test_negative_numbers(self):
        from swgoh_comlink.helpers import parse_enum

        assert parse_enum("-1", {"ALL": -1, "NONE": 0}) == "ALL"

    @pytest.mark.parametrize("members", [None, [], "CurrencyType"])
    def test_invalid_members_raises(self, members: Any):
        from swgoh_comlink.helpers import parse_enum

        with pytest.raises(SwgohComlinkValueError, match=r"parse_enum\(\)"):
            parse_enum(16, members)


def test_wire_docstring_examples():
    import doctest

    from swgoh_comlink.helpers import _wire

    results = doctest.testmod(_wire)
    assert results.failed == 0
    assert results.attempted >= 20


# ── _items ──────────────────────────────────────────────────────────────

_ITEM_LOC = {
    "ARTIFACT_GURAD_AND_PENTRATE_3_COST_RARE_NAME": "Guard and Penetrate",
    "PLAYERTITLE_GRANDARENA_INTRO_NAME": "[c][FFFF00]Fight Me[-][/c]",
    "STATMODSETBONUS_SPEED_NAME": "Speed",
    "STATMODSETBONUS_DEFENSE_NAME": "Defense",
    "UNIT_GLLEIA_NAME": "Leia Organa",
    "UNIT_VADER_NAME": "Darth Vader",
    "UNIT_ANAKINKNIGHT_NAME": "Jedi Knight Anakin",
    "MATERIAL_ABILITYMATULTIMATE_NAME": "Ability Material Ultimate",
    "EQUIPMENT_016_NAME": "Mk 2 TaggeCo Holo Lens",
    "MYSTERYBOX_ERA_T1_TITLE": "Era Battle Prize Box",
    "PLAYERPORTRAIT_MISSION_NAME": "Mission Vao",
    "LIGHTSPEEDTOKEN_TIER05_NAME": "KYBER LIGHTSPEED TOKEN",
}
_ITEM_GAME_DATA: dict[str, Any] = {
    "material": [
        # An id shared with an equipment piece: ids are only unique within an ItemType.
        {"id": "016", "nameKey": "MATERIAL_ABILITYMATULTIMATE_NAME"},
        {"id": "unitshard_GLLEIA", "nameKey": "UNIT_GLLEIA_NAME"},
        # Event shard variant: no unit has this baseId, but the material names the unit.
        {"id": "unitshard_VADER_JKL_EVENT", "nameKey": "UNIT_VADER_NAME"},
        # A shard whose own key is not localized falls back to the unit.
        {"id": "unitshard_ANAKINKNIGHT", "nameKey": "UNIT_ANAKINKNIGHT_SHARD_MISSING"},
    ],
    "equipment": [{"id": "016", "nameKey": "EQUIPMENT_016_NAME"}],
    "mysteryBox": [{"id": "mysterybox_era_T1", "titleKey": "MYSTERYBOX_ERA_T1_TITLE", "descKey": "X"}],
    "playerTitle": [{"id": "PLAYERTITLE_GRANDARENA_INTRO", "nameKey": "PLAYERTITLE_GRANDARENA_INTRO_NAME"}],
    "playerPortrait": [{"id": "PLAYERPORTRAIT_MISSION", "nameKey": "PLAYERPORTRAIT_MISSION_NAME"}],
    "artifactDefinition": [
        {"id": "artifact_guard_and_pentrate_3_cost_rare", "nameKey": "ARTIFACT_GURAD_AND_PENTRATE_3_COST_RARE_NAME"}
    ],
    "lightspeedToken": [{"id": "LST_TIER05", "nameKey": "LIGHTSPEEDTOKEN_TIER05_NAME"}],
    "units": [
        {"baseId": "ANAKINKNIGHT", "nameKey": "UNIT_ANAKINKNIGHT_NAME", "rarity": 1},
        {"baseId": "ANAKINKNIGHT", "nameKey": "UNIT_ANAKINKNIGHT_NAME", "rarity": 2},
    ],
    "statModSet": [
        {"id": "4", "name": "STATMODSETBONUS_SPEED_NAME", "setCount": 4},
        {"id": "3", "name": "STATMODSETBONUS_DEFENSE_NAME", "setCount": 2},
    ],
    "mysteryStatMod": [
        {"id": "35155", "slot": [2], "setId": "3", "minRarity": 5, "maxRarity": 5, "minTier": 5, "maxTier": 5},
        {"id": "11112", "slot": [2, 3, 4, 5, 6, 7], "setId": "4", "minRarity": 1, "maxRarity": 2, "minTier": 1,
         "maxTier": 2},
        {"id": "two", "slot": [2, 3], "setId": "4", "minRarity": 5, "maxRarity": 5, "minTier": 1, "maxTier": 1},
        # Game data fetched with enums=True carries enum names in place of the numbers.
        {"id": "enum", "slot": ["STATMOD_SLOT_02"], "setId": "4", "minRarity": "SIX_STAR", "maxRarity": "SIX_STAR",
         "minTier": "STATMOD_TIER_05", "maxTier": "STATMOD_TIER_05"},
    ],
}  # fmt: skip


class TestItemTypeConstants:
    def test_tables(self):
        from swgoh_comlink.helpers import CURRENCY_NAMES, CURRENCY_TYPES, ITEM_TYPES

        assert ITEM_TYPES[7] == "MATERIAL"
        assert ITEM_TYPES[16] == "MYSTERY_STAT_MOD"
        assert CURRENCY_TYPES[1] == "GRIND"
        assert CURRENCY_NAMES[CURRENCY_TYPES[41]] == "Micro Attenuators"
        # Every currency member has a display name.
        assert set(CURRENCY_NAMES) == set(CURRENCY_TYPES.values())


class TestGetDataDiscNames:
    def test_joins_through_the_records_own_name_key(self):
        from swgoh_comlink.helpers import get_data_disc_names

        discs = get_data_disc_names(_ITEM_GAME_DATA["artifactDefinition"], _ITEM_LOC)
        assert discs == {"artifact_guard_and_pentrate_3_cost_rare": "Guard and Penetrate"}

    def test_without_localization_returns_name_keys(self):
        from swgoh_comlink.helpers import get_data_disc_names

        discs = get_data_disc_names(_ITEM_GAME_DATA["artifactDefinition"])
        assert discs["artifact_guard_and_pentrate_3_cost_rare"] == "ARTIFACT_GURAD_AND_PENTRATE_3_COST_RARE_NAME"

    def test_invalid_input_raises(self):
        from swgoh_comlink.helpers import get_data_disc_names

        not_a_list: Any = {}
        with pytest.raises(SwgohComlinkValueError, match="get_data_disc_names"):
            get_data_disc_names(not_a_list)
        not_a_dict: Any = []
        with pytest.raises(SwgohComlinkValueError):
            get_data_disc_names([], not_a_dict)


class TestGetPlayerTitleNames:
    def test_names_are_localized_and_markup_free(self):
        from swgoh_comlink.helpers import get_player_title_names

        titles = [*_ITEM_GAME_DATA["playerTitle"], {"id": "PLAYERTITLE_NEW", "nameKey": "PLAYERTITLE_NEW_NAME"}, {}]
        result = get_player_title_names(titles, _ITEM_LOC)
        assert result == {"PLAYERTITLE_GRANDARENA_INTRO": "Fight Me", "PLAYERTITLE_NEW": "PLAYERTITLE_NEW_NAME"}

    def test_invalid_input_raises(self):
        from swgoh_comlink.helpers import get_player_title_names

        not_a_list: Any = "titles"
        with pytest.raises(SwgohComlinkValueError, match="get_player_title_names"):
            get_player_title_names(not_a_list)


class TestGetModCatalog:
    _STAT_MODS: list[dict[str, Any]] = [
        {"id": "451", "setId": "4", "slot": 2, "rarity": 5},
        {"id": "137", "setId": "3", "slot": "STATMOD_SLOT_06", "rarity": "SEVEN_STAR"},
        {"id": "999", "setId": "9", "slot": 4, "rarity": 1},
    ]

    def test_sets_and_definitions(self):
        from swgoh_comlink.helpers import get_mod_catalog

        catalog = get_mod_catalog(self._STAT_MODS, _ITEM_GAME_DATA["statModSet"], _ITEM_LOC)
        assert catalog["sets"]["4"] == {"set_id": "4", "name": "Speed", "set_count": 4}
        assert catalog["sets"]["3"]["set_count"] == 2
        assert catalog["definitions"]["451"] == {
            "definition_id": "451",
            "set_id": "4",
            "set_name": "Speed",
            "slot": 2,
            "slot_name": "Square",
            "rarity": 5,
        }
        # Enum names (enums=True) are read as their numbers.
        assert catalog["definitions"]["137"]["slot"] == 7
        assert catalog["definitions"]["137"]["rarity"] == 7
        # A set statModSet does not list keeps its id as its name.
        assert catalog["definitions"]["999"]["set_name"] == "9"

    def test_without_localization_uses_mod_set_ids(self):
        from swgoh_comlink.helpers import MOD_SET_IDS, get_mod_catalog

        catalog = get_mod_catalog(self._STAT_MODS, _ITEM_GAME_DATA["statModSet"])
        assert catalog["sets"]["3"]["name"] == MOD_SET_IDS["3"]
        assert catalog["definitions"]["451"]["set_name"] == MOD_SET_IDS["4"]

    def test_invalid_input_raises(self):
        from swgoh_comlink.helpers import get_mod_catalog

        not_a_list: Any = None
        with pytest.raises(SwgohComlinkValueError, match="get_mod_catalog"):
            get_mod_catalog(not_a_list, [])
        with pytest.raises(SwgohComlinkValueError, match="stat_mod_sets"):
            get_mod_catalog([], not_a_list)


class TestItemNames:
    @pytest.mark.parametrize(
        ("item_type", "item_id", "expected"),
        [
            (7, "016", "Ability Material Ultimate"),
            (11, "016", "Mk 2 TaggeCo Holo Lens"),
            ("EQUIPMENT", "016", "Mk 2 TaggeCo Holo Lens"),
            ("7", "unitshard_GLLEIA", "Leia Organa"),
            ("MATERIAL", "unitshard_VADER_JKL_EVENT", "Darth Vader"),
            (7, "unitshard_ANAKINKNIGHT", "Jedi Knight Anakin"),
            (2, "ANAKINKNIGHT:ONE_STAR", "Jedi Knight Anakin"),
            ("UNIT", "ANAKINKNIGHT", "Jedi Knight Anakin"),
            (3, "GRIND", "Credits"),
            ("CURRENCY", 41, "Micro Attenuators"),
            (3, "41", "Micro Attenuators"),
            (14, "mysterybox_era_T1", "Era Battle Prize Box"),
            (17, "PLAYERTITLE_GRANDARENA_INTRO", "Fight Me"),
            (19, "PLAYERPORTRAIT_MISSION", "Mission Vao"),
            (23, "artifact_guard_and_pentrate_3_cost_rare", "Guard and Penetrate"),
            (34, "LST_TIER05", "KYBER LIGHTSPEED TOKEN"),
            (16, "35155", "5-dot Defense Square mod (A)"),
            ("MYSTERY_STAT_MOD", "11112", "1-2-dot Speed any-slot mod (E-D)"),
            (16, "two", "5-dot Speed Square or Arrow mod (E)"),
            (16, "enum", "6-dot Speed Arrow mod (A)"),
        ],
    )
    def test_names_each_item_type(self, item_type: Any, item_id: Any, expected: str):
        from swgoh_comlink.helpers import ItemNames

        assert ItemNames(_ITEM_GAME_DATA, _ITEM_LOC).get(item_type, item_id) == expected

    @pytest.mark.parametrize(
        ("item_type", "item_id"),
        [
            (6, ""),  # XP names no particular item
            (7, "missing"),
            (7, "unitshard_NOBODY"),
            (3, "NOT_A_CURRENCY"),
            (3, "99"),
            (16, "missing"),
            ("NOT_AN_ITEM_TYPE", "016"),
            (None, "016"),
        ],
    )
    def test_unresolved_returns_default(self, item_type: Any, item_id: str):
        from swgoh_comlink.helpers import ItemNames

        names = ItemNames(_ITEM_GAME_DATA, _ITEM_LOC)
        assert names.get(item_type, item_id) is None
        assert names.get(item_type, item_id, "fallback") == "fallback"

    def test_missing_collections_resolve_to_nothing(self):
        from swgoh_comlink.helpers import ItemNames

        names = ItemNames({}, _ITEM_LOC)
        assert names.get(7, "016") is None
        assert names.get(3, "GRIND") == "Credits"

    def test_without_localization_returns_keys(self):
        from swgoh_comlink.helpers import ItemNames

        names = ItemNames(_ITEM_GAME_DATA)
        assert names.get(17, "PLAYERTITLE_GRANDARENA_INTRO") == "PLAYERTITLE_GRANDARENA_INTRO_NAME"
        # Mystery mods fall back to the English set names.
        assert names.get(16, "35155") == "5-dot Defense Square mod (A)"

    def test_invalid_input_raises(self):
        from swgoh_comlink.helpers import ItemNames

        not_a_dict: Any = []
        with pytest.raises(SwgohComlinkValueError, match="game_data"):
            ItemNames(not_a_dict)
        with pytest.raises(SwgohComlinkValueError, match="material"):
            ItemNames({"material": {}})
        with pytest.raises(SwgohComlinkValueError, match="localization"):
            ItemNames({}, not_a_dict)


class TestGetNamedRewards:
    def test_flat_and_conditional_items(self):
        from swgoh_comlink.helpers import ItemNames, get_named_rewards

        rewards: list[Any] = [
            {"id": "GRIND", "type": 3, "minQuantity": 20000, "maxQuantity": 20000},
            {"id": "unitshard_GLLEIA", "type": "MATERIAL", "minQuantity": 5, "maxQuantity": 10},
            {"id": "ANAKINKNIGHT:ONE_STAR", "type": 2, "minQuantity": 1, "maxQuantity": 1},
            {
                "bucketItem": [{"id": "016", "type": 11, "minQuantity": 1, "maxQuantity": 1}],
                "requirementId": "glleia_tier06_rewards_not_exhausted",
            },
            {"id": "", "type": 6, "minQuantity": 6, "maxQuantity": 6},
            {"id": "unknown", "type": "SOMETHING_NEW", "minQuantity": 1, "maxQuantity": 1},
            {"primaryReward": [], "rankStart": 1},
            "not an entry",
        ]
        result = get_named_rewards(rewards, ItemNames(_ITEM_GAME_DATA, _ITEM_LOC))
        assert [(r["item_type"], r["name"]) for r in result] == [
            (3, "Credits"),
            (7, "Leia Organa"),
            (2, "Jedi Knight Anakin"),
            (11, "Mk 2 TaggeCo Holo Lens"),
            (6, "XP"),
            ("SOMETHING_NEW", "unknown"),
        ]
        credits, shards, unit, gear, xp, _ = result
        assert (credits["min_quantity"], credits["max_quantity"]) == (20000, 20000)
        assert (shards["min_quantity"], shards["max_quantity"]) == (5, 10)
        assert shards["base_id"] == "GLLEIA" and unit["base_id"] == "ANAKINKNIGHT" and credits["base_id"] is None
        assert gear["requirement_id"] == "glleia_tier06_rewards_not_exhausted"
        assert credits["requirement_id"] is None
        assert xp["id"] == ""

    def test_invalid_input_raises(self):
        from swgoh_comlink.helpers import ItemNames, get_named_rewards

        not_a_list: Any = {}
        with pytest.raises(SwgohComlinkValueError, match="get_named_rewards"):
            get_named_rewards(not_a_list, ItemNames({}))
        not_item_names: Any = {}
        with pytest.raises(SwgohComlinkValueError, match="item_names"):
            get_named_rewards([], not_item_names)


class TestItemHelpersRobustness:
    def test_valid_calls_do_not_walk_the_stack(self, monkeypatch: pytest.MonkeyPatch):
        import inspect

        from swgoh_comlink.helpers import (
            ItemNames,
            get_data_disc_names,
            get_mod_catalog,
            get_named_rewards,
            get_player_title_names,
        )

        def fail() -> None:
            raise AssertionError("inspect.stack() called on valid input")

        monkeypatch.setattr(inspect, "stack", fail)
        names = ItemNames(_ITEM_GAME_DATA, _ITEM_LOC)
        get_named_rewards([{"id": "GRIND", "type": 3}], names)
        get_data_disc_names(_ITEM_GAME_DATA["artifactDefinition"], _ITEM_LOC)
        get_player_title_names(_ITEM_GAME_DATA["playerTitle"], _ITEM_LOC)
        get_mod_catalog([], _ITEM_GAME_DATA["statModSet"], _ITEM_LOC)


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


class TestConstantsGameDataItemsEnumSync:
    """Lock in helper alignment with the live `GameDataItemsEnum` from `get_enums()`."""

    def test_new_items_resolve(self):
        from swgoh_comlink.helpers._constants import Constants

        assert Constants.get("AbilityDecisionTrees") == "1099511627776"
        assert Constants.get("EraDefinitions") == "2251799813685248"
        assert Constants.get("UBSUpdate") == "2150109456"

    def test_episode_definitions_plural(self):
        from swgoh_comlink.helpers._constants import Constants

        assert Constants.get("EpisodeDefinitions") == "281474976710656"

    def test_account_linking_alias(self):
        from swgoh_comlink.helpers._constants import Constants

        assert Constants.get("AccountLinking") == "562949953421312"

    def test_segment_values_match_server(self):
        from swgoh_comlink.helpers._constants import Constants

        assert Constants.Segment1 == 2097151
        assert Constants.Segment2 == 1125968624222208
        assert Constants.Segment3 == 206158430208
        assert Constants.Segment4 == 3377424842620928

    def test_dataitems_members_present(self):
        from swgoh_comlink.helpers._data_items import DataItems

        assert DataItems.ABILITY_DECISION_TREE.value == 1099511627776
        assert DataItems.ERA_DEFINITION.value == 2251799813685248
        assert DataItems.UBS_UPDATE.value == 2150109456


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
