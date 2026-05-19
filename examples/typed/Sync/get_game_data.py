# coding=utf-8
"""
get_game_data.py — typed-client + typed segments variant

Sibling of ``examples/Sync/get_game_data.py``. Uses the typed client
together with ``swgoh_comlink.compat.decode_segment`` so individual
``/data`` segments come back as ``msgspec.Struct`` instances instead
of raw dicts.

The 14 segments registered in ``STOCK_SEGMENT_TYPES`` (Units,
SkillDefinition, Equipment, StatMod, StatModSet, Ability, Material,
Recipe, Effect, Campaign, plus the datacron segments) all decode
~1.79× faster at ~0.66× memory vs json.loads + dict access.
"""

from swgoh_comlink.compat import STOCK_SEGMENT_TYPES, decode_segment
from swgoh_comlink.helpers import Constants
from swgoh_comlink.typed import SwgohComlink

cl = SwgohComlink()

# ── 1. Raw segment (legacy dict path; same as v2) ──────────────────────────
#
# The typed client's get_game_data() still returns the full /data
# payload as a dict — typing happens via decode_segment() on the
# individual segments below. (Different from the per-endpoint typed
# returns like get_player(): /data is too large + heterogeneous to
# decode in a single typed Struct.)
raw_units_segment = cl.get_game_data(items="UnitDefinitions")
print(f"Raw segment keys (top-level): {list(raw_units_segment.keys())[:5]}...")

# ── 2. Typed decode of the Units segment ────────────────────────────────────
typed_units = decode_segment(raw_units_segment, "units")
print(f"\nTyped Units segment: {len(typed_units)} unit defs")
sample = typed_units[0]
print(f"  Sample unit: {sample.base_id} (name_key={sample.name_key})")
print(f"  combat_type: {sample.combat_type}")

# ── 3. List the segments the registry knows how to type ─────────────────────
print("\nRegistered segments (decode_segment supports these):")
for name in sorted(STOCK_SEGMENT_TYPES):
    print(f"  - {name}")

# ── 4. Combine multiple segments in one call (segment numbers) ──────────────
# Same as the dict example: the Constants helper exposes the wire
# segment IDs that getGameData accepts.
seg_1_and_2 = cl.get_game_data(items=Constants.Segment1 + Constants.Segment2)
print(f"\nSegments 1+2 top-level keys: {list(seg_1_and_2.keys())}")

# ── 5. Typed decode of a different segment ──────────────────────────────────
# Each registered segment exposes typed attributes specific to that
# data type. Equipment Structs have `id`, `nameKey`, `stat_mod_slot`,
# `slot`, etc.
raw_equipment = cl.get_game_data(items="Equipment")
typed_equipment = decode_segment(raw_equipment, "equipment")
print(f"\nTyped Equipment segment: {len(typed_equipment)} entries")
print(f"  Sample equipment: {typed_equipment[0]}")
