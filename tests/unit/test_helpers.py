"""Tests for pure helper functions that need no HTTP mocking."""

from __future__ import annotations

import doctest
import inspect
import json
import logging
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from swgoh_comlink._base import _SENSITIVE_KEYS
from swgoh_comlink.exceptions import SwgohComlinkValueError
from swgoh_comlink.globals import LoggingFormatter, get_logger
from swgoh_comlink.helpers import (
    CURRENCY_NAMES,
    CURRENCY_TYPES,
    ITEM_TYPES,
    MOD_SET_IDS,
    ItemNames,
    _wire,
    as_epoch,
    as_id,
    as_int,
    as_list,
    as_scalar,
    as_str,
    base_id,
    calc_current_stamina,
    calc_stamina_full_time,
    get_ability_upgrade_costs,
    get_conquest_feats,
    get_data_disc_names,
    get_event_schedule,
    get_game_config,
    get_game_config_int,
    get_gear_craft_tree,
    get_guild_activity,
    get_mod_catalog,
    get_named_effects,
    get_named_rewards,
    get_player_title_names,
    get_relic_promotion_costs,
    get_tb_mission_requirements,
    get_tb_mission_scores,
    get_tb_platoon_definitions,
    get_tb_star_thresholds,
    get_unit_abilities,
    get_unit_gear_tiers,
    parse_enum,
    sum_upgrade_costs,
)
from swgoh_comlink.helpers._arena import get_arena_payout, get_max_rank_jump
from swgoh_comlink.helpers._constants import _LEGACY_NAME_MAP, Constants
from swgoh_comlink.helpers._data_items import DataItems
from swgoh_comlink.helpers._decorators import func_debug_logger, func_timer
from swgoh_comlink.helpers._events import _event_name
from swgoh_comlink.helpers._gac import (
    _async_find_bracket_boundary,
    _find_bracket_boundary,
    convert_divisions_to_int,
    convert_league_to_int,
    search_gac_brackets,
)
from swgoh_comlink.helpers._game_data import (
    create_localized_unit_name_dictionary,
    get_current_datacron_sets,
    get_datacron_dismantle_total,
    get_datacron_dismantle_value,
    get_playable_units,
    get_raid_leaderboard_ids,
)
from swgoh_comlink.helpers._localization import (
    ANSI_BOLD,
    ANSI_ITALIC,
    ANSI_RESET,
    ANSI_STRIKE,
    ANSI_UNDERLINE,
    _hex_to_ansi_truecolor,
    _parse_tokens,
    parse_swgoh_string,
)
from swgoh_comlink.helpers._omicron import (
    get_omicron_skill_tier,
    get_omicron_skills,
    get_tw_omicrons,
    get_unit_from_skill,
    is_omicron_skill,
)
from swgoh_comlink.helpers._utils import (
    convert_relic_tier,
    get_enum_key_by_value,
    get_function_name,
    human_time,
    sanitize_allycode,
    validate_file_path,
)

# ── _utils ──────────────────────────────────────────────────────────────


_RESOURCES = Path(__file__).parent.parent / "resources"


@pytest.fixture(scope="module")
def example_player() -> dict[str, Any]:
    return json.loads((_RESOURCES / "example-player.json").read_text())


class TestGetFunctionName:
    def test_returns_calling_function_name(self):

        def my_custom_func():
            return get_function_name()

        assert my_custom_func() == "my_custom_func()"


@pytest.mark.parametrize(
    ("category", "value", "default", "expected"),
    [
        pytest.param("colors", 2, None, "blue", id="match"),
        pytest.param("colors", 99, None, None, id="no-match"),
        pytest.param("shapes", 1, None, None, id="missing-category"),
        pytest.param("shapes", 1, "fallback", "fallback", id="custom-default"),
    ],
)
def test_get_enum_key_by_value(category, value, default, expected):
    enum_dict = {"colors": {"red": 1, "blue": 2}}
    args = (enum_dict, category, value) if default is None else (enum_dict, category, value, default)
    assert get_enum_key_by_value(*args) == expected


class TestValidateFilePath:
    def test_valid_file(self, tmp_path: Path):

        f = tmp_path / "test.txt"
        f.write_text("hello")
        assert validate_file_path(f) is True

    def test_nonexistent_file(self, tmp_path: Path):

        assert validate_file_path(tmp_path / "nope.txt") is False

    def test_directory_returns_false(self, tmp_path: Path):

        assert validate_file_path(tmp_path) is False

    def test_empty_raises(self):

        with pytest.raises(SwgohComlinkValueError, match="path"):
            validate_file_path("")


class TestSanitizeAllycode:
    @pytest.mark.parametrize("allycode", ["123456789", 123456789, "123-456-789"], ids=["str", "int", "dashes-removed"])
    def test_valid(self, allycode):
        assert sanitize_allycode(allycode) == "123456789"

    @pytest.mark.parametrize(
        "allycode",
        [
            pytest.param("12345", id="wrong-length"),
            pytest.param("12345abcd", id="non-digits"),
            # 0 is falsy but is not the REQUIRED sentinel, so it is validated and rejected.
            pytest.param(0, id="zero"),
            pytest.param(3.14, id="float"),
            pytest.param([1, 2, 3], id="list"),
        ],
    )
    def test_invalid_raises(self, allycode):
        with pytest.raises(SwgohComlinkValueError, match="Invalid ally code"):
            sanitize_allycode(allycode)

    def test_default_none_returns_empty(self):
        assert sanitize_allycode() == ""


class TestHumanTime:
    @pytest.mark.parametrize(
        ("timestamp", "expected"),
        [
            pytest.param(0, "1970-01-01 00:00:00", id="seconds"),
            pytest.param("0", "1970-01-01 00:00:00", id="string"),
            pytest.param(1700000000.5, "2023-11-14 22:13:20", id="float"),
            # 13+ digit timestamps are milliseconds.
            pytest.param(1700000000000, "2023-11-14 22:13:20", id="milliseconds"),
        ],
    )
    def test_formats_utc(self, timestamp, expected):
        assert human_time(timestamp) == expected

    @pytest.mark.parametrize(
        ("value", "match"),
        [pytest.param("not_a_number", "Unable to convert", id="bad-string"), pytest.param([], "required", id="list")],
    )
    def test_invalid_raises(self, value, match):
        with pytest.raises(SwgohComlinkValueError, match=match):
            human_time(value)


class TestConvertRelicTier:
    # The game's RelicTier enum: RelicTier_DEFAULT = 0, RELIC_LOCKED = 1, RELIC_UNLOCKED = 2, RELIC_TIER_01 = 3
    @pytest.mark.parametrize(
        ("tier", "expected"),
        [
            (0, "LOCKED"),
            (1, "LOCKED"),
            (2, "UNLOCKED"),
            (3, "1"),
            (12, "10"),
            ("9", "7"),
            (99, None),
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
    def test_converts(self, tier, expected):
        assert convert_relic_tier(tier) == expected

    def test_every_relic_in_example_player_converts(self, example_player):
        tiers = {unit["relic"]["currentTier"] for unit in example_player["rosterUnit"] if unit.get("relic")}
        assert 12 in tiers  # relic 10, the maximum
        assert all(convert_relic_tier(tier) is not None for tier in tiers)

    @pytest.mark.parametrize("value", [None, True, 1.0])
    def test_invalid_type_raises(self, value: Any):
        with pytest.raises(SwgohComlinkValueError, match="relic_tier"):
            convert_relic_tier(value)


# ── _arena ──────────────────────────────────────────────────────────────


class TestGetMaxRankJump:
    @pytest.mark.parametrize(
        ("rank", "expected"),
        [(1, 1), (5, 1), (6, 2), (10, 6), (54, 43), (55, 46), (100, 84)],
    )
    def test_max_rank_jump(self, rank, expected):

        assert get_max_rank_jump(rank) == expected


def _at(hour: int, minute: int = 0, day: int = 8) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=timezone.utc)


class TestGetArenaPayout:
    # localTimeZoneOffsetMinutes: payout is 18:00 (squad) / 19:00 (fleet) UTC moved back by the offset
    @pytest.mark.parametrize(
        ("offset", "fleet", "now", "expected"),
        [
            pytest.param(0, False, _at(12), _at(18), id="squad-anchor"),
            pytest.param(0, True, _at(12), _at(19), id="fleet-anchor"),
            # UTC+10: 19:00 local is 09:00 UTC
            pytest.param(600, True, _at(8), _at(9), id="offset-moves-payout"),
            pytest.param(0, False, _at(18), _at(18, day=9), id="at-payout-rolls-over"),
            pytest.param(0, False, _at(20), _at(18, day=9), id="passed-payout-rolls-over"),
            # US Pacific (UTC-7) fleet pays at 02:00 UTC: at 01:00 UTC the next payout is an hour away.
            pytest.param(-420, True, _at(1), _at(2), id="next-utc-day-not-skipped"),
        ],
    )
    def test_next_payout(self, offset, fleet, now, expected):
        assert get_arena_payout(offset, fleet=fleet, now=now) == expected

    def test_returns_aware_utc(self):
        assert get_arena_payout(0).tzinfo == timezone.utc

    def test_naive_now_is_local_time(self):
        now = datetime.now()
        payout = get_arena_payout(0, now=now)
        assert timedelta(0) < payout - now.astimezone() <= timedelta(days=1)


# ── _omicron ────────────────────────────────────────────────────────────

_SKILL_LIST: list[dict[str, Any]] = [
    {"id": "skill_A", "omicronMode": 8, "tier": [{"isOmicronTier": False}, {"isOmicronTier": True}]},
    {"id": "skill_B", "omicronMode": 3, "tier": [{"isOmicronTier": False}]},
    {"id": "skill_C", "omicronMode": 8, "tier": [{"isOmicronTier": True}]},
]


@pytest.mark.parametrize(
    ("select", "expected_ids"),
    [
        pytest.param(lambda: get_tw_omicrons(_SKILL_LIST), ["skill_A", "skill_C"], id="tw-mode-8"),
        pytest.param(lambda: get_tw_omicrons([]), [], id="tw-empty"),
        pytest.param(lambda: get_omicron_skills(_SKILL_LIST, 3), ["skill_B"], id="single-mode"),
        pytest.param(lambda: get_omicron_skills(_SKILL_LIST, [3, 8]), ["skill_A", "skill_B", "skill_C"], id="modes"),
        pytest.param(lambda: get_omicron_skills(_SKILL_LIST, 99), [], id="no-match"),
    ],
)
def test_omicron_skill_selection(select, expected_ids):
    assert [skill["id"] for skill in select()] == expected_ids


@pytest.mark.parametrize(
    ("skill", "expected"),
    [
        pytest.param({"tier": [{"isOmicronTier": False}, {"isOmicronTier": True}]}, 1, id="found"),
        pytest.param({"tier": [{"isOmicronTier": False}]}, None, id="none"),
    ],
)
def test_get_omicron_skill_tier(skill, expected):
    assert get_omicron_skill_tier(skill) == expected


@pytest.mark.parametrize(
    ("skills", "kwargs", "expected"),
    [
        pytest.param(_SKILL_LIST, {"skill_id": "skill_A", "skill_tier": 1}, True, id="omicron-tier"),
        # skill_A has its omicron at tier index 1, so tier 99 does not match.
        pytest.param(_SKILL_LIST, {"skill_id": "skill_A", "skill_tier": 99}, False, id="wrong-tier"),
        pytest.param(_SKILL_LIST, {"roster_unit_skill": {"id": "skill_A", "tier": 1}}, True, id="roster-unit-skill"),
        pytest.param(_SKILL_LIST, {"skill_id": "nonexistent", "skill_tier": 1}, False, id="not-in-list"),
        pytest.param([_SKILL_LIST[1]], {"skill_id": "skill_B", "skill_tier": 1}, False, id="skill-without-omicron"),
    ],
)
def test_is_omicron_skill(skills, kwargs, expected):
    assert is_omicron_skill(skills, **kwargs) is expected


@pytest.mark.parametrize(
    ("call", "match"),
    [
        pytest.param(lambda: get_tw_omicrons("not a list"), "list", id="tw-not-list"),
        pytest.param(lambda: get_omicron_skills("bad", 8), "list", id="skills-not-list"),
        pytest.param(lambda: get_omicron_skills([], "bad"), "omicron_type", id="bad-omicron-type"),
        pytest.param(lambda: get_omicron_skill_tier("not a dict"), "dictionary", id="tier-not-dict"),
        pytest.param(lambda: get_omicron_skill_tier({"id": "skill_A"}), "tier", id="tier-key-missing"),
        pytest.param(lambda: is_omicron_skill("bad", skill_id="s", skill_tier=1), "list", id="is-not-list"),
        pytest.param(lambda: is_omicron_skill([], skill_id=123, skill_tier=1), "skill_id", id="bad-skill-id"),
        pytest.param(lambda: is_omicron_skill([], skill_id="", skill_tier=0), "are required", id="no-skill-id-or-tier"),
        pytest.param(
            lambda: is_omicron_skill([], roster_unit_skill={"id": "", "tier": 0}), "Invalid", id="bad-roster-skill"
        ),
    ],
)
def test_omicron_helpers_reject_invalid_input(call, match):
    with pytest.raises(SwgohComlinkValueError, match=match):
        call()


class TestGetUnitFromSkill:
    def test_found(self):

        units = [
            {"baseId": "UNIT1", "nameKey": "Unit One", "skillReference": [{"id": "skill_X"}]},
            {"baseId": "UNIT2", "nameKey": "Unit Two", "skillReference": [{"id": "skill_Y"}]},
        ]
        result = get_unit_from_skill(units, "skill_Y")
        assert result is not None
        assert result.baseId == "UNIT2"
        assert result.nameKey == "Unit Two"

    def test_not_found(self):

        units = [{"baseId": "U1", "nameKey": "N1", "skillReference": [{"id": "s1"}]}]
        assert get_unit_from_skill(units, "nonexistent") is None

    def test_empty_skill_reference(self):

        units = [{"baseId": "U1", "nameKey": "N1", "skillReference": None}]
        assert get_unit_from_skill(units, "s1") is None

    def test_invalid_unit_list_raises(self):

        with pytest.raises(SwgohComlinkValueError, match="list"):
            get_unit_from_skill("bad", "skill")

    def test_invalid_skill_type_raises(self):

        with pytest.raises(SwgohComlinkValueError, match="string"):
            get_unit_from_skill([], 123)


# ── _game_data ──────────────────────────────────────────────────────────


class TestGetRaidLeaderboardIds:
    def test_valid_guild_campaign(self):

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

        campaign_data = [{"id": "LIGHT_SIDE"}]
        assert get_raid_leaderboard_ids(campaign_data) == []


class TestCreateLocalizedUnitNameDictionary:
    @pytest.mark.parametrize(
        ("locale", "expected"),
        [
            pytest.param(
                "# comment\nUNIT_BOSSK_NAME|Bossk\nUNIT_BOSSK_DESC|A hunter\n", {"UNIT_BOSSK_NAME": "Bossk"}, id="str"
            ),
            pytest.param(
                ["UNIT_VADER_NAME|Darth Vader", "UNIT_VADER_DESC|Sith Lord"],
                {"UNIT_VADER_NAME": "Darth Vader"},
                id="list",
            ),
            pytest.param([b"UNIT_LUKE_NAME|Luke Skywalker"], {"UNIT_LUKE_NAME": "Luke Skywalker"}, id="bytes-in-list"),
            pytest.param(
                ["UNIT_JEDIKNIGHTREVAN_NAME_V2|Jedi Knight Revan", "UNIT_BOSSK_NAME|Bossk", "UNIT_BOSSK_DESC|A hunter"],
                {"UNIT_JEDIKNIGHTREVAN_NAME_V2": "Jedi Knight Revan", "UNIT_BOSSK_NAME": "Bossk"},
                id="name-variant-suffix",
            ),
            pytest.param("# comment\nSOME_OTHER|value\nno pipe here\n", {}, id="non-unit-lines-skipped"),
        ],
    )
    def test_keeps_unit_names(self, locale, expected):
        assert create_localized_unit_name_dictionary(locale) == expected

    def test_invalid_type_raises(self):
        with pytest.raises(SwgohComlinkValueError, match="list"):
            create_localized_unit_name_dictionary(12345)


class TestGetPlayableUnits:
    def test_keeps_obtainable_seven_star_units_and_tolerates_missing_fields(self):
        units = [
            {"baseId": "PLAYABLE", "rarity": 7, "obtainable": True, "obtainableTime": "0"},
            {"baseId": "FIVE_STAR", "rarity": 5, "obtainable": True, "obtainableTime": "0"},
            {"baseId": "NOT_OBTAINABLE", "rarity": 7, "obtainable": False, "obtainableTime": "0"},
            {"baseId": "TIMED", "rarity": 7, "obtainable": True, "obtainableTime": "12345"},
            {"baseId": "OLD_DUMP", "rarity": 7, "obtainable": True},  # predates obtainableTime
            {"baseId": "ENUMS", "rarity": "SEVEN_STAR", "obtainable": True, "obtainableTime": "0"},
            {"baseId": "INT_TIME", "rarity": 7, "obtainable": True, "obtainableTime": 0},
            {"baseId": "NO_RARITY", "obtainable": True, "obtainableTime": "0"},
            {"baseId": "NO_OBTAINABLE", "rarity": 7, "obtainableTime": "0"},
            {"baseId": "GL_TEMPLATE", "rarity": 7, "obtainable": True, "obtainableTime": "4102444800000"},
        ]
        assert [u["baseId"] for u in get_playable_units(units)] == ["PLAYABLE", "OLD_DUMP", "ENUMS", "INT_TIME"]

    def test_invalid_type_raises(self):
        with pytest.raises(SwgohComlinkValueError, match="list"):
            get_playable_units("bad")


class TestGetCurrentDatacronSets:
    def test_active_sets_returned(self):

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

        with pytest.raises(SwgohComlinkValueError, match="list"):
            get_current_datacron_sets("bad")


class TestGetDatacronDismantleValue:
    @pytest.mark.parametrize(
        ("datacron", "sets", "recipes", "expected"),
        [
            pytest.param(
                {"setId": "set1", "affix": [1, 2]},
                [
                    {
                        "id": "set1",
                        "tier": [
                            {"id": 0, "dustGrantRecipeId": None},
                            {"id": 1, "dustGrantRecipeId": None},
                            {"id": 2, "dustGrantRecipeId": "recipe1"},
                        ],
                    }
                ],
                [{"id": "recipe1", "ingredients": [{"id": "mat_A", "maxQuantity": 100, "type": 3}]}],
                {"mat_A": {"quantity": 100, "type": 3}, "focused": False},
                id="normal",
            ),
            pytest.param(
                {"setId": "set1", "focused": True, "affix": [1]},
                [{"id": "set1", "focusedTier": [{"id": 1, "dustGrantRecipeId": "recipe_f"}]}],
                [{"id": "recipe_f", "ingredients": [{"id": "mat_B", "maxQuantity": 50, "type": 2}]}],
                {"mat_B": {"quantity": 50, "type": 2}, "focused": True},
                id="focused",
            ),
            pytest.param({"setId": "nope"}, [], [], {}, id="missing-set"),
            pytest.param(
                {"setId": "set1", "affix": [1]},
                [{"id": "set1", "tier": [{"id": 1, "dustGrantRecipeId": "recipe_x"}]}],
                [],
                {},
                id="missing-recipe",
            ),
            pytest.param(
                {"setId": "set1", "affix": [1]},
                [{"id": "set1", "tier": [{"id": 1, "dustGrantRecipeId": None}]}],
                [],
                {},
                id="no-dust-recipe",
            ),
        ],
    )
    def test_dismantle_value(self, datacron, sets, recipes, expected):
        assert get_datacron_dismantle_value(datacron, sets, recipes) == expected


class TestGetDatacronDismantleTotal:
    def test_aggregates_materials(self):
        datacrons = [{"setId": "set1", "affix": [1]}, {"setId": "set1", "affix": [1]}]
        sets = [{"id": "set1", "tier": [{"id": 1, "dustGrantRecipeId": "r1"}]}]
        recipes = [{"id": "r1", "ingredients": [{"id": "mat_A", "maxQuantity": 10, "type": 1}]}]
        assert get_datacron_dismantle_total(datacrons, sets, recipes) == {"mat_A": {"quantity": 20, "type": 1}}

    def test_empty_list_returns_empty(self):
        assert get_datacron_dismantle_total([], [], []) == {}


# ── _conquest ──────────────────────────────────────────────────────────


_REFRESH = 1_790_164_800  # 2026-09-23 12:00:00 UTC, in seconds as lastRefreshTime carries it


def _utc(seconds: float):

    return datetime.fromtimestamp(seconds, tz=timezone.utc)


class TestCalcCurrentStamina:
    @pytest.mark.parametrize(
        ("minutes_ago", "remaining", "pass_plus", "expected"),
        [
            pytest.param(120, 87, False, 91, id="one-point-per-30-minutes"),  # floor(120 / 30 * 1.0) + 87
            pytest.param(120, 87, True, 92, id="pass-plus"),  # floor(120 / 30 * 1.33) + 87
            pytest.param(6000, 50, False, 100, id="capped-at-100"),
        ],
    )
    def test_current_stamina(self, monkeypatch, minutes_ago, remaining, pass_plus, expected):
        monkeypatch.setattr("swgoh_comlink.helpers._conquest.time.time", lambda: _REFRESH)
        unit = {"lastRefreshTime": str(_REFRESH - minutes_ago * 60), "remainingStamina": remaining}
        assert calc_current_stamina(unit, pass_plus=pass_plus) == expected

    @pytest.mark.parametrize(
        ("unit", "match"),
        [
            pytest.param("not a dict", "dict", id="not-dict"),
            pytest.param({"lastRefreshTime": "123"}, "Invalid unit data", id="no-remaining-stamina"),
            pytest.param({"remainingStamina": 87}, "Invalid unit data", id="no-last-refresh-time"),
        ],
    )
    def test_invalid_unit_raises(self, unit, match):
        with pytest.raises(SwgohComlinkValueError, match=match):
            calc_current_stamina(unit)


class TestCalcStaminaFullTime:
    @pytest.mark.parametrize("remaining", [90, 90.0, "90"], ids=["int", "float", "str"])
    def test_one_point_per_thirty_minutes(self, remaining: Any):
        unit = {"unitId": "u1", "remainingStamina": remaining, "lastRefreshTime": str(_REFRESH)}
        assert calc_stamina_full_time(unit, now=_utc(_REFRESH + 3600)) == _utc(_REFRESH + 10 * 1800)

    def test_returns_aware_utc(self):

        result = calc_stamina_full_time({"remainingStamina": 50, "lastRefreshTime": _REFRESH})
        assert result.tzinfo == timezone.utc

    @pytest.mark.parametrize("pass_plus", [False, True])
    def test_agrees_with_calc_current_stamina(self, pass_plus: bool):
        """For every starting stamina, the unit is full at the returned time and not one second before."""
        for remaining in range(100):
            unit = {"remainingStamina": remaining, "lastRefreshTime": _REFRESH}
            full = calc_stamina_full_time(unit, pass_plus, now=_utc(_REFRESH)).timestamp()
            with patch("swgoh_comlink.helpers._conquest.time.time", return_value=full):
                assert calc_current_stamina(unit, pass_plus) == 100, remaining
            with patch("swgoh_comlink.helpers._conquest.time.time", return_value=full - 1):
                assert calc_current_stamina(unit, pass_plus) < 100, remaining

    def test_pass_plus_is_faster(self):

        unit = {"remainingStamina": 0, "lastRefreshTime": _REFRESH}
        now = _utc(_REFRESH)
        assert calc_stamina_full_time(unit, True, now=now) < calc_stamina_full_time(unit, now=now)

    def test_full_unit_returns_the_moment_it_filled(self):

        unit = {"remainingStamina": 98, "lastRefreshTime": _REFRESH}
        assert calc_stamina_full_time(unit, now=_utc(_REFRESH + 86_400)) == _utc(_REFRESH + 3600)
        assert calc_stamina_full_time({"remainingStamina": 100, "lastRefreshTime": _REFRESH}) == _utc(_REFRESH)

    @pytest.mark.parametrize("refresh", [None, 0, "", "junk"])
    def test_missing_refresh_time_counts_from_now(self, refresh: Any):

        unit: dict[str, Any] = {"remainingStamina": 99}
        if refresh is not None:
            unit["lastRefreshTime"] = refresh
        # Whole seconds, as lastRefreshTime carries them
        assert calc_stamina_full_time(unit, now=_utc(_REFRESH + 0.75)) == _utc(_REFRESH + 1800)

    def test_future_refresh_time_counts_from_now(self):

        unit = {"remainingStamina": 99, "lastRefreshTime": _REFRESH + 600}
        assert calc_stamina_full_time(unit, now=_utc(_REFRESH)) == _utc(_REFRESH + 1800)

    def test_naive_now_is_local_time(self):

        now = datetime.now()
        assert calc_stamina_full_time({"remainingStamina": 99}, now=now) == _utc(int(now.timestamp()) + 1800)

    @pytest.mark.parametrize(
        "unit",
        [
            None,
            [],
            {"lastRefreshTime": _REFRESH},
            {"remainingStamina": "full"},
            {"remainingStamina": True},
            {"remainingStamina": float("inf"), "lastRefreshTime": _REFRESH},
            {"remainingStamina": float("nan"), "lastRefreshTime": _REFRESH},
        ],
        ids=["none", "list", "no-stamina", "junk-stamina", "bool", "inf", "nan"],
    )
    def test_invalid_unit_raises(self, unit: Any):

        with pytest.raises(SwgohComlinkValueError, match="calc_stamina_full_time"):
            calc_stamina_full_time(unit)


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

        feats = get_conquest_feats(_CONQUEST_DEFS, _CHALLENGES, difficulty="Hard")
        assert feats[0]["reward_artifact"] == "artifact_x"
        assert feats[1]["scope"] == "S0"

    def test_enum_name_reward_types(self):

        (feat,) = get_conquest_feats(_CONQUEST_DEFS, _CHALLENGES, difficulty="normal")
        assert feat["keycards"] == 1

    def test_feats_without_a_kind_token(self):

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

        with pytest.raises(SwgohComlinkValueError):
            get_conquest_feats(*args, **kwargs)


# ── _events ─────────────────────────────────────────────────────────────

_EVENTS_NOW_MS = 1_790_164_800_000  # 2026-09-23 12:00 UTC
_DAY_MS = 86_400_000
_PERMANENT_END = "4945772573272"  # 2126-09-24: how the game spells "never ends"


def _run(start: int, end: int | str, run_id: str | None = None, **extra: Any) -> dict[str, Any]:
    run: dict[str, Any] = {"startTime": str(start), "endTime": str(end), **extra}
    if run_id is not None:
        run["id"] = run_id
    return run


def _events_now():

    return datetime.fromtimestamp(_EVENTS_NOW_MS / 1000, tz=timezone.utc)


_NODE = {"campaignId": "EVENTS", "campaignMapId": "JOURNEY", "campaignNodeDifficulty": 4, "campaignNodeId": "JM"}
_GAME_EVENTS: dict[str, Any] = {
    "gameEvent": [
        {
            "id": "EVENT_JOURNEY_MANDALORIAN",
            "nameKey": "EVENT_JOURNEY_MANDALORIAN_NAME",
            "type": 3,
            "instance": [_run(1_476_532_800_000, _PERMANENT_END, "J1", campaignElementIdentifier=_NODE)],
        },
        {
            "id": "EVENT_MARQUEE_JAXXON",
            "nameKey": "EVENT_MARQUEE_JAXXON_NAME_V2",
            "type": 1,
            "instance": [
                _run(_EVENTS_NOW_MS - _DAY_MS, _EVENTS_NOW_MS + 2 * _DAY_MS, "LATER_END"),
                _run(_EVENTS_NOW_MS - 2 * _DAY_MS, _EVENTS_NOW_MS + _DAY_MS, "EARLIER_END"),
            ],
        },
        {
            "id": "EVENT_MARQUEE_THERONIN",
            "nameKey": "EVENT_MARQUEE_THERONIN_NAME",
            "type": 1,
            "instance": [
                _run(_EVENTS_NOW_MS + 20 * _DAY_MS, _EVENTS_NOW_MS + 27 * _DAY_MS, "SECOND"),
                _run(_EVENTS_NOW_MS + 13 * _DAY_MS, _EVENTS_NOW_MS + 20 * _DAY_MS, "FIRST"),
            ],
        },
        {
            "id": "challenge_XP",
            "nameKey": "EVENT_XP_NAME",
            "type": 1,
            "instance": [_run(_EVENTS_NOW_MS - 3 * _DAY_MS, _EVENTS_NOW_MS - _DAY_MS)],
        },
        {
            "id": "EVENT_SMUGGLERS_RUN",
            "nameKey": "EVENT_SMUGGLERS_RUN_NAME",
            "type": 1,
            "instance": [_run(_EVENTS_NOW_MS + _DAY_MS, _EVENTS_NOW_MS + 2 * _DAY_MS)],
        },
    ]
}
_EVENT_LOC = {
    "EVENT_JOURNEY_MANDALORIAN_NAME": "THE MANDALORIAN\\n[c][FFC891]Hero's Journey[-][/c]",
    "EVENT_MARQUEE_JAXXON_NAME_V2": "ACTION JAXXON\\n[c][FFC891]Special Marquee Event[-][/c]",
    "EVENT_MARQUEE_THERONIN_NAME": "THE WANDERER'S BLADE\\n[c][FFC891]Special Marquee Event[-][/c]",
    "EVENT_SMUGGLERS_RUN_NAME": "SMUGGLER'S RUN II\\n[c][FFC891]Resource Event[-][/c]",
}


class TestGetEventSchedule:
    def test_live_then_upcoming_soonest_first(self):

        schedule = get_event_schedule(_GAME_EVENTS, _EVENT_LOC, now=_events_now())
        assert [(e["event_id"], e["status"]) for e in schedule] == [
            ("EVENT_JOURNEY_MANDALORIAN", "live"),
            ("EVENT_MARQUEE_JAXXON", "live"),
            ("EVENT_SMUGGLERS_RUN", "upcoming"),
            ("EVENT_MARQUEE_THERONIN", "upcoming"),
        ]

    def test_names_split_the_banner_and_keep_the_game_case(self):

        schedule = get_event_schedule(_GAME_EVENTS, _EVENT_LOC, now=_events_now())
        assert [(e["title"], e["subtitle"], e["name"]) for e in schedule] == [
            ("THE MANDALORIAN", "Hero's Journey", "THE MANDALORIAN - Hero's Journey"),
            ("ACTION JAXXON", "Special Marquee Event", "ACTION JAXXON - Special Marquee Event"),
            ("SMUGGLER'S RUN II", "Resource Event", "SMUGGLER'S RUN II - Resource Event"),
            ("THE WANDERER'S BLADE", "Special Marquee Event", "THE WANDERER'S BLADE - Special Marquee Event"),
        ]

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("DUEL OF THE FATES\\n[c][FFC891]Assault Battles[-][/c]", ("DUEL OF THE FATES", "Assault Battles")),
            ("IMPERIAL TIE BOMBER\\n[c][FFC891]Ship Event[-][/c]", ("IMPERIAL TIE BOMBER", "Ship Event")),
            ("TIER II (VERY HARD)", ("TIER II (VERY HARD)", None)),
            ("Terrible Tings", ("Terrible Tings", None)),
            ("ONE\\nTWO\\nthree", ("ONE", "TWO - three")),
            ("[c][FFC891][-][/c]", ("", None)),
        ],
    )
    def test_event_name_formatting(self, text: str, expected: tuple[str, str | None]):

        assert _event_name(text) == expected

    def test_without_localization_uses_name_key(self):

        schedule = get_event_schedule(_GAME_EVENTS["gameEvent"], now=_events_now())
        assert schedule[0]["name"] == "EVENT_JOURNEY_MANDALORIAN_NAME"
        assert (schedule[0]["title"], schedule[0]["subtitle"]) == ("EVENT_JOURNEY_MANDALORIAN_NAME", None)
        no_key = get_event_schedule([{"id": "EV", "instance": [_run(0, _PERMANENT_END)]}], now=_events_now())
        assert (no_key[0]["name"], no_key[0]["title"], no_key[0]["subtitle"]) == ("EV", "EV", None)

    def test_permanent_event_has_no_end(self):

        journey = get_event_schedule(_GAME_EVENTS, now=_events_now())[0]
        assert journey["end"] is None
        assert journey["start"] == datetime(2016, 10, 15, 12, tzinfo=timezone.utc)
        assert journey["instance_id"] == "J1"
        assert journey["type"] == 3
        assert journey["campaign_element"] == _NODE

    def test_overlapping_runs_pick_the_one_ending_first(self):

        jaxxon = get_event_schedule(_GAME_EVENTS, now=_events_now())[1]
        assert jaxxon["instance_id"] == "EARLIER_END"
        assert jaxxon["end"] is not None and jaxxon["end"].tzinfo == timezone.utc
        assert jaxxon["end"].timestamp() * 1000 == _EVENTS_NOW_MS + _DAY_MS

    def test_upcoming_event_uses_its_next_run(self):

        ronin = get_event_schedule(_GAME_EVENTS, now=_events_now())[-1]
        assert ronin["instance_id"] == "FIRST"
        assert ronin["start"].timestamp() * 1000 == _EVENTS_NOW_MS + 13 * _DAY_MS

    def test_live_only(self):

        schedule = get_event_schedule(_GAME_EVENTS, now=_events_now(), include_upcoming=False)
        assert {e["status"] for e in schedule} == {"live"}
        assert len(schedule) == 2

    def test_run_boundaries(self):

        events = [{"id": "EV", "instance": [_run(_EVENTS_NOW_MS, _EVENTS_NOW_MS + _DAY_MS)]}]
        assert get_event_schedule(events, now=_events_now())[0]["status"] == "live"
        assert get_event_schedule(events, now=_events_now() + timedelta(days=1)) == []

    def test_integer_times_and_unusable_runs(self):

        events: list[Any] = [
            {"id": "INT", "instance": [{"startTime": _EVENTS_NOW_MS - 1, "endTime": _EVENTS_NOW_MS + 1}]},
            {"id": "NO_END", "instance": [{"startTime": str(_EVENTS_NOW_MS + _DAY_MS)}]},
            {"id": "NO_RUNS", "instance": None},
            "not an event",
        ]
        assert [e["event_id"] for e in get_event_schedule(events, now=_events_now())] == ["INT"]

    @pytest.mark.parametrize("events", [None, "events", {"events": []}])
    def test_invalid_events_raises(self, events: Any):

        with pytest.raises(SwgohComlinkValueError, match="get_event_schedule"):
            get_event_schedule(events)

    def test_invalid_localization_raises(self):

        localization: Any = ["not", "a", "dict"]
        with pytest.raises(SwgohComlinkValueError, match="localization"):
            get_event_schedule(_GAME_EVENTS, localization)


# ── _guild (pure functions) ─────────────────────────────────────────────


def _guild_payload(**overrides: Any) -> dict[str, Any]:
    guild: dict[str, Any] = {
        "profile": {
            "id": "g1",
            "name": "Test Guild",
            "memberCount": 48,
            "memberMax": 50,
            "guildGalacticPower": "755564483",
        },
        "member": [
            {
                "playerId": "p1",
                "playerName": "Leader",
                "memberLevel": 4,
                "galacticPower": "11000000",
                "guildJoinTime": "1655938556",
                "lastActivityTime": "1790164800000",
            },
            {"playerId": "p2", "playerName": "Officer", "memberLevel": "GUILD_OFFICER", "guildJoinTime": 1579804504},
            {"playerId": "p3", "playerName": "New", "memberLevel": 2, "guildJoinTime": "0", "lastActivityTime": "0"},
        ],
        "recentTerritoryBattleResult": [
            {"definitionId": "t05D", "totalStars": 40},
            {"definitionId": "t05D", "totalStars": "47"},
        ],
        "recentTerritoryWarResult": [
            {
                "territoryWarId": "TW1",
                "score": "27361",
                "opponentScore": "11916",
                "opponentGuildProfile": {"name": "A"},
            },
            {"territoryWarId": "TW2", "score": "12842", "opponentScore": "26567"},
            {"territoryWarId": "TW3", "score": 100, "opponentScore": 100},
        ],
        "recentRaidResult": [
            {
                "raidId": "order66",
                "guildRewardScore": "33500000",
                "raidMember": [
                    {"playerId": "p1", "memberProgress": "13500000"},
                    {"playerId": "p2", "memberProgress": "20000000"},
                ],
            }
        ],
    }
    guild.update(overrides)
    return guild


class TestGetGuildActivity:
    def test_profile_totals(self):

        activity = get_guild_activity(_guild_payload())
        assert (activity["guild_id"], activity["name"]) == ("g1", "Test Guild")
        assert (activity["member_count"], activity["member_max"]) == (48, 50)
        assert activity["galactic_power"] == 755564483

    def test_wrapped_response_is_accepted(self):

        assert get_guild_activity({"guild": _guild_payload()}) == get_guild_activity(_guild_payload())

    def test_best_territory_battle_is_the_most_stars(self):

        assert get_guild_activity(_guild_payload())["best_territory_battle"] == {
            "definition_id": "t05D",
            "total_stars": 47,
        }

    def test_territory_war_record(self):

        activity = get_guild_activity(_guild_payload())
        assert [(w["territory_war_id"], w["result"]) for w in activity["territory_wars"]] == [
            ("TW1", "win"),
            ("TW2", "loss"),
            ("TW3", "tie"),
        ]
        assert activity["territory_wars"][0]["score"] == 27361
        assert activity["territory_wars"][0]["opponent_name"] == "A"
        assert activity["territory_wars"][1]["opponent_name"] is None
        assert (activity["territory_war_wins"], activity["territory_war_losses"]) == (1, 1)

    def test_last_raid_and_member_scores(self):

        activity = get_guild_activity(_guild_payload())
        raid = activity["last_raid"]
        assert raid is not None
        assert raid["raid_id"] == "order66"
        assert raid["guild_score"] == 33_500_000 == sum(raid["member_scores"].values())
        assert [m["raid_score"] for m in activity["members"]] == [13_500_000, 20_000_000, None]

    def test_members(self):

        leader, officer, new = get_guild_activity(_guild_payload())["members"]
        assert (leader["player_id"], leader["name"], leader["galactic_power"]) == ("p1", "Leader", 11_000_000)
        # guildJoinTime is in seconds, lastActivityTime in milliseconds
        assert leader["joined"] == datetime(2022, 6, 22, 22, 55, 56, tzinfo=timezone.utc)
        assert leader["last_activity"] == datetime(2026, 9, 23, 12, tzinfo=timezone.utc)
        assert officer["joined"] == datetime(2020, 1, 23, 18, 35, 4, tzinfo=timezone.utc)
        assert officer["last_activity"] is None
        assert new["joined"] is None and new["last_activity"] is None

    @pytest.mark.parametrize(
        ("member_level", "expected"),
        [
            (1, (1, "Pending")),
            (2, (2, "Member")),
            (3, (3, "Officer")),
            (4, (4, "Leader")),
            ("4", (4, "Leader")),
            ("GUILD_PENDING", (1, "Pending")),
            ("GUILD_MEMBER", (2, "Member")),
            ("GUILD_OFFICER", (3, "Officer")),
            ("GUILD_LEADER", (4, "Leader")),
            (0, (None, None)),
            (None, (None, None)),
            ([4], (None, None)),
        ],
    )
    def test_member_roles(self, member_level: Any, expected: tuple[Any, Any]):

        (member,) = get_guild_activity({"member": [{"playerId": "p", "memberLevel": member_level}]})["members"]
        assert (member["member_level"], member["role"]) == expected

    def test_without_recent_activity(self):

        activity = get_guild_activity(
            _guild_payload(recentTerritoryBattleResult=[], recentTerritoryWarResult=None, recentRaidResult=[])
        )
        assert activity["best_territory_battle"] is None
        assert activity["territory_wars"] == []
        assert (activity["territory_war_wins"], activity["territory_war_losses"]) == (0, 0)
        assert activity["last_raid"] is None
        assert all(m["raid_score"] is None for m in activity["members"])

    def test_member_count_falls_back_to_roster(self):

        activity = get_guild_activity(_guild_payload(profile={"id": "g1"}))
        assert activity["member_count"] == 3
        assert (activity["name"], activity["member_max"], activity["galactic_power"]) == ("", 0, 0)

    @pytest.mark.parametrize("guild", [None, [], "guild"])
    def test_invalid_guild_raises(self, guild: Any):

        with pytest.raises(SwgohComlinkValueError, match="get_guild_activity"):
            get_guild_activity(guild)


# ── _game_config ────────────────────────────────────────────────────────

# Shaped like get_game_metadata(): every config value is a string, and a key can be listed twice
_METADATA: dict[str, Any] = {
    "config": [
        {"key": "max-conquest-currency", "value": "3500"},
        {"key": "stat-mod-max-storage", "value": "500"},
        {"key": "stat-mod-max-level", "value": "15"},
        {"key": "squad-preset-tab-total-max-squads-saved", "value": "200"},
        {"key": "stat-mod-highlight-stat", "value": "SPEED"},
        {"key": "conquest-energy-refresh-daily-cap", "value": "CONQUEST_ENERGY_REFRESH_DAILY_CAP"},
        {"key": "stat-mod-max-level", "value": "16"},
        {"key": "no-value"},
    ],
    "latestGamedataVersion": "0.40.6:abc",
    "latestLocalizationBundleVersion": "xyz",
}


class TestGetGameConfig:
    def test_all_keys(self):
        # The duplicate stat-mod-max-level keeps its first value; a key without a value is dropped.
        assert get_game_config(_METADATA) == {
            "max-conquest-currency": "3500",
            "stat-mod-max-storage": "500",
            "stat-mod-max-level": "15",
            "squad-preset-tab-total-max-squads-saved": "200",
            "stat-mod-highlight-stat": "SPEED",
            "conquest-energy-refresh-daily-cap": "CONQUEST_ENERGY_REFRESH_DAILY_CAP",
        }

    @pytest.mark.parametrize(
        ("source", "key", "expected"),
        [
            pytest.param(_METADATA, "stat-mod-max-storage", "500", id="single-key"),
            pytest.param(_METADATA, "stat-mod-max-level", "15", id="duplicate-keeps-first"),
            pytest.param(_METADATA, "missing-key", None, id="missing"),
            pytest.param(_METADATA, "no-value", None, id="no-value"),
            pytest.param(_METADATA["config"], "max-conquest-currency", "3500", id="config-list"),
        ],
    )
    def test_single_key(self, source, key, expected):
        assert get_game_config(source, key) == expected

    @pytest.mark.parametrize("metadata", [None, "config", {"latestGamedataVersion": "x"}, {"config": "x"}])
    def test_invalid_metadata_raises(self, metadata: Any):
        with pytest.raises(SwgohComlinkValueError, match="get_game_config"):
            get_game_config(metadata)


class TestGetGameConfigInt:
    @pytest.mark.parametrize(
        ("key", "default", "expected"),
        [
            ("max-conquest-currency", None, 3500),
            ("squad-preset-tab-total-max-squads-saved", None, 200),
            *(
                pytest.param(key, default, default, id=f"{key}-default-{default}")
                for key in ["missing-key", "stat-mod-highlight-stat", "conquest-energy-refresh-daily-cap"]
                for default in (None, 0)
            ),
        ],
    )
    def test_reads_numeric_values(self, key: str, default: int | None, expected: int | None):
        args = (_METADATA, key) if default is None else (_METADATA, key, default)
        assert get_game_config_int(*args) == expected

    def test_invalid_metadata_raises(self):
        with pytest.raises(SwgohComlinkValueError, match="get_game_config_int"):
            get_game_config_int({}, "max-conquest-currency")


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
    def test_reads_every_key_family_and_picks_the_authoritative_definition(self):
        effects = get_named_effects(_EFFECT_LOC)
        assert list(effects) == sorted(effects)
        assert effects == {
            "Concussion Mine": {
                "name": "Concussion Mine",
                "description": "Deals damage",
                "key": "Battleeffect_ConcussionMine",
            },
            # The lowest tier wins.
            "Demoralized": {"name": "Demoralized", "description": "tier 0", "key": "DEMORALIZED_DEBUFF_TIER0"},
            "Fear": {"name": "Fear", "description": "Miss the next turn", "key": "FEAR_DEBUFF_DESC"},
            "Insight": {"name": "Insight", "description": "additional effects", "key": "MOFFGIDEON_INSIGHT_V2"},
            # BattleEffect_ beats the generic OVERCHARGE_BUFF_DESC; the colon may follow the closing tags.
            "Overcharge": {
                "name": "Overcharge",
                "description": "Protection Temporarily Increased",
                "key": "BattleEffect_Overcharge",
            },
            "Potency Up": {
                "name": "Potency Up",
                "description": "Increased chance to apply detrimental effects",
                "key": "BattleEffect_PotencyUp",
            },
            # The newest _V<n> wins.
            "Provoked": {
                "name": "Provoked",
                "description": "+100% counter chance\nnext line",
                "key": "BattleEffect_Provoked_V2",
            },
            "VIP": {"name": "VIP", "description": "gain bonuses", "key": "50RT_VIP_ALLY"},
            "Vulnerable": {"name": "Vulnerable", "description": "current", "key": "BattleEffect_Vulnerable_V2"},
        }

    def test_invalid_input_raises(self):
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

        assert as_int(value) == expected

    @pytest.mark.parametrize("value", [None, "", "abc", "1.5", True, False, [], {}, float("inf"), float("nan")])
    def test_unreadable_returns_default(self, value: Any):

        assert as_int(value) == 0
        assert as_int(value, default=-1) == -1


@pytest.mark.parametrize(
    ("value", "kwargs", "expected"),
    [
        ("Rebels", {}, "Rebels"),
        ("", {}, ""),
        (42, {}, ""),
        (None, {}, ""),
        ([], {}, ""),
        (None, {"default": "?"}, "?"),
    ],
)
def test_as_str_only_passes_strings(value: Any, kwargs: dict[str, str], expected: str):
    assert as_str(value, **kwargs) == expected


@pytest.mark.parametrize(
    ("value", "kwargs", "expected"),
    [
        ("O1700000000000:1", {}, "O1700000000000:1"),
        (2, {}, "2"),
        (0, {}, "0"),
        ("", {}, ""),
        (None, {}, ""),
        (True, {}, ""),
        (1.5, {}, ""),
        (None, {"default": "none"}, "none"),
    ],
)
def test_as_id_reads_string_or_int(value: Any, kwargs: dict[str, str], expected: str):
    assert as_id(value, **kwargs) == expected


class TestAsScalar:
    @pytest.mark.parametrize(
        ("value", "expected"), [(3, 3), (0, 0), ("CHARACTER", "CHARACTER"), (True, None), (None, None), (1.5, None)]
    )
    def test_keeps_int_or_str(self, value: Any, expected: int | str | None):

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
    def test_seconds_and_milliseconds_as_aware_utc(self, value: Any, expected: datetime):
        moment = as_epoch(value)
        # Aware datetimes compare by instant, so check the zone separately.
        assert moment == expected
        assert moment is not None and moment.tzinfo is timezone.utc

    @pytest.mark.parametrize("value", [None, 0, "0", "", "-5", -1, "abc", True, "99999999999999999999"])
    def test_no_time_returns_none(self, value: Any):
        assert as_epoch(value) is None

    def test_example_player_times(self, example_player):
        assert as_epoch(example_player["lastActivityTime"]) == datetime(2026, 2, 8, 1, 50, 37, tzinfo=timezone.utc)
        assert all(as_epoch(season["joinTime"]) for season in example_player["seasonStatus"])


class TestAsList:
    def test_list_is_returned_as_is(self):

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

        assert base_id(value) == expected

    def test_example_player_roster(self, example_player):
        player = example_player
        ids = {base_id(unit["definitionId"]) for unit in player["rosterUnit"]}
        assert "MAGMATROOPER" in ids
        assert not any(":" in unit_id for unit_id in ids)


# No <Type>_DEFAULT member, and one member is another's last word: a lower-case member name must
# not also be read as a decoder-style name for that last word.
_RESPONSE_CODES = {"OK": 0, "SERVER_ERROR": 1, "ERROR": 2, "FEATURE_SUSPENDED": 3, "SUSPENDED": 4}
_METADATA_REQUEST_TYPES = {"MetadataRequestType_DEFAULT": 0, "DEFAULT": 1, "CLIENT_PARAMS": 2}


class TestParseEnum:
    @pytest.mark.parametrize(
        ("value", "members", "kwargs", "expected"),
        [
            # Every spelling of a member of an enum with a <Type>_DEFAULT member
            *(
                pytest.param(value, _CURRENCY, {}, expected, id=f"currency-{value!r}")
                for value, expected in [
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
                ]
            ),
            # No <Type>_DEFAULT member: any type half is accepted unless enum_name is given.
            pytest.param("CAMPAIGNNODEDIFFICULTY_NORMALDIFF", _DIFFICULTY, {}, "NORMAL_DIFF", id="decoder-any-type"),
            pytest.param("OTHER_NORMALDIFF", _DIFFICULTY, {}, "NORMAL_DIFF", id="decoder-other-type"),
            pytest.param(
                "CAMPAIGNNODEDIFFICULTY_NORMALDIFF",
                _DIFFICULTY,
                {"enum_name": "CampaignNodeDifficulty"},
                "NORMAL_DIFF",
                id="decoder-named-type",
            ),
            pytest.param(
                "OTHER_NORMALDIFF", _DIFFICULTY, {"enum_name": "CampaignNodeDifficulty"}, None, id="decoder-wrong-type"
            ),
            *(
                pytest.param(value, _RESPONSE_CODES, {}, expected, id=f"case-variant-{value}")
                for value, expected in [
                    ("server_error", "SERVER_ERROR"),
                    ("Server_Error", "SERVER_ERROR"),
                    ("SERVER_ERROR", "SERVER_ERROR"),
                    ("error", "ERROR"),
                    ("feature_suspended", "FEATURE_SUSPENDED"),
                    # Upper-case with one underscore is still read as a decoder-style name
                    ("RESPONSECODE_SUSPENDED", "SUSPENDED"),
                ]
            ),
            # "DEFAULT" is both a member and the <Type>_DEFAULT suffix.
            pytest.param("METADATAREQUESTTYPE_DEFAULT", _METADATA_REQUEST_TYPES, {}, None, id="ambiguous"),
            pytest.param("DEFAULT", _METADATA_REQUEST_TYPES, {}, "DEFAULT", id="ambiguous-exact-member"),
            pytest.param(
                "METADATAREQUESTTYPE_CLIENTPARAMS", _METADATA_REQUEST_TYPES, {}, "CLIENT_PARAMS", id="unambiguous"
            ),
            pytest.param(
                "metadatarequesttype_default",
                _METADATA_REQUEST_TYPES,
                {},
                "MetadataRequestType_DEFAULT",
                id="lower-case-type-default",
            ),
            pytest.param(1, {"OLD_NAME": 1, "NEW_NAME": 1}, {}, "OLD_NAME", id="alias-returns-first-name"),
            pytest.param("-1", {"ALL": -1, "NONE": 0}, {}, "ALL", id="negative-number"),
        ],
    )
    def test_reads_member_names(self, value: Any, members: dict[str, int], kwargs: dict[str, str], expected):
        assert parse_enum(value, members, **kwargs) == expected

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
        assert parse_enum(value, _CURRENCY) is None

    @pytest.mark.parametrize("members", [None, [], "CurrencyType"])
    def test_invalid_members_raises(self, members: Any):
        with pytest.raises(SwgohComlinkValueError, match=r"parse_enum\(\)"):
            parse_enum(16, members)


def test_wire_docstring_examples():

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
    "playerTitle": [
        {"id": "PLAYERTITLE_GRANDARENA_INTRO", "nameKey": "PLAYERTITLE_GRANDARENA_INTRO_NAME"},
        {"id": "PLAYERTITLE_NO_NAME", "nameKey": ""},
    ],
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
        # Unreadable rarities are shown as "?".
        {"id": "unreadable", "slot": [2], "setId": "4", "minRarity": True, "maxRarity": None, "minTier": 1,
         "maxTier": 1},
    ],
}  # fmt: skip


class TestItemTypeConstants:
    def test_tables(self):

        assert ITEM_TYPES[7] == "MATERIAL"
        assert ITEM_TYPES[16] == "MYSTERY_STAT_MOD"
        assert CURRENCY_TYPES[1] == "GRIND"
        assert CURRENCY_NAMES[CURRENCY_TYPES[41]] == "Micro Attenuators"
        # Every currency member has a display name.
        assert set(CURRENCY_NAMES) == set(CURRENCY_TYPES.values())


class TestGetDataDiscNames:
    def test_joins_through_the_records_own_name_key(self):

        discs = get_data_disc_names(_ITEM_GAME_DATA["artifactDefinition"], _ITEM_LOC)
        assert discs == {"artifact_guard_and_pentrate_3_cost_rare": "Guard and Penetrate"}

    def test_without_localization_returns_name_keys(self):

        discs = get_data_disc_names(_ITEM_GAME_DATA["artifactDefinition"])
        assert discs["artifact_guard_and_pentrate_3_cost_rare"] == "ARTIFACT_GURAD_AND_PENTRATE_3_COST_RARE_NAME"

    def test_invalid_input_raises(self):

        not_a_list: Any = {}
        with pytest.raises(SwgohComlinkValueError, match="get_data_disc_names"):
            get_data_disc_names(not_a_list)
        not_a_dict: Any = []
        with pytest.raises(SwgohComlinkValueError):
            get_data_disc_names([], not_a_dict)


class TestGetPlayerTitleNames:
    def test_names_are_localized_and_markup_free(self):

        titles = [*_ITEM_GAME_DATA["playerTitle"], {"id": "PLAYERTITLE_NEW", "nameKey": "PLAYERTITLE_NEW_NAME"}, {}]
        result = get_player_title_names(titles, _ITEM_LOC)
        assert result == {"PLAYERTITLE_GRANDARENA_INTRO": "Fight Me", "PLAYERTITLE_NEW": "PLAYERTITLE_NEW_NAME"}

    def test_invalid_input_raises(self):

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

        catalog = get_mod_catalog(self._STAT_MODS, _ITEM_GAME_DATA["statModSet"])
        assert catalog["sets"]["3"]["name"] == MOD_SET_IDS["3"]
        assert catalog["definitions"]["451"]["set_name"] == MOD_SET_IDS["4"]

    def test_invalid_input_raises(self):

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
            (16, "unreadable", "?-dot Speed Square mod (E)"),
        ],
    )
    def test_names_each_item_type(self, item_type: Any, item_id: Any, expected: str):

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
            (17, "PLAYERTITLE_NO_NAME"),  # an empty name key resolves to nothing
            ("NOT_AN_ITEM_TYPE", "016"),
            (None, "016"),
        ],
    )
    def test_unresolved_returns_default(self, item_type: Any, item_id: str):

        names = ItemNames(_ITEM_GAME_DATA, _ITEM_LOC)
        assert names.get(item_type, item_id) is None
        assert names.get(item_type, item_id, "fallback") == "fallback"

    def test_missing_collections_resolve_to_nothing(self):

        names = ItemNames({}, _ITEM_LOC)
        assert names.get(7, "016") is None
        assert names.get(3, "GRIND") == "Credits"

    def test_without_localization_returns_keys(self):

        names = ItemNames(_ITEM_GAME_DATA)
        assert names.get(17, "PLAYERTITLE_GRANDARENA_INTRO") == "PLAYERTITLE_GRANDARENA_INTRO_NAME"
        # Mystery mods fall back to the English set names.
        assert names.get(16, "35155") == "5-dot Defense Square mod (A)"

    @pytest.mark.parametrize(
        ("args", "match"),
        [
            pytest.param(([],), "game_data", id="game-data-not-dict"),
            pytest.param(({"material": {}},), "material", id="collection-not-list"),
            pytest.param(({}, []), "localization", id="localization-not-dict"),
        ],
    )
    def test_invalid_input_raises(self, args: tuple[Any, ...], match: str):
        with pytest.raises(SwgohComlinkValueError, match=match):
            ItemNames(*args)


def _recorded_enums() -> dict[str, Any]:
    """The ItemType and CurrencyType groups of a real get_enums() response (game data 0.40.6)."""

    return json.loads((_RESOURCES / "enums-item-currency.json").read_text())


class TestItemNamesLiveEnums:
    def test_snapshots_match_recorded_get_enums(self):

        enums = _recorded_enums()
        for snapshot, group in ((ITEM_TYPES, "ItemType"), (CURRENCY_TYPES, "CurrencyType")):
            live = {number: name for name, number in enums[group].items() if name != f"{group}_DEFAULT"}
            assert snapshot == live, f"{group} snapshot is out of date with get_enums()"

    def test_live_enums_name_a_new_currency(self):

        enums = _recorded_enums()
        enums["CurrencyType"]["GUILD_RAID_CURRENCY_13"] = 99
        live = ItemNames(_ITEM_GAME_DATA, _ITEM_LOC, enums=enums)
        snapshot = ItemNames(_ITEM_GAME_DATA, _ITEM_LOC)

        assert live.get(3, "99") == "Guild Raid Currency 13"
        assert live.get("CURRENCY", "GUILD_RAID_CURRENCY_13") == "Guild Raid Currency 13"
        # Curated names still win, and names that are not CurrencyType members stay unresolved.
        assert live.get(3, "GRIND") == "Credits"
        assert live.get(3, "NOT_A_CURRENCY") is None
        # Without the live table the new currency is unknown.
        assert snapshot.get(3, "99") is None
        assert snapshot.get(3, "GUILD_RAID_CURRENCY_13") is None

    def test_live_enums_recognise_a_new_item_type(self):

        live = ItemNames(_ITEM_GAME_DATA, enums={"ItemType": {"FUTURE_ITEM": 40}})
        snapshot = ItemNames(_ITEM_GAME_DATA)
        rewards = [{"type": 40, "id": "", "maxQuantity": 1}, {"type": "FUTURE_ITEM", "id": "", "maxQuantity": 1}]

        assert live.item_type_number("FUTURE_ITEM") == 40
        assert live.item_type_name(40) == "FUTURE_ITEM"
        assert [(r["item_type"], r["name"]) for r in get_named_rewards(rewards, live)] == [
            (40, "FUTURE_ITEM"),
            (40, "FUTURE_ITEM"),
        ]
        assert snapshot.item_type_number("FUTURE_ITEM") is None
        assert [(r["item_type"], r["name"]) for r in get_named_rewards(rewards, snapshot)] == [
            (40, "40"),
            ("FUTURE_ITEM", "FUTURE_ITEM"),
        ]

    def test_default_members_are_not_names(self):

        names = ItemNames(_ITEM_GAME_DATA, enums=_recorded_enums())

        assert names.item_type_name(0) is None
        assert names.item_type_number("ItemType_DEFAULT") is None
        assert names.get(3, "0") is None
        (reward,) = get_named_rewards([{"type": 0, "id": "", "maxQuantity": 1}], names)
        assert (reward["item_type"], reward["name"]) == (0, "0")

    @pytest.mark.parametrize("enums", [["ItemType"], {"ItemType": ["MATERIAL"]}, {"CurrencyType": "GRIND"}])
    def test_invalid_enums_raise(self, enums: Any):

        with pytest.raises(SwgohComlinkValueError, match="enums"):
            ItemNames(_ITEM_GAME_DATA, enums=enums)


class TestGetNamedRewards:
    def test_flat_and_conditional_items(self):

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

    @pytest.mark.parametrize(
        ("rewards", "item_names", "match"),
        [
            pytest.param({}, ItemNames({}), "get_named_rewards", id="rewards-not-list"),
            pytest.param([], {}, "item_names", id="item-names-wrong-type"),
        ],
    )
    def test_invalid_input_raises(self, rewards: Any, item_names: Any, match: str):
        with pytest.raises(SwgohComlinkValueError, match=match):
            get_named_rewards(rewards, item_names)

    def test_item_without_type_and_non_dict_bucket_items(self):

        rewards: list[Any] = [
            {"bucketItem": ["not an item", None, {"id": "x"}, {"type": 6}], "requirementId": "req"},
        ]
        result = get_named_rewards(rewards, ItemNames(_ITEM_GAME_DATA, _ITEM_LOC))
        assert [(r["item_type"], r["id"], r["name"]) for r in result] == [(None, "x", "x"), (6, "", "XP")]


class TestItemHelpersRobustness:
    def test_non_dict_records_are_skipped(self):

        junk: list[Any] = ["x", None]
        assert get_data_disc_names([*junk, *_ITEM_GAME_DATA["artifactDefinition"]], _ITEM_LOC) == {
            "artifact_guard_and_pentrate_3_cost_rare": "Guard and Penetrate"
        }
        catalog = get_mod_catalog([*junk, {"id": "1", "setId": "4", "slot": 2, "rarity": 5}], junk)
        assert catalog["sets"] == {} and list(catalog["definitions"]) == ["1"]
        game_data = {key: [*junk, *records] for key, records in _ITEM_GAME_DATA.items()}
        names = ItemNames(game_data, _ITEM_LOC)
        assert names.get(7, "unitshard_GLLEIA") == "Leia Organa"
        assert names.get(2, "ANAKINKNIGHT") == "Jedi Knight Anakin"
        assert names.get(16, "35155") == "5-dot Defense Square mod (A)"

    def test_no_star_rarity_enum(self):

        catalog = get_mod_catalog([{"id": "1", "rarity": "NO_STAR"}, {"id": "2", "rarity": 8}], [])
        assert catalog["definitions"]["1"]["rarity"] == catalog["definitions"]["2"]["rarity"] == 8
        mod = {"id": "m", "slot": [2], "setId": "4", "minRarity": "NO_STAR", "maxRarity": 8, "minTier": 1, "maxTier": 1}
        assert ItemNames({"mysteryStatMod": [mod]}).get(16, "m") == "8-dot Speed Square mod (E)"

    def test_valid_calls_do_not_walk_the_stack(self, monkeypatch: pytest.MonkeyPatch):

        def fail() -> None:
            raise AssertionError("inspect.stack() called on valid input")

        monkeypatch.setattr(inspect, "stack", fail)
        names = ItemNames(_ITEM_GAME_DATA, _ITEM_LOC)
        get_named_rewards([{"id": "GRIND", "type": 3}], names)
        get_data_disc_names(_ITEM_GAME_DATA["artifactDefinition"], _ITEM_LOC)
        get_player_title_names(_ITEM_GAME_DATA["playerTitle"], _ITEM_LOC)
        get_mod_catalog([], _ITEM_GAME_DATA["statModSet"], _ITEM_LOC)


# ── _territory_battle ──────────────────────────────────────────────────


def _tb_zone(zone_id: str, planet: str = "", name_key: str = "") -> dict[str, Any]:
    return {"zoneId": zone_id, "linkedConflictId": planet, "nameKey": name_key, "maxUnitCountPerPlayer": 2147483647}


def _tb_mission_zone(zone_id: str, planet: str, mission_id: str, table: str | None = None, difficulty: Any = 4):
    zone: dict[str, Any] = {
        "zoneDefinition": _tb_zone(zone_id, planet, "COMBAT_MISSION_NAME"),
        "campaignElementIdentifier": {
            "campaignId": "t05D",
            "campaignMapId": "TB_MAP",
            "campaignNodeDifficulty": difficulty,
            "campaignNodeId": "NODE_1",
            "campaignMissionId": mission_id,
        },
        "combatType": 1,
    }
    if table:
        zone["encounterRewardTableId"] = table
    return zone


def _tb_bracket(score: Any, reward_type: Any = 2) -> dict[str, Any]:
    return {"galacticScoreRequirement": score, "reward": {"type": reward_type, "value": "1"}}


def _tb_platoon(platoon_id: str, points: str, reward_type: Any = 1) -> dict[str, Any]:
    return {
        "id": platoon_id,
        "squad": [{"id": "squad-01"}, {"id": "squad-02"}],
        "reward": {"type": reward_type, "value": points},
    }


_TB_DEFS = [
    {
        "id": "t04D",
        "territoryBattleVersion_3": False,
        "conflictZoneDefinition": [
            {"zoneDefinition": _tb_zone("geo_phase01_conflict01"), "victoryPointRewards": [_tb_bracket("10")]}
        ],
        # Before version 3, special missions in the strike array are real, playable missions.
        "strikeZoneDefinition": [_tb_mission_zone("geo_phase01_conflict01_strike01", "p", "X_SPECIALMISSION", "t1")],
    },
    {
        "id": "t05D",
        # Comlink's spelling; the on-disk dump of the game data spells it territoryBattleVersion_3.
        "territoryBattleVersion3": True,
        "conflictZoneDefinition": [
            {
                "zoneDefinition": _tb_zone("tb3_phase01_conflict01", name_key="PLANET_CORUSCANT"),
                "forceAlignment": 2,
                "victoryPointRewards": [_tb_bracket("300"), _tb_bracket(100), _tb_bracket("200", "VICTORY_POINT")],
            },
            {
                "zoneDefinition": _tb_zone("tb3_phase03_conflict01_bonus"),
                "isBonus": True,
                # The first two brackets pay a mystery box, not a star.
                "victoryPointRewards": [_tb_bracket("50", 3), _tb_bracket("80", 3), _tb_bracket("90")],
            },
        ],
        "strikeZoneDefinition": [
            _tb_mission_zone("tb3_phase01_conflict01_strike01", "tb3_phase01_conflict01", "COMBAT_01", "tb3_p1"),
            _tb_mission_zone("tb3_phase01_conflict01_strike02", "tb3_phase01_conflict01", "COMBAT_02", "tb3_p1"),
            # Shares its campaign mission with strike02 on the same planet.
            _tb_mission_zone("tb3_phase01_conflict01_dup", "tb3_phase01_conflict01", "COMBAT_02", "tb3_p1"),
            # A special mission left in the strike array of a version 3 map.
            _tb_mission_zone(
                "tb3_phase01_conflict02_specialmission", "tb3_phase01_conflict02", "P1_SPECIALMISSION", "tb3_p1"
            ),
            # Names a mission the campaign does not have.
            _tb_mission_zone("tb3_phase01_conflict02_strike01", "tb3_phase01_conflict02", "MISSING", "tb3_gap"),
        ],  # fmt: skip
        "covertZoneDefinition": [
            {
                **_tb_mission_zone("tb3_phase01_conflict01_covert01", "tb3_phase01_conflict01", "SPECIAL_01"),
                "combatType": "SHIP",
            }
        ],
        "reconZoneDefinition": [
            {
                "zoneDefinition": {
                    **_tb_zone("tb3_phase01_conflict01_recon01", "tb3_phase01_conflict01"),
                    "nameKey": "RECON_NAME",
                    "maxUnitCountPerPlayer": 10,
                },
                "unitRarity": 7,
                "unitRelicTier": 7,
                "combatType": 1,
                "platoonDefinition": [
                    _tb_platoon("platoon-1", "100"),
                    _tb_platoon("platoon-2", "250"),
                    _tb_platoon("platoon-3", "999", reward_type=3),
                ],
            },
            {
                "zoneDefinition": _tb_zone("tb3_phase01_conflict02_recon01", "tb3_phase01_conflict02"),
                "unitRarity": "SIX_STAR",
                "unitRelicTier": "RELIC_LOCKED",
                "combatType": 2,
                "platoonDefinition": [],
            },
        ],  # fmt: skip
    },
]


def _tb_gate(**overrides: Any) -> dict[str, Any]:
    gate = {
        "categoryId": ["profession_jedi", "hidden_tag"],
        "commanderCategoryId": [],
        "excludeCategoryId": [],
        "mandatoryRosterUnit": [],
        "matchType": 2,
        "minimumRequiredUnitQuantity": 5,
        "maximumAllowedUnitQuantity": 5,
        "minimumUnitRarity": 7,
        "minimumUnitLevel": 85,
        "minimumUnitTier": 13,
        "minimumRelicTier": 9,
    }
    return gate | overrides


def _tb_campaign_mission(mission_id: str, gate: dict[str, Any], desc_key: str = "") -> dict[str, Any]:
    return {"id": mission_id, "descKey": desc_key, "entryCategoryAllowed": gate}


_TB_CAMPAIGNS = [
    {
        "id": "t05D",
        "campaignMap": [
            {
                "id": "TB_MAP",
                "campaignNodeDifficultyGroup": [
                    {
                        "campaignNodeDifficulty": 4,
                        "campaignNode": [
                            {
                                "id": "NODE_1",
                                "campaignNodeMission": [
                                    _tb_campaign_mission(
                                        "COMBAT_01",
                                        _tb_gate(
                                            mandatoryRosterUnit=[{"id": "KITFISTO", "slot": 1},
                                                                 {"id": "MACEWINDU", "slot": 0}],
                                        ),
                                        "COMBAT_01_REQUIREMENTS",
                                    ),
                                    _tb_campaign_mission(
                                        "COMBAT_02",
                                        _tb_gate(categoryId=["role_leader"], commanderCategoryId=["profession_jedi"],
                                                 excludeCategoryId=["unknown_tag"], minimumRelicTier="RELIC_TIER_05",
                                                 minimumUnitRarity="SEVEN_STAR", minimumUnitTier="TIER_12"),
                                    ),
                                    _tb_campaign_mission("P1_SPECIALMISSION", _tb_gate()),
                                    # Ships cannot hold relics: RELIC_LOCKED is no relic floor.
                                    _tb_campaign_mission("SPECIAL_01", _tb_gate(categoryId=[], minimumRelicTier=1)),
                                ],
                            }
                        ],
                    },
                    # The same node and mission ids under another difficulty, with a different gate. It comes
                    # last, so a key without the difficulty would pick it over the difficulty 4 gate.
                    {
                        "campaignNodeDifficulty": 5,
                        "campaignNode": [
                            {"id": "NODE_1", "campaignNodeMission": [_tb_campaign_mission("COMBAT_01", _tb_gate(
                                minimumRelicTier=12))]}
                        ],
                    },
                ],
            }
        ],
    },
    {"id": "OTHER_CAMPAIGN", "campaignMap": []},
]  # fmt: skip
_TB_CATEGORIES = [
    {"id": "profession_jedi", "descKey": "CATEGORY_JEDI_DESC"},
    {"id": "role_leader", "descKey": "CATEGORY_LEADER_DESC"},
    {"id": "hidden_tag", "descKey": "PLACEHOLDER"},
]
_TB_LOC = {
    "PLANET_CORUSCANT": "[c][ffff33]Coruscant[-][/c]",
    "COMBAT_MISSION_NAME": "Combat Mission",
    "RECON_NAME": "Coruscant Operation",
    "CATEGORY_JEDI_DESC": "Jedi",
    "PLACEHOLDER": "Placeholder",
    "COMBAT_01_REQUIREMENTS": "5x Jedi (Relic 7+)\\n[c][f0ff23]Mace Windu[-][/c]\\n[c][f0ff23]Kit Fisto[-][/c]",
}
_TB_TABLES = [
    # Rows keyed by wave count as strings, out of order, with a non-score row.
    {"id": "tb3_p1", "row": [{"key": "2", "value": "GALACTIC_SCORE:200"}, {"key": "0", "value": "GALACTIC_SCORE:0"},
                             {"key": "1", "value": "GALACTIC_SCORE:100"}, {"key": "3", "value": "ITEM:abc"}]},
    # Wave 1 is missing; it repeats wave 0's total.
    {"id": "tb3_gap", "row": [{"key": "0", "value": "GALACTIC_SCORE:0"}, {"key": "2", "value": "GALACTIC_SCORE:50"}]},
    {"id": "t1", "row": [{"key": "0", "value": "GALACTIC_SCORE:0"}, {"key": "1", "value": "GALACTIC_SCORE:7"}]},
    {"id": "unrelated", "row": [{"key": "x", "value": "SPRITE:y"}]},
]  # fmt: skip


class TestGetTbStarThresholds:
    def test_reads_only_victory_point_brackets_sorted(self):

        zones = get_tb_star_thresholds(_TB_DEFS, _TB_LOC)
        assert [(z["tb_id"], z["zone_id"], z["stars"]) for z in zones] == [
            ("t04D", "geo_phase01_conflict01", [10]),
            ("t05D", "tb3_phase01_conflict01", [100, 200, 300]),
            ("t05D", "tb3_phase03_conflict01_bonus", [90]),
        ]
        coruscant, bonus = zones[1:]
        assert coruscant["name"] == "Coruscant"
        assert (coruscant["phase"], coruscant["is_bonus"], coruscant["force_alignment"]) == (1, False, 2)
        assert (bonus["phase"], bonus["is_bonus"]) == (3, True)
        # Without a localization entry the name is its key, or the zone id when there is no key.
        assert zones[0]["name"] == "geo_phase01_conflict01"

    def test_tb_id_is_case_insensitive(self):

        assert {z["tb_id"] for z in get_tb_star_thresholds(_TB_DEFS, tb_id="T04d")} == {"t04D"}

    @pytest.mark.parametrize(
        ("args", "kwargs"),
        [
            (({"id": "t05D"},), {}),
            ((_TB_DEFS, ["not", "a", "dict"]), {}),
            ((_TB_DEFS,), {"tb_id": "t99D"}),
            ((_TB_DEFS,), {"tb_id": 5}),
            (([None],), {}),
            ((["t05D"],), {"tb_id": "t05D"}),
        ],
    )
    def test_invalid_input_raises(self, args: tuple[Any, ...], kwargs: dict[str, Any]):

        with pytest.raises(SwgohComlinkValueError):
            get_tb_star_thresholds(*args, **kwargs)


class TestGetTbMissionRequirements:
    def _get(self, **kwargs: Any) -> dict[str, Any]:

        missions = get_tb_mission_requirements(_TB_DEFS, _TB_CAMPAIGNS, _TB_CATEGORIES, _TB_LOC, **kwargs)
        return {m["zone_id"]: m for m in missions}

    def test_lists_combat_then_special_missions(self):
        missions = self._get(tb_id="t05D")
        assert [(zone_id, m["mission_type"]) for zone_id, m in missions.items()] == [
            ("tb3_phase01_conflict01_strike01", "combat"),
            ("tb3_phase01_conflict01_strike02", "combat"),
            ("tb3_phase01_conflict01_dup", "combat"),
            ("tb3_phase01_conflict02_specialmission", "combat"),
            ("tb3_phase01_conflict02_strike01", "combat"),
            ("tb3_phase01_conflict01_covert01", "special"),
        ]

    def test_resolves_the_gate_at_the_zones_difficulty(self):
        strike = self._get()["tb3_phase01_conflict01_strike01"]
        assert strike["resolved"] is True
        assert strike["campaign_mission_id"] == "COMBAT_01"
        assert (strike["conflict_zone_id"], strike["phase"], strike["name"]) == (
            "tb3_phase01_conflict01",
            1,
            "Combat Mission",
        )
        # Wire relic tier 9 is relic 7; the difficulty 5 copy of this mission (wire 12) is not used.
        assert strike["min_relic"] == 7
        assert (strike["min_rarity"], strike["min_gear"], strike["min_level"]) == (7, 13, 85)
        assert (strike["min_squad_size"], strike["max_squad_size"], strike["category_match_type"]) == (5, 5, 2)
        assert strike["mandatory_units"] == [{"base_id": "MACEWINDU", "slot": 0}, {"base_id": "KITFISTO", "slot": 1}]
        assert strike["requirement_text"] == "5x Jedi (Relic 7+)\nMace Windu\nKit Fisto"
        assert strike["is_fleet"] is False

    def test_difficulty_without_a_group_is_unresolved(self):

        # Node and mission ids match the campaign, but no group has difficulty 3.
        zone = _tb_mission_zone("tb3_phase01_conflict01_strike01", "tb3_phase01_conflict01", "COMBAT_01", difficulty=3)
        definition = {"id": "t05D", "strikeZoneDefinition": [zone]}
        (strike,) = get_tb_mission_requirements([definition], _TB_CAMPAIGNS, _TB_CATEGORIES, _TB_LOC)
        assert strike["resolved"] is False
        assert (strike["min_relic"], strike["requirement_text"]) == (0, "")

    def test_names_categories_and_skips_placeholder_names(self):
        missions = self._get()
        assert missions["tb3_phase01_conflict01_strike01"]["allowed_categories"] == [
            {"id": "profession_jedi", "name": "Jedi"},
            {"id": "hidden_tag", "name": "hidden_tag"},
        ]
        strike = missions["tb3_phase01_conflict01_strike02"]
        # A category with no localization entry keeps its key; one missing from 'categories' its id.
        assert strike["allowed_categories"] == [{"id": "role_leader", "name": "CATEGORY_LEADER_DESC"}]
        assert strike["commander_categories"] == [{"id": "profession_jedi", "name": "Jedi"}]
        assert strike["excluded_categories"] == [{"id": "unknown_tag", "name": "unknown_tag"}]

    def test_enum_names_and_relic_locked(self):
        missions = self._get()
        strike = missions["tb3_phase01_conflict01_strike02"]
        assert (strike["min_relic"], strike["min_rarity"], strike["min_gear"]) == (5, 7, 12)
        fleet = missions["tb3_phase01_conflict01_covert01"]
        assert fleet["is_fleet"] is True
        assert fleet["min_relic"] == 0

    def test_unresolved_mission_is_kept_without_a_gate(self):
        strike = self._get()["tb3_phase01_conflict02_strike01"]
        assert strike["resolved"] is False
        assert strike["requirement_text"] == ""
        assert strike["allowed_categories"] == [] and strike["min_squad_size"] == 0

    def test_hidden_reasons(self):
        missions = self._get()
        assert {zone_id: m["hidden_reason"] for zone_id, m in missions.items() if m["hidden_reason"]} == {
            "tb3_phase01_conflict01_dup": "duplicate",
            "tb3_phase01_conflict02_specialmission": "special",
        }
        # Not a version 3 map, so a special mission in the strike array is a normal mission.
        assert missions["geo_phase01_conflict01_strike01"]["hidden_reason"] is None

    def test_dump_spelling_of_the_version_3_flag(self):

        definition = {k: v for k, v in _TB_DEFS[1].items() if k != "territoryBattleVersion3"}
        missions = get_tb_mission_requirements([definition], _TB_CAMPAIGNS, _TB_CATEGORIES)
        assert sum(m["hidden_reason"] == "special" for m in missions) == 0
        definition["territoryBattleVersion_3"] = True
        missions = get_tb_mission_requirements([definition], _TB_CAMPAIGNS, _TB_CATEGORIES)
        assert sum(m["hidden_reason"] == "special" for m in missions) == 1

    def test_without_localization_returns_keys(self):

        missions = get_tb_mission_requirements(_TB_DEFS, _TB_CAMPAIGNS, _TB_CATEGORIES, tb_id="t05D")
        assert missions[0]["requirement_text"] == "COMBAT_01_REQUIREMENTS"
        assert missions[0]["allowed_categories"][0]["name"] == "CATEGORY_JEDI_DESC"

    @pytest.mark.parametrize(
        "args",
        [
            ({"id": "t05D"}, _TB_CAMPAIGNS, _TB_CATEGORIES),
            (_TB_DEFS, None, _TB_CATEGORIES),
            (_TB_DEFS, _TB_CAMPAIGNS, "category"),
            (_TB_DEFS, _TB_CAMPAIGNS, _TB_CATEGORIES, "loc"),
            (_TB_DEFS, [None], _TB_CATEGORIES),
            (_TB_DEFS, _TB_CAMPAIGNS, ["profession_jedi"]),
        ],
    )
    def test_invalid_input_raises(self, args: tuple[Any, ...]):

        with pytest.raises(SwgohComlinkValueError):
            get_tb_mission_requirements(*args)


class TestGetTbMissionScores:
    def test_cumulative_points_by_waves(self):

        scores = {s["zone_id"]: s for s in get_tb_mission_scores(_TB_DEFS, _TB_TABLES)}
        # The covert zone has no points table and is not listed.
        assert list(scores) == [
            "geo_phase01_conflict01_strike01",
            "tb3_phase01_conflict01_strike01",
            "tb3_phase01_conflict01_strike02",
            "tb3_phase01_conflict01_dup",
            "tb3_phase01_conflict02_specialmission",
            "tb3_phase01_conflict02_strike01",
        ]
        strike = scores["tb3_phase01_conflict01_strike01"]
        assert strike["wave_points"] == [0, 100, 200]
        assert (strike["max_points"], strike["reward_table_id"], strike["mission_type"]) == (200, "tb3_p1", "combat")
        assert scores["tb3_phase01_conflict02_strike01"]["wave_points"] == [0, 0, 50]
        assert scores["tb3_phase01_conflict01_dup"]["hidden_reason"] == "duplicate"
        assert scores["geo_phase01_conflict01_strike01"]["max_points"] == 7

    def test_tb_id_filter(self):

        assert {s["tb_id"] for s in get_tb_mission_scores(_TB_DEFS, _TB_TABLES, tb_id="t04d")} == {"t04D"}

    @pytest.mark.parametrize(
        "args",
        [
            ({"id": "t05D"}, _TB_TABLES),
            (_TB_DEFS, None),
            (_TB_DEFS, [*_TB_TABLES, "tb3_p1"]),
            # The mission's table is not in the collection.
            (_TB_DEFS, _TB_TABLES[1:]),
        ],
    )
    def test_invalid_input_raises(self, args: tuple[Any, ...]):

        with pytest.raises(SwgohComlinkValueError):
            get_tb_mission_scores(*args)


class TestGetTbPlatoonDefinitions:
    def test_reads_floors_and_points_per_platoon(self):

        zone, fleet = get_tb_platoon_definitions(_TB_DEFS, _TB_LOC)
        assert (zone["tb_id"], zone["zone_id"], zone["conflict_zone_id"], zone["phase"]) == (
            "t05D",
            "tb3_phase01_conflict01_recon01",
            "tb3_phase01_conflict01",
            1,
        )
        assert zone["name"] == "Coruscant Operation"
        assert (zone["min_rarity"], zone["min_relic"], zone["max_units_per_player"]) == (7, 5, 10)
        assert zone["platoons"] == [
            {"platoon_id": "platoon-1", "squad_ids": ["squad-01", "squad-02"], "points": 100},
            {"platoon_id": "platoon-2", "squad_ids": ["squad-01", "squad-02"], "points": 250},
            # Not a territory points reward.
            {"platoon_id": "platoon-3", "squad_ids": ["squad-01", "squad-02"], "points": 0},
        ]
        assert zone["total_points"] == 350
        assert (fleet["is_fleet"], fleet["min_rarity"], fleet["min_relic"]) == (True, 6, 0)
        assert fleet["max_units_per_player"] is None
        assert (fleet["platoons"], fleet["total_points"]) == ([], 0)

    def test_invalid_input_raises(self):

        with pytest.raises(SwgohComlinkValueError):
            get_tb_platoon_definitions(_TB_DEFS, tb_id="t99D")


def test_tb_helpers_read_type_prefixed_enum_names():

    # Some servers send enums=True names prefixed with their type and without inner underscores.
    definition = {
        "id": "t05D",
        "conflictZoneDefinition": [
            {
                "zoneDefinition": _tb_zone("tb3_phase03_conflict01_bonus"),
                "victoryPointRewards": [
                    _tb_bracket("50", "TERRITORYREWARDTYPE_MYSTERYBOXCONFLICT"),
                    _tb_bracket("90", "TERRITORYREWARDTYPE_VICTORYPOINT"),
                ],
            }
        ],
        "strikeZoneDefinition": [
            {**_tb_mission_zone("tb3_phase01_conflict01_strike02", "p", "COMBAT_02"), "combatType": "COMBATTYPE_SHIP"}
        ],
        "reconZoneDefinition": [
            {
                "zoneDefinition": _tb_zone("tb3_phase01_conflict01_recon01", "p"),
                "unitRarity": "RARITY_SIXSTAR",
                "unitRelicTier": "RELICTIER_RELICTIER07",
                "combatType": "COMBATTYPE_CHARACTER",
                "platoonDefinition": [
                    _tb_platoon("platoon-1", "100", "TERRITORYREWARDTYPE_GALACTICSCORE"),
                    _tb_platoon("platoon-2", "999", "TERRITORYREWARDTYPE_MYSTERYBOXCONFLICT"),
                ],
            }
        ],
    }
    gate = _tb_gate(minimumRelicTier="RELICTIER_RELICTIER05", minimumUnitRarity="RARITY_SEVENSTAR",
                    minimumUnitTier="UNITTIER_TIER12")  # fmt: skip
    campaigns = [
        {
            "id": "t05D",
            "campaignMap": [
                {
                    "id": "TB_MAP",
                    "campaignNodeDifficultyGroup": [
                        {
                            "campaignNodeDifficulty": 4,
                            "campaignNode": [
                                {"id": "NODE_1", "campaignNodeMission": [_tb_campaign_mission("COMBAT_02", gate)]}
                            ],
                        }
                    ],
                }
            ],
        }
    ]

    (zone,) = get_tb_star_thresholds([definition])
    assert zone["stars"] == [90]
    (mission,) = get_tb_mission_requirements([definition], campaigns, _TB_CATEGORIES)
    assert mission["is_fleet"] is True
    assert (mission["min_relic"], mission["min_rarity"], mission["min_gear"]) == (5, 7, 12)
    (recon,) = get_tb_platoon_definitions([definition])
    assert (recon["is_fleet"], recon["min_rarity"], recon["min_relic"], recon["total_points"]) == (False, 6, 7, 100)


# ── _upgrades ──────────────────────────────────────────────────────────


def _ingredient(item_id: str, kind: Any, quantity: int, high: int | None = None) -> dict[str, Any]:
    return {"id": item_id, "type": kind, "minQuantity": quantity, "maxQuantity": quantity if high is None else high}


def _recipe(recipe_id: str, *ingredients: dict[str, Any]) -> dict[str, Any]:
    return {"id": recipe_id, "ingredients": list(ingredients)}


def _piece(piece_id: str, recipe_id: str = "", tier: int = 1, mark: str = "Mk I") -> dict[str, Any]:
    return {"id": piece_id, "nameKey": f"EQUIPMENT_{piece_id.upper()}_NAME", "recipeId": recipe_id, "tier": tier,
            "mark": mark}  # fmt: skip


_UPGRADE_EQUIPMENT = [
    _piece("001"),
    _piece("164", "recipe164", tier=12, mark="Mk XII"),
    _piece("164Prototype", "recipe164Prototype", tier=12),
    _piece("164PrototypeSalvage", tier=12),
    _piece("156", "recipe156", tier=7),
    _piece("156Salvage", tier=7),
    # The placeholder every character's tier 13 slots: a real equipment row with no recipe.
    _piece("9999", tier=12),
]
_UPGRADE_RECIPES = [
    _recipe("recipe164", _ingredient("164Prototype", 11, 1), _ingredient("156", 11, 2), _ingredient("GRIND", 3, 20350)),
    _recipe("recipe164Prototype", _ingredient("164PrototypeSalvage", 11, 30), _ingredient("GRIND", 3, 14000)),
    # Ingredient types as enum names, as returned with enums=True.
    _recipe("recipe156", _ingredient("156Salvage", "EQUIPMENT", 20), _ingredient("GRIND", "CURRENCY", 5150)),
    _recipe("relic_promotion_recipe_01", _ingredient("GRIND", 3, 10000), _ingredient("SCV_001", 7, 40)),
    _recipe("relic_promotion_recipe_02", _ingredient("GRIND", 3, 15000), _ingredient("SCV_001", 7, 30),
            _ingredient("RM_001", 7, 15)),
    _recipe("SKILLRECIPE_T1", _ingredient("GRIND", 3, 1000), _ingredient("ability_mat_A", 7, 2)),
    _recipe("SKILLRECIPE_ZETA", _ingredient("GRIND", 3, 5000), _ingredient("ability_mat_zeta", "MATERIAL", 1)),
    _recipe("SHIPSKILLRECIPE_T1", _ingredient("SHIP_GRIND", 3, 100), _ingredient("shipability_mat_A", 7, 3)),
]  # fmt: skip
_UPGRADE_TABLES = [
    {"id": "crew_rating_per_relic_tier", "row": [{"key": "1", "value": "0"}]},
    # Rows out of order: costs come back R1 first.
    {"id": "relic_promotion_table", "row": [{"key": "TIER_02", "value": "relic_promotion_recipe_02"},
                                            {"key": "TIER_01", "value": "relic_promotion_recipe_01"}]},
]  # fmt: skip
_HERO_TIERS = (
    [{"tier": 13, "equipmentSet": ["9999"] * 6}]
    + [{"tier": 1, "equipmentSet": ["001", "164", "156", "001", "156", "001"]}]
    + [{"tier": n, "equipmentSet": ["001"] * 6} for n in range(2, 13)]
)
_UPGRADE_UNITS = [
    {"baseId": "HERO", "rarity": 1, "combatType": 1, "unitTier": _HERO_TIERS,
     "skillReference": [{"skillId": "basicskill_HERO"}, {"skillId": "leaderskill_HERO"}]},
    {"baseId": "HERO", "rarity": 7, "combatType": 1, "unitTier": _HERO_TIERS, "skillReference": []},
    {"baseId": "SHIP", "rarity": 7, "combatType": 2, "skillReference": [{"skillId": "basicskill_SHIP"}],
     "crew": [{"unitId": "PILOT", "skillReference": [{"skillId": "specialskill_SHIP01"}]}]},
]  # fmt: skip
_UPGRADE_SKILLS = [
    {"id": "basicskill_HERO", "tier": [{"recipeId": "SKILLRECIPE_T1"}, {"recipeId": "SKILLRECIPE_T1"}]},
    {"id": "leaderskill_HERO", "tier": [{"recipeId": "SKILLRECIPE_T1"},
                                        {"recipeId": "SKILLRECIPE_ZETA", "isZetaTier": True, "isOmicronTier": True}]},
    {"id": "basicskill_SHIP", "tier": [{"recipeId": "SHIPSKILLRECIPE_T1"}]},
    {"id": "specialskill_SHIP01", "tier": [{"recipeId": "SHIPSKILLRECIPE_T1"}]},
]  # fmt: skip


def _enum_tiers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """``rows`` with their UnitTier ``tier`` as the enum names returned with enums=True."""
    return [{**row, "tier": f"TIER_{row['tier']:02d}"} for row in rows]


def _digit_tiers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """``rows`` with their UnitTier ``tier`` as a numeric string."""
    return [{**row, "tier": str(row["tier"])} for row in rows]


_TIER_SPELLINGS = [pytest.param(_enum_tiers, id="enum-names"), pytest.param(_digit_tiers, id="digit-strings")]


def _cost(credits: int = 0, ship_credits: int = 0, materials: Any = None, equipment: Any = None) -> dict[str, Any]:
    return {"credits": credits, "ship_credits": ship_credits, "materials": materials or {},
            "equipment": equipment or {}}  # fmt: skip


class TestGetUnitGearTiers:
    def test_lists_thirteen_tiers_in_order_without_the_placeholder(self):

        tiers = get_unit_gear_tiers(_UPGRADE_UNITS, "hero")
        assert [t["tier"] for t in tiers] == list(range(1, 14))
        assert tiers[0]["equipment"] == ["001", "164", "156", "001", "156", "001"]
        assert tiers[0]["cost"] == _cost(equipment={"001": 3, "164": 1, "156": 2})
        assert tiers[-1]["equipment"] == []
        assert tiers[-1]["cost"] == _cost()

    def test_ship_has_no_gear(self):

        assert get_unit_gear_tiers(_UPGRADE_UNITS, "SHIP") == []

    @pytest.mark.parametrize("spell", _TIER_SPELLINGS)
    def test_tier_spellings_match_integers(self, spell):
        units = [{**_UPGRADE_UNITS[0], "unitTier": spell(_HERO_TIERS)}]
        assert get_unit_gear_tiers(units, "HERO") == get_unit_gear_tiers(_UPGRADE_UNITS, "HERO")

    @pytest.mark.parametrize(
        ("units", "base_id"),
        [
            ({}, "HERO"),
            (_UPGRADE_UNITS, None),
            (_UPGRADE_UNITS, "NOBODY"),
            ([{"baseId": "HERO", "unitTier": [{"tier": "GEAR_ONE", "equipmentSet": []}]}], "HERO"),
        ],
    )
    def test_invalid_input_raises(self, units: Any, base_id: Any):

        with pytest.raises(SwgohComlinkValueError):
            get_unit_gear_tiers(units, base_id)


class TestGetGearCraftTree:
    def test_expands_down_to_farmed_pieces(self):

        loc = {"EQUIPMENT_164_NAME": "[c][ffff33]Mk 12 ArmaTek Cybernetics[-][/c]"}
        tree = get_gear_craft_tree(_UPGRADE_EQUIPMENT, _UPGRADE_RECIPES, "164", loc)
        assert (tree["name"], tree["tier"], tree["mark"], tree["quantity"]) == (
            "Mk 12 ArmaTek Cybernetics",
            12,
            "Mk XII",
            1,
        )
        assert tree["recipe_credits"] == 20350
        prototype, detonator = tree["ingredients"]
        # Names fall back to the nameKey.
        assert (prototype["id"], prototype["quantity"], prototype["name"]) == (
            "164Prototype",
            1,
            "EQUIPMENT_164PROTOTYPE_NAME",
        )
        # Quantities multiply down the tree: 2 pieces x 20 salvage each.
        assert (detonator["quantity"], detonator["ingredients"][0]["quantity"]) == (2, 40)
        assert detonator["cost"] == _cost(credits=2 * 5150, equipment={"156Salvage": 40})
        assert detonator["ingredients"][0]["ingredients"] == []
        assert tree["cost"] == _cost(
            credits=20350 + 14000 + 2 * 5150, equipment={"164PrototypeSalvage": 30, "156Salvage": 40}
        )

    @pytest.mark.parametrize("spell", _TIER_SPELLINGS)
    def test_tier_spellings_match_integers(self, spell):
        tree = get_gear_craft_tree(spell(_UPGRADE_EQUIPMENT), _UPGRADE_RECIPES, "164")
        assert tree == get_gear_craft_tree(_UPGRADE_EQUIPMENT, _UPGRADE_RECIPES, "164")
        assert (tree["tier"], tree["ingredients"][1]["tier"]) == (12, 7)

    @pytest.mark.parametrize("tier", [None, "TIER_UNDEFINED"])
    def test_missing_tier_counts_as_zero(self, tier):
        assert get_gear_craft_tree([{**_piece("001"), "tier": tier}], [], "001")["tier"] == 0

    def test_unrecognized_tier_raises(self):

        with pytest.raises(SwgohComlinkValueError, match="unrecognized tier 'TWELVE'"):
            get_gear_craft_tree([{**_piece("001"), "tier": "TWELVE"}], [], "001")

    def test_farmed_piece_is_a_leaf(self):

        tree = get_gear_craft_tree(_UPGRADE_EQUIPMENT, _UPGRADE_RECIPES, "001")
        assert (tree["ingredients"], tree["recipe_credits"], tree["cost"]) == ([], 0, _cost(equipment={"001": 1}))

    @pytest.mark.parametrize(
        ("recipes", "message"),
        [
            # A quantity range has no single cost.
            ([_recipe("recipe156", _ingredient("156Salvage", 11, 10, 20))], "10 to 20"),
            ([_recipe("recipe156", _ingredient("PREMIUM", 3, 10))], "unsupported currency"),
            ([_recipe("recipe156", _ingredient("SOMETHING", 2, 1))], "unsupported type"),
            ([_recipe("recipe156", _ingredient("ability_mat_A", 7, 1))], "more than credits"),
            ([_recipe("recipe156", _ingredient("NOPE", 11, 1))], "'NOPE' is not in 'equipment'"),
            ([_recipe("recipe156", _ingredient("156", 11, 1))], "crafted from itself"),
            ([], "recipe 'recipe156'"),
        ],
    )
    def test_rejects_recipes_it_cannot_cost_exactly(self, recipes: list[dict[str, Any]], message: str):

        with pytest.raises(SwgohComlinkValueError, match=message):
            get_gear_craft_tree(_UPGRADE_EQUIPMENT, recipes, "156")

    @pytest.mark.parametrize(
        "args",
        [
            ({}, _UPGRADE_RECIPES, "164"),
            (_UPGRADE_EQUIPMENT, None, "164"),
            (_UPGRADE_EQUIPMENT, _UPGRADE_RECIPES, 164),
            (_UPGRADE_EQUIPMENT, _UPGRADE_RECIPES, "164", ["not", "a", "dict"]),
        ],
    )
    def test_invalid_input_raises(self, args: tuple[Any, ...]):

        with pytest.raises(SwgohComlinkValueError):
            get_gear_craft_tree(*args)


class TestGetRelicPromotionCosts:
    def test_joins_the_promotion_table_to_recipes(self):

        assert get_relic_promotion_costs(_UPGRADE_TABLES, _UPGRADE_RECIPES) == [
            {
                "relic_tier": 1,
                "recipe_id": "relic_promotion_recipe_01",
                "cost": _cost(credits=10000, materials={"SCV_001": 40}),
            },
            {
                "relic_tier": 2,
                "recipe_id": "relic_promotion_recipe_02",
                "cost": _cost(credits=15000, materials={"SCV_001": 30, "RM_001": 15}),
            },
        ]

    @pytest.mark.parametrize(
        ("tables", "recipes", "message"),
        [
            (_UPGRADE_TABLES[:1], _UPGRADE_RECIPES, "is not in 'tables'"),
            ([{"id": "relic_promotion_table", "row": [{"key": "TIER_02", "value": "x"}]}], _UPGRADE_RECIPES, "1 to n"),
            ([{"id": "relic_promotion_table", "row": [{"key": "R1", "value": "x"}]}], _UPGRADE_RECIPES, "unexpected"),
            (_UPGRADE_TABLES, [], "relic tier 1"),
            ("table", _UPGRADE_RECIPES, "must be a list"),
        ],
    )
    def test_invalid_input_raises(self, tables: Any, recipes: Any, message: str):

        with pytest.raises(SwgohComlinkValueError, match=message):
            get_relic_promotion_costs(tables, recipes)


class TestGetAbilityUpgradeCosts:
    def test_costs_each_level_with_zeta_and_omicron_flags(self):

        basic, leader = get_ability_upgrade_costs(_UPGRADE_UNITS, _UPGRADE_SKILLS, _UPGRADE_RECIPES, "HERO")
        assert (basic["base_id"], basic["skill_id"], basic["crew_base_id"]) == ("HERO", "basicskill_HERO", None)
        assert [t["level"] for t in leader["tiers"]] == [2, 3]
        assert [(t["is_zeta"], t["is_omicron"]) for t in leader["tiers"]] == [(False, False), (True, True)]
        assert leader["tiers"][1] == {
            "level": 3,
            "recipe_id": "SKILLRECIPE_ZETA",
            "is_zeta": True,
            "is_omicron": True,
            "cost": _cost(credits=5000, materials={"ability_mat_zeta": 1}),
        }

    def test_ship_includes_crew_abilities_and_ship_credits(self):

        own, crew = get_ability_upgrade_costs(_UPGRADE_UNITS, _UPGRADE_SKILLS, _UPGRADE_RECIPES, "ship")
        assert (own["crew_base_id"], crew["crew_base_id"], crew["skill_id"]) == (None, "PILOT", "specialskill_SHIP01")
        assert crew["tiers"][0]["cost"] == _cost(ship_credits=100, materials={"shipability_mat_A": 3})

    @pytest.mark.parametrize(
        ("args", "message"),
        [
            ((_UPGRADE_UNITS, _UPGRADE_SKILLS[1:], _UPGRADE_RECIPES, "HERO"), "'basicskill_HERO'"),
            ((_UPGRADE_UNITS, _UPGRADE_SKILLS, _UPGRADE_RECIPES[:-1], "SHIP"), "'SHIPSKILLRECIPE_T1'"),
            ((_UPGRADE_UNITS, _UPGRADE_SKILLS, _UPGRADE_RECIPES, "NOBODY"), "'NOBODY'"),
            ((_UPGRADE_UNITS, {}, _UPGRADE_RECIPES, "HERO"), "must be a list"),
        ],
    )
    def test_invalid_input_raises(self, args: tuple[Any, ...], message: str):

        with pytest.raises(SwgohComlinkValueError, match=message):
            get_ability_upgrade_costs(*args)


class TestSumUpgradeCosts:
    def test_adds_costs_of_any_kind(self):

        relics = get_relic_promotion_costs(_UPGRADE_TABLES, _UPGRADE_RECIPES)
        ship = get_ability_upgrade_costs(_UPGRADE_UNITS, _UPGRADE_SKILLS, _UPGRADE_RECIPES, "SHIP")
        costs = [r["cost"] for r in relics] + [t["cost"] for a in ship for t in a["tiers"]]
        assert sum_upgrade_costs(costs) == _cost(
            credits=25000, ship_credits=200, materials={"RM_001": 15, "SCV_001": 70, "shipability_mat_A": 6}
        )

    def test_missing_fields_count_as_zero(self):

        assert sum_upgrade_costs([{"equipment": {"164": 2}}, {"credits": 5}]) == _cost(credits=5, equipment={"164": 2})
        assert sum_upgrade_costs([]) == _cost()

    def test_crafts_gear_down_to_salvage(self):

        tiers = get_unit_gear_tiers(_UPGRADE_UNITS, "HERO")
        assert sum_upgrade_costs(t["cost"] for t in tiers)["equipment"] == {"001": 69, "156": 2, "164": 1}

        crafted = sum_upgrade_costs((t["cost"] for t in tiers), _UPGRADE_EQUIPMENT, _UPGRADE_RECIPES)
        # 164 crafts from two 156 of its own, so four 156 are crafted in all.
        assert crafted == _cost(
            credits=20350 + 14000 + 4 * 5150, equipment={"001": 69, "156Salvage": 80, "164PrototypeSalvage": 30}
        )
        assert list(crafted["equipment"]) == sorted(crafted["equipment"])

    def test_crafts_enum_tier_gear_like_integer_tier_gear(self):

        units = [{**_UPGRADE_UNITS[0], "unitTier": _enum_tiers(_HERO_TIERS)}]
        enum_tiers = get_unit_gear_tiers(units, "HERO")
        int_tiers = get_unit_gear_tiers(_UPGRADE_UNITS, "HERO")
        enum_total = sum_upgrade_costs(
            (t["cost"] for t in enum_tiers), _enum_tiers(_UPGRADE_EQUIPMENT), _UPGRADE_RECIPES
        )
        assert enum_total == sum_upgrade_costs((t["cost"] for t in int_tiers), _UPGRADE_EQUIPMENT, _UPGRADE_RECIPES)

    def test_checks_collections_before_consuming_costs(self):

        costs = iter([_cost(credits=1)])
        not_a_list: Any = {}
        with pytest.raises(SwgohComlinkValueError, match="must be a list"):
            sum_upgrade_costs(costs, not_a_list, [])
        assert next(costs) == _cost(credits=1)

    @pytest.mark.parametrize(
        ("args", "message"),
        [
            (([], _UPGRADE_EQUIPMENT), "pass both"),
            (([], None, _UPGRADE_RECIPES), "pass both"),
            (([], {}, _UPGRADE_RECIPES), "must be a list"),
            ((["credits"],), "must be a mapping"),
            (([{"equipment": {"NOPE": 1}}], _UPGRADE_EQUIPMENT, _UPGRADE_RECIPES), "'NOPE'"),
        ],
    )
    def test_invalid_input_raises(self, args: tuple[Any, ...], message: str):

        with pytest.raises(SwgohComlinkValueError, match=message):
            sum_upgrade_costs(*args)


# ── _gac (pure functions) ──────────────────────────────────────────────


@pytest.mark.parametrize(
    ("convert", "value", "expected"),
    [
        *(
            pytest.param(convert_league_to_int, league, value, id=f"league-{league}")
            for league, value in [
                ("kyber", 100),
                ("aurodium", 80),
                ("chromium", 60),
                ("bronzium", 40),
                ("carbonite", 20),
                ("KYBER", 100),
                ("Kyber", 100),
                ("unknown", None),
            ]
        ),
        *(
            pytest.param(convert_divisions_to_int, division, value, id=f"division-{type(division).__name__}-{division}")
            for division, value in [
                ("1", 25),
                ("2", 20),
                ("3", 15),
                ("4", 10),
                ("5", 5),
                (1, 25),
                (5, 5),
                ("99", None),
            ]
        ),
    ],
)
def test_gac_league_and_division_conversion(convert, value, expected):
    assert convert(value) == expected


@pytest.mark.parametrize("convert", [convert_league_to_int, convert_divisions_to_int])
@pytest.mark.parametrize("value", [None, ""])
def test_gac_league_and_division_conversion_requires_a_value(convert, value):
    with pytest.raises(SwgohComlinkValueError, match="required"):
        convert(value)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        pytest.param("Player3", {"player": {"name": "Player3"}, "bracket": 1}, id="found"),
        pytest.param("player1", {"player": {"name": "Player1"}, "bracket": 0}, id="case-insensitive"),
        pytest.param("Nobody", {}, id="not-found"),
    ],
)
def test_search_gac_brackets(name, expected):
    brackets = {0: [{"name": "Player1"}, {"name": "Player2"}], 1: [{"name": "Player3"}]}
    assert search_gac_brackets(brackets, name) == expected


@pytest.mark.parametrize("implementation", ["sync", "async"])
@pytest.mark.parametrize(
    ("brackets", "initial_step", "expected"),
    [
        pytest.param(0, 1024, -1, id="bracket-0-empty"),
        pytest.param(1, 1, 0, id="one-bracket-step-1"),
        pytest.param(1, 1024, 0, id="one-bracket"),
        pytest.param(2, 1024, 1, id="two-brackets"),
        pytest.param(10, 4, 9, id="small-step"),
        pytest.param(100, 1024, 99, id="first-probe-overshoots"),
        pytest.param(500, 64, 499, id="custom-step"),
        pytest.param(2048, 1024, 2047, id="power-of-two"),
        pytest.param(6250, 1024, 6249, id="typical-league"),  # ~50k players / 8 per bracket
        pytest.param(18750, 1024, 18749, id="large-league"),  # ~150k players
    ],
)
async def test_find_bracket_boundary(implementation, brackets, initial_step, expected):
    """Exponential probing then binary search: the last non-empty index in O(log n) probes."""
    probed: list[int] = []

    def probe(index: int) -> bool:
        probed.append(index)
        return index < brackets

    async def async_probe(index: int) -> bool:
        return probe(index)

    if implementation == "sync":
        result = _find_bracket_boundary(probe, initial_step=initial_step)
    else:
        result = await _async_find_bracket_boundary(async_probe, initial_step=initial_step)

    assert result == expected
    # Each phase probes at most bit_length(max(brackets, step)) times; a linear scan would not.
    assert len(probed) <= 2 * max(brackets, initial_step).bit_length() + 1


# ── _constants ──────────────────────────────────────────────────────────


class TestConstants:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            pytest.param("Segment1", str(Constants.Segment1), id="own-attribute"),
            pytest.param("UnitDefinitions", "137438953472", id="legacy-name"),  # 2**37, DataItems.UNITS
            pytest.param("UNITS", "137438953472", id="data-items-name"),
            # Aligned with the live GameDataItemsEnum from get_enums().
            pytest.param("AbilityDecisionTrees", "1099511627776", id="ability-decision-trees"),
            pytest.param("EraDefinitions", "2251799813685248", id="era-definitions"),
            pytest.param("UBSUpdate", "2150109456", id="ubs-update"),
            pytest.param("EpisodeDefinitions", "281474976710656", id="episode-definitions-plural"),
            pytest.param("AccountLinking", "562949953421312", id="account-linking-alias"),
            pytest.param("TotallyFakeItem", None, id="unknown"),
        ],
    )
    def test_get(self, name, expected):
        assert Constants.get(name) == expected

    def test_legacy_name_mapped_to_missing_data_item_returns_none(self):
        with patch.dict(_LEGACY_NAME_MAP, {"FakeLegacyName": "NONEXISTENT_MEMBER"}):
            assert Constants.get("FakeLegacyName") is None

    def test_get_names(self):
        names = Constants.get_names()
        assert isinstance(names, list)
        assert {"RELIC_TIERS", "UnitDefinitions", "UNITS"} <= set(names)

    def test_segment_values_match_server(self):
        assert (Constants.Segment1, Constants.Segment2, Constants.Segment3, Constants.Segment4) == (
            2097151,
            1125968624222208,
            206158430208,
            3377424842620928,
        )

    def test_dataitems_members_present(self):
        assert DataItems.ABILITY_DECISION_TREE.value == 1099511627776
        assert DataItems.ERA_DEFINITION.value == 2251799813685248
        assert DataItems.UBS_UPDATE.value == 2150109456


# ── _decorators ─────────────────────────────────────────────────────────


def test_func_timer_returns_result_and_logs(caplog):
    @func_timer
    def add(a, b):
        return a + b

    with caplog.at_level(logging.DEBUG, logger="swgoh_comlink.helpers._decorators"):
        assert add(2, 3) == 5

    assert "add" in caplog.text
    assert "executed in" in caplog.text


@pytest.mark.parametrize("sensitive_key", sorted(_SENSITIVE_KEYS))
def test_func_debug_logger_returns_result_and_masks_sensitive_kwargs(caplog, sensitive_key):
    @func_debug_logger
    def dummy(**kwargs):
        return "ok"

    with caplog.at_level(logging.DEBUG, logger="swgoh_comlink.helpers._decorators"):
        assert dummy(**{sensitive_key: "hidden_value"}, normal="visible") == "ok"

    assert "hidden_value" not in caplog.text
    assert "***" in caplog.text
    assert "visible" in caplog.text


# ── globals ─────────────────────────────────────────────────────────────


def test_logging_formatter_includes_level_function_and_message():
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
    output = LoggingFormatter().format(record)
    assert "hello" in output
    assert "INFO" in output
    assert "my_func" in output


@pytest.mark.parametrize(("args", "name"), [((), "swgoh_comlink.globals"), (("my.custom.logger",), "my.custom.logger")])
def test_get_logger(args, name):
    logger = get_logger(*args)
    assert isinstance(logger, logging.Logger)
    assert logger.name == name


# ── _localization ──────────────────────────────────────────────────────

_R, _B, _I, _U, _S = ANSI_RESET, ANSI_BOLD, ANSI_ITALIC, ANSI_UNDERLINE, ANSI_STRIKE


def _fg(r: int, g: int, b: int) -> str:
    """24-bit ANSI foreground color sequence."""
    return f"\033[38;2;{r};{g};{b}m"


@pytest.mark.parametrize(
    ("hex_color", "expected"),
    [
        pytest.param("FF0000", "\033[38;2;255;0;0m", id="basic"),
        pytest.param("#00FF00", "\033[38;2;0;255;0m", id="hash-prefix"),
        pytest.param("aaBBcc", "\033[38;2;170;187;204m", id="mixed-case"),
    ],
)
def test_hex_to_ansi_truecolor(hex_color, expected):
    assert _hex_to_ansi_truecolor(hex_color) == expected


def _text(value: str) -> dict[str, Any]:
    return {"type": "text", "value": value}


def _tok(kind: str, **fields: Any) -> dict[str, Any]:
    return {"type": kind, **fields}


def _color(r: int, g: int, b: int, a: int = 0xFF) -> dict[str, Any]:
    hex6 = f"{r:02X}{g:02X}{b:02X}"
    return {"type": "color", "r": r, "g": g, "b": b, "a": a, "hex6": hex6, "hex8": f"{hex6}{a:02X}"}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("", [], id="empty"),
        pytest.param("hello world", [_text("hello world")], id="plain"),
        pytest.param("line1\\nline2", [_text("line1"), _tok("newline"), _text("line2")], id="newline-escape"),
        pytest.param(
            "[c][FF0000]red[-][/c]",
            [_tok("color_block_open"), _color(255, 0, 0), _text("red"), _tok("color_reset"), _tok("color_end")],
            id="color-block",
        ),
        pytest.param("[-c]", [_tok("color_end")], id="dash-c-ends-color"),
        pytest.param("[FF0000]red", [_color(255, 0, 0), _text("red")], id="standalone-color"),
        pytest.param("[F0FF23]", [_color(0xF0, 0xFF, 0x23)], id="hex6"),
        pytest.param("[F0A]", [_color(0xFF, 0x00, 0xAA)], id="hex3-expands"),
        pytest.param("[F0A8]", [_color(0xFF, 0x00, 0xAA, 0x88)], id="hex4-rgba"),
        pytest.param("[12345678]", [_color(0x12, 0x34, 0x56, 0x78)], id="hex8-rgba"),
        pytest.param("[F]", [_tok("alpha", a=0xFF)], id="hex1-alpha"),
        pytest.param("[b]bold[/b]", [_tok("bold_open"), _text("bold"), _tok("bold_close")], id="bold"),
        pytest.param("[i]italic[/i]", [_tok("italic_open"), _text("italic"), _tok("italic_close")], id="italic"),
        pytest.param("[u]x[/u]", [_tok("underline_open"), _text("x"), _tok("underline_close")], id="underline"),
        pytest.param("[s]x[/s]", [_tok("strike_open"), _text("x"), _tok("strike_close")], id="strike"),
        pytest.param("[t]x[/t]", [_tok("sprite_open"), _text("x"), _tok("sprite_close")], id="sprite"),
        pytest.param(
            "[sub]a[/sub][sup]b[/sup]",
            [
                *(_tok("sub_open", scale=None), _text("a"), _tok("sub_close")),
                *(_tok("sup_open", scale=None), _text("b"), _tok("sup_close")),
            ],
            id="sub-sup",
        ),
        pytest.param(
            "[sub=1.5]a[/sub][sup=0.8]b[/sup]",
            [
                *(_tok("sub_open", scale=1.5), _text("a"), _tok("sub_close")),
                *(_tok("sup_open", scale=0.8), _text("b"), _tok("sup_close")),
            ],
            id="sub-sup-scaled",
        ),
        pytest.param("[y=2]xx[/y]", [_tok("scale_open", scale=2.0), _text("xx"), _tok("scale_close")], id="scale"),
        # Single-letter named tags must not be misread as a 1-digit alpha literal.
        *(
            pytest.param(f"[{tag}]", [_tok(kind)], id=f"named-tag-{tag}-not-alpha")
            for tag, kind in [
                ("b", "bold_open"),
                ("c", "color_block_open"),
                ("i", "italic_open"),
                ("s", "strike_open"),
                ("t", "sprite_open"),
                ("u", "underline_open"),
            ]
        ),
    ],
)
def test_parse_tokens(text, expected):
    assert _parse_tokens(text) == expected


# Every input rendered in every output format, compared exactly. A missing format means that
# rendering is deliberately not pinned (see the comment on the row).
_RENDERINGS: list[tuple[str, str, dict[str, str]]] = [
    (
        "plain",
        "hello world",
        {
            "bare": "hello world",
            "discord": "hello world",
            "web": "<p>hello world</p>",
            "terminal": "hello world",
        },
    ),
    ("empty", "", {"bare": "", "discord": "", "web": "<p></p>", "terminal": ""}),
    ("newline", "a\\nb", {"bare": "a\nb", "discord": "a\nb", "web": "<p>a\nb</p>", "terminal": "a\nb"}),
    (
        "bold",
        "[b]bold[/b]",
        {
            "bare": "bold",
            "discord": "**bold**",
            "web": "<p><b>bold</b></p>",
            "terminal": f"{_B}bold{_R}",
        },
    ),
    (
        "italic",
        "[i]italic[/i]",
        {
            "bare": "italic",
            "discord": "*italic*",
            "web": "<p><em>italic</em></p>",
            "terminal": f"{_I}italic{_R}",
        },
    ),
    ("underline", "[u]x[/u]", {"bare": "x", "discord": "__x__", "web": "<p><u>x</u></p>", "terminal": f"{_U}x{_R}"}),
    ("strike", "[s]x[/s]", {"bare": "x", "discord": "~~x~~", "web": "<p><s>x</s></p>", "terminal": f"{_S}x{_R}"}),
    (
        "color-block",
        "[c][FF0000]red[/c]",
        {
            "bare": "red",
            "discord": "red",
            "web": '<p><span style="color:#FF0000">red</span></p>',
            "terminal": f"{_fg(255, 0, 0)}red{_R}",
        },
    ),
    (
        "color-reset-then-end",
        "[c][FFAA00]golden[-][/c]",
        {
            "bare": "golden",
            "discord": "golden",
            "web": '<p><span style="color:#FFAA00">golden</span></p>',
            "terminal": f"{_fg(255, 170, 0)}golden{_R}{_R}",
        },
    ),
    (
        "color-reset-within-block",
        "[c][FF0000]red[-]plain[/c]",
        {
            "bare": "redplain",
            "discord": "redplain",
            "web": '<p><span style="color:#FF0000">red</span>plain</p>',
            "terminal": f"{_fg(255, 0, 0)}red{_R}plain{_R}",
        },
    ),
    (
        "color-reset-outside-block",
        "[FF0000]red[-]plain",
        {
            "bare": "redplain",
            "discord": "redplain",
            "web": '<p><span style="color:#FF0000">red</span>plain</p>',
            "terminal": f"{_fg(255, 0, 0)}red{_R}plain",
        },
    ),
    (
        "standalone-color",
        "[00FF00]green",
        {
            "bare": "green",
            "discord": "green",
            "web": '<p><span style="color:#00FF00">green</span></p>',
            "terminal": f"{_fg(0, 255, 0)}green{_R}",
        },
    ),
    (
        "hex3",
        "[F0A]x[/c]",
        {
            "bare": "x",
            "discord": "x",
            "web": '<p><span style="color:#FF00AA">x</span></p>',
            "terminal": f"{_fg(255, 0, 170)}x{_R}",
        },
    ),
    # Terminal output cannot render alpha, but still emits the RGB channel.
    (
        "hex4-rgba",
        "[F0A8]x[/c]",
        {
            "bare": "x",
            "discord": "x",
            "web": '<p><span style="color:rgba(255,0,170,0.533)">x</span></p>',
            "terminal": f"{_fg(255, 0, 170)}x{_R}",
        },
    ),
    (
        "hex8-rgba",
        "[12345678]x[/c]",
        {
            "bare": "x",
            "discord": "x",
            "web": '<p><span style="color:rgba(18,52,86,0.471)">x</span></p>',
            "terminal": f"{_fg(18, 52, 86)}x{_R}",
        },
    ),
    # An alpha literal with no prior color applies to the default white.
    (
        "alpha-without-color",
        "hello[8]world",
        {
            "bare": "helloworld",
            "discord": "helloworld",
            "web": '<p>hello<span style="color:rgba(255,255,255,0.533)">world</span></p>',
            "terminal": f"hello{_fg(255, 255, 255)}world{_R}",
        },
    ),
    (
        "alpha-reuses-color",
        "[FF0000]r[8]still_red[/c]",
        {
            "bare": "rstill_red",
            "discord": "rstill_red",
            "web": '<p><span style="color:#FF0000">r</span><span style="color:rgba(255,0,0,0.533)">still_red</span></p>',
            "terminal": f"{_fg(255, 0, 0)}r{_fg(255, 0, 0)}still_red{_R}",
        },
    ),
    (
        "color-alpha-color",
        "[FF0000]red[8]faded[00FF00]green[/c]",
        {
            "bare": "redfadedgreen",
            "discord": "redfadedgreen",
            "web": (
                '<p><span style="color:#FF0000">red</span><span style="color:rgba(255,0,0,0.533)">faded</span>'
                '<span style="color:#00FF00">green</span></p>'
            ),
            "terminal": f"{_fg(255, 0, 0)}red{_fg(255, 0, 0)}faded{_fg(0, 255, 0)}green{_R}",
        },
    ),
    # Closing a style resets the terminal, so the still-open color must be re-emitted.
    (
        "bold-close-reapplies-color",
        "[c][FF0000][b]styled[/b]text[/c]",
        {
            "bare": "styledtext",
            "discord": "**styled**text",
            "web": '<p><span style="color:#FF0000"><b>styled</b>text</span></p>',
            "terminal": f"{_fg(255, 0, 0)}{_B}styled{_R}{_fg(255, 0, 0)}text{_R}",
        },
    ),
    (
        "italic-close-reapplies-color",
        "[c][FF0000][i]styled[/i]text[/c]",
        {
            "bare": "styledtext",
            "discord": "*styled*text",
            "web": '<p><span style="color:#FF0000"><em>styled</em>text</span></p>',
            "terminal": f"{_fg(255, 0, 0)}{_I}styled{_R}{_fg(255, 0, 0)}text{_R}",
        },
    ),
    (
        "underline-close-reapplies-color",
        "[FF0000][u]red[/u]still",
        {
            "bare": "redstill",
            "discord": "__red__still",
            "web": '<p><span style="color:#FF0000"><u>red</u>still</span></p>',
            "terminal": f"{_fg(255, 0, 0)}{_U}red{_R}{_fg(255, 0, 0)}still{_R}",
        },
    ),
    # Ending the color resets the terminal, so the still-open bold must be re-emitted.
    (
        "color-end-reapplies-bold",
        "[b][c][FF0000]red[/c]still_bold[/b]",
        {
            "bare": "redstill_bold",
            "discord": "**redstill_bold**",
            "web": '<p><b><span style="color:#FF0000">red</span>still_bold</b></p>',
            "terminal": f"{_B}{_fg(255, 0, 0)}red{_R}{_B}still_bold{_R}",
        },
    ),
    (
        "bold-close-keeps-italic",
        "[i][b]both[/b]just_italic[/i]",
        {
            "bare": "bothjust_italic",
            "discord": "***both**just_italic*",
            "web": "<p><em><b>both</b>just_italic</em></p>",
            "terminal": f"{_I}{_B}both{_R}{_I}just_italic{_R}",
        },
    ),
    (
        "italic-close-keeps-bold",
        "[b][i]both[/i]just_bold[/b]",
        {
            "bare": "bothjust_bold",
            "discord": "***both*just_bold**",
            "web": "<p><b><em>both</em>just_bold</b></p>",
            "terminal": f"{_B}{_I}both{_R}{_B}just_bold{_R}",
        },
    ),
    (
        "strike-close-keeps-bold",
        "[b][s]x[/s]still_bold[/b]",
        {
            "bare": "xstill_bold",
            "discord": "**~~x~~still_bold**",
            "web": "<p><b><s>x</s>still_bold</b></p>",
            "terminal": f"{_B}{_S}x{_R}{_B}still_bold{_R}",
        },
    ),
    (
        "nested-bold-italic",
        "[b][i]bold-italic[/i][/b]",
        {
            "bare": "bold-italic",
            "discord": "***bold-italic***",
            "web": "<p><b><em>bold-italic</em></b></p>",
            "terminal": f"{_B}{_I}bold-italic{_R}{_B}{_R}",
        },
    ),
    (
        "nested-bold-underline",
        "[b][u]x[/u][/b]",
        {"bare": "x", "discord": "**__x__**", "web": "<p><b><u>x</u></b></p>", "terminal": f"{_B}{_U}x{_R}{_B}{_R}"},
    ),
    (
        "nested-bold-underline-italic",
        "[b][u][i]x[/i][/u][/b]",
        {
            "bare": "x",
            "discord": "**__*x*__**",
            "web": "<p><b><u><em>x</em></u></b></p>",
            "terminal": f"{_B}{_U}{_I}x{_R}{_B}{_U}{_R}{_B}{_R}",
        },
    ),
    (
        "nested-bold-underline-strike",
        "[b][u][s]x[/s][/u][/b]",
        {
            "bare": "x",
            "discord": "**__~~x~~__**",
            "web": "<p><b><u><s>x</s></u></b></p>",
            "terminal": f"{_B}{_U}{_S}x{_R}{_B}{_U}{_R}{_B}{_R}",
        },
    ),
    (
        "styles-reapplied-after-inner-close",
        "[u][s][b]x[/b]y[/s][/u]",
        {
            "bare": "xy",
            "discord": "__~~**x**y~~__",
            "web": "<p><u><s><b>x</b>y</s></u></p>",
            "terminal": f"{_U}{_S}{_B}x{_R}{_U}{_S}y{_R}{_U}{_R}",
        },
    ),
    # Unclosed styles: terminal and web close them at the end. Discord is not pinned: it leaves
    # the markers open ("**no close"), which may or may not be intended.
    (
        "unclosed-bold",
        "[b]no close",
        {"bare": "no close", "web": "<p><b>no close</b></p>", "terminal": f"{_B}no close{_R}"},
    ),
    (
        "unclosed-four-styles",
        "[b][i][u][s]x",
        {
            "bare": "x",
            "web": "<p><b><em><u><s>x</s></u></em></b></p>",
            "terminal": f"{_B}{_I}{_U}{_S}x{_R}",
        },
    ),
    # Closing a color span closes the styles opened inside it, then reopens them after it.
    (
        "color-end-with-open-styles",
        "[c][FF0000][i][u][s]x[/c]y",
        {
            "bare": "xy",
            "web": '<p><span style="color:#FF0000"><em><u><s>x</s></u></em></span><em><u><s>y</s></u></em></p>',
            "terminal": f"{_fg(255, 0, 0)}{_I}{_U}{_S}x{_R}{_I}{_U}{_S}y{_R}",
        },
    ),
    (
        "color-reset-with-open-styles",
        "[b][FF0000][i]x[-]y[/i][/b]",
        {"bare": "xy", "web": '<p><b><span style="color:#FF0000"><em>x</em></span><em>y</em></b></p>'},
    ),
    (
        "color-change-with-open-styles",
        "[FF0000][i]x[00FF00]y[/i]",
        {
            "bare": "xy",
            "web": '<p><span style="color:#FF0000"><em>x</em></span><span style="color:#00FF00"><em>y</em></span></p>',
        },
    ),
    (
        "alpha-change-with-open-styles",
        "[FF0000][b]x[8]y[/b]",
        {
            "bare": "xy",
            "web": '<p><span style="color:#FF0000"><b>x</b></span>'
            '<span style="color:rgba(255,0,0,0.533)"><b>y</b></span></p>',
        },
    ),
    (
        "unclosed-style-around-color",
        "[b][FF0000]x",
        {"bare": "x", "web": '<p><b><span style="color:#FF0000">x</span></b></p>'},
    ),
    (
        "unclosed-style-inside-color",
        "[FF0000][b]x",
        {"bare": "x", "web": '<p><span style="color:#FF0000"><b>x</b></span></p>'},
    ),
    # Visual-only tags: stripped from text outputs, kept as HTML on the web.
    ("sprite", "[t]icon[/t]", {"bare": "icon", "discord": "icon", "web": "<p>icon</p>", "terminal": "icon"}),
    (
        "sprite-then-color",
        "[t]icon[/t][F0A]red",
        {
            "bare": "iconred",
            "discord": "iconred",
            "web": '<p>icon<span style="color:#FF00AA">red</span></p>',
            "terminal": f"icon{_fg(255, 0, 170)}red{_R}",
        },
    ),
    ("sub", "[sub]x[/sub]", {"bare": "x", "discord": "x", "web": "<p><sub>x</sub></p>", "terminal": "x"}),
    (
        "sub-scaled",
        "[sub=0.8]x[/sub]",
        {
            "bare": "x",
            "discord": "x",
            "web": '<p><sub style="font-size:0.8em">x</sub></p>',
            "terminal": "x",
        },
    ),
    ("sup", "[sup]x[/sup]", {"bare": "x", "discord": "x", "web": "<p><sup>x</sup></p>", "terminal": "x"}),
    (
        "sup-scaled",
        "[sup=1.25]x[/sup]",
        {
            "bare": "x",
            "discord": "x",
            "web": '<p><sup style="font-size:1.25em">x</sup></p>',
            "terminal": "x",
        },
    ),
    ("scale-without-value", "[y]x[/y]", {"bare": "x", "discord": "x", "web": "<p><span>x</span></p>", "terminal": "x"}),
    (
        "scale-integer",
        "[y=2]x[/y]",
        {
            "bare": "x",
            "discord": "x",
            "web": '<p><span style="font-size:2em">x</span></p>',
            "terminal": "x",
        },
    ),
    (
        "scale-float",
        "[y=1.5]big[/y]",
        {
            "bare": "big",
            "discord": "big",
            "web": '<p><span style="font-size:1.5em">big</span></p>',
            "terminal": "big",
        },
    ),
    (
        "sub-sup-scale",
        "[sub=0.8]a[/sub][sup]b[/sup][y=1.2]c[/y]",
        {
            "bare": "abc",
            "discord": "abc",
            "web": '<p><sub style="font-size:0.8em">a</sub><sup>b</sup><span style="font-size:1.2em">c</span></p>',
            "terminal": "abc",
        },
    ),
    (
        "mixed-markup",
        "[b]Title[/b]\\n[c][FFAA00]Gold text[-][/c] and [i]italic[/i]",
        {
            "bare": "Title\nGold text and italic",
            "discord": "**Title**\nGold text and *italic*",
            "web": '<p><b>Title</b>\n<span style="color:#FFAA00">Gold text</span> and <em>italic</em></p>',
            "terminal": f"{_B}Title{_R}\n{_fg(255, 170, 0)}Gold text{_R}{_R} and {_I}italic{_R}",
        },
    ),
    (
        "issue-83-golden",
        "[c][FF0000][b]Boss[/b][-] deals [u]2x[/u] damage[/c]",
        {
            "bare": "Boss deals 2x damage",
            "discord": "**Boss** deals __2x__ damage",
            "web": '<p><span style="color:#FF0000"><b>Boss</b></span> deals <u>2x</u> damage</p>',
            "terminal": f"{_fg(255, 0, 0)}{_B}Boss{_R}{_fg(255, 0, 0)}{_R} deals {_U}2x{_R} damage{_R}",
        },
    ),
]


@pytest.mark.parametrize(
    ("text", "output", "expected"),
    [
        pytest.param(text, output, expected, id=f"{output}-{name}")
        for name, text, rendered in _RENDERINGS
        for output, expected in rendered.items()
    ],
)
def test_parse_swgoh_string(text, output, expected):
    assert parse_swgoh_string(text, output=output) == expected


def test_parse_swgoh_string_defaults_to_bare():
    assert parse_swgoh_string("[b]text[/b]") == "text"


class _NestingChecker(HTMLParser):
    """Record whether every end tag closes the most recently opened element."""

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.well_nested = True

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack.pop() != tag:
            self.well_nested = False


@pytest.mark.parametrize(
    "text",
    [pytest.param(text, id=name) for name, text, _ in _RENDERINGS],
)
def test_web_output_is_well_nested(text):
    checker = _NestingChecker()
    checker.feed(parse_swgoh_string(text, output="web"))
    checker.close()
    assert checker.well_nested
    assert checker.stack == []


# ── Additional quick-win helper tests ──────────────────────────────────
