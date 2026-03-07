"""GameDataBuilder transformation logic.

Transforms raw Comlink game data responses into the dict format expected
by ``StatCalc.set_game_data()``.  All methods are pure computation — no I/O.

The output dict has six top-level keys:

- ``unitData``   — per-unit combat metadata (gear tiers, skills, relics, etc.)
- ``gearData``   — equipment stat bonuses
- ``modSetData`` — mod set completion bonuses
- ``crTables``   — crew-rating lookup tables (plus mastery tables)
- ``gpTables``   — galactic-power lookup tables
- ``relicData``  — relic tier stat bonuses and growth modifiers
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enum / constant mappings
# ---------------------------------------------------------------------------

_RARITY_ENUM: dict[str, int] = {
    "ONE_STAR": 1,
    "TWO_STAR": 2,
    "THREE_STAR": 3,
    "FOUR_STAR": 4,
    "FIVE_STAR": 5,
    "SIX_STAR": 6,
    "SEVEN_STAR": 7,
}

_STAT_ENUM: dict[str, int] = {
    "MAX_HEALTH": 1,
    "STRENGTH": 2,
    "AGILITY": 3,
    "INTELLIGENCE": 4,
    "SPEED": 5,
    "ATTACK_DAMAGE": 6,
    "ABILITY_POWER": 7,
    "ARMOR": 8,
    "SUPPRESSION": 9,
    "ARMOR_PENETRATION": 10,
    "SUPPRESSION_PENETRATION": 11,
    "DODGE_RATING": 12,
    "DEFLECTION_RATING": 13,
    "ATTACK_CRITICAL_RATING": 14,
    "ABILITY_CRITICAL_RATING": 15,
    "CRITICAL_DAMAGE": 16,
    "ACCURACY": 17,
    "RESISTANCE": 18,
    "DODGE_PERCENT_ADDITIVE": 19,
    "DEFLECTION_PERCENT_ADDITIVE": 20,
    "ATTACK_CRITICAL_PERCENT_ADDITIVE": 21,
    "ABILITY_CRITICAL_PERCENT_ADDITIVE": 22,
    "ARMOR_PERCENT_ADDITIVE": 23,
    "SUPPRESSION_PERCENT_ADDITIVE": 24,
    "ARMOR_PENETRATION_PERCENT_ADDITIVE": 25,
    "SUPPRESSION_PENETRATION_PERCENT_ADDITIVE": 26,
    "HEALTH_STEAL": 27,
    "MAX_SHIELD": 28,
    "SHIELD_PENETRATION": 29,
    "HEALTH_REGEN": 30,
    "ATTACK_DAMAGE_PERCENT_ADDITIVE": 31,
    "ABILITY_POWER_PERCENT_ADDITIVE": 32,
    "DODGE_NEGATE_PERCENT_ADDITIVE": 33,
    "DEFLECTION_NEGATE_PERCENT_ADDITIVE": 34,
    "ATTACK_CRITICAL_NEGATE_PERCENT_ADDITIVE": 35,
    "ABILITY_CRITICAL_NEGATE_PERCENT_ADDITIVE": 36,
    "DODGE_NEGATE_RATING": 37,
    "DEFLECTION_NEGATE_RATING": 38,
    "ATTACK_CRITICAL_NEGATE_RATING": 39,
    "ABILITY_CRITICAL_NEGATE_RATING": 40,
    "OFFENSE": 41,
    "DEFENSE": 42,
    "DEFENSE_PENETRATION": 43,
    "EVASION_RATING": 44,
    "CRITICAL_RATING": 45,
    "EVASION_NEGATE_RATING": 46,
    "CRITICAL_NEGATE_RATING": 47,
    "OFFENSE_PERCENT_ADDITIVE": 48,
    "DEFENSE_PERCENT_ADDITIVE": 49,
    "DEFENSE_PENETRATION_PERCENT_ADDITIVE": 50,
    "EVASION_PERCENT_ADDITIVE": 51,
    "EVASION_NEGATE_PERCENT_ADDITIVE": 52,
    "CRITICAL_CHANCE_PERCENT_ADDITIVE": 53,
    "CRITICAL_NEGATE_CHANCE_PERCENT_ADDITIVE": 54,
    "MAX_HEALTH_PERCENT_ADDITIVE": 55,
    "MAX_SHIELD_PERCENT_ADDITIVE": 56,
    "SPEED_PERCENT_ADDITIVE": 57,
    "COUNTER_ATTACK_RATING": 58,
    "TAUNT": 59,
}

_PRIMARY_STATS: dict[int, str] = {2: "strength", 3: "agility", 4: "intelligence"}

_RELIC_TIER_OFFSET: int = 2

# Pre-compiled patterns
_TIER_RE = re.compile(r"TIER_0?(\d+)")
_MASTERY_RE = re.compile(r"_mastery$")
_ROLE_RE = re.compile(r"^role_(?!leader)([^_]+)$")
_RELIC_SUFFIX_RE = re.compile(r"(\d+)$")
_ABILITY_KEY_RE = re.compile(r"^(\w+?)_\w+?(\d)?$")


# ===================================================================
# Public API
# ===================================================================


class GameDataBuilderBase:
    """Pure-computation base for building StatCalc game data.

    Subclasses add sync or async I/O to fetch the raw data from Comlink.
    """

    @staticmethod
    def _build_game_data(raw: dict[str, Any]) -> dict[str, Any]:
        """Transform a raw Comlink ``get_game_data()`` response.

        Args:
            raw: Full JSON response from ``SwgohComlink.get_game_data()``.

        Returns:
            Dict ready for ``StatCalc.set_game_data()`` with keys
            ``unitData``, ``gearData``, ``modSetData``, ``crTables``,
            ``gpTables``, ``relicData``.
        """
        stat_tables = _build_stat_tables(raw.get("statProgression", []))
        skills_map = _build_skills_map(raw.get("skill", []))

        unit_data = _build_unit_data(
            raw.get("units", []),
            stat_tables,
            skills_map,
        )
        gear_data = _build_gear_data(raw.get("equipment", []))
        mod_set_data = _build_mod_set_data(raw.get("statModSet", []))
        cr_tables, gp_tables = _build_cr_gp_tables(
            raw.get("table", []),
            raw.get("xpTable", []),
        )
        relic_data = _build_relic_data(
            raw.get("relicTierDefinition", []),
            stat_tables,
        )

        result = {
            "unitData": unit_data,
            "gearData": gear_data,
            "modSetData": mod_set_data,
            "crTables": cr_tables,
            "gpTables": gp_tables,
            "relicData": relic_data,
        }
        logger.info(
            "Built game data: units=%d gear=%d relics=%d",
            len(unit_data),
            len(gear_data),
            len(relic_data),
        )
        return result


# ===================================================================
# Intermediate builders
# ===================================================================


def _build_stat_tables(raw_progressions: list[dict]) -> dict[str, dict[str, int]]:
    """Parse ``statProgression`` entries into ``{tableId: {statId: value}}``."""
    tables: dict[str, dict[str, int]] = {}
    for entry in raw_progressions:
        table_id = entry.get("id", "")
        if not table_id.startswith("stattable_"):
            continue
        table_data: dict[str, int] = {}
        for s in entry.get("stat", {}).get("statList", []):
            table_data[str(s.get("unitStatId", ""))] = _num(
                s.get("unscaledDecimalValue", 0)
            )
        tables[table_id] = table_data
    return tables


def _build_skills_map(raw_skills: list[dict]) -> dict[str, dict[str, Any]]:
    """Build ``{skillId: {id, maxTier, isZeta, powerOverrideTags}}``."""
    skills: dict[str, dict[str, Any]] = {}
    for skill in raw_skills:
        skill_id = skill.get("id", "")
        tier_list = skill.get("tierList", [])
        max_tier = len(tier_list) + 1

        is_zeta = False
        if tier_list:
            is_zeta = tier_list[-1].get("powerOverrideTag", "") == "zeta"

        power_tags: dict[str, str] = {}
        for i, tier in enumerate(tier_list):
            tag = tier.get("powerOverrideTag", "")
            if tag:
                power_tags[str(i + 2)] = tag

        skills[skill_id] = {
            "id": skill_id,
            "maxTier": max_tier,
            "isZeta": is_zeta,
            "powerOverrideTags": power_tags,
        }
    return skills


def _build_unit_data(
    raw_units: list[dict],
    stat_tables: dict[str, dict[str, int]],
    skills_map: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Build per-unit metadata for characters and ships.

    The Comlink ``units`` field is an array of rarity groups, each
    containing a ``unitDef`` array.  Rarity-1 entries supply base
    definitions (gear tiers, skills, etc.); all rarities contribute
    ``statProgressionId`` for growth modifier tables.
    """
    base_units: dict[str, dict] = {}
    stat_prog_map: dict[str, dict[str, str]] = {}

    for unit_group in raw_units:
        rarity = unit_group.get("rarity", 1)
        for unit in unit_group.get("unitDef", []):
            base_id = unit.get("baseId", "")
            if not base_id:
                continue
            if not unit.get("obtainable", False):
                continue

            prog_id = unit.get("statProgressionId", "")
            if prog_id:
                stat_prog_map.setdefault(base_id, {})[str(rarity)] = prog_id

            if rarity == 1:
                base_units[base_id] = unit

    data: dict[str, dict[str, Any]] = {}
    for base_id, unit in base_units.items():
        combat_type = unit.get("combatType", 1)
        primary_stat = unit.get("primaryUnitStat", 2)

        if combat_type == 1:
            data[base_id] = _build_character(
                base_id, unit, primary_stat, stat_prog_map, stat_tables, skills_map
            )
        else:
            data[base_id] = _build_ship(
                base_id, unit, primary_stat, stat_prog_map, stat_tables, skills_map
            )
    return data


def _build_character(
    base_id: str,
    unit: dict,
    primary_stat: int,
    stat_prog_map: dict[str, dict[str, str]],
    stat_tables: dict[str, dict[str, int]],
    skills_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    # Gear tiers
    gear_lvl: dict[str, dict[str, Any]] = {}
    for gt in unit.get("unitTierList", []):
        tier_num = str(gt.get("tier", 1))
        tier_stats: dict[str, int] = {}
        for s in gt.get("baseStat", {}).get("statList", []):
            tier_stats[str(s.get("unitStatId", ""))] = _num(
                s.get("unscaledDecimalValue", 0)
            )
        gear_lvl[tier_num] = {
            "gear": gt.get("equipmentSetList", []),
            "stats": tier_stats,
        }

    # Growth modifiers per rarity
    growth: dict[str, dict[str, int]] = {}
    for rarity_str, prog_id in stat_prog_map.get(base_id, {}).items():
        if prog_id in stat_tables:
            growth[rarity_str] = dict(stat_tables[prog_id])

    # Skill references
    skill_refs = _resolve_skills(unit.get("skillReferenceList", []), skills_map)

    # Relic tier mapping
    relic: dict[str, str] = {}
    relic_def = unit.get("relicDefinition") or {}
    for tier_id in relic_def.get("relicTierDefinitionIdList", []):
        m = _RELIC_SUFFIX_RE.search(tier_id)
        if m:
            relic[str(int(m.group(1)) + _RELIC_TIER_OFFSET)] = tier_id

    # Mastery modifier
    mastery_id = _mastery_name(primary_stat, unit.get("categoryIdList", []))

    return {
        "combatType": 1,
        "primaryStat": primary_stat,
        "gearLvl": gear_lvl,
        "growthModifiers": growth,
        "skills": skill_refs,
        "relic": relic,
        "masteryModifierID": mastery_id,
    }


def _build_ship(
    base_id: str,
    unit: dict,
    primary_stat: int,
    stat_prog_map: dict[str, dict[str, str]],
    stat_tables: dict[str, dict[str, int]],
    skills_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    # Base stats
    stats: dict[str, int] = {}
    for s in unit.get("baseStat", {}).get("statList", []):
        stats[str(s.get("unitStatId", ""))] = _num(
            s.get("unscaledDecimalValue", 0)
        )

    # Growth modifiers per rarity
    growth: dict[str, dict[str, int]] = {}
    for rarity_str, prog_id in stat_prog_map.get(base_id, {}).items():
        if prog_id in stat_tables:
            growth[rarity_str] = dict(stat_tables[prog_id])

    # Skill references
    skill_refs = _resolve_skills(unit.get("skillReferenceList", []), skills_map)

    # Crew contribution stats table
    crew_table_id = unit.get("crewContributionTableId", "")
    crew_stats = dict(stat_tables.get(crew_table_id, {}))

    # Crew member IDs
    crew = [m.get("unitId", "") for m in unit.get("crewList", [])]

    return {
        "combatType": 2,
        "primaryStat": primary_stat,
        "stats": stats,
        "growthModifiers": growth,
        "skills": skill_refs,
        "crewStats": crew_stats,
        "crew": crew,
    }


def _build_gear_data(raw_equipment: list[dict]) -> dict[str, dict[str, Any]]:
    """Build ``{gearId: {stats: {statId: value}}}``."""
    data: dict[str, dict[str, Any]] = {}
    for gear in raw_equipment:
        gear_id = gear.get("id", "")
        stat_list = gear.get("equipmentStat", {}).get("statList", [])
        if stat_list:
            stats: dict[str, int] = {}
            for s in stat_list:
                stats[str(s.get("unitStatId", ""))] = _num(
                    s.get("unscaledDecimalValue", 0)
                )
            data[gear_id] = {"stats": stats}
    return data


def _build_mod_set_data(raw_mod_sets: list[dict]) -> dict[str, dict[str, Any]]:
    """Build ``{setId: {id, count, value}}``."""
    data: dict[str, dict[str, Any]] = {}
    for ms in raw_mod_sets:
        set_id = str(ms.get("id", ""))
        bonus = ms.get("completeBonus", {}).get("stat", {})
        data[set_id] = {
            "id": bonus.get("unitStatId", 0),
            "count": ms.get("setCount", 0),
            "value": _num(bonus.get("unscaledDecimalValue", 0)),
        }
    return data


def _build_cr_gp_tables(
    raw_tables: list[dict],
    raw_xp_tables: list[dict],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build crew-rating and galactic-power lookup tables.

    Parses the ``table`` (DataTable) and ``xpTable`` (XpTable) arrays
    from the Comlink response, routing each recognised table ID to the
    appropriate output structure.
    """
    cr: dict[str, Any] = {}
    gp: dict[str, Any] = {}

    for table in raw_tables:
        tid = table.get("id", "")
        rows = table.get("rowList", [])

        # ---- CR tables ----
        if tid == "crew_rating_per_unit_rarity":
            cr["crewRarityCR"] = _rarity_rows(rows)
        elif tid == "crew_rating_per_gear_piece_at_tier":
            cr["gearPieceCR"] = _tier_rows(rows)
        elif tid == "crew_rating_per_gear_level":
            cr["gearLevelCR"] = _int_rows(rows)
        elif tid == "crew_contribution_multiplier_per_rarity":
            cr["shipRarityFactor"] = _rarity_rows(rows)
        elif tid == "crew_rating_per_mod_rarity_level_tier":
            cr["modRarityLevelCR"] = _mod_cr_rows(rows)
        elif tid == "crew_rating_modifier_per_relic_tier":
            cr["relicTierLevelFactor"] = _relic_rows(rows)
        elif tid == "crew_rating_per_relic_tier":
            cr["relicTierCR"] = _relic_rows(rows)

        # ---- Shared CR + GP ----
        elif tid == "galactic_power_per_tagged_ability_level_table":
            cr["abilitySpecialCR"] = _ability_special_cr(rows)
            gp["abilitySpecialGP"] = _ability_special_gp(rows)

        # ---- GP tables ----
        elif tid == "galactic_power_modifier_per_ship_crew_size_table":
            gp["crewSizeFactor"] = _int_rows(rows)
        elif tid == "galactic_power_per_unit_rarity":
            gp["unitRarityGP"] = _rarity_rows(rows)
        elif tid == "galactic_power_per_gear_level":
            gp["gearLevelGP"] = _int_rows(rows)
        elif tid == "galactic_power_per_relic_tier":
            gp["relicTierGP"] = _relic_rows(rows)
        elif tid == "galactic_power_modifier_per_relic_tier":
            gp["relicTierLevelFactor"] = _relic_rows(rows)
        elif tid == "galactic_power_modifier_per_ship_rarity":
            gp["shipRarityFactor"] = _rarity_rows(rows)
        elif tid == "galactic_power_per_gear_piece_at_tier":
            gp["gearPieceGP"] = _gear_piece_gp_rows(rows)
        elif tid == "galactic_power_per_mod_rarity_level_tier":
            gp["modRarityLevelTierGP"] = _mod_gp_rows(rows)

        # ---- Mastery tables ----
        elif _MASTERY_RE.search(tid):
            cr[tid] = _stat_enum_rows(rows)

    # ---- XP tables ----
    for table in raw_xp_tables:
        tid = table.get("id", "")
        rows = table.get("rowList", [])

        if tid == "crew_rating_per_unit_level":
            cr["unitLevelCR"] = _xp_rows(rows)
        elif tid == "crew_rating_per_ability_level":
            cr["abilityLevelCR"] = _xp_rows(rows)
        elif tid == "galactic_power_per_unit_level":
            gp["unitLevelGP"] = _xp_rows(rows)
        elif tid == "galactic_power_per_ability_level":
            gp["abilityLevelGP"] = _xp_rows(rows)
        elif tid == "galactic_power_per_ship_level":
            gp["shipLevelGP"] = _xp_rows(rows)
        elif tid == "galactic_power_per_ship_ability_level":
            gp["shipAbilityLevelGP"] = _xp_rows(rows)

    return cr, gp


def _build_relic_data(
    raw_relic_defs: list[dict],
    stat_tables: dict[str, dict[str, int]],
) -> dict[str, dict[str, Any]]:
    """Build ``{relicDefId: {stats: {...}, gms: {...}}}``."""
    data: dict[str, dict[str, Any]] = {}
    for relic in raw_relic_defs:
        relic_id = relic.get("id", "")
        stats: dict[str, int] = {}
        for s in relic.get("stat", {}).get("statList", []):
            stats[str(s.get("unitStatId", ""))] = _num(
                s.get("unscaledDecimalValue", 0)
            )
        gms = dict(stat_tables.get(relic.get("relicStatTable", ""), {}))
        data[relic_id] = {"stats": stats, "gms": gms}
    return data


# ===================================================================
# Row-parsing helpers
# ===================================================================


def _rarity_rows(rows: list[dict]) -> dict[str, float]:
    """Rows keyed by rarity enum strings (``ONE_STAR`` … ``SEVEN_STAR``)."""
    out: dict[str, float] = {}
    for r in rows:
        rarity = _RARITY_ENUM.get(r.get("key", ""))
        if rarity is not None:
            out[str(rarity)] = _num(r.get("value", 0))
    return out


def _tier_rows(rows: list[dict]) -> dict[str, float]:
    """Rows keyed by ``TIER_01``, ``TIER_02``, etc."""
    out: dict[str, float] = {}
    for r in rows:
        m = _TIER_RE.match(r.get("key", ""))
        if m:
            out[m.group(1)] = _num(r.get("value", 0))
    return out


def _int_rows(rows: list[dict]) -> dict[str, float]:
    """Rows with plain integer keys."""
    return {str(r.get("key", "")): _num(r.get("value", 0)) for r in rows}


def _relic_rows(rows: list[dict]) -> dict[str, float]:
    """Rows with 0-based index keys, shifted by ``_RELIC_TIER_OFFSET``."""
    out: dict[str, float] = {}
    for r in rows:
        try:
            tier = int(r.get("key", 0)) + _RELIC_TIER_OFFSET
        except (ValueError, TypeError):
            continue
        out[str(tier)] = _num(r.get("value", 0))
    return out


def _stat_enum_rows(rows: list[dict]) -> dict[str, float]:
    """Rows keyed by stat enum strings (``STRENGTH``, ``MAX_HEALTH``, …)."""
    out: dict[str, float] = {}
    for r in rows:
        sid = _STAT_ENUM.get(r.get("key", ""))
        if sid is not None:
            out[str(sid)] = _num(r.get("value", 0))
    return out


def _mod_cr_rows(rows: list[dict]) -> dict[str, dict[str, float]]:
    """Mod CR rows (``pips:level:tier:set``); keep only tier=1, set=0.

    Returns ``{pips: {level: value}}``.
    """
    out: dict[str, dict[str, float]] = {}
    for r in rows:
        key = r.get("key", "")
        if not key.endswith("1:0"):
            continue
        parts = key.split(":")
        if len(parts) < 2:
            continue
        pips, level = parts[0], parts[1]
        out.setdefault(pips, {})[level] = _num(r.get("value", 0))
    return out


def _mod_gp_rows(rows: list[dict]) -> dict[str, dict[str, dict[str, float]]]:
    """Mod GP rows (``pips:level:tier[:set]``).

    Returns ``{pips: {level: {tier: value}}}``.
    """
    out: dict[str, dict[str, dict[str, float]]] = {}
    for r in rows:
        parts = r.get("key", "").split(":")
        if len(parts) < 3:
            continue
        pips, level, tier = parts[0], parts[1], parts[2]
        out.setdefault(pips, {}).setdefault(level, {})[tier] = _num(
            r.get("value", 0)
        )
    return out


def _gear_piece_gp_rows(rows: list[dict]) -> dict[str, dict[str, float]]:
    """Gear-piece GP rows (``tier:slot`` or ``TIER_XX:slot``).

    Returns ``{tier: {slot: value}}``.
    """
    out: dict[str, dict[str, float]] = {}
    for r in rows:
        parts = r.get("key", "").split(":")
        if len(parts) < 2:
            continue
        tier_raw, slot = parts[0], parts[1]
        m = _TIER_RE.match(tier_raw)
        tier = m.group(1) if m else str(tier_raw)
        out.setdefault(tier, {})[slot] = _num(r.get("value", 0))
    return out


def _ability_special_cr(rows: list[dict]) -> dict[str, Any]:
    """Parse ability-special table for CR (grouped contracts/hardware)."""
    out: dict[str, Any] = {}
    for r in rows:
        key = r.get("key", "")
        value = _num(r.get("value", 0))
        if key == "zeta":
            out["zeta"] = value
            continue
        m = _ABILITY_KEY_RE.match(key)
        if not m:
            continue
        kind, digit = m.group(1), m.group(2)
        if kind == "contract":
            sub = out.setdefault("contract", {})
            sub[str((int(digit) + 1) if digit else 1)] = value
        elif kind == "reinforcement":
            sub = out.setdefault("hardware", {"1": 0})
            sub[str(int(digit) + 1 if digit else 1)] = value
    return out


def _ability_special_gp(rows: list[dict]) -> dict[str, float]:
    """Parse ability-special table for GP (flat key→value)."""
    return {r.get("key", ""): _num(r.get("value", 0)) for r in rows}


def _xp_rows(rows: list[dict]) -> dict[str, float]:
    """XP-table rows (0-indexed ``index`` → 1-indexed output keys)."""
    return {str(r.get("index", 0) + 1): _num(r.get("xp", 0)) for r in rows}


# ===================================================================
# Tiny utilities
# ===================================================================


def _num(value: Any) -> int | float:
    """Coerce *value* to ``int`` or ``float``, defaulting to ``0``."""
    if isinstance(value, (int, float)):
        return value
    try:
        s = str(value)
        return float(s) if "." in s else int(s)
    except (ValueError, TypeError):
        return 0


def _resolve_skills(
    refs: list[dict], skills_map: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Map ``skillReferenceList`` entries to resolved skill dicts."""
    out: list[dict[str, Any]] = []
    for ref in refs:
        sid = ref.get("skillId", "")
        if sid in skills_map:
            out.append(dict(skills_map[sid]))
    return out


def _mastery_name(primary_stat_id: int, categories: list[str]) -> str:
    """Derive the mastery-modifier table name from stat ID and role tags."""
    stat = _PRIMARY_STATS.get(primary_stat_id, "strength")
    role = "attacker"
    for tag in categories:
        m = _ROLE_RE.match(tag)
        if m:
            role = m.group(1)
            break
    return f"{stat}_role_{role}_mastery"
