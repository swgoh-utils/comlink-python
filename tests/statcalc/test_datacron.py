"""Datacron behaviour, driven entirely through ``calc_player_stats``.

Single seam by design: a player payload is an ordinary dict, so hand-authored
players give exact control over gear tiers, relic tiers and affix thresholds
without reaching into the resolution module.  Nothing here may monkeypatch
private methods or assert on where the datacron step sits in the pipeline —
that position is an implementation detail.
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any

import pytest

from swgoh_comlink import StatCalc

_RESOURCES = Path(__file__).resolve().parent.parent / "resources"
_GAME_DATA_FILE = _RESOURCES / "gameData.json"
_PLAYER_FILE = _RESOURCES / "example-player.json"

# A character present in the committed game data, used wherever the test needs
# a real unit definition rather than a specific character's properties.
_CHAR = "CADBANE"

DATACRON_ID = "test-datacron"


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def game_data() -> dict[str, Any]:
    return json.loads(_GAME_DATA_FILE.read_text())["data"]


@pytest.fixture(scope="module")
def calc(game_data: dict[str, Any]) -> StatCalc:
    return StatCalc(game_data=game_data)


@pytest.fixture(scope="module")
def example_player() -> dict[str, Any]:
    return json.loads(_PLAYER_FILE.read_text())


# ── Payload builders ─────────────────────────────────────────────────────


def stat_affix(
    stat_type: int,
    value: int,
    *,
    required_unit_tier: int = 0,
    required_relic_tier: int = 1,
) -> dict[str, Any]:
    """A Stat Affix. Never carries a target rule — real ones never do."""
    return {
        "tag": [],
        "targetRule": "",
        "abilityId": "",
        "statType": stat_type,
        "statValue": str(value),
        "requiredUnitTier": required_unit_tier,
        "requiredRelicTier": required_relic_tier,
        "scopeIcon": "",
    }


def ability_affix(ability_id: str = "datacron_alignment_generic_030") -> dict[str, Any]:
    """An Ability Affix, shaped as the game reports one: stat type 1, value 0."""
    return {
        "tag": ["darkside"],
        "targetRule": "target_datacron_darkside",
        "abilityId": ability_id,
        "statType": 1,
        "statValue": "0",
        "requiredUnitTier": 0,
        "requiredRelicTier": 1,
        "scopeIcon": "tex.datacronui_affix_darkside",
    }


def datacron(*affixes: dict[str, Any], datacron_id: str = DATACRON_ID) -> dict[str, Any]:
    return {
        "id": datacron_id,
        "setId": 25,
        "templateId": "datacron_set_25_base",
        "tag": [],
        "affix": list(affixes),
        "rerollOption": [],
        "locked": False,
        "rerollIndex": 0,
        "rerollCount": 0,
        "focused": False,
    }


def character(
    def_id: str = _CHAR,
    *,
    gear_tier: int = 13,
    relic_tier: int | None = 11,
    level: int = 85,
    rarity: int = 7,
) -> dict[str, Any]:
    """A roster unit. `relic_tier=None` produces a unit with no relic at all."""
    unit: dict[str, Any] = {
        "definitionId": f"{def_id}:SEVEN_STAR",
        "currentRarity": rarity,
        "currentLevel": level,
        "currentTier": gear_tier,
        "equipment": [],
        "skill": [],
        "equippedStatMod": [],
        "relic": None if relic_tier is None else {"currentTier": relic_tier},
    }
    return unit


def player(*units: dict[str, Any], datacrons: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "rosterUnit": list(units),
        "datacron": [] if datacrons is None else datacrons,
    }


def datacron_bucket(calc: StatCalc, payload: dict[str, Any], datacron_id: str | None = DATACRON_ID) -> dict[str, Any]:
    """Run one player through the seam and return the first unit's bucket."""
    result = calc.calc_player_stats(copy.deepcopy(payload), datacron_id=datacron_id)
    assert isinstance(result, dict)
    return result["rosterUnit"][0]["stats"].get("datacron", {})


# ── The bucket appears, and only when asked for ───────────────────────────


def test_characters_gain_a_datacron_bucket(calc: StatCalc) -> None:
    payload = player(character(), datacrons=[datacron(stat_affix(16, 50_000_000))])

    assert datacron_bucket(calc, payload) == {"Critical Damage": pytest.approx(0.5)}


def test_bucket_is_absent_not_empty_when_no_datacron_requested(calc: StatCalc) -> None:
    payload = player(character(), datacrons=[datacron(stat_affix(16, 50_000_000))])

    result = calc.calc_player_stats(copy.deepcopy(payload))
    assert isinstance(result, dict)

    assert "datacron" not in result["rosterUnit"][0]["stats"]


def test_output_is_unchanged_when_no_datacron_requested(calc: StatCalc, example_player: dict[str, Any]) -> None:
    """The whole feature is dormant unless a datacron is named."""
    before = calc.calc_player_stats(copy.deepcopy(example_player))
    after = calc.calc_player_stats(copy.deepcopy(example_player), datacron_id=None)

    assert after == before


# ── Passthrough stat types ────────────────────────────────────────────────


def test_stat_values_are_scaled_for_display(calc: StatCalc) -> None:
    """Affix values arrive in Unscaled Space and leave in display units."""
    payload = player(character(), datacrons=[datacron(stat_affix(17, 12_500_000))])

    assert datacron_bucket(calc, payload)["Potency"] == pytest.approx(0.125)


def test_a_stat_type_repeated_across_levels_is_summed(calc: StatCalc) -> None:
    payload = player(
        character(),
        datacrons=[
            datacron(
                stat_affix(16, 21_927_327),
                stat_affix(16, 23_172_075),
                stat_affix(16, 42_891_143),
            )
        ],
    )

    # 21.927327 + 23.172075 + 42.891143 = 87.990545%, applied as the 87.99%
    # the card displays.
    assert datacron_bucket(calc, payload)["Critical Damage"] == pytest.approx(0.8799)


def test_a_percentage_is_applied_as_the_card_displays_it(calc: StatCalc) -> None:
    """The game applies the two-decimal percentage, not the stored value.

    Measured on Lord Vader: a 27.14327% Protection affix against a base of
    116,765 contributed 31,690, which is 27.14% of it. The stored value would
    have given 31,693.
    """
    payload = player(character(), datacrons=[datacron(stat_affix(16, 27_143_270))])

    assert datacron_bucket(calc, payload)["Critical Damage"] == pytest.approx(0.2714)


def test_percentages_are_summed_before_they_are_rounded(calc: StatCalc) -> None:
    """Rounding each affix first would give a different, wrong answer.

    Measured: affixes of 2.828575% and 19.515055% are applied as 22.34% — the
    rounded sum. Rounding each part first gives 2.83 + 19.52 = 22.35%.
    """
    payload = player(
        character(),
        datacrons=[datacron(stat_affix(16, 2_828_575), stat_affix(16, 19_515_055))],
    )

    assert datacron_bucket(calc, payload)["Critical Damage"] == pytest.approx(0.2234)


def test_distinct_stat_types_stay_distinct(calc: StatCalc) -> None:
    payload = player(
        character(),
        datacrons=[datacron(stat_affix(17, 10_000_000), stat_affix(18, 20_000_000))],
    )

    assert datacron_bucket(calc, payload) == {
        "Potency": pytest.approx(0.1),
        "Tenacity": pytest.approx(0.2),
    }


def test_bucket_stat_names_match_the_other_buckets(calc: StatCalc) -> None:
    """Names must line up so a caller can pair buckets without a lookup table."""
    payload = player(character(), datacrons=[datacron(stat_affix(16, 50_000_000))])

    result = calc.calc_player_stats(copy.deepcopy(payload), datacron_id=DATACRON_ID)
    assert isinstance(result, dict)
    stats = result["rosterUnit"][0]["stats"]

    assert set(stats["datacron"]) <= set(stats["final"])


# ── Ability Affixes ───────────────────────────────────────────────────────


def test_ability_affixes_contribute_nothing(calc: StatCalc) -> None:
    payload = player(character(), datacrons=[datacron(ability_affix(), ability_affix())])

    assert datacron_bucket(calc, payload) == {}


def test_ability_affixes_are_skipped_even_carrying_a_real_stat_value(calc: StatCalc) -> None:
    """Identified by granting an ability, not by having a zero value."""
    affix = ability_affix()
    affix["statValue"] = "50000000"
    payload = player(character(), datacrons=[datacron(affix)])

    assert datacron_bucket(calc, payload) == {}


def test_stat_affixes_survive_alongside_ability_affixes(calc: StatCalc) -> None:
    payload = player(
        character(),
        datacrons=[datacron(stat_affix(16, 30_000_000), ability_affix(), stat_affix(17, 10_000_000))],
    )

    assert datacron_bucket(calc, payload) == {
        "Critical Damage": pytest.approx(0.3),
        "Potency": pytest.approx(0.1),
    }


# ── Affix Requirement gating ──────────────────────────────────────────────


@pytest.mark.parametrize(
    ("unit_gear_tier", "applies"),
    [(13, True), (12, True), (11, False), (1, False)],
    ids=["above", "met exactly", "one short", "far short"],
)
def test_gear_tier_requirement(calc: StatCalc, unit_gear_tier: int, applies: bool) -> None:
    payload = player(
        character(gear_tier=unit_gear_tier),
        datacrons=[datacron(stat_affix(16, 50_000_000, required_unit_tier=12))],
    )

    assert bool(datacron_bucket(calc, payload)) is applies


@pytest.mark.parametrize(
    ("unit_relic_tier", "applies"),
    [(11, True), (8, True), (7, False), (3, False)],
    ids=["above", "met exactly", "one short", "far short"],
)
def test_relic_tier_requirement(calc: StatCalc, unit_relic_tier: int, applies: bool) -> None:
    """Encoded tiers on both sides, so the comparison is direct.

    Offsetting either side would shift this threshold by two tiers, which is
    exactly what the 'one short' case would stop catching.
    """
    payload = player(
        character(relic_tier=unit_relic_tier),
        datacrons=[datacron(stat_affix(16, 50_000_000, required_relic_tier=8))],
    )

    assert bool(datacron_bucket(calc, payload)) is applies


def test_both_requirements_must_be_met(calc: StatCalc) -> None:
    affix = stat_affix(16, 50_000_000, required_unit_tier=12, required_relic_tier=8)

    both = player(character(gear_tier=13, relic_tier=9), datacrons=[datacron(affix)])
    assert datacron_bucket(calc, both)

    gear_short = player(character(gear_tier=11, relic_tier=9), datacrons=[datacron(affix)])
    assert datacron_bucket(calc, gear_short) == {}

    relic_short = player(character(gear_tier=13, relic_tier=7), datacrons=[datacron(affix)])
    assert datacron_bucket(calc, relic_short) == {}


def test_relic_less_unit_still_receives_unrestricted_affixes(calc: StatCalc) -> None:
    """Regression: a unit with no relic sits at the locked base state, not zero.

    Treating it as zero fails even the baseline requirement every affix
    carries, silently zeroing every relic-less unit while leaving the
    high-relic units anyone would spot-check looking perfectly correct.
    """
    payload = player(
        character(gear_tier=1, relic_tier=None),
        datacrons=[datacron(stat_affix(16, 50_000_000))],
    )

    assert datacron_bucket(calc, payload) == {"Critical Damage": pytest.approx(0.5)}


def test_relic_less_unit_is_denied_affixes_that_require_a_relic(calc: StatCalc) -> None:
    payload = player(
        character(gear_tier=13, relic_tier=None),
        datacrons=[datacron(stat_affix(16, 50_000_000, required_relic_tier=3))],
    )

    assert datacron_bucket(calc, payload) == {}


def test_the_same_datacron_gives_different_units_different_contributions(calc: StatCalc) -> None:
    """The whole point of gating: one datacron, a roster of varied progress."""
    dc = datacron(
        stat_affix(16, 10_000_000),
        stat_affix(17, 20_000_000, required_relic_tier=8),
        stat_affix(18, 30_000_000, required_unit_tier=12, required_relic_tier=11),
    )
    payload = player(
        character(gear_tier=13, relic_tier=11),
        character(gear_tier=13, relic_tier=8),
        character(gear_tier=1, relic_tier=None),
        datacrons=[dc],
    )

    result = calc.calc_player_stats(copy.deepcopy(payload), datacron_id=DATACRON_ID)
    assert isinstance(result, dict)
    buckets = [unit["stats"]["datacron"] for unit in result["rosterUnit"]]

    assert set(buckets[0]) == {"Critical Damage", "Potency", "Tenacity"}
    assert set(buckets[1]) == {"Critical Damage", "Potency"}
    assert set(buckets[2]) == {"Critical Damage"}


def test_a_relic_threshold_splits_the_real_roster(calc: StatCalc, example_player: dict[str, Any]) -> None:
    """Gating against real units, whose relic tiers span the threshold.

    The committed player's characters sit across several relic tiers, so an
    affix requiring a high one must reach strictly fewer of them than an
    unrestricted affix does.
    """
    payload = copy.deepcopy(example_player)
    payload["datacron"] = [
        datacron(stat_affix(16, 10_000_000), datacron_id="unrestricted"),
        datacron(stat_affix(16, 10_000_000, required_relic_tier=11), datacron_id="restricted"),
    ]

    def reached(datacron_id: str) -> int:
        result = calc.calc_player_stats(copy.deepcopy(payload), datacron_id=datacron_id)
        assert isinstance(result, dict)
        return sum(1 for unit in result["rosterUnit"] if unit.get("stats", {}).get("datacron"))

    everyone = reached("unrestricted")
    qualified = reached("restricted")

    assert everyone > 0
    assert 0 < qualified < everyone


# ── Percent-additive expansion ────────────────────────────────────────────


def test_additive_offense_expands_onto_both_damage_stats(calc: StatCalc) -> None:
    payload = player(character(), datacrons=[datacron(stat_affix(41, 5_000_000))])

    assert datacron_bucket(calc, payload) == {
        "Physical Damage": pytest.approx(0.05),
        "Special Damage": pytest.approx(0.05),
    }


@pytest.mark.parametrize(
    ("stat_type", "targets"),
    [
        (48, ["Physical Damage", "Special Damage"]),
        (55, ["Health"]),
        (56, ["Protection"]),
        (57, ["Speed"]),
    ],
    ids=["offense%", "health%", "protection%", "speed%"],
)
def test_proportional_types_expand_onto_their_targets(calc: StatCalc, stat_type: int, targets: list[str]) -> None:
    payload = player(character(), datacrons=[datacron(stat_affix(stat_type, 30_000_000))])

    assert sorted(datacron_bucket(calc, payload)) == sorted(targets)


def test_a_percentage_resolves_against_base_and_gear_excluding_mods(
    calc: StatCalc, example_player: dict[str, Any]
) -> None:
    """As measured in game, percentages resolve against base + gear.

    Mods are excluded. Health is not converted for display, so `final` minus the
    `mods` bucket is exactly that base. Measured against Lord Vader: a +27.14%
    Protection datacron contributed 31,690 on a total of 208,666 carrying 91,901
    from mods — 27.14% of 116,765, not of 208,666.
    """
    fraction = 0.25
    payload = copy.deepcopy(example_player)
    payload["datacron"] = [datacron(stat_affix(55, int(fraction * 1e8)))]

    result = calc.calc_player_stats(payload, datacron_id=DATACRON_ID)
    assert isinstance(result, dict)

    checked = with_mods = 0
    for unit in result["rosterUnit"]:
        stats = unit.get("stats", {})
        bucket = stats.get("datacron")
        if not bucket:
            continue

        total = stats["final"]["Health"]
        from_mods = stats.get("mods", {}).get("Health", 0)
        unmodded = total - from_mods
        assert unmodded > 0

        # floor(..., 8) in Unscaled Space quantises to whole display units.
        assert bucket["Health"] == pytest.approx(unmodded * fraction, abs=1.0)
        if from_mods:
            # Only modded units can tell the two candidate bases apart.
            assert bucket["Health"] != pytest.approx(total * fraction, abs=1.0)
            with_mods += 1
        checked += 1

    assert checked > 100, "expected most of the roster to be covered"
    assert with_mods > 100, "without modded units this proves nothing"


@pytest.mark.parametrize(
    ("stat_type", "targets"),
    [
        (42, ["Armor", "Resistance"]),
        (49, ["Armor", "Resistance"]),
        (53, ["Physical Critical Chance", "Special Critical Chance"]),
        (54, ["Physical Critical Avoidance", "Special Critical Avoidance"]),
    ],
    ids=["defense flat", "defense%", "crit chance%", "crit avoidance%"],
)
def test_types_reaching_converted_stats_expand(calc: StatCalc, stat_type: int, targets: list[str]) -> None:
    payload = player(character(), datacrons=[datacron(stat_affix(stat_type, 50_000_000))])

    assert sorted(datacron_bucket(calc, payload)) == sorted(targets)


def test_expansion_and_passthrough_coexist(calc: StatCalc) -> None:
    payload = player(
        character(),
        datacrons=[datacron(stat_affix(16, 40_000_000), stat_affix(57, 10_000_000))],
    )
    bucket = datacron_bucket(calc, payload)

    assert bucket["Critical Damage"] == pytest.approx(0.4)
    assert "Speed" in bucket


def test_gating_applies_before_expansion(calc: StatCalc) -> None:
    """An affix the unit does not qualify for must not expand onto anything."""
    payload = player(
        character(gear_tier=1, relic_tier=3),
        datacrons=[datacron(stat_affix(48, 30_000_000, required_relic_tier=11))],
    )

    assert datacron_bucket(calc, payload) == {}


# ── Converted stats reconcile with final ──────────────────────────────────


def test_a_converted_stat_reconciles_against_an_independent_recomputation(calc: StatCalc) -> None:
    """The promise of the feature: `final + datacron` is right for every stat.

    Armor is stored as a non-linear percentage, `v / (level*7.5 + v)`, so a
    flat delta could not simply be added to it. The bucket must instead hold
    the *marginal* percentage the datacron adds.

    The oracle here is independent of the datacron code: invert the published
    conversion to recover the unit's flat armour, apply the percentage by hand,
    convert forward again, and require the two buckets to sum to that.
    """
    level = 85
    fraction = 0.5
    payload = player(
        character(level=level),
        datacrons=[datacron(stat_affix(49, int(fraction * 1e8)))],
    )

    result = calc.calc_player_stats(copy.deepcopy(payload), datacron_id=DATACRON_ID)
    assert isinstance(result, dict)
    stats = result["rosterUnit"][0]["stats"]

    level_effect = level * 7.5
    p0 = stats["final"]["Armor"]
    assert 0 < p0 < 1

    flat = level_effect * p0 / (1 - p0)
    # Proportional growth is floored to whole display units in Unscaled Space.
    grown = flat + math.floor(flat * fraction)
    expected = grown / (level_effect + grown)

    assert p0 + stats["datacron"]["Armor"] == pytest.approx(expected, rel=1e-6)


def test_a_converted_stat_is_not_given_a_flat_delta(calc: StatCalc) -> None:
    """Guard against the naive implementation: a flat armour delta would dwarf
    the percentage it is meant to be added to."""
    payload = player(character(), datacrons=[datacron(stat_affix(49, 50_000_000))])

    result = calc.calc_player_stats(copy.deepcopy(payload), datacron_id=DATACRON_ID)
    assert isinstance(result, dict)
    stats = result["rosterUnit"][0]["stats"]

    assert 0 < stats["datacron"]["Armor"] < 1
    assert 0 < stats["final"]["Armor"] + stats["datacron"]["Armor"] < 1


def test_a_converted_stat_shows_diminishing_returns(calc: StatCalc) -> None:
    """Non-linearity is applied, not decorative.

    The conversion is concave, so doubling an affix's value must yield *less*
    than double the marginal contribution. A flat delta, or a percentage
    applied linearly, would yield exactly double.
    """

    def marginal(value: int) -> float:
        payload = player(character(), datacrons=[datacron(stat_affix(49, value))])
        result = calc.calc_player_stats(copy.deepcopy(payload), datacron_id=DATACRON_ID)
        assert isinstance(result, dict)
        return float(result["rosterUnit"][0]["stats"]["datacron"]["Armor"])

    single = marginal(50_000_000)
    double = marginal(100_000_000)

    assert single > 0
    assert single < double < 2 * single


def test_every_datacron_stat_has_a_matching_final_key(calc: StatCalc, example_player: dict[str, Any]) -> None:
    """Across the whole roster and every expansion, the two buckets line up."""
    payload = copy.deepcopy(example_player)
    payload["datacron"] = [
        datacron(
            stat_affix(16, 20_000_000),
            stat_affix(48, 30_000_000),
            stat_affix(49, 30_000_000),
            stat_affix(53, 10_000_000),
            stat_affix(54, 10_000_000),
            stat_affix(55, 20_000_000),
            stat_affix(56, 20_000_000),
        )
    ]

    result = calc.calc_player_stats(payload, datacron_id=DATACRON_ID)
    assert isinstance(result, dict)

    checked = 0
    for unit in result["rosterUnit"]:
        bucket = unit.get("stats", {}).get("datacron")
        if not bucket:
            continue
        assert set(bucket) <= set(unit["stats"]["final"])
        checked += 1

    assert checked > 100


# ── Degenerate datacrons ──────────────────────────────────────────────────


def test_datacron_with_no_affixes_yields_an_empty_bucket(calc: StatCalc) -> None:
    payload = player(character(), datacrons=[datacron()])

    assert datacron_bucket(calc, payload) == {}


def test_partially_levelled_datacron_is_handled(calc: StatCalc) -> None:
    """A three-affix datacron is as valid as a fifteen-affix one."""
    payload = player(
        character(),
        datacrons=[datacron(stat_affix(16, 10_000_000), stat_affix(17, 10_000_000), ability_affix())],
    )

    assert datacron_bucket(calc, payload) == {
        "Critical Damage": pytest.approx(0.1),
        "Potency": pytest.approx(0.1),
    }


# ── Selection errors ──────────────────────────────────────────────────────


def test_unknown_datacron_id_raises(calc: StatCalc) -> None:
    payload = player(character(), datacrons=[datacron(stat_affix(16, 10_000_000))])

    with pytest.raises(KeyError, match="not among the player's"):
        calc.calc_player_stats(payload, datacron_id="no-such-datacron")


def test_player_owning_no_datacrons_is_distinct_from_a_missing_collection(calc: StatCalc) -> None:
    """An empty collection is a real state; a missing one is a malformed payload."""
    owns_none = player(character(), datacrons=[])
    with pytest.raises(KeyError, match="not among the player's"):
        calc.calc_player_stats(owns_none, datacron_id=DATACRON_ID)

    malformed = player(character())
    del malformed["datacron"]
    with pytest.raises(KeyError, match="no 'datacron' collection"):
        calc.calc_player_stats(malformed, datacron_id=DATACRON_ID)


def test_a_missing_collection_is_ignored_when_no_datacron_is_requested(calc: StatCalc) -> None:
    payload = player(character())
    del payload["datacron"]

    result = calc.calc_player_stats(payload)
    assert isinstance(result, dict)
    assert "datacron" not in result["rosterUnit"][0]["stats"]


# ── Ships ─────────────────────────────────────────────────────────────────


def test_ships_gain_no_bucket_and_their_stats_are_unchanged(
    calc: StatCalc, example_player: dict[str, Any], game_data: dict[str, Any]
) -> None:
    """Datacrons are a squad mechanic — no game mode applies one to a fleet."""
    owned = example_player["datacron"][0]["id"]

    without = calc.calc_player_stats(copy.deepcopy(example_player))
    with_dc = calc.calc_player_stats(copy.deepcopy(example_player), datacron_id=owned)
    assert isinstance(without, dict)
    assert isinstance(with_dc, dict)

    ships = {
        unit["definitionId"].split(":")[0]
        for unit in with_dc["rosterUnit"]
        if game_data["unitData"].get(unit["definitionId"].split(":")[0], {}).get("combatType") == 2
    }
    assert ships, "example player has no ships; this test would prove nothing"

    by_id = {unit["definitionId"]: unit for unit in without["rosterUnit"]}
    for unit in with_dc["rosterUnit"]:
        if unit["definitionId"].split(":")[0] not in ships:
            continue
        assert "datacron" not in unit["stats"]
        assert unit["stats"] == by_id[unit["definitionId"]]["stats"]


def test_characters_crewing_a_ship_still_receive_their_own_bucket(
    calc: StatCalc, example_player: dict[str, Any], game_data: dict[str, Any]
) -> None:
    """Crew rating reads a unit's raw attributes, never its calculated stats,
    so a crew member's bucket cannot leak into the ship it crews."""
    owned = example_player["datacron"][0]["id"]

    result = calc.calc_player_stats(copy.deepcopy(example_player), datacron_id=owned)
    assert isinstance(result, dict)

    crewed = {
        crew_id
        for unit in result["rosterUnit"]
        for crew_id in game_data["unitData"].get(unit["definitionId"].split(":")[0], {}).get("crew", [])
    }
    assert crewed, "example player has no crewed ships; this test would prove nothing"

    seen = [unit for unit in result["rosterUnit"] if unit["definitionId"].split(":")[0] in crewed and "stats" in unit]
    assert seen, "no crew members in roster"
    assert all("datacron" in unit["stats"] for unit in seen)
