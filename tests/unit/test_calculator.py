"""Unit tests for StatCalc calculator.

Uses tests/resources/gameData.json and tests/resources/example-player.json
to exercise the full stat and GP calculation pipeline offline.
"""

from __future__ import annotations

import copy
import io
import json
from pathlib import Path
from typing import Any

import msgspec
import pytest

from swgoh_comlink import StatCalc
from swgoh_comlink._models import PLAYER_DECODER, RosterUnit
from swgoh_comlink.StatCalc._typed_fastpath import _roster_unit_to_calc_dict

_PLAYER_FILE = Path(__file__).resolve().parent.parent / "resources" / "example-player.json"

# abilityLevelCR / abilityLevelGP at tier 8 in tests/resources/gameData.json.
_TIER_8_ABILITY_LEVEL = 523


# ── Fixtures and helpers ─────────────────────────────────────────────────


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


@pytest.fixture
def crewed_ship(game_data, processed_player) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return _find_ship(processed_player["rosterUnit"], game_data["unitData"], with_crew=True)


@pytest.fixture
def crewless_ship(game_data, processed_player) -> dict[str, Any]:
    ship, crew = _find_ship(processed_player["rosterUnit"], game_data["unitData"], with_crew=False)
    assert crew == []
    return ship


def _def_id(unit: dict[str, Any]) -> str:
    return unit["definitionId"].split(":")[0]


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
        meta = unit_data.get(_def_id(u), {})
        if meta.get("combatType") != 2:
            continue
        crew_ids = meta.get("crew", [])
        if with_crew != bool(crew_ids):
            continue
        crew = [copy.deepcopy(c) for c in roster if _def_id(c) in crew_ids]
        if with_crew and len(crew) != len(crew_ids):
            continue
        return copy.deepcopy(u), crew
    kind = "with crew" if with_crew else "crewless"
    raise ValueError(f"No ship {kind} found")


def _to_normalized(raw: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    """The normalized (defId/rarity/level/...) form of a raw Comlink roster unit."""
    return {
        "defId": _def_id(raw),
        "rarity": raw["currentRarity"],
        "level": raw["currentLevel"],
        "gear": raw["currentTier"],
        "equipped": raw.get("equipment", []),
        "relic": raw.get("relic"),
        "skills": [{"id": s["id"], "tier": s["tier"] + 2} for s in raw.get("skill", [])],
        "purchasedAbilityId": raw.get("purchasedAbilityId", []),
        "equippedStatMod": raw.get("equippedStatMod"),
        **overrides,
    }


# ── Static helpers ───────────────────────────────────────────────────────


@pytest.mark.parametrize(("value", "args", "expected"), [(99.9, (), 99), (123456, (2,), 123400)])
def test_floor(value: float, args: tuple[int, ...], expected: int):
    assert StatCalc._floor(value, *args) == expected


@pytest.mark.parametrize(
    ("table", "key", "args", "expected"),
    [
        # v3.3 dropped the list-table branch: every game data table reached via _table_get is a dict.
        pytest.param({1: 20, 2: 30}, 1, (), 20, id="dict-int-key"),
        pytest.param({1: 20}, "1", (), 20, id="dict-str-key-int-table"),
        pytest.param({1: 20}, "bad", (), 0, id="dict-non-numeric-key-missing"),
        pytest.param({"a": 1}, "a", (), 1, id="dict"),
        pytest.param({"1": 10}, 1, (), 10, id="dict-int-key-coerced"),
        pytest.param(None, "x", (), 0, id="none"),
        pytest.param({}, "missing", (42,), 42, id="default"),
    ],
)
def test_table_get(table: Any, key: Any, args: tuple[Any, ...], expected: Any):
    assert StatCalc._table_get(table, key, *args) == expected


@pytest.mark.parametrize(("stats", "expected"), [({}, {"5": 50}), ({"5": 100}, {"5": 150})], ids=["new", "accumulate"])
def test_add_stat(stats: dict[str, Any], expected: dict[str, Any]):
    StatCalc._add_stat(stats, 5, 50)
    assert stats == expected


@pytest.mark.parametrize(
    ("stat_id", "value", "expected"),
    [
        # Flat stats scale by 1e8; percentage stats by 1e6.
        *((stat_id, 2.0, 2e8) for stat_id in (1, 5, 28, 41, 42)),
        *((stat_id, 2.0, 2e6) for stat_id in (10, 17)),
    ],
)
def test_scale_mod_stat_value(stat_id: int, value: float, expected: float):
    assert StatCalc._scale_mod_stat_value(stat_id, value) == expected


@pytest.mark.parametrize(
    ("convert", "args", "expected"),
    [
        # Character level effect is 85 * 7.5 = 637.5, so 637.5 flat is 50%.
        pytest.param(StatCalc._convert_flat_def_to_percent, (637.5, 85, 1, False), 0.5, id="def-character"),
        # Ship level effect is 300 + 85 * 5 = 725.
        pytest.param(StatCalc._convert_flat_def_to_percent, (725, 85, 1, True), 0.5, id="def-ship"),
        pytest.param(StatCalc._convert_flat_crit_to_percent, (2400, 1), 1.1, id="crit"),  # 2400/2400 + 0.1
        pytest.param(StatCalc._convert_flat_acc_to_percent, (1200, 1), 1.0, id="accuracy"),
        pytest.param(StatCalc._convert_flat_crit_avoid_to_percent, (2400, 1), 1.0, id="crit-avoidance"),
    ],
)
def test_flat_to_percent_conversions(convert, args: tuple[Any, ...], expected: float):
    assert convert(*args) == pytest.approx(expected)


# ── Game data and unit normalization ─────────────────────────────────────


class TestNormalization:
    def test_payload_is_used_directly_or_unwrapped(self):
        payload = {"unitData": {"X": {}}}
        assert StatCalc._normalize_game_data_payload(payload) is payload
        assert StatCalc._normalize_game_data_payload({"data": payload}) is payload

    def test_unsupported_payload_raises(self):
        with pytest.raises(RuntimeError, match="Unsupported"):
            StatCalc._normalize_game_data_payload({"bad": 1})

    @pytest.mark.parametrize(
        ("unit", "expected"),
        [
            ({"defId": "BOSSK"}, "BOSSK"),
            ({"definitionId": "BOSSK:SEVEN_STAR"}, "BOSSK"),
            (None, None),
            ({}, None),
            ({"rarity": 7}, None),
        ],
    )
    def test_get_def_id(self, calc, unit, expected):
        assert calc._get_def_id(unit) == expected

    def test_normalize_char_raw_format(self, calc, player):
        raw = player["rosterUnit"][0]
        normalized = calc._normalize_char(raw)
        assert (normalized["defId"], normalized["rarity"], normalized["level"], normalized["gear"]) == (
            _def_id(raw),
            raw["currentRarity"],
            raw["currentLevel"],
            raw["currentTier"],
        )
        # Raw skill tiers are 0-based upgrades; normalized tiers count the base level and start at 2.
        assert [s["tier"] for s in normalized["skills"]] == [s["tier"] + 2 for s in raw["skill"]]

    def test_normalize_char_already_normalized(self, calc):
        normalized = calc._normalize_char({"defId": "BOSSK", "rarity": 7, "level": 85, "gear": 13})
        assert normalized["defId"] == "BOSSK"
        assert normalized.get("equipped") == []

    def test_normalize_ship_raw_format(self, calc, player, game_data):
        ship_raw, crew_raw = _find_ship(player["rosterUnit"], game_data["unitData"], with_crew=True)
        ship, crew = calc._normalize_ship_and_crew(ship_raw, crew_raw)
        assert ship["defId"] == _def_id(ship_raw)
        assert [c["defId"] for c in crew] == [_def_id(c) for c in crew_raw]

    def test_normalize_ship_already_normalized(self, calc):
        ship = {"defId": "YOURSHIP", "rarity": 7, "level": 85, "skills": []}
        crew_member = {"defId": "CREWUNIT", "rarity": 7, "level": 85, "gear": 13, "equipped": [], "skills": []}
        norm_ship, norm_crew = calc._normalize_ship_and_crew(ship, [crew_member])
        assert (norm_ship["defId"], [c["defId"] for c in norm_crew]) == ("YOURSHIP", ["CREWUNIT"])


def test_rename_stats(calc):
    # Known stat ids are renamed (1 is Health), unknown ones pass through, non-dict values are kept.
    assert calc._rename_stats({"gp": 5000, "final": {"1": 100, "99999": 42}}) == {
        "gp": 5000,
        "final": {"Health": 100, "99999": 42},
    }


def test_require_game_data_raises_without_data():
    sc = StatCalc.__new__(StatCalc)
    sc._unit_data = None
    with pytest.raises(RuntimeError, match="set_game_data"):
        sc._require_game_data()


def test_game_data_is_fetched_from_github_when_not_given(monkeypatch, game_data):
    seen_urls: list[str] = []

    def urlopen(url: str, timeout: float) -> io.BytesIO:
        seen_urls.append(url)
        return io.BytesIO(json.dumps({"data": {"unitData": game_data["unitData"]}}).encode())

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    loaded: list[dict[str, Any]] = []
    monkeypatch.setattr(StatCalc, "set_game_data", lambda self, data: loaded.append(data))

    StatCalc()

    assert seen_urls == [StatCalc._DEFAULT_GAMEDATA_URL]
    assert loaded == [{"unitData": game_data["unitData"]}]  # the {"data": ...} wrapper is unwrapped


# ── calc_char_stats ──────────────────────────────────────────────────────


class TestCalcCharStats:
    def test_raw_format_adds_stats_and_gp_in_place(self, calc, player):
        char = _find_char(player["rosterUnit"])
        result = calc.calc_char_stats(char)
        assert result is char
        assert set(result["stats"]) == {"final", "mods", "gp"}
        assert result["gp"] > 0
        assert result["gp"] == result["stats"]["gp"]

    def test_normalized_format_matches_raw(self, calc, player):
        raw = _find_char(player["rosterUnit"])
        from_normalized = calc.calc_char_stats(_to_normalized(raw))
        from_raw = calc.calc_char_stats(raw)
        assert (from_normalized["stats"], from_normalized["gp"]) == (from_raw["stats"], from_raw["gp"])

    def test_high_relic_char(self, calc, player):
        assert calc.calc_char_stats(_find_char(player["rosterUnit"], relic_min=5))["gp"] > 0

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


def test_gear_pieces_add_stats_in_either_format(calc, game_data, player):
    char = _find_char(player["rosterUnit"], relic_min=3)
    gear_id = next(iter(game_data["gearData"]))

    def raw_stats(equipped: list[Any]) -> dict[str, Any]:
        normalized = calc._normalize_char(char)
        normalized["equipped"] = equipped
        return calc._get_char_raw_stats(normalized)

    baseline = raw_stats([])
    assert raw_stats([{"equipmentId": gear_id}]) == raw_stats([gear_id]) != baseline
    # Gear missing from game data is skipped.
    assert raw_stats([{"equipmentId": "NONEXISTENT_GEAR_999"}]) == baseline


class TestModStats:
    @staticmethod
    def _mod_stats(calc, char: dict[str, Any], mods: list[dict[str, Any]] | None) -> dict[str, Any]:
        normalized = calc._normalize_char(char)
        normalized["equippedStatMod"] = None
        normalized["mods"] = mods
        base = calc._calculate_base_stats(
            calc._get_char_raw_stats(normalized), normalized["level"], normalized["defId"]
        )
        return calc._calculate_mod_stats(base["base"], normalized)

    def test_stat_tuple_and_primary_secondary_formats_agree(self, calc, player):
        """Two mods of one set, written as stat tuples or as primary/secondary dicts, give equal stats."""
        char = _find_char(player["rosterUnit"], relic_min=3)
        mod = {"set": 1, "level": 15, "pips": 5, "tier": 5}
        as_tuples = [
            {**mod, "stat": [(5, 100.0), (28, 50.0), (41, 10.0)]},
            {**mod, "stat": [(5, 80.0), (42, 5.0)]},
        ]
        as_dicts = [
            {
                **mod,
                "primaryStat": {"unitStat": 5, "value": 100.0},
                "secondaryStat": [{"unitStat": 28, "value": 50.0}, {"unitStat": 41, "value": 10.0}],
            },
            {**mod, "primaryStat": {"unitStat": 5, "value": 80.0}, "secondaryStat": [{"unitStat": 42, "value": 5.0}]},
        ]
        from_tuples = self._mod_stats(calc, char, as_tuples)
        assert from_tuples
        assert from_tuples == self._mod_stats(calc, char, as_dicts)
        # The second mod adds to the first rather than replacing it.
        assert from_tuples != self._mod_stats(calc, char, as_tuples[:1])

    @pytest.mark.parametrize(
        ("mods", "expected"),
        [
            pytest.param(None, {}, id="no-mods"),
            # A mod with no set, or an unknown one, adds its stats and only misses out on a set bonus.
            *(
                pytest.param(
                    [{**set_field, "level": 15, "pips": 5, "tier": 5, "stat": [(5, 100.0)]}], {"5": 1e10}, id=name
                )
                for name, set_field in [
                    ("no-set", {}),
                    ("set-zero", {"set": 0}),
                    ("set-none", {"set": None}),
                    ("unknown-set", {"set": 99}),
                ]
            ),
        ],
    )
    def test_mods_without_a_usable_set(self, calc, player, mods, expected):
        assert self._mod_stats(calc, _find_char(player["rosterUnit"], relic_min=3), mods) == expected


# ── calc_ship_stats ──────────────────────────────────────────────────────


class TestCalcShipStats:
    def test_ship_with_crew(self, calc, crewed_ship):
        ship, crew = crewed_ship
        result = calc.calc_ship_stats(ship, crew)
        assert {"final", "crew"} <= set(result["stats"])
        assert result["gp"] > 0

    def test_crewless_ship(self, calc, crewless_ship):
        result = calc.calc_ship_stats(crewless_ship, [])
        assert "final" in result["stats"]
        assert result["gp"] > 0

    def test_missing_ship_raises_key_error(self, calc):
        with pytest.raises(KeyError, match="not found in game data"):
            calc._get_ship_raw_stats({"defId": "NONEXISTENT_SHIP", "rarity": 7, "level": 85}, [])


@pytest.mark.parametrize("problem", ["wrong-count", "wrong-member"])
@pytest.mark.parametrize("entry_point", ["calc_ship_stats", "_calc_ship_gp"])
def test_crew_must_match_the_ship(calc, game_data, player, entry_point: str, problem: str):
    """Both the stats pipeline and the GP calculation reject crew that does not match the ship."""
    ship, crew = _find_ship(player["rosterUnit"], game_data["unitData"], with_crew=True)
    if problem == "wrong-count":
        crew, match = [], "Incorrect number"
    else:
        expected_crew = game_data["unitData"][_def_id(ship)]["crew"]
        outsider = next(
            copy.deepcopy(u)
            for u in player["rosterUnit"]
            if _def_id(u) not in expected_crew and game_data["unitData"].get(_def_id(u), {}).get("combatType") == 1
        )
        crew, match = [outsider, *crew[1:]], "not in"
    if entry_point == "_calc_ship_gp":
        ship, crew = calc._normalize_ship_and_crew(ship, crew)

    with pytest.raises(ValueError, match=match):
        getattr(calc, entry_point)(ship, crew)


# ── GP calculations ──────────────────────────────────────────────────────


class TestCalcGP:
    def test_char_gp_matches_stats_pipeline(self, calc, player):
        char = _find_char(player["rosterUnit"], relic_min=3)
        gp = calc.calc_char_gp(copy.deepcopy(char))
        assert isinstance(gp, int)
        assert gp > 0
        assert gp == calc.calc_char_stats(char)["gp"]

    def test_ship_gp_matches_stats_pipeline(self, calc, crewed_ship):
        ship, crew = crewed_ship
        gp = calc.calc_ship_gp(copy.deepcopy(ship), copy.deepcopy(crew))
        assert isinstance(gp, int)
        assert gp > 0
        assert gp == calc.calc_ship_stats(ship, crew)["gp"]

    def test_crewless_ship_gp_defaults_to_no_crew(self, calc, crewless_ship):
        norm_ship, _ = calc._normalize_ship_and_crew(crewless_ship, [])
        assert calc._calc_ship_gp(norm_ship) == calc._calc_ship_gp(norm_ship, []) > 0

    def test_normalized_mods_add_gp(self, calc, player):
        normalized = _to_normalized(_find_char(player["rosterUnit"], relic_min=3), equippedStatMod=None)
        with_mod = {**normalized, "mods": [{"set": 1, "level": 15, "pips": 5, "tier": 5, "stat": [(5, 100.0)]}]}
        assert calc._calc_char_gp(with_mod) > calc._calc_char_gp(normalized)


class TestSkillGP:
    def test_skill_with_override_tag_uses_special_gp(self, calc, game_data):
        defid, skill_id, tier, tag = next(
            (defid, skill["id"], int(tier), tag)
            for defid, meta in game_data["unitData"].items()
            for skill in meta.get("skills", [])
            for tier, tag in skill.get("powerOverrideTags", {}).items()
        )
        gp = calc._get_skill_gp(defid, {"id": skill_id, "tier": tier})
        assert gp == calc._gp_tables["abilitySpecialGP"][tag] > 0

    def test_skill_without_override(self, calc, game_data):
        defid, skill_id = next(
            (defid, skill["id"])
            for defid, meta in game_data["unitData"].items()
            for skill in meta.get("skills", [])
            if not skill.get("powerOverrideTags")
        )
        assert calc._get_skill_gp(defid, {"id": skill_id, "tier": 8}) == _TIER_8_ABILITY_LEVEL

    def test_missing_skill_returns_zero(self, calc, game_data):
        defid = next(iter(game_data["unitData"]))
        assert calc._get_skill_gp(defid, {"id": "nonexistent_skill", "tier": 1}) == 0

    def test_crewless_skills_split_into_ability_and_reinforcement(self, calc, crewless_ship):
        norm_ship, _ = calc._normalize_ship_and_crew(crewless_ship, [])
        gps = calc._get_crewless_skills_gp(_def_id(crewless_ship), norm_ship.get("skills", []))
        assert set(gps) == {"ability", "reinforcement"}
        assert gps["ability"] + gps["reinforcement"] > 0

    def test_unknown_crewless_skill_adds_nothing(self, calc, crewless_ship):
        gps = calc._get_crewless_skills_gp(_def_id(crewless_ship), [{"id": "nonexistent_skill", "tier": 1}])
        assert gps == {"ability": 0, "reinforcement": 0}


# ── Crew rating ──────────────────────────────────────────────────────────


class TestCrewRating:
    def test_crew_rating_counts_each_mod(self, calc, crewed_ship):
        _, crew = crewed_ship
        norm_crew = [calc._normalize_char(c) for c in crew]
        assert calc._get_crew_rating(norm_crew) > 0

        norm_crew[0] = {**norm_crew[0], "equippedStatMod": None, "mods": None}
        without_mods = calc._get_crew_rating(norm_crew)
        norm_crew[0]["mods"] = [{"pips": 5, "level": 15}]
        assert calc._get_crew_rating(norm_crew) - without_mods == calc._cr_tables["modRarityLevelCR"]["5"]["15"]

    def test_crewless_crew_rating(self, calc, crewless_ship):
        norm_ship, _ = calc._normalize_ship_and_crew(crewless_ship, [])
        assert calc._get_crewless_crew_rating(norm_ship) > 0

    @pytest.mark.parametrize(
        ("skill_ids", "multiplier"),
        [
            pytest.param(["hardwareskill_TEST"], 0.696, id="hardware"),
            pytest.param(["basicskill_TEST"], 2.46, id="other"),
            pytest.param(["hardwareskill_TEST", "basicskill_TEST"], 0.696 + 2.46, id="mixed"),
        ],
    )
    def test_crewless_skills_crew_rating_multipliers(self, calc, skill_ids, multiplier):
        """Hardware skills weigh 0.696x the tier's ability-level CR; every other skill 2.46x."""
        skills = [{"id": skill_id, "tier": 8} for skill_id in skill_ids]
        assert calc._get_crewless_skills_crew_rating(skills) == pytest.approx(multiplier * _TIER_8_ABILITY_LEVEL)

    def test_skill_crew_rating(self, calc):
        assert calc._get_skill_crew_rating({"id": "basicskill_TEST", "tier": 8}) == _TIER_8_ABILITY_LEVEL


# ── calc_roster_stats / calc_player_stats ────────────────────────────────


class TestCalcRosterStats:
    def test_list_format_full_roster(self, calc, game_data, player):
        roster = calc.calc_roster_stats(copy.deepcopy(player["rosterUnit"]))
        characters = [u for u in roster if game_data["unitData"].get(_def_id(u), {}).get("combatType") == 1]
        assert characters
        assert all(isinstance(u["gp"], int) and "final" in u["stats"] for u in characters)

    def test_dict_format_legacy_roster(self, calc, player):
        raw = _find_char(player["rosterUnit"], relic_min=3)
        unit: dict[str, Any] = {
            "currentRarity": raw["currentRarity"],
            "currentLevel": raw["currentLevel"],
            "currentTier": raw["currentTier"],
            "gear": [],
            "skill": raw.get("skill", []),
        }
        calc.calc_roster_stats({_def_id(raw): [unit]})
        assert "final" in unit["stats"]
        assert unit["gp"] > 0

    @pytest.mark.parametrize(
        "make_roster",
        [
            pytest.param(lambda ship_id: [{"defId": "NONEXISTENT_UNIT_XYZ", "rarity": 7}], id="list-unknown-id"),
            pytest.param(lambda ship_id: [{"rarity": 7, "level": 85}], id="list-no-id"),
            pytest.param(lambda ship_id: {"NONEXISTENT_UNIT_XYZ": [{"currentRarity": 7}]}, id="dict-unknown-id"),
            # The legacy dict format only calculates characters.
            pytest.param(lambda ship_id: {ship_id: [{"currentRarity": 7}]}, id="dict-ship"),
        ],
    )
    def test_units_it_cannot_calculate_are_left_untouched(self, calc, game_data, make_roster):
        ship_id = next(k for k, v in game_data["unitData"].items() if v["combatType"] == 2)
        roster = make_roster(ship_id)
        assert calc.calc_roster_stats(copy.deepcopy(roster)) == roster


class TestCalcPlayerStats:
    @pytest.mark.parametrize("as_list", [False, True], ids=["dict", "list"])
    def test_adds_stats_and_gp_to_every_unit(self, calc, player, as_list: bool):
        p = copy.deepcopy(player)
        result = calc.calc_player_stats([p] if as_list else p)
        assert result == ([p] if as_list else p)
        assert all("final" in u["stats"] and u["gp"] > 0 for u in p["rosterUnit"])

    @pytest.mark.parametrize(
        ("players", "error", "match"),
        [
            pytest.param("bad", TypeError, "Expected a list or dict", id="str"),
            pytest.param(123, TypeError, "Expected a list or dict", id="int"),
            pytest.param({}, RuntimeError, "rosterUnit", id="empty-dict"),
            pytest.param({"name": "player"}, RuntimeError, "rosterUnit", id="dict-without-roster"),
        ],
    )
    def test_invalid_input_raises(self, calc, players, error, match):
        with pytest.raises(error, match=match):
            calc.calc_player_stats(players)


# ── Raw-format ultimate ability GP ───────────────────────────────────────


def _find_ultimate_char(roster: list[dict]) -> dict[str, Any]:
    """Return a deepcopy of the first raw unit with a purchased ultimate ability."""
    for u in roster:
        if u.get("purchasedAbilityId"):
            return copy.deepcopy(u)
    pytest.skip("No character with purchasedAbilityId found")


class TestRawUltimateGP:
    def test_raw_and_normalized_gp_match(self, calc, player):
        raw = _find_ultimate_char(player["rosterUnit"])
        normalized = _to_normalized(raw)
        without_ultimate = {**normalized, "purchasedAbilityId": []}

        raw_gp = calc.calc_char_gp(raw)

        assert raw_gp == calc.calc_char_gp(normalized)
        assert raw_gp > calc.calc_char_gp(without_ultimate)

    def test_roster_stats_includes_ultimate_gp(self, calc, player):
        p = copy.deepcopy(player)
        calc.calc_player_stats(p)

        ultimates = [unit for unit in p["rosterUnit"] if unit.get("purchasedAbilityId")]
        assert ultimates
        for unit in ultimates:
            assert unit["gp"] == calc.calc_char_gp(_to_normalized(unit))

    def test_raw_crew_normalization_keeps_purchased_ability(self, calc, game_data, player):
        ship, crew = _find_ship(player["rosterUnit"], game_data["unitData"], with_crew=True)
        crew[0]["purchasedAbilityId"] = ["ultimateability_test"]

        _, norm_crew = calc._normalize_ship_and_crew(ship, crew)

        assert norm_crew[0]["purchasedAbilityId"] == ["ultimateability_test"]

    def test_typed_roster_unit_adapter_keeps_purchased_ability(self, player):
        raw = _find_ultimate_char(player["rosterUnit"])
        unit = msgspec.json.decode(json.dumps(raw).encode(), type=RosterUnit)

        assert _roster_unit_to_calc_dict(unit)["purchasedAbilityId"] == raw["purchasedAbilityId"]

    @pytest.mark.parametrize("entry", ["player", "roster"])
    def test_typed_input_matches_dict_path(self, calc, player, entry: str):
        """Struct input (typed client) keeps ultimate GP and matches the dict path's stats and GP for every unit."""
        dict_player = copy.deepcopy(player)
        calc.calc_player_stats(dict_player)
        struct_player = PLAYER_DECODER.decode(json.dumps(player).encode())

        if entry == "player":
            typed_units = calc.calc_player_stats(struct_player)["rosterUnit"]
        else:
            typed_units = calc.calc_roster_stats(list(struct_player.roster_unit))

        ultimates = [i for i, unit in enumerate(dict_player["rosterUnit"]) if unit.get("purchasedAbilityId")]
        assert ultimates
        for i in ultimates:
            without_ultimate = _to_normalized(player["rosterUnit"][i], purchasedAbilityId=[])
            assert typed_units[i]["gp"] == dict_player["rosterUnit"][i]["gp"] > calc.calc_char_gp(without_ultimate)
        assert [(u.get("gp"), u.get("stats")) for u in typed_units] == [
            (u.get("gp"), u.get("stats")) for u in dict_player["rosterUnit"]
        ]


# ── Ships with crew missing from the roster ──────────────────────────────


class TestRosterShipMissingCrew:
    def test_ship_skipped_and_later_ships_still_processed(self, calc, game_data, player, caplog):
        unit_data = game_data["unitData"]
        roster = copy.deepcopy(player["rosterUnit"])
        ship, crew = _find_ship(roster, unit_data, with_crew=True)
        dropped = crew[0]["definitionId"]

        # Remove one crew member and make the broken ship the first ship processed
        roster = [u for u in roster if u["definitionId"] not in (dropped, ship["definitionId"])]
        roster.insert(0, ship)

        with caplog.at_level("WARNING", logger=StatCalc._LOGGER.name):
            calc.calc_roster_stats(roster)

        assert "gp" not in ship
        assert "stats" not in ship
        assert _def_id(ship) in caplog.text

        owned = {_def_id(u) for u in roster}
        other_ships = [
            u
            for u in roster
            if u is not ship
            and unit_data.get(_def_id(u), {}).get("combatType") == 2
            and all(cid in owned for cid in unit_data[_def_id(u)]["crew"])
        ]
        assert other_ships
        assert all(isinstance(u.get("gp"), int) and u["gp"] > 0 for u in other_ships)


# ── Raw equipment slot handling ──────────────────────────────────────────


class TestRawEquipmentSlotGP:
    def test_comlink_equipment_slot_zero_adds_gp(self, calc, player):
        """Comlink emits 0-based ``slot`` (including the falsy 0) on each equipment entry."""
        raw = _find_char(player["rosterUnit"])
        raw["currentTier"] = 12
        bare = copy.deepcopy(raw)
        bare["equipment"] = []
        raw["equipment"] = [{"equipmentId": "172", "slot": 0, "isAtMaxLevel": False}]

        piece_gp = calc._gp_tables["gearPieceGP"]["12"]["0"]

        assert piece_gp > 0
        assert calc.calc_char_gp(raw) - calc.calc_char_gp(bare) == pytest.approx(piece_gp * 1.5, abs=1)


class TestSlotlessEquipmentGP:
    def test_duplicate_gear_ids_resolve_to_distinct_slots(self, calc, game_data):
        gear_set = game_data["unitData"]["GLREY"]["gearLvl"]["12"]["gear"]
        dup_id = next(g for g in gear_set if gear_set.count(g) > 1)
        expected = [i for i, g in enumerate(gear_set) if g == dup_id][:2]
        char = {"defId": "GLREY", "gear": 12, "equipped": [{"equipmentId": dup_id}, dup_id]}

        assert calc._resolve_gear_slots(char) == expected

    def test_explicit_slots_are_not_reassigned(self, calc, game_data):
        gear_set = game_data["unitData"]["GLREY"]["gearLvl"]["12"]["gear"]
        dup_id = next(g for g in gear_set if gear_set.count(g) > 1)
        first, second = [i for i, g in enumerate(gear_set) if g == dup_id][:2]
        char = {
            "defId": "GLREY",
            "gear": 12,
            "equipped": [{"equipmentId": dup_id}, {"equipmentId": dup_id, "slot": first}],
        }

        assert calc._resolve_gear_slots(char) == [second, first]

    def test_unknown_gear_id_warns_and_adds_no_gp(self, calc, caplog):
        char = {"defId": "GLREY", "gear": 12, "equipped": [{"equipmentId": "NOT_IN_GEAR_SET"}]}

        with caplog.at_level("WARNING", logger=StatCalc._LOGGER.name):
            assert calc._resolve_gear_slots(char) == [None]
        assert "NOT_IN_GEAR_SET" in caplog.text

    def test_legacy_dict_roster_counts_gear_gp(self, calc, game_data, player):
        raw = _find_char(player["rosterUnit"], relic_min=3)
        def_id = _def_id(raw)
        gear_ids = game_data["unitData"][def_id]["gearLvl"]["12"]["gear"][:3]

        def legacy_gp(gear: list[str]) -> int:
            unit: dict[str, Any] = {
                "currentRarity": 7,
                "currentLevel": 85,
                "currentTier": 12,
                "gear": gear,
                "skill": [],
            }
            calc.calc_roster_stats({def_id: [unit]})
            return unit["gp"]

        piece_gp = calc._gp_tables["gearPieceGP"]["12"]["0"]

        assert piece_gp > 0
        assert legacy_gp(gear_ids) - legacy_gp([]) == pytest.approx(3 * piece_gp * 1.5, abs=1)
