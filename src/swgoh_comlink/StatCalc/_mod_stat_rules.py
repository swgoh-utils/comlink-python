# coding=utf-8
"""v3.3 Phase 2 — declarative mod-stat dispatch rules.

Replaces the 11-branch if/elif cascade at the bottom of
:meth:`~swgoh_comlink.StatCalc.StatCalc._calculate_mod_stats` with a
data-driven lookup table.

The legacy v3.2 cascade had two flavours of rule:

1. **Dual-stat broadcast** (stat_ids 41, 42, 53, 54).
   ``raw_value`` adds straight into two target stat ids without any
   scaling by base stats.  Compact, no per-call arithmetic — just two
   ``stats[target] += value`` writes.

2. **Floor-and-replace** (stat_ids 48, 49, 55, 56, 57).
   ``raw_value`` scales the *base* stat by ``1e-8 * value``, then the
   result is floor-truncated at 8 digits, and the difference between
   that floored value and the existing mod-stat value is added back.
   Effectively: ``mod_stats[t] = floor(mod_stats[t] + base_stats[t] *
   1e-8 * value, 8)``.

Both shapes plus the trivial "just add to the raw stat id" fallback
(everything not listed) are captured in :data:`MOD_STAT_RULES` below.
The :func:`apply_rule` helper handles the dispatch.

Parity: byte-identical with the v3.2 cascade. Verified by
``tests/unit/test_statcalc_v3_3_parity.py`` per-unit checksum.
"""

from __future__ import annotations

from typing import Final


def _floor(value: float, digits: int = 0) -> float:
    """Truncate *value* to *digits* digits (matches ``StatCalc._floor``).

    Always returns ``float`` — matches the legacy helper's effective
    return type (``int`` post-truncation upcasts to float in the mod
    stats accumulation, so float-typing here avoids spurious mypy
    narrow-then-widen.)
    """
    if digits == 0:
        return float(int(value))
    scale = 10**digits
    return float(int(value / scale) * scale)


# ── Dispatch rules ──────────────────────────────────────────────────────────


class _Rule:
    """Marker base for the two rule flavours below."""

    __slots__ = ()


class Broadcast(_Rule):
    """Add ``raw_value`` straight to each target stat id.

    Used for stat ids 41 (→ 6, 7), 42 (→ 8, 9), 53 (→ 21, 22),
    54 (→ 35, 36).
    """

    __slots__ = ("targets",)

    def __init__(self, *targets: int) -> None:
        self.targets: tuple[int, ...] = targets


class FloorReplace(_Rule):
    """Apply the floor-and-replace scaling pattern to each target.

    For each target ``t`` in ``targets``::

        delta = floor(mod_stats[t] + base_stats[t] * 1e-8 * value, 8)
                - mod_stats[t]
        mod_stats[t] += delta

    Used for stat ids 48 (→ 6, 7), 49 (→ 8, 9), 55 (→ 1), 56 (→ 28),
    57 (→ 5).
    """

    __slots__ = ("targets",)

    def __init__(self, *targets: int) -> None:
        self.targets: tuple[int, ...] = targets


MOD_STAT_RULES: Final[dict[int, _Rule]] = {
    41: Broadcast(6, 7),
    42: Broadcast(8, 9),
    48: FloorReplace(6, 7),
    49: FloorReplace(8, 9),
    53: Broadcast(21, 22),
    54: Broadcast(35, 36),
    55: FloorReplace(1),
    56: FloorReplace(28),
    57: FloorReplace(5),
}


# ── Dispatch helper ─────────────────────────────────────────────────────────


def apply_rule(
    stat_id: int,
    value: float,
    mod_stats: dict[str, float],
    base_stats: dict[str, float],
) -> None:
    """Apply the rule for *stat_id* to *mod_stats* in place.

    Falls back to ``mod_stats[str(stat_id)] += value`` for any
    ``stat_id`` not in :data:`MOD_STAT_RULES` (the legacy cascade's
    ``else`` branch).

    Mutates *mod_stats* in place; returns ``None``. Matches the
    v3.2 cascade byte-for-byte.
    """
    rule = MOD_STAT_RULES.get(stat_id)
    if rule is None:
        # Fallback: trivial accumulate.
        key = str(stat_id)
        mod_stats[key] = mod_stats.get(key, 0.0) + value
        return

    if isinstance(rule, Broadcast):
        for target in rule.targets:
            key = str(target)
            mod_stats[key] = mod_stats.get(key, 0.0) + value
        return

    # FloorReplace
    assert isinstance(rule, FloorReplace)
    for target in rule.targets:
        key = str(target)
        current = mod_stats.get(key, 0.0)
        # base_stats keys are stringified ints (via StatCalc._add_stat).
        # str fallback to int matches the legacy _table_get semantics
        # but in practice base_stats only has str keys.
        base_val = base_stats.get(str(target), 0.0)
        floored = _floor(current + base_val * 1e-8 * value, 8)
        delta = floored - current
        mod_stats[key] = current + delta


__all__ = [
    "MOD_STAT_RULES",
    "Broadcast",
    "FloorReplace",
    "apply_rule",
]
