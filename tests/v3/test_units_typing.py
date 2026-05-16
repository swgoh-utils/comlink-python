# coding=utf-8
"""v3.1 probe — typed `/data.units` decode via ``compat.decode_units_segment``.

Three sanity tests that exercise the helper end-to-end against the
recorded ``/data`` cassette:

* Bulk shape: every entry decodes into a :class:`Unit` Struct.
* Field round-trip: a sentinel unit's typed fields match the raw
  dict view.
* Empty-payload defenses: returns ``[]`` on missing / empty input.
"""

from __future__ import annotations

from tests.v3.conftest import load_cassette_json

from swgoh_comlink import compat
from swgoh_comlink._models import (
    AbilityRef,
    RelicDefinition,
    SkillReference,
    Unit,
    UnitTierEntry,
)

# Sentinel unit chosen because the recorded cassette includes the full
# nesting set for it: typed unit_tier list, relic_definition, skill refs,
# example_squad, mod_recommendation. Pulled by base_id (the id field on
# the cassette appends ":FOUR_STAR" for rarity binding).
SENTINEL_BASE_ID = "BADBATCHECHO"


def _find_sentinel(payload: dict) -> dict:
    for u in payload["units"]:
        if u.get("baseId") == SENTINEL_BASE_ID:
            return u
    raise AssertionError(f"sentinel {SENTINEL_BASE_ID!r} not in cassette")


def test_decode_units_segment_returns_list_of_units() -> None:
    payload = load_cassette_json("data")
    units = compat.decode_units_segment(payload)

    assert len(units) > 10_000, "cassette should hold the full unit table"
    assert all(isinstance(u, Unit) for u in units), "every item must be a Unit Struct"
    # Spot-check sub-Struct types on the first non-trivial unit.
    first_with_relic = next((u for u in units if u.relic_definition is not None), None)
    assert first_with_relic is not None, "cassette should contain at least one relic-bearing unit"
    assert isinstance(first_with_relic.relic_definition, RelicDefinition)
    first_with_tiers = next((u for u in units if u.unit_tier), None)
    assert first_with_tiers is not None
    assert isinstance(first_with_tiers.unit_tier[0], UnitTierEntry)
    assert isinstance(first_with_tiers.basic_attack_ref, AbilityRef)


def test_decode_units_segment_field_round_trip() -> None:
    payload = load_cassette_json("data")
    raw = _find_sentinel(payload)
    units = compat.decode_units_segment(payload)

    typed = next(u for u in units if u.base_id == SENTINEL_BASE_ID)

    # Scalars
    assert typed.id == raw["id"]
    assert typed.name_key == raw["nameKey"]
    assert typed.rarity == raw["rarity"]
    assert typed.max_rarity == raw["maxRarity"]
    assert typed.combat_type == raw["combatType"]
    assert typed.base_power == raw["basePower"]
    assert typed.legend is raw["legend"]

    # Nested: base_stat → first entry
    assert raw["baseStat"]["stat"], "sentinel must have base stats"
    typed_stat = typed.base_stat.stat[0]
    raw_stat = raw["baseStat"]["stat"][0]
    assert typed_stat.unit_stat_id == raw_stat["unitStatId"]
    assert typed_stat.stat_value_decimal == raw_stat["statValueDecimal"]

    # Skill refs (list[Struct])
    assert len(typed.skill_reference) == len(raw["skillReference"])
    if typed.skill_reference:
        assert isinstance(typed.skill_reference[0], SkillReference)
        assert typed.skill_reference[0].skill_id == raw["skillReference"][0]["skillId"]

    # Unit tiers — verify both the wrapper and the nested baseStat.stat
    assert len(typed.unit_tier) == len(raw["unitTier"])
    if typed.unit_tier:
        raw_tier = raw["unitTier"][0]
        typed_tier = typed.unit_tier[0]
        assert typed_tier.tier == raw_tier["tier"]
        assert typed_tier.equipment_set == raw_tier["equipmentSet"]
        if raw_tier["baseStat"]["stat"]:
            assert typed_tier.base_stat.stat[0].unit_stat_id == raw_tier["baseStat"]["stat"][0]["unitStatId"]

    # AbilityRef on basic_attack_ref
    assert typed.basic_attack_ref.ability_id == raw["basicAttackRef"]["abilityId"]
    assert typed.basic_attack_ref.required_rarity == raw["basicAttackRef"]["requiredRarity"]

    # Categories
    assert typed.category_id == raw["categoryId"]


def test_decode_units_segment_empty_payload() -> None:
    assert compat.decode_units_segment({}) == []
    assert compat.decode_units_segment({"units": []}) == []
    # Other segments are ignored — caller can pass any /data dict.
    assert compat.decode_units_segment({"skill": [{"id": "x"}]}) == []
