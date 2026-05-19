# coding=utf-8
"""
calc_stats_local.py — typed-client + bimorphic StatCalc variant

Sibling of ``examples/Sync/calc_stats_local.py``. Demonstrates the
two v3 StatCalc winners (ADR-0006):

  1. ``get_statcalc_game_data(client, cache=cache)`` — cached
     normalized game_data. Cold-start: 25.7 ms → 3.6 ms (+85.9 %).
     The second + every subsequent process startup reads the cached
     normalized form from disk; no rebuild required.

  2. ``StatCalc.calc_player_stats(player_struct)`` — bimorphic input.
     Accepts a typed ``Player`` Struct directly; no
     ``msgspec.to_builtins(player)`` boilerplate required. Conversion
     happens at the boundary via the v3.3 typed-fastpath
     (ADR-0007 Phase 4b).

Requires the v3 alpha + the `[cache]` optional extra
(``pip install ... swgoh_comlink-3.0.0a1...[cache]``).
"""

from swgoh_comlink import StatCalc, get_statcalc_game_data
from swgoh_comlink._cache import GameDataCache
from swgoh_comlink.typed import SwgohComlink

# ── Setup ───────────────────────────────────────────────────────────────────

# The typed client returns Player / RosterUnit / Mod Structs from its
# endpoint methods. StatCalc's internal calc machinery is dict-based,
# but its public API (`calc_player_stats`) now accepts either.
client = SwgohComlink()

# GameDataCache stores both the raw /data payload AND the StatCalc-
# normalized form. Version-keyed by the comlink's reported game data
# version — when the game updates, the cache invalidates automatically.
cache = GameDataCache()  # default ~/.cache/swgoh-comlink/

# ── 1. Cached game-data init (Phase v3.2 Candidate E) ──────────────────────
#
# First call (per process, per game-data version):
#   - hits /data (cached by GameDataCache anyway, so subsequent process
#     starts skip the network)
#   - runs GameDataBuilder._build_game_data on the raw payload (~25 ms)
#   - persists the normalized form to disk
#
# Second + later process starts:
#   - msgpack-decodes the cached normalized form (~3 ms)
#   - skips the GameDataBuilder rebuild entirely
gd = get_statcalc_game_data(client, cache=cache)
sc = StatCalc(game_data=gd)
print(f"StatCalc initialised with {len(gd['unitData'])} unit defs")

# ── 2. Bimorphic StatCalc on a typed Player Struct (Phase v3.3 Phase 4b) ───
#
# Fetch a player as a typed Struct. Hand it directly to
# calc_player_stats — no msgspec.to_builtins call needed at the
# caller, the boundary adapter handles it.
player = client.get_player(allycode=314927874)
print(f"\nCalculating stats for {player.name} ({len(player.roster_unit)} units)...")

# calc_player_stats() mutates + returns its input. For a Struct input
# the return type is dict (the conversion happens at the boundary;
# downstream stats-bearing fields are stored in the returned dict).
result = sc.calc_player_stats(player)

# Pick out one unit and show its computed stats.
first_unit = result["rosterUnit"][0]
print(f"\nFirst unit: {first_unit.get('definitionId')}")
print(f"  GP:    {first_unit.get('gp')}")
stats = first_unit.get("stats") or {}
final = stats.get("final") or {}
print(f"  Stats: {len(final)} fields")
for stat_name in ("Strength", "Health", "Speed", "Protection"):
    val = final.get(stat_name)
    if val is not None:
        print(f"    {stat_name:12s}: {val}")

# ── 3. Hot-loop opt-out (use raw=True for the per-tick path) ───────────────
#
# Bimorphic Struct overhead is ~+10 % vs dict input (down from v3.2's
# +22.9 % via the typed-fastpath, but still nonzero). For per-tick
# loops where the conversion compounds, the dict surface remains the
# zero-overhead path:
player_raw = client.get_player(allycode=314927874, raw=True)
result_raw = sc.calc_player_stats(player_raw)
print(f"\nDict-input path: {result_raw['rosterUnit'][0].get('definitionId')} — same result, 0 % overhead")
