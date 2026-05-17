# coding=utf-8
"""v3.1 — typed `/data` segment decode via ``compat.decode_segment``.

Validates the generic helper end-to-end against the recorded ``/data``
cassette for every entry in :data:`compat.STOCK_SEGMENT_TYPES` (units +
13 other segments), plus sanity tests for the error paths and the
bring-your-own-Struct path.

The BADBATCHECHO field-round-trip test on the ``units`` segment is kept
as a representative deep-shape verification — it protects the Unit
Struct's nested fields (base_stat / skill_reference / unit_tier /
basic_attack_ref / category_id) against silent drift.
"""

from __future__ import annotations

import msgspec
import pytest
from tests.v3.conftest import load_cassette_json

from swgoh_comlink import compat
from swgoh_comlink._models import (
    AbilityRef,
    RelicDefinition,
    SkillReference,
    Unit,
    UnitTierEntry,
)

# Sentinel chosen because the recorded cassette includes the full
# nesting set for it: typed unit_tier list, relic_definition, skill
# refs, example_squad, mod_recommendation.
SENTINEL_BASE_ID = "BADBATCHECHO"


def _find_unit(payload: dict, base_id: str) -> dict:
    for u in payload["units"]:
        if u.get("baseId") == base_id:
            return u
    raise AssertionError(f"sentinel {base_id!r} not in cassette")


# ── Parametrized: every stock segment decodes cleanly ──────────────────────


@pytest.mark.parametrize(
    "segment,target",
    list(compat.STOCK_SEGMENT_TYPES.items()),
    ids=list(compat.STOCK_SEGMENT_TYPES),
)
def test_stock_segment_decodes(segment: str, target: type) -> None:
    payload = load_cassette_json("data")
    decoded = compat.decode_segment(payload, segment)
    raw = payload.get(segment, [])
    assert len(decoded) == len(raw), f"count mismatch for {segment}"
    if decoded:
        assert isinstance(decoded[0], target), f"first item is {type(decoded[0]).__name__}, expected {target.__name__}"


# ── Sanity / error-path tests ──────────────────────────────────────────────


def test_decode_segment_unknown_no_target_raises() -> None:
    with pytest.raises(ValueError, match="no stock type registered"):
        compat.decode_segment({}, "no_such_segment")


def test_decode_segment_with_custom_target() -> None:
    """User-supplied Struct decodes without touching STOCK_SEGMENT_TYPES."""

    class MyTinyMaterial(msgspec.Struct, rename="camel"):
        id: str = ""
        rarity: int = 0
        tier: int = 0

    payload = load_cassette_json("data")
    out = compat.decode_segment(payload, "material", target=MyTinyMaterial)
    assert len(out) > 100
    assert all(isinstance(m, MyTinyMaterial) for m in out)
    # Confirm the user fields populated (not just zero defaults).
    assert any(m.id and m.rarity > 0 for m in out)


def test_decode_segment_empty_payload() -> None:
    assert compat.decode_segment({}, "units") == []
    assert compat.decode_segment({"units": []}, "units") == []
    # Unknown key but registered segment → still []
    assert compat.decode_segment({"foo": [{"x": 1}]}, "material") == []


# ── Sentinel deep-shape verification (units Struct round-trip) ─────────────


def test_units_field_round_trip_sentinel() -> None:
    payload = load_cassette_json("data")
    raw = _find_unit(payload, SENTINEL_BASE_ID)
    units = compat.decode_segment(payload, "units")
    typed = next(u for u in units if u.base_id == SENTINEL_BASE_ID)
    assert isinstance(typed, Unit)

    # Scalars
    assert typed.id == raw["id"]
    assert typed.name_key == raw["nameKey"]
    assert typed.rarity == raw["rarity"]
    assert typed.max_rarity == raw["maxRarity"]
    assert typed.combat_type == raw["combatType"]
    assert typed.base_power == raw["basePower"]
    assert typed.legend is raw["legend"]

    # base_stat → first stat entry
    assert raw["baseStat"]["stat"], "sentinel must have base stats"
    assert typed.base_stat.stat[0].unit_stat_id == raw["baseStat"]["stat"][0]["unitStatId"]
    assert typed.base_stat.stat[0].stat_value_decimal == raw["baseStat"]["stat"][0]["statValueDecimal"]

    # Typed nested lists
    assert len(typed.skill_reference) == len(raw["skillReference"])
    if typed.skill_reference:
        assert isinstance(typed.skill_reference[0], SkillReference)
        assert typed.skill_reference[0].skill_id == raw["skillReference"][0]["skillId"]

    assert len(typed.unit_tier) == len(raw["unitTier"])
    if typed.unit_tier:
        raw_tier = raw["unitTier"][0]
        typed_tier = typed.unit_tier[0]
        assert isinstance(typed_tier, UnitTierEntry)
        assert typed_tier.tier == raw_tier["tier"]
        assert typed_tier.equipment_set == raw_tier["equipmentSet"]
        if raw_tier["baseStat"]["stat"]:
            assert typed_tier.base_stat.stat[0].unit_stat_id == raw_tier["baseStat"]["stat"][0]["unitStatId"]

    # AbilityRef on basic_attack_ref
    assert isinstance(typed.basic_attack_ref, AbilityRef)
    assert typed.basic_attack_ref.ability_id == raw["basicAttackRef"]["abilityId"]
    assert typed.basic_attack_ref.required_rarity == raw["basicAttackRef"]["requiredRarity"]

    # relic_definition (optional)
    if raw.get("relicDefinition"):
        assert isinstance(typed.relic_definition, RelicDefinition)
        assert typed.relic_definition.upgrade_table_id == raw["relicDefinition"]["upgradeTableId"]

    # Categories
    assert typed.category_id == raw["categoryId"]
