"""Datacron stat resolution.

Pure computation: no instance state, no game data, no I/O. Datacron stat affixes
carry no unit scope of any kind, so resolving them needs nothing beyond the
datacron itself, the unit it is applied to, and that unit's stats before the
datacron is considered.

Values are in unscaled space throughout: raw game-data fixed point, where ``1e8``
represents ``1.0``. Callers scale for display afterwards.
"""

from __future__ import annotations

import math
from typing import Any

__all__ = [
    "STAT_PERCENT_OF_BASE",
    "STAT_SPLITS",
    "resolve_datacron_stats",
]

# Percent-additive stat ids do not name the stat they affect: they expand onto one
# or more real target stats. Mods and datacrons expand the same ids onto the same
# targets, so the mapping is shared. The arithmetic is not (mods resolve against
# base alone, datacrons against base plus gear), but two copies of the mapping
# could drift apart and silently credit the wrong stat.

#: Stat ids that add their value to each of several stats (e.g. 41, Offense, adds to 6 and 7).
STAT_SPLITS: dict[int, tuple[str, ...]] = {
    41: ("6", "7"),
    42: ("8", "9"),
    53: ("21", "22"),
    54: ("35", "36"),
}

#: Percent stat ids that add a share of an existing stat to each target, floored to whole units.
STAT_PERCENT_OF_BASE: dict[int, tuple[str, ...]] = {
    48: ("6", "7"),
    49: ("8", "9"),
    55: ("1",),
    56: ("28",),
    57: ("5",),
}

# Relic tiers are encoded with their two base states, locked and unlocked, taking
# the first two values, so the relic number a player sees is two lower than the
# encoded one: an encoded 5 is relic 3. An affix's ``requiredRelicTier`` and a
# unit's ``currentTier`` both use this encoding, so they are compared directly.
_LOCKED_RELIC_TIER = 1

_UNIT = 1e8


def resolve_datacron_stats(
    datacron: dict[str, Any],
    unit: dict[str, Any],
    unmodded_total: dict[str, float],
) -> dict[str, float]:
    """Resolve one datacron's stat contribution to one unit.

    Args:
        datacron: A datacron from a player's ``datacron`` collection.
        unit: A normalized character, with ``gear`` and ``relic`` keys.
        unmodded_total: The unit's per-stat base plus gear totals, excluding mods,
            in unscaled space. Datacron percentages resolve against this total;
            in-game readings show mods are not part of it.

    Returns:
        Per-stat contributions keyed by stat id, in unscaled space. Empty when the
        datacron grants the unit nothing.
    """
    gear_tier = int(unit.get("gear") or 0)
    relic_tier = _relic_tier(unit)

    totals: dict[int, float] = {}
    for affix in datacron.get("affix") or ():
        # An ability affix grants an ability, not a stat. It reports stat type 1
        # with value 0 today; skipping it by its ability keeps a future non-zero
        # value from being counted as Health.
        if affix.get("abilityId"):
            continue
        if gear_tier < int(affix.get("requiredUnitTier") or 0):
            continue
        if relic_tier < int(affix.get("requiredRelicTier") or 0):
            continue
        if not (stat_id := int(affix.get("statType") or 0)):
            continue
        totals[stat_id] = totals.get(stat_id, 0.0) + float(affix.get("statValue") or 0)

    return _expand({stat_id: _as_displayed(value) for stat_id, value in totals.items()}, unmodded_total)


def _as_displayed(value: float) -> float:
    """Round a stat's summed percentage to the two decimals the datacron card shows.

    In-game readings match the displayed percentage, not the six-decimal stored
    one. Affixes are summed before rounding: two affixes of 2.828575% and
    19.515055% apply as 22.34%, not as 22.35%, the sum of the rounded parts.
    """
    return round(value / 1e6, 2) * 1e6


def _expand(totals: dict[int, float], unmodded_total: dict[str, float]) -> dict[str, float]:
    """Resolve percent-additive stat ids onto the stats they actually modify."""
    expanded: dict[str, float] = {}
    for stat_id, value in totals.items():
        if (targets := STAT_SPLITS.get(stat_id)) is not None:
            for target in targets:
                expanded[target] = expanded.get(target, 0.0) + value
        elif (targets := STAT_PERCENT_OF_BASE.get(stat_id)) is not None:
            for target in targets:
                # Floored to whole units, as the mod path floors its own percentage growth.
                current = expanded.get(target, 0.0)
                grown = current + unmodded_total.get(target, 0.0) * 1e-8 * value
                expanded[target] = math.floor(grown / _UNIT) * _UNIT
        else:
            key = str(stat_id)
            expanded[key] = expanded.get(key, 0.0) + value
    return expanded


def _relic_tier(unit: dict[str, Any]) -> int:
    """Return the unit's encoded relic tier.

    A unit with no relic reports ``relic`` as ``None`` rather than a zeroed
    structure, and sits at the locked base state. Treating it as 0 would fail
    even the baseline relic requirement every affix carries and silently drop
    the datacron's contribution to every relic-less unit.
    """
    relic = unit.get("relic")
    if not isinstance(relic, dict) or relic.get("currentTier") is None:
        return _LOCKED_RELIC_TIER
    return int(relic["currentTier"])
