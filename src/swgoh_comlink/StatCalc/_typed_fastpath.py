# coding=utf-8
"""v3.3 Phase 4b — typed-fastpath input adapter.

NOT for production import without Phase 5 approval. Lives on the
throwaway ``v3.3/statcalc-typed-fastpath`` branch.

**What this does**

The v3.2-shipped bimorphic path (Candidate A, in ``calculator.py``)
funnels typed :class:`~swgoh_comlink._models.Player` Structs through
``msgspec.to_builtins()`` at the boundary, then routes the resulting
dict tree through the existing pure-dict path. That conversion costs
~5 ms (+22.9 %) on a 397-unit roster — almost entirely because
``msgspec.to_builtins`` walks every field of every nested
:class:`~swgoh_comlink._models.Mod` (9 fields × 6 mods × 397 units),
plus all the Player-level metadata StatCalc never reads (profile,
guild_id, datacron, pvp_profile, season_status, …).

This module skips ``msgspec.to_builtins`` entirely. Instead it does
direct attribute reads on the Struct's ``__slots__`` (~2-3× faster
than dict subscript) and constructs only the minimum dict shape
``_normalize_char`` / ``_normalize_ship_and_crew`` expect.

The targeted bar is **bimorphic Struct overhead ≤ 5 %** (vs v3.2's
+22.9 %). If achieved, the new fastpath replaces the v3.2 Candidate A
dispatcher internally; external behaviour stays.

**What StatCalc actually reads from a RosterUnit** (per the v3.2 audit
+ ``_normalize_char`` source inspection):

- ``definition_id`` — parsed (split on ``:``) to get unit base ID
- ``current_level``, ``current_rarity``, ``current_tier``
- ``equipment`` — only ``len()`` matters (for ship crew rating)
- ``equipped_stat_mod`` — full Mod data, see below
- ``relic`` — only ``current_tier`` matters
- ``skill[]`` — ``id`` + ``tier`` (with the v2-style ``tier + 2`` shift)

**What StatCalc actually reads from a Mod** (per
``_calculate_mod_stats`` source):

- ``definition_id`` (string; ``[0]`` = set_id, ``[1]`` = pips, ``[2]`` = slot)
- ``primary_stat.stat.unit_stat_id``
- ``primary_stat.stat.unscaled_decimal_value`` (str, cast to float)
- ``secondary_stat[].stat.unit_stat_id``
- ``secondary_stat[].stat.unscaled_decimal_value``
- ``tier``
- ``level``

Every other field on the Mod Struct (``bonus_quantity``,
``converted_item``, ``id``, ``level_cost``, ``locked``,
``remove_cost``, ``rerolled_count``, ``sell_value``, ``xp``) is
unused by StatCalc and skipped here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from swgoh_comlink._models import Mod, Player, RosterUnit


def _mod_to_calc_dict(mod: Mod) -> dict[str, Any]:
    """Convert one :class:`~swgoh_comlink._models.Mod` via direct attribute reads.

    Builds the exact subset of fields ``_calculate_mod_stats`` reads
    in the ``elif char.get("equippedStatMod"):`` branch (the new
    Struct-format path), so the StatCalc code path is unchanged.
    """
    primary = mod.primary_stat
    secondary = mod.secondary_stat
    return {
        "definitionId": mod.definition_id,
        "tier": mod.tier,
        "level": mod.level,
        "primaryStat": (
            {
                "stat": {
                    "unitStatId": primary.stat.unit_stat_id,
                    "unscaledDecimalValue": primary.stat.unscaled_decimal_value,
                }
            }
            if primary is not None
            else None
        ),
        "secondaryStat": [
            {
                "stat": {
                    "unitStatId": s.stat.unit_stat_id,
                    "unscaledDecimalValue": s.stat.unscaled_decimal_value,
                }
            }
            for s in (secondary or [])
        ],
    }


def _roster_unit_to_calc_dict(unit: RosterUnit) -> dict[str, Any]:
    """Convert one :class:`~swgoh_comlink._models.RosterUnit` to the
    minimal dict shape :meth:`StatCalc._normalize_char` expects.

    Direct attribute reads only — no ``msgspec.to_builtins`` walk.
    Skips ``id``, ``current_xp``, ``promotion_recipe_reference``,
    ``purchased_ability_id``, ``unit_stat``, ``equipped_stat_mod_old``
    (all unused by StatCalc).
    """
    mods = unit.equipped_stat_mod
    relic = unit.relic
    skills = unit.skill
    return {
        "definitionId": unit.definition_id,
        "currentRarity": unit.current_rarity,
        "currentLevel": unit.current_level,
        "currentTier": unit.current_tier,
        # equipment Structs are typed as ``dict[str, Any]`` already
        # (the v3.1 typed-segments work didn't promote Equipment to
        # a Struct because the field is small and dict-shaped on the
        # wire). The list contents (``{equipmentId, slot}``) are
        # consumed both by ``_get_char_raw_stats`` (reads
        # equipmentId for gear stat lookup) and by ``_get_crew_rating``
        # (len(equipped) for ship crew rating). Pass through directly
        # — no per-item conversion required.
        "equipment": list(unit.equipment) if unit.equipment else [],
        "equippedStatMod": [_mod_to_calc_dict(m) for m in mods] if mods else None,
        "relic": ({"currentTier": relic.current_tier} if relic is not None else None),
        "skill": [{"id": s.id, "tier": s.tier} for s in skills],
    }


def player_struct_to_calc_dict(player: Player) -> dict[str, Any]:
    """Convert one :class:`~swgoh_comlink._models.Player` to the minimal
    dict shape :meth:`StatCalc.calc_player_stats` expects.

    Skips every Player-level field StatCalc doesn't read (``profile``,
    ``guild_id``, ``datacron``, ``pvp_profile``, ``season_status``,
    ``lifetime_season_status``, ``selected_player_*``, etc.).
    """
    return {
        "rosterUnit": [_roster_unit_to_calc_dict(u) for u in player.roster_unit],
    }


__all__ = [
    "_mod_to_calc_dict",
    "_roster_unit_to_calc_dict",
    "player_struct_to_calc_dict",
]
