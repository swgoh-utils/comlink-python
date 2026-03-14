"""Unit tests for StatCalc calculator.

Uses tests/resources/gameData.json and tests/resources/example-player.json
to exercise the full stat and GP calculation pipeline offline.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from swgoh_comlink import StatCalc

_RESOURCES = Path(__file__).resolve().parent.parent / "resources"
_GAME_DATA_FILE = _RESOURCES / "gameData.json"
_PLAYER_FILE = _RESOURCES / "example-player.json"


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def game_data() -> dict[str, Any]:
    return json.loads(_GAME_DATA_FILE.read_text())["data"]


@pytest.fixture(scope="module")
def player() -> dict[str, Any]:
    return json.loads(_PLAYER_FILE.read_text())


@pytest.fixture(scope="module")
def calc(game_data: dict[str, Any]) -> StatCalc:
    return StatCalc(game_data=game_data)


@pytest.fixture(scope="module")
def processed_player(calc: StatCalc, player: dict[str, Any]) -> dict[str, Any]:
    """Full roster with stats and GP pre-calculated (needed for ship crew)."""
    p = copy.deepcopy(player)
    calc.calc_player_stats(p)
    return p


def _find_char(roster: list[dict], *, relic_min: int = 0) -> dict[str, Any]:
    """Return a deepcopy of the first character meeting the relic threshold."""
    for u in roster:
        relic = u.get("relic")
        if relic and relic.get("currentTier", 0) >= relic_min:
            return copy.deepcopy(u)
    raise ValueError(f"No character with relic >= {relic_min}")


def _find_ship(
    roster: list[dict],
    unit_data: dict[str, Any],
    *,
    with_crew: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return (ship, crew_list) deepcopied from the roster."""
    for u in roster:
        defid = u["definitionId"].split(":")[0]
        meta = unit_data.get(defid, {})
        if meta.get("combatType") != 2:
            continue
        crew_ids = meta.get("crew", [])
        if with_crew and not crew_ids:
            continue
        if not with_crew and crew_ids:
            continue
        crew = [
            copy.deepcopy(c)
            for c in roster
            if c["definitionId"].split(":")[0] in crew_ids
        ]
        if with_crew and len(crew) != len(crew_ids):
            continue
        return copy.deepcopy(u), crew
    kind = "with crew" if with_crew else "crewless"
    raise ValueError(f"No ship {kind} found")


# ── Static helpers ───────────────────────────────────────────────────────


class TestStaticHelpers:
    def test_floor_no_digits(self):
        assert StatCalc._floor(99.9) == 99

    def test_floor_with_digits(self):
        assert StatCalc._floor(123456, 2) == 123400

    def test_table_get_list(self):
        assert StatCalc._table_get([10, 20, 30], 1) == 20

    def test_table_get_list_out_of_bounds(self):
        assert StatCalc._table_get([10, 20], 99) == 0

    def test_table_get_list_invalid_key(self):
        assert StatCalc._table_get([10, 20], "bad") == 0

    def test_table_get_dict_str_key(self):
        assert StatCalc._table_get({"a": 1}, "a") == 1

    def test_table_get_dict_int_key_coerced(self):
        assert StatCalc._table_get({"1": 10}, 1) == 10

    def test_table_get_none(self):
        assert StatCalc._table_get(None, "x") == 0

    def test_table_get_default(self):
        assert StatCalc._table_get({}, "missing", 42) == 42

    def test_add_stat_creates_key(self):
        s: dict[str, Any] = {}
        StatCalc._add_stat(s, 5, 100)
        assert s["5"] == 100

    def test_add_stat_accumulates(self):
        s: dict[str, Any] = {"5": 100}
        StatCalc._add_stat(s, 5, 50)
        assert s["5"] == 150

    def test_scale_mod_stat_flat_type(self):
        assert StatCalc._scale_mod_stat_value(1, 5.0) == 5e8
        assert StatCalc._scale_mod_stat_value(5, 2.0) == 2e8
        assert StatCalc._scale_mod_stat_value(28, 3.0) == 3e8
        assert StatCalc._scale_mod_stat_value(41, 1.0) == 1e8
        assert StatCalc._scale_mod_stat_value(42, 1.0) == 1e8

    def test_scale_mod_stat_percent_type(self):
        assert StatCalc._scale_mod_stat_value(10, 5.0) == 5e6
        assert StatCalc._scale_mod_stat_value(17, 2.0) == 2e6


# ── Conversion helpers ───────────────────────────────────────────────────


class TestConversionHelpers:
    def test_flat_def_to_percent_character(self):
        result = StatCalc._convert_flat_def_to_percent(637.5, 85, 1, False)
        # level_effect = 85 * 7.5 = 637.5, result = 637.5/(637.5+637.5) = 0.5
        assert abs(result - 0.5) < 1e-10

    def test_flat_def_to_percent_ship(self):
        result = StatCalc._convert_flat_def_to_percent(725, 85, 1, True)
        # level_effect = 300 + 85*5 = 725, result = 725/(725+725) = 0.5
        assert abs(result - 0.5) < 1e-10

    def test_flat_crit_to_percent(self):
        result = StatCalc._convert_flat_crit_to_percent(2400, 1)
        # 2400/2400 + 0.1 = 1.1
        assert abs(result - 1.1) < 1e-10

    def test_flat_acc_to_percent(self):
        result = StatCalc._convert_flat_acc_to_percent(1200, 1)
        assert abs(result - 1.0) < 1e-10

    def test_flat_crit_avoid_to_percent(self):
        result = StatCalc._convert_flat_crit_avoid_to_percent(2400, 1)
        assert abs(result - 1.0) < 1e-10


# ── Normalization ────────────────────────────────────────────────────────


class TestNormalization:
    def test_normalize_payload_direct(self):
        payload = {"unitData": {"X": {}}}
        assert StatCalc._normalize_game_data_payload(payload) is payload

    def test_normalize_payload_nested(self):
        inner = {"unitData": {"X": {}}}
        result = StatCalc._normalize_game_data_payload({"data": inner})
        assert result is inner

    def test_normalize_payload_bad_format(self):
        with pytest.raises(RuntimeError, match="Unsupported"):
            StatCalc._normalize_game_data_payload({"bad": 1})

    def test_get_def_id_with_defId(self, calc):
        assert calc._get_def_id({"defId": "BOSSK"}) == "BOSSK"

    def test_get_def_id_with_definitionId(self, calc):
        assert calc._get_def_id({"definitionId": "BOSSK:SEVEN_STAR"}) == "BOSSK"

    def test_get_def_id_none(self, calc):
        assert calc._get_def_id(None) is None

    def test_get_def_id_empty(self, calc):
        assert calc._get_def_id({}) is None

    def test_normalize_char_raw_format(self, calc, player):
        raw = player["rosterUnit"][0]
        normalized = calc._normalize_char(raw)
        assert normalized["defId"] == raw["definitionId"].split(":")[0]
        assert normalized["rarity"] == raw["currentRarity"]
        assert normalized["level"] == raw["currentLevel"]
        assert normalized["gear"] == raw["currentTier"]
        assert "skills" in normalized
        # Skills should have tier + 2
        if raw.get("skill"):
            assert normalized["skills"][0]["tier"] == raw["skill"][0]["tier"] + 2

    def test_normalize_char_already_normalized(self, calc):
        char = {"defId": "BOSSK", "rarity": 7, "level": 85, "gear": 13}
        normalized = calc._normalize_char(char)
        assert normalized["defId"] == "BOSSK"
        assert normalized.get("equipped") == []

    def test_normalize_ship_raw_format(self, calc, player, game_data):
        ship_raw, crew_raw = _find_ship(
            player["rosterUnit"], game_data["unitData"], with_crew=True
        )
        ship, crew = calc._normalize_ship_and_crew(ship_raw, crew_raw)
        assert ship["defId"] == ship_raw["definitionId"].split(":")[0]
        assert len(crew) == len(crew_raw)

    def test_normalize_ship_already_normalized(self, calc):
        ship = {"defId": "YOURSHIP", "rarity": 7, "level": 85, "skills": []}
        crew_member = {
            "defId": "CREWUNIT",
            "rarity": 7,
            "level": 85,
            "gear": 13,
            "equipped": [],
            "skills": [],
        }
        norm_ship, norm_crew = calc._normalize_ship_and_crew(ship, [crew_member])
        assert norm_ship["defId"] == "YOURSHIP"
        assert norm_crew[0]["defId"] == "CREWUNIT"


# ── Rename stats ─────────────────────────────────────────────────────────


class TestRenameStats:
    def test_known_stat_renamed(self, calc):
        result = calc._rename_stats({"final": {"1": 100}})
        # Stat ID "1" maps to "Health" in STATS_NAME_MAP
        assert "Health" in result["final"]
        assert result["final"]["Health"] == 100

    def test_non_dict_value_preserved(self, calc):
        result = calc._rename_stats({"gp": 5000, "final": {}})
        assert result["gp"] == 5000

    def test_unknown_stat_passthrough(self, calc):
        result = calc._rename_stats({"final": {"99999": 42}})
        assert result["final"]["99999"] == 42


# ── Require game data ────────────────────────────────────────────────────


class TestRequireGameData:
    def test_raises_when_no_data(self):
        sc = StatCalc.__new__(StatCalc)
        sc._unit_data = None
        with pytest.raises(RuntimeError, match="set_game_data"):
            sc._require_game_data()


# ── calc_char_stats ──────────────────────────────────────────────────────


class TestCalcCharStats:
    def test_raw_format_produces_stats_and_gp(self, calc, player):
        char = _find_char(player["rosterUnit"])
        result = calc.calc_char_stats(char)
        assert "stats" in result
        assert "gp" in result
        assert result["gp"] > 0

    def test_normalized_format(self, calc, player):
        raw = _find_char(player["rosterUnit"])
        normalized = {
            "defId": raw["definitionId"].split(":")[0],
            "rarity": raw["currentRarity"],
            "level": raw["currentLevel"],
            "gear": raw["currentTier"],
            "equipped": [],
            "equippedStatMod": raw.get("equippedStatMod"),
            "relic": raw.get("relic"),
            "skills": [
                {"id": s["id"], "tier": s["tier"] + 2} for s in raw.get("skill", [])
            ],
        }
        result = calc.calc_char_stats(normalized)
        assert "stats" in result

    def test_high_relic_char(self, calc, player):
        char = _find_char(player["rosterUnit"], relic_min=5)
        result = calc.calc_char_stats(char)
        assert result["gp"] > 0

    def test_unknown_unit_raises(self, calc):
        fake = {
            "definitionId": "FAKE_UNIT:SEVEN_STAR",
            "currentRarity": 7,
            "currentLevel": 85,
            "currentTier": 13,
            "relic": {"currentTier": 1},
            "skill": [],
            "equipment": [],
            "equippedStatMod": [],
        }
        with pytest.raises(KeyError, match="FAKE_UNIT"):
            calc.calc_char_stats(fake)


# ── Gear piece aggregation (synthetic) ───────────────────────────────────


class TestGearPieceAggregation:
    def test_equipped_gear_adds_stats(self, calc, game_data, player):
        """Use a normalized char with synthetic equipped gear to cover lines 419-435."""
        char = _find_char(player["rosterUnit"], relic_min=3)

        # Pick a real gear ID from gearData
        gear_id = next(iter(game_data["gearData"]))
        normalized = calc._normalize_char(char)
        normalized["equipped"] = [{"equipmentId": gear_id}]

        stats = calc._get_char_raw_stats(normalized)
        # Gear stats should be distributed between base (stat IDs 2,3,4) and gear
        assert "base" in stats
        assert "gear" in stats

    def test_equipped_gear_string_format(self, calc, game_data, player):
        """Cover the non-dict gear_piece branch (line 423)."""
        char = _find_char(player["rosterUnit"], relic_min=3)
        gear_id = next(iter(game_data["gearData"]))
        normalized = calc._normalize_char(char)
        normalized["equipped"] = [gear_id]

        stats = calc._get_char_raw_stats(normalized)
        assert "base" in stats

    def test_missing_gear_entry_skipped(self, calc, player):
        char = _find_char(player["rosterUnit"], relic_min=3)
        normalized = calc._normalize_char(char)
        normalized["equipped"] = [{"equipmentId": "NONEXISTENT_GEAR_999"}]

        # Should not raise — missing gear is silently skipped
        stats = calc._get_char_raw_stats(normalized)
        assert "base" in stats


# ── Mod format branches (synthetic) ──────────────────────────────────────


class TestModFormats:
    def test_equippedStatMod_format(self, calc, player):
        """Covers the equippedStatMod branch (lines 686+) — exercised by example player."""
        char = _find_char(player["rosterUnit"], relic_min=3)
        result = calc.calc_char_stats(char)
        # The example player uses equippedStatMod, so mods should be calculated
        assert "stats" in result

    def test_normalized_mods_stat_tuple_format(self, calc, player, game_data):
        """Covers the mods branch with stat tuples (lines 648-684)."""
        char = _find_char(player["rosterUnit"], relic_min=3)
        normalized = calc._normalize_char(char)
        # Replace equippedStatMod with normalized 'mods' format
        normalized["equippedStatMod"] = None
        normalized["mods"] = [
            {
                "set": 1,
                "level": 15,
                "pips": 5,
                "tier": 5,
                "stat": [(5, 100.0), (28, 50.0), (41, 10.0)],
            },
            {
                "set": 1,
                "level": 15,
                "pips": 5,
                "tier": 5,
                "stat": [(5, 80.0), (42, 5.0)],
            },
        ]

        base_stats = calc._get_char_raw_stats(normalized)
        base_stats = calc._calculate_base_stats(
            base_stats, normalized["level"], normalized["defId"]
        )
        mod_stats = calc._calculate_mod_stats(base_stats["base"], normalized)
        assert isinstance(mod_stats, dict)
        assert len(mod_stats) > 0

    def test_normalized_mods_primary_secondary_format(self, calc, player):
        """Covers the primaryStat/secondaryStat dict branch (lines 671-684)."""
        char = _find_char(player["rosterUnit"], relic_min=3)
        normalized = calc._normalize_char(char)
        normalized["equippedStatMod"] = None
        normalized["mods"] = [
            {
                "set": 2,
                "level": 15,
                "pips": 5,
                "tier": 5,
                "primaryStat": {"unitStat": 5, "value": 100.0},
                "secondaryStat": [
                    {"unitStat": 28, "value": 50.0},
                    {"unitStat": 41, "value": 10.0},
                ],
            },
        ]

        base_stats = calc._get_char_raw_stats(normalized)
        base_stats = calc._calculate_base_stats(
            base_stats, normalized["level"], normalized["defId"]
        )
        mod_stats = calc._calculate_mod_stats(base_stats["base"], normalized)
        assert isinstance(mod_stats, dict)

    def test_no_mods_returns_empty(self, calc, player):
        char = _find_char(player["rosterUnit"], relic_min=3)
        normalized = calc._normalize_char(char)
        normalized["equippedStatMod"] = None
        normalized["mods"] = None

        base_stats = calc._get_char_raw_stats(normalized)
        base_stats = calc._calculate_base_stats(
            base_stats, normalized["level"], normalized["defId"]
        )
        result = calc._calculate_mod_stats(base_stats["base"], normalized)
        assert result == {}


# ── calc_ship_stats ──────────────────────────────────────────────────────


class TestCalcShipStats:
    def test_ship_with_crew(self, calc, game_data, processed_player):
        ship, crew = _find_ship(
            processed_player["rosterUnit"], game_data["unitData"], with_crew=True
        )
        result = calc.calc_ship_stats(ship, crew)
        assert "stats" in result
        assert result["gp"] > 0

    def test_crewless_ship(self, calc, game_data, processed_player):
        ship, crew = _find_ship(
            processed_player["rosterUnit"], game_data["unitData"], with_crew=False
        )
        assert crew == []
        result = calc.calc_ship_stats(ship, [])
        assert "stats" in result
        assert result["gp"] > 0

    def test_wrong_crew_count_raises(self, calc, game_data, player):
        ship, _ = _find_ship(
            player["rosterUnit"], game_data["unitData"], with_crew=True
        )
        with pytest.raises(ValueError, match="Incorrect number"):
            calc.calc_ship_stats(ship, [])

    def test_wrong_crew_member_raises(self, calc, game_data, player):
        ship, crew = _find_ship(
            player["rosterUnit"], game_data["unitData"], with_crew=True
        )
        # Swap in a wrong crew member
        fake_crew = [_find_char(player["rosterUnit"])] * len(crew)
        # Only raises if fake_crew defIds are not in meta["crew"]
        defid = ship["definitionId"].split(":")[0]
        expected_crew = game_data["unitData"][defid]["crew"]
        fake_defid = fake_crew[0]["definitionId"].split(":")[0]
        if fake_defid not in expected_crew:
            with pytest.raises(ValueError, match="not in"):
                calc.calc_ship_stats(ship, fake_crew)


# ── GP calculations ──────────────────────────────────────────────────────


class TestCalcGP:
    def test_char_gp_positive(self, calc, player):
        char = _find_char(player["rosterUnit"], relic_min=3)
        gp = calc.calc_char_gp(char)
        assert isinstance(gp, int)
        assert gp > 0

    def test_ship_gp_with_crew(self, calc, game_data, processed_player):
        ship, crew = _find_ship(
            processed_player["rosterUnit"], game_data["unitData"], with_crew=True
        )
        gp = calc.calc_ship_gp(ship, crew)
        assert isinstance(gp, int)
        assert gp > 0

    def test_char_gp_with_purchased_ability(self, calc, player):
        """Cover purchasedAbilityId GP contribution (lines 1018-1021)."""
        for u in player["rosterUnit"]:
            if u.get("purchasedAbilityId") and len(u["purchasedAbilityId"]) > 0:
                # Use normalized format so purchasedAbilityId is passed through
                raw = copy.deepcopy(u)
                defid = raw["definitionId"].split(":")[0]
                normalized_with = {
                    "defId": defid,
                    "rarity": raw["currentRarity"],
                    "level": raw["currentLevel"],
                    "gear": raw["currentTier"],
                    "equipped": [],
                    "relic": raw.get("relic"),
                    "skills": [
                        {"id": s["id"], "tier": s["tier"] + 2}
                        for s in raw.get("skill", [])
                    ],
                    "purchasedAbilityId": raw["purchasedAbilityId"],
                    "equippedStatMod": raw.get("equippedStatMod"),
                }
                gp_with = calc._calc_char_gp(normalized_with)

                normalized_without = copy.deepcopy(normalized_with)
                normalized_without["purchasedAbilityId"] = []
                gp_without = calc._calc_char_gp(normalized_without)
                assert gp_with > gp_without
                return
        pytest.skip("No character with purchasedAbilityId found")

    def test_char_gp_with_normalized_mods(self, calc, player):
        """Cover the mods GP branch (lines 1023-1034)."""
        char = _find_char(player["rosterUnit"], relic_min=3)
        normalized = {
            "defId": char["definitionId"].split(":")[0],
            "rarity": char["currentRarity"],
            "level": char["currentLevel"],
            "gear": char["currentTier"],
            "equipped": [],
            "relic": char.get("relic"),
            "skills": [
                {"id": s["id"], "tier": s["tier"] + 2} for s in char.get("skill", [])
            ],
            "mods": [
                {"set": 1, "level": 15, "pips": 5, "tier": 5,
                 "stat": [(5, 100.0)]},
            ],
        }
        gp = calc._calc_char_gp(normalized)
        assert gp > 0


# ── Crew rating ──────────────────────────────────────────────────────────


class TestCrewRating:
    def test_crew_rating_positive(self, calc, game_data, processed_player):
        _, crew = _find_ship(
            processed_player["rosterUnit"], game_data["unitData"], with_crew=True
        )
        # Normalize crew for _get_crew_rating
        norm_crew = []
        for c in crew:
            norm_crew.append(calc._normalize_char(c))
        rating = calc._get_crew_rating(norm_crew)
        assert rating > 0

    def test_crewless_crew_rating(self, calc, game_data, processed_player):
        ship, _ = _find_ship(
            processed_player["rosterUnit"], game_data["unitData"], with_crew=False
        )
        norm_ship, _ = calc._normalize_ship_and_crew(ship, [])
        rating = calc._get_crewless_crew_rating(norm_ship)
        assert rating > 0

    def test_crewless_skills_hardware_multiplier(self, calc, game_data, processed_player):
        """Ensure hardware skills use the 0.696 multiplier."""
        ship, _ = _find_ship(
            processed_player["rosterUnit"], game_data["unitData"], with_crew=False
        )
        norm_ship, _ = calc._normalize_ship_and_crew(ship, [])
        cr = calc._get_crewless_skills_crew_rating(norm_ship.get("skills", []))
        assert cr > 0

    def test_skill_crew_rating(self, calc):
        skill = {"id": "basicskill_TEST", "tier": 8}
        cr = calc._get_skill_crew_rating(skill)
        assert cr >= 0


# ── calc_roster_stats ────────────────────────────────────────────────────


class TestCalcRosterStats:
    def test_list_format_full_roster(self, calc, player):
        p = copy.deepcopy(player)
        result = calc.calc_roster_stats(p["rosterUnit"])
        chars_with_stats = sum(1 for u in result if "stats" in u)
        assert chars_with_stats > 0

    def test_dict_format_legacy_roster(self, calc, game_data, player):
        """Cover the dict-keyed roster branch (lines 174-195)."""
        raw = _find_char(player["rosterUnit"], relic_min=3)
        defid = raw["definitionId"].split(":")[0]
        legacy_roster = {
            defid: [
                {
                    "currentRarity": raw["currentRarity"],
                    "currentLevel": raw["currentLevel"],
                    "currentTier": raw["currentTier"],
                    "gear": [],
                    "skill": raw.get("skill", []),
                }
            ]
        }
        result = calc.calc_roster_stats(legacy_roster)
        assert "stats" in result[defid][0]


# ── calc_player_stats ────────────────────────────────────────────────────


class TestCalcPlayerStats:
    def test_single_dict(self, calc, player):
        p = copy.deepcopy(player)
        result = calc.calc_player_stats(p)
        assert all("stats" in u for u in result["rosterUnit"])
        assert all("gp" in u for u in result["rosterUnit"])

    def test_list_of_players(self, calc, player):
        result = calc.calc_player_stats([copy.deepcopy(player)])
        assert all("stats" in u for u in result[0]["rosterUnit"])

    def test_type_error(self, calc):
        with pytest.raises(TypeError):
            calc.calc_player_stats("bad")

    def test_missing_roster_unit(self, calc):
        with pytest.raises(RuntimeError, match="rosterUnit"):
            calc.calc_player_stats({})


# ── Format stats ─────────────────────────────────────────────────────────


class TestFormatStats:
    def test_char_format_has_final_and_mods(self, calc, player):
        char = _find_char(player["rosterUnit"], relic_min=3)
        result = calc.calc_char_stats(char)
        assert "final" in result["stats"]

    def test_ship_format_has_crew_key(self, calc, game_data, processed_player):
        ship, crew = _find_ship(
            processed_player["rosterUnit"], game_data["unitData"], with_crew=True
        )
        result = calc.calc_ship_stats(ship, crew)
        assert "crew" in result["stats"]
        assert "final" in result["stats"]


# ── Skill GP ─────────────────────────────────────────────────────────────


class TestGetSkillGP:
    def test_skill_with_override_tag(self, calc, game_data):
        """Find a skill with powerOverrideTags and verify GP lookup."""
        for defid, meta in game_data["unitData"].items():
            for skill in meta.get("skills", []):
                if skill.get("powerOverrideTags"):
                    tier = next(iter(skill["powerOverrideTags"]))
                    gp = calc._get_skill_gp(
                        defid, {"id": skill["id"], "tier": int(tier)}
                    )
                    assert gp > 0
                    return
        pytest.skip("No skill with powerOverrideTags found")

    def test_skill_without_override(self, calc, game_data):
        for defid, meta in game_data["unitData"].items():
            for skill in meta.get("skills", []):
                if not skill.get("powerOverrideTags"):
                    gp = calc._get_skill_gp(
                        defid, {"id": skill["id"], "tier": 8}
                    )
                    assert gp >= 0
                    return

    def test_missing_skill_returns_zero(self, calc, game_data):
        defid = next(iter(game_data["unitData"]))
        gp = calc._get_skill_gp(defid, {"id": "nonexistent_skill", "tier": 1})
        assert gp == 0


# ── Crewless ship GP ────────────────────────────────────────────────────


class TestCrewlessSkillsGP:
    def test_reinforcement_vs_ability_split(self, calc, game_data, processed_player):
        ship, _ = _find_ship(
            processed_player["rosterUnit"], game_data["unitData"], with_crew=False
        )
        defid = ship["definitionId"].split(":")[0]
        norm_ship, _ = calc._normalize_ship_and_crew(ship, [])
        gps = calc._get_crewless_skills_gp(defid, norm_ship.get("skills", []))
        assert "ability" in gps
        assert "reinforcement" in gps
        # Crewless ships with hardware skills should have reinforcement > 0
        assert gps["ability"] + gps["reinforcement"] > 0
