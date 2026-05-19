# coding=utf-8
"""
get_player.py — typed-client variant

Sibling of ``examples/Sync/get_player.py``. Uses the typed client
(``swgoh_comlink.typed``) so endpoint methods return ``msgspec.Struct``
instances with typed attributes instead of ``dict`` values.

Requires the v3 alpha — install via the v3.0.0a1 GitHub Release. The
v2 PyPI package's ``swgoh_comlink`` import does NOT expose the
``typed`` submodule.
"""

# The typed client lives at a separate import path. The dict-default
# `from swgoh_comlink import SwgohComlink` continues to work for v2
# callers; this `.typed` import opts you into msgspec.Struct returns.
from swgoh_comlink.typed import SwgohComlink

# Construct the client. Same kwargs as the dict client — `url`,
# `profile`, `max_retries`, etc.
comlink = SwgohComlink()

# get_player() returns a typed `Player` Struct, not a dict.
player = comlink.get_player(allycode=314927874)

# Attribute access — no `["key"]` subscripts, IDE autocomplete works.
print(f"Name:           {player.name}")
print(f"Level:          {player.level}")
print(f"Ally code:      {player.ally_code}")
print(f"Guild ID:       {player.guild_id}")
print(f"Guild name:     {player.guild_name}")
print(f"Roster units:   {len(player.roster_unit)}")

# Nested Structs work the same way. Each `RosterUnit` is a typed
# Struct exposing `definition_id`, `current_level`, `current_rarity`,
# `equipped_stat_mod`, etc.
first_unit = player.roster_unit[0]
print("\nFirst unit:")
print(f"  definition_id:  {first_unit.definition_id}")
print(f"  current_level:  {first_unit.current_level}")
print(f"  current_rarity: {first_unit.current_rarity}")
mods = first_unit.equipped_stat_mod or []
print(f"  mods:           {len(mods)}")

# Need a v2-style dict for downstream code that expects one?
# Convert any Struct via msgspec.to_builtins(). For StatCalc input
# this is unnecessary — calc_player_stats accepts the Struct
# directly (see examples/typed/Sync/calc_stats_local.py).
import msgspec  # noqa: E402

player_as_dict = msgspec.to_builtins(player)
print(f"\nplayer_as_dict['name'] == player.name: {player_as_dict['name'] == player.name}")
