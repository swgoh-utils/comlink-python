# coding=utf-8
"""Unit tests for GameDataBuilder transformation logic in _builder_base.py.

All tests use inline fixture data and require no running Comlink service.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from swgoh_comlink.StatCalc.data_builder._builder_base import (
    GameDataBuilderBase,
    _ability_special_gp,
    _build_cr_gp_tables,
    _build_gear_data,
    _build_mod_set_data,
    _build_relic_data,
    _build_skills_map,
    _build_stat_tables,
    _build_unit_data,
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


@pytest.mark.parametrize(
    ("value", "expected", "expected_type"),
    [
        (42, 42, int),
        (-5, -5, int),
        (0, 0, int),
        (3.14, 3.14, float),
        (-3.14, -3.14, float),
        # Whole floats are normalized to int.
        (10.0, 10, int),
        (0.0, 0, int),
        ("100", 100, int),
        ("52500000000", 52500000000, int),
        ("3.14", 3.14, float),
        ("10.0", 10, int),
        (" 7 ", 7, int),
        (None, 0, int),
        ("", 0, int),
        ("abc", 0, int),
        # Game data carries ints, floats and decimal strings; nothing else is a number.
        (True, 0, int),
        (False, 0, int),
        (float("inf"), 0, int),
        (float("-inf"), 0, int),
        (float("nan"), 0, int),
        ("inf", 0, int),
        ("nan", 0, int),
        ("1.0e400", 0, int),
    ],
)
def test_num_coerces_to_int_or_float(value: Any, expected: int | float, expected_type: type):
    result = _num(value)
    assert result == expected
    assert type(result) is expected_type


class TestResolveSkills:
    @pytest.mark.parametrize(
        ("refs", "skills_map", "expected_ids"),
        [
            pytest.param([], {"basic01": {"id": "basic01"}}, [], id="no-refs"),
            pytest.param([{"skillId": "x"}], {}, [], id="empty-map"),
            pytest.param([{"skillId": "basic01"}], {"basic01": {"id": "basic01"}}, ["basic01"], id="single"),
            pytest.param(
                [{"skillId": "s1"}, {"skillId": "missing"}, {"skillId": "s2"}],
                {"s1": {"id": "s1"}, "s2": {"id": "s2"}},
                ["s1", "s2"],
                id="unknown-refs-skipped-in-order",
            ),
        ],
    )
    def test_resolves_known_refs(self, refs, skills_map, expected_ids):
        assert [skill["id"] for skill in _resolve_skills(refs, skills_map)] == expected_ids

    def test_returns_copies(self):
        skills_map = {"s1": {"id": "s1", "maxTier": 5}}
        result = _resolve_skills([{"skillId": "s1"}], skills_map)
        result[0]["maxTier"] = 99
        assert skills_map["s1"]["maxTier"] == 5


@pytest.mark.parametrize(
    ("primary_stat", "categories", "expected"),
    [
        pytest.param(2, ["role_attacker"], "strength_role_attacker_mastery", id="strength"),
        pytest.param(3, ["role_tank"], "agility_role_tank_mastery", id="agility"),
        pytest.param(4, ["role_healer"], "intelligence_role_healer_mastery", id="intelligence"),
        pytest.param(99, ["role_support"], "strength_role_support_mastery", id="unknown-stat-is-strength"),
        pytest.param(2, [], "strength_role_attacker_mastery", id="no-role-is-attacker"),
        pytest.param(2, ["role_leader", "role_support"], "strength_role_support_mastery", id="leader-ignored"),
        pytest.param(3, ["role_tank", "role_attacker"], "agility_role_tank_mastery", id="first-role-wins"),
        pytest.param(2, ["faction_jedi", "role_healer"], "strength_role_healer_mastery", id="non-role-ignored"),
    ],
)
def test_mastery_name(primary_stat: int, categories: list[str], expected: str):
    assert _mastery_name(primary_stat, categories) == expected


# ===================================================================
# Group B — Row parsers
# ===================================================================

_STARS = ["ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN"]


def _rows(*pairs: tuple[str, Any]) -> list[dict[str, Any]]:
    return [{"key": key, "value": value} for key, value in pairs]


@pytest.mark.parametrize(
    ("parser", "rows", "expected"),
    [
        pytest.param(
            _rarity_rows,
            _rows(*((f"{name}_STAR", (i + 1) * 10) for i, name in enumerate(_STARS))),
            {str(i): i * 10 for i in range(1, 8)},
            id="rarity-all-seven",
        ),
        pytest.param(
            _rarity_rows, _rows(("THREE_STAR", 30), ("FIVE_STAR", 50)), {"3": 30, "5": 50}, id="rarity-subset"
        ),
        pytest.param(_rarity_rows, _rows(("UNKNOWN", 100)), {}, id="rarity-unknown-skipped"),
        pytest.param(_tier_rows, _rows(("TIER_01", 100), ("TIER_12", 1200)), {"1": 100, "12": 1200}, id="tier"),
        pytest.param(_tier_rows, _rows(("SOMETHING", 5)), {}, id="tier-unknown-skipped"),
        pytest.param(_int_rows, _rows(("1", 0.37), ("2", 0.50)), {"1": 0.37, "2": 0.50}, id="int"),
        # Relic keys are shifted by the relic tier offset (2).
        pytest.param(_relic_rows, _rows(("0", 100), ("1", 200)), {"2": 100, "3": 200}, id="relic-offset"),
        pytest.param(_relic_rows, _rows(("abc", 100)), {}, id="relic-invalid-skipped"),
        pytest.param(_stat_enum_rows, _rows(("STRENGTH", 3), ("MAX_HEALTH", 420)), {"2": 3, "1": 420}, id="stat-enum"),
        pytest.param(_stat_enum_rows, _rows(("NONEXISTENT", 99)), {}, id="stat-enum-unknown-skipped"),
        # Mod CR keeps tier 1, set 0 rows: pips -> level -> value.
        pytest.param(
            _mod_cr_rows,
            _rows(("5:10:1:0", 100), ("5:15:1:0", 150), ("6:10:1:0", 200), ("5:10:2:0", 999), ("5:10:1:1", 999)),
            {"5": {"10": 100, "15": 150}, "6": {"10": 200}},
            id="mod-cr",
        ),
        # Mod GP keeps set 0 rows: pips -> level -> tier -> value.
        pytest.param(
            _mod_gp_rows,
            _rows(("5:10:1:0", 100), ("5:10:2:0", 200), ("6:15:1:0", 300), ("5:10:1:1", 999)),
            {"5": {"10": {"1": 100, "2": 200}}, "6": {"15": {"1": 300}}},
            id="mod-gp",
        ),
        pytest.param(_mod_gp_rows, _rows(("1:2:0", 5)), {}, id="mod-gp-short-key-skipped"),
        # Gear level GP is shifted up one tier; gear 1 is always 0.
        pytest.param(
            _gear_level_rows,
            _rows(("TIER_01", 10), ("TIER_05", 50), ("TIER_13", 130)),
            {"1": 0, "2": 10, "6": 50, "14": 130},
            id="gear-level",
        ),
        # Gear piece slots are 1-based in the key and 0-based in the table.
        pytest.param(
            _gear_piece_gp_rows,
            _rows(("TIER_01:1", 10), ("TIER_01:6", 60), ("2:2", 20)),
            {"1": {"0": 10, "5": 60}, "2": {"1": 20}},
            id="gear-piece",
        ),
        pytest.param(_gear_piece_gp_rows, _rows(("TIER_01", 5)), {}, id="gear-piece-no-slot-skipped"),
        pytest.param(
            _ability_special_gp, _rows(("zeta", 1500), ("omicron", 2000)), {"zeta": 1500, "omicron": 2000}, id="special"
        ),
        # XP rows are 0-indexed in the payload and 1-indexed in the table.
        pytest.param(
            _xp_rows,
            [{"index": 0, "xp": 100}, {"index": 1, "xp": 200}, {"index": 2, "xp": 400}],
            {"1": 100, "2": 200, "3": 400},
            id="xp",
        ),
    ],
)
def test_row_parser(parser: Callable[[list[dict[str, Any]]], dict[str, Any]], rows, expected):
    assert parser(rows) == expected


@pytest.mark.parametrize(
    ("parser", "expected"),
    [
        (_rarity_rows, {}),
        (_tier_rows, {}),
        (_int_rows, {}),
        (_relic_rows, {}),
        (_stat_enum_rows, {}),
        (_mod_cr_rows, {}),
        (_mod_gp_rows, {}),
        (_gear_level_rows, {"1": 0}),
        (_gear_piece_gp_rows, {}),
        (_ability_special_gp, {}),
        (_xp_rows, {}),
    ],
    ids=lambda p: getattr(p, "__name__", None),
)
def test_row_parser_empty_rows(parser: Callable[[list[dict[str, Any]]], dict[str, Any]], expected):
    assert parser([]) == expected


# ===================================================================
# Group C — Intermediate builder functions
# ===================================================================


def _stat(stat_id: int, value: Any) -> dict[str, Any]:
    return {"unitStatId": stat_id, "unscaledDecimalValue": value}


@pytest.mark.parametrize(
    "build",
    [
        _build_stat_tables,
        _build_skills_map,
        _build_gear_data,
        _build_mod_set_data,
        lambda entries: _build_relic_data(entries, {}),
    ],
    ids=["stat-tables", "skills-map", "gear-data", "mod-set-data", "relic-data"],
)
def test_builders_return_empty_for_empty_input(build: Callable[[list[Any]], dict[str, Any]]):
    assert build([]) == {}


def test_build_stat_tables():
    entries = [
        {"id": "stattable_a", "stat": {"stat": [_stat(2, 100), _stat(3, "50.0")]}},
        {"id": "stattable_b", "stat": {"stat": [_stat(1, 10)]}},
        {"id": "other_thing", "stat": {"stat": [_stat(1, 5)]}},  # not a stat table
    ]
    result = _build_stat_tables(entries)
    assert result == {"stattable_a": {"2": 100, "3": 50}, "stattable_b": {"1": 10}}
    assert type(result["stattable_a"]["3"]) is int


def test_build_skills_map():
    def tiers(*tags: str) -> list[dict[str, str]]:
        return [{"powerOverrideTag": tag} for tag in tags]

    skills = [
        {"id": "basic01", "tier": []},
        {"id": "special01", "tier": tiers("", "", "zeta")},
        {"id": "unique01", "tier": tiers("", "zeta", "", "omicron")},
    ]
    # maxTier counts the base tier, so it is len(tier) + 1 and the tier at index i is level i + 2.
    # isZeta means the *last* upgrade is the zeta; a zeta earlier in the list does not count.
    assert _build_skills_map(skills) == {
        "basic01": {"id": "basic01", "maxTier": 1, "isZeta": False, "powerOverrideTags": {}},
        "special01": {"id": "special01", "maxTier": 4, "isZeta": True, "powerOverrideTags": {"4": "zeta"}},
        "unique01": {
            "id": "unique01",
            "maxTier": 5,
            "isZeta": False,
            "powerOverrideTags": {"3": "zeta", "5": "omicron"},
        },
    }


def test_build_gear_data_skips_gear_without_stats():
    equipment = [
        {"id": "g1", "equipmentStat": {"stat": [_stat(1, 500), _stat(6, 25)]}},
        {"id": "g2", "equipmentStat": {"stat": []}},
        {"id": "g3", "equipmentStat": {"stat": [_stat(2, 20)]}},
    ]
    assert _build_gear_data(equipment) == {"g1": {"stats": {"1": 500, "6": 25}}, "g3": {"stats": {"2": 20}}}


def test_build_mod_set_data():
    mod_sets = [
        {"id": "1", "setCount": 4, "completeBonus": {"stat": _stat(1, "0.05")}},
        {"id": "2", "setCount": 2, "completeBonus": {"stat": _stat(5, "10.0")}},
    ]
    result = _build_mod_set_data(mod_sets)
    assert result == {"1": {"id": 1, "count": 4, "value": 0.05}, "2": {"id": 5, "count": 2, "value": 10}}
    assert type(result["2"]["value"]) is int


def test_build_relic_data():
    relic_defs = [
        {"id": "relic_tier_01", "stat": {"stat": [_stat(1, 1000)]}, "relicStatTable": "stattable_relic_01"},
        {"id": "relic_tier_02", "stat": {"stat": []}, "relicStatTable": "nonexistent_table"},
    ]
    assert _build_relic_data(relic_defs, {"stattable_relic_01": {"2": 50, "3": 30}}) == {
        "relic_tier_01": {"stats": {"1": 1000}, "gms": {"2": 50, "3": 30}},
        "relic_tier_02": {"stats": {}, "gms": {}},
    }


# ── CR / GP table routing ──────────────────────────────────────────────
# Each table ID is routed to fixed keys in the CR and/or GP output. The parsers have their own
# tests above, so these check routing: which keys appear, which parser filled each, and which
# CR/GP pairs share one object.

_RARITY = _rows(("SEVEN_STAR", 70))
_TIER = _rows(("TIER_01", 42))
_MOD = _rows(("5:10:1:0", 100))
_RELIC = _rows(("0", 100))
_FACTOR = _rows(("1", 0.5))
_XP = [{"index": 0, "xp": 100}]


@pytest.mark.parametrize(
    ("table_id", "rows", "cr", "gp", "shared"),
    [
        pytest.param("crew_rating_per_unit_rarity", _RARITY, {"crewRarityCR": _rarity_rows},
                     {"unitRarityGP": _rarity_rows}, True, id="unit-rarity"),
        pytest.param("crew_rating_per_gear_piece_at_tier", _TIER, {"gearPieceCR": _tier_rows}, {}, False,
                     id="gear-piece-cr"),
        pytest.param("galactic_power_per_complete_gear_tier_table", _TIER, {"gearLevelCR": _gear_level_rows},
                     {"gearLevelGP": _gear_level_rows}, True, id="gear-level"),
        pytest.param("crew_contribution_multiplier_per_rarity", _RARITY, {"shipRarityFactor": _rarity_rows},
                     {"shipRarityFactor": _rarity_rows}, True, id="ship-rarity-factor"),
        pytest.param("crew_rating_per_mod_rarity_level_tier", _MOD, {"modRarityLevelCR": _mod_cr_rows},
                     {"modRarityLevelTierGP": _mod_gp_rows}, False, id="mods"),
        pytest.param("crew_rating_modifier_per_relic_tier", _RELIC, {"relicTierLevelFactor": _relic_rows}, {}, False,
                     id="relic-level-factor-cr"),
        pytest.param("crew_rating_per_relic_tier", _RELIC, {"relicTierCR": _relic_rows}, {}, False, id="relic-cr"),
        pytest.param("crew_rating_modifier_per_ability_crewless_ships", _FACTOR,
                     {"crewlessAbilityFactor": _int_rows}, {}, False, id="crewless-cr"),
        pytest.param("galactic_power_per_tagged_ability_level_table", _rows(("zeta", 1500)), {},
                     {"abilitySpecialGP": _ability_special_gp}, False, id="ability-special-gp"),
        pytest.param("galactic_power_modifier_per_ship_crew_size_table", _FACTOR, {}, {"crewSizeFactor": _int_rows},
                     False, id="crew-size"),
        pytest.param("galactic_power_per_relic_tier", _RELIC, {}, {"relicTierGP": _relic_rows}, False, id="relic-gp"),
        pytest.param("galactic_power_modifier_per_relic_tier", _RELIC, {}, {"relicTierLevelFactor": _relic_rows},
                     False, id="relic-level-factor-gp"),
        pytest.param("galactic_power_per_tier_slot_table", _rows(("TIER_01:1", 10)), {},
                     {"gearPieceGP": _gear_piece_gp_rows}, False, id="gear-piece-gp"),
        pytest.param("galactic_power_modifier_per_ability_crewless_ships", _FACTOR, {},
                     {"crewlessAbilityFactor": _int_rows}, False, id="crewless-gp"),
        pytest.param("strength_role_attacker_mastery", _rows(("STRENGTH", 5)),
                     {"strength_role_attacker_mastery": _stat_enum_rows}, {}, False, id="mastery"),
        pytest.param("unknown_table", _RARITY, {}, {}, False, id="unknown"),
    ],
)  # fmt: skip
def test_cr_gp_table_routing(table_id: str, rows, cr: dict[str, Any], gp: dict[str, Any], shared: bool):
    built_cr, built_gp = _build_cr_gp_tables([{"id": table_id, "row": rows}], [])
    _assert_routed(built_cr, built_gp, cr, gp, rows, shared)


@pytest.mark.parametrize(
    ("table_id", "cr", "gp", "shared"),
    [
        pytest.param("crew_rating_per_unit_level", {"unitLevelCR": _xp_rows}, {"unitLevelGP": _xp_rows}, True,
                     id="unit-level"),
        pytest.param("crew_rating_per_ability_level", {"abilityLevelCR": _xp_rows}, {"abilityLevelGP": _xp_rows},
                     True, id="ability-level"),
        pytest.param("galactic_power_per_ship_level_table", {}, {"shipLevelGP": _xp_rows}, False, id="ship-level"),
        pytest.param("galactic_power_per_ship_ability_level_table", {}, {"shipAbilityLevelGP": _xp_rows}, False,
                     id="ship-ability-level"),
        pytest.param("unknown_xp_table", {}, {}, False, id="unknown"),
    ],
)  # fmt: skip
def test_cr_gp_xp_table_routing(table_id: str, cr: dict[str, Any], gp: dict[str, Any], shared: bool):
    built_cr, built_gp = _build_cr_gp_tables([], [{"id": table_id, "row": _XP}])
    _assert_routed(built_cr, built_gp, cr, gp, _XP, shared)


def _assert_routed(built_cr, built_gp, cr, gp, rows, shared: bool) -> None:
    assert built_cr == {key: parser(rows) for key, parser in cr.items()}
    assert built_gp == {key: parser(rows) for key, parser in gp.items()}
    assert all(value for value in [*built_cr.values(), *built_gp.values()])  # never vacuously empty
    if shared:
        ((cr_value,), (gp_value,)) = built_cr.values(), built_gp.values()
        assert cr_value is gp_value


def test_cr_gp_tables_empty_inputs():
    assert _build_cr_gp_tables([], []) == ({}, {})


# ===================================================================
# Group D — Units and the full build
# ===================================================================


def _char_unit(base_id: str, **overrides: Any) -> dict[str, Any]:
    return {
        "baseId": base_id,
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
        **overrides,
    }


def _ship_unit(base_id: str, **overrides: Any) -> dict[str, Any]:
    return {
        "baseId": base_id,
        "obtainable": True,
        "obtainableTime": "0",
        "rarity": 1,
        "combatType": 2,
        "primaryUnitStat": 2,
        "baseStat": {"stat": []},
        "skillReference": [],
        "crewContributionTableId": "",
        "crew": [],
        "statProgressionId": "",
        **overrides,
    }


def test_build_character():
    skills_map = {"basic01": {"id": "basic01", "maxTier": 8, "isZeta": False, "powerOverrideTags": {}}}
    unit = _char_unit(
        "BOSSK",
        unitTier=[
            {"tier": 1, "baseStat": {"stat": [_stat(1, 100)]}, "equipmentSet": ["eq001"]},
            {"tier": 2, "baseStat": {"stat": []}, "equipmentSet": ["eq002"]},
        ],
        skillReference=[{"skillId": "basic01"}],
        categoryId=["role_tank"],
        relicDefinition={"relicTierDefinitionId": ["relic_def_01_tier_0", "relic_def_01_tier_1"]},
        statProgressionId="stattable_bossk",
    )

    result = _build_unit_data([unit], {"stattable_bossk": {"2": 50}}, skills_map)

    assert result == {
        "BOSSK": {
            "combatType": 1,
            "primaryStat": 2,
            "gearLvl": {"1": {"gear": ["eq001"], "stats": {"1": 100}}, "2": {"gear": ["eq002"], "stats": {}}},
            "growthModifiers": {"1": {"2": 50}},
            "skills": [skills_map["basic01"]],
            # Relic tier ids are keyed by their numeric suffix plus the relic tier offset (2).
            "relic": {"2": "relic_def_01_tier_0", "3": "relic_def_01_tier_1"},
            "masteryModifierID": "strength_role_tank_mastery",
        }
    }


def test_build_ship_collects_crew_skills():
    skills_map = {
        "ship_skill": {"id": "ship_skill", "maxTier": 8, "isZeta": False, "powerOverrideTags": {}},
        "crew_skill": {"id": "crew_skill", "maxTier": 3, "isZeta": False, "powerOverrideTags": {}},
    }
    unit = _ship_unit(
        "SHIP1",
        baseStat={"stat": [_stat(1, 5000)]},
        skillReference=[{"skillId": "ship_skill"}],
        crewContributionTableId="crew_table",
        crew=[
            {"unitId": "PILOT_A", "skillReference": [{"skillId": "crew_skill"}]},
            {"unitId": "PILOT_B", "skillReference": []},
        ],
    )

    result = _build_unit_data([unit], {"crew_table": {"5": 0.5}}, skills_map)

    assert result == {
        "SHIP1": {
            "combatType": 2,
            "primaryStat": 2,
            "stats": {"1": 5000},
            "growthModifiers": {},
            "skills": [skills_map["ship_skill"], skills_map["crew_skill"]],
            "crewStats": {"5": 0.5},
            "crew": ["PILOT_A", "PILOT_B"],
        }
    }


@pytest.mark.parametrize("make_unit", [_char_unit, _ship_unit], ids=["character", "ship"])
@pytest.mark.parametrize("seven_star", [7, "SEVEN_STAR"], ids=["int-rarity", "enum-rarity"])
def test_growth_modifiers_across_rarities(make_unit: Callable[..., dict[str, Any]], seven_star: Any):
    """Every rarity row of a unit contributes its stat progression; enum rarities are read as numbers."""
    units = [
        make_unit("UNIT1", statProgressionId="stattable_unit1_r1"),
        make_unit("UNIT1", rarity=seven_star, statProgressionId="stattable_unit1_r7"),
    ]
    stat_progression = [
        {"id": "stattable_unit1_r1", "stat": {"stat": [_stat(2, 10)]}},
        {"id": "stattable_unit1_r7", "stat": {"stat": [_stat(2, 70)]}},
    ]

    result = GameDataBuilderBase._build_game_data({"units": units, "statProgression": stat_progression})

    assert result["unitData"]["UNIT1"]["growthModifiers"] == {"1": {"2": 10}, "7": {"2": 70}}


@pytest.mark.parametrize("make_unit", [_char_unit, _ship_unit], ids=["character", "ship"])
@pytest.mark.parametrize("rarities", [[2, 7], [7, 2], ["SEVEN_STAR", "TWO_STAR"]], ids=["asc", "desc", "enum"])
def test_unit_without_one_star_row_uses_lowest_rarity_as_base(make_unit: Callable[..., dict[str, Any]], rarities):
    """Units that start above 1★ (e.g. ADELPHIRANGER at 2★) have no rarity-1 row but must still be built."""
    units = [make_unit("STARTS_AT_TWO", rarity=r, statProgressionId=f"stattable_{r}") for r in rarities]

    result = _build_unit_data(units, {}, {})

    assert list(result) == ["STARTS_AT_TWO"]


@pytest.mark.parametrize(
    "excluded",
    [
        pytest.param({"obtainable": False}, id="not-obtainable"),
        pytest.param({"obtainableTime": "123"}, id="obtainable-later"),
        pytest.param({"baseId": ""}, id="no-base-id"),
    ],
)
def test_unobtainable_or_unidentified_units_are_excluded(excluded: dict[str, Any]):
    units = [_char_unit("PLAYABLE"), _char_unit("EXCLUDED", **excluded)]

    assert list(_build_unit_data(units, {}, {})) == ["PLAYABLE"]


def test_build_game_data_from_empty_raw_has_six_empty_sections():
    assert GameDataBuilderBase._build_game_data({}) == {
        "unitData": {},
        "gearData": {},
        "modSetData": {},
        "crTables": {},
        "gpTables": {},
        "relicData": {},
    }
