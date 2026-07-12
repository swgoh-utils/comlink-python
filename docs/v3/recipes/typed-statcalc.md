# Using StatCalc with the typed client

`StatCalc` ships in v3.2 with two new conveniences:

1. **Bimorphic input** — `calc_player_stats` and `calc_roster_stats`
   accept either Comlink-format dicts (the legacy surface) OR
   `msgspec.Struct` objects from the typed client.
2. **Cached normalized game data** — `get_statcalc_game_data` persists
   the normalized form across process restarts, cutting cold-start
   `StatCalc` setup from ~26 ms to ~4 ms.

Both shipped as the two "winners" from the v3.2 StatCalc research
(see [ADR-0006](../../adr/0006-statcalc-internals-overhaul.md) for the
six candidates that didn't ship and why).

## TL;DR — typed-client startup, hot loop, both

```python
from swgoh_comlink.typed import SwgohComlink
from swgoh_comlink._cache import GameDataCache
from swgoh_comlink.StatCalc import StatCalc, get_statcalc_game_data

client = SwgohComlink(url="http://comlink.local:3200")
cache = GameDataCache()                              # XDG-default dir
gd = get_statcalc_game_data(client, cache=cache)     # ~4 ms warm
sc = StatCalc(game_data=gd)

# Hot path option 1: typed Struct — convenient, +22 % per-roster cost
player = client.get_player(allycode=123456789)        # Player Struct
stats = sc.calc_player_stats(player)                  # bimorphic; returns dict

# Hot path option 2: raw dict — zero overhead, dict-typed at the seam
player_raw = client.get_player(allycode=123456789, raw=True)
stats = sc.calc_player_stats(player_raw)
```

## When to use which input shape

| Caller style | Recommendation | Why |
|---|---|---|
| Typed Struct, calling **infrequently or for a few players per tick** | Hand `StatCalc` the Struct. | v3.3 dropped the bimorphic overhead from +22.9 % to +10.1 %; for an occasional caller this is well within tolerance. |
| Typed Struct, calling **per-unit in a tight loop with thousands of units/sec** | `client.get_player(..., raw=True)`. | +10 % still compounds at scale. The dict surface remains the zero-overhead path. |
| v2-style dict caller (existing code) | Keep doing what you're doing. | The bimorphic dispatcher's `isinstance(players, msgspec.Struct)` check is one branch on the dict path — zero cost. |

The v3.3 typed-fastpath in
`src/swgoh_comlink/StatCalc/_typed_fastpath.py`
reads `msgspec.Struct.__slots__` directly instead of walking the
whole Player via `msgspec.to_builtins`. Only the fields StatCalc
actually reads (`definition_id`, `current_level`, `current_rarity`,
`current_tier`, `equipment`, `equipped_stat_mod`, `relic`,
`skill[].id`, `skill[].tier`, and the per-Mod `definition_id` /
`primary_stat.stat` / `secondary_stat[].stat` / `tier` / `level`)
are touched — saving the per-Mod walk of fields StatCalc never
reads (`bonus_quantity`, `converted_item`, `sell_value`, `xp`, …).
See [ADR-0007](../../adr/0007-statcalc-rewrite-evaluation.md) for
the full measurement and the deferred native-acceleration variants.

## What "bimorphic" buys you

```python
# Pre-v3.2 — typed caller had to convert themselves
import msgspec
player_struct = client.get_player(allycode=...)        # Player Struct
player_dict = msgspec.to_builtins(player_struct)       # +~5 ms
stats = sc.calc_player_stats(player_dict)              # +~22 ms

# v3.2 — same total cost, one fewer line, no caller-side imports
player_struct = client.get_player(allycode=...)
stats = sc.calc_player_stats(player_struct)            # bimorphic
```

You can also hand `StatCalc` a list of typed `Player` Structs:

```python
players = [client.get_player(allycode=a) for a in tracked_allies]
all_stats = sc.calc_player_stats(players)              # list of Structs OK
```

Or a list of `RosterUnit` Structs directly to
`calc_roster_stats`:

```python
player = client.get_player(allycode=...)
roster_stats = sc.calc_roster_stats(list(player.roster_unit))
```

## What `get_statcalc_game_data` buys you

`GameDataBuilder._build_game_data(raw)` does the same ~25 ms of work
on every process startup, transforming raw `/data` into the 6
normalized tables StatCalc needs. `get_statcalc_game_data` plumbs that
into the Phase 7 `GameDataCache` (msgpack on disk + in-process memo),
keyed by the upstream game version. After the first call, every
process startup just msgpack-decodes the cached normalized form
(~4 ms).

```python
from swgoh_comlink import SwgohComlink
from swgoh_comlink._cache import GameDataCache
from swgoh_comlink.StatCalc import StatCalc, get_statcalc_game_data

client = SwgohComlink(url="http://comlink.local:3200")
cache = GameDataCache()

# First process startup after a game-version bump:
#   - fetches raw /data (cached by GameDataCache from then on)
#   - runs GameDataBuilder._build_game_data    ~25 ms
#   - persists the normalized form (~120 KB on disk)
# Every subsequent process startup:
#   - msgpack-decodes the normalized form     ~4 ms

gd = get_statcalc_game_data(client, cache=cache)
sc = StatCalc(game_data=gd)
```

This is a **cold-start** win. The hot path (`calc_player_stats`
per-unit work) is unaffected. The optimization is most valuable for:

- Cron jobs / scheduled tasks spawning a fresh interpreter per run.
- AWS Lambda / Cloud Run scaling new instances on traffic.
- CLI tools where startup latency is user-visible.

Long-running bots that init `StatCalc` once and reuse it for hours
won't see a meaningful difference here — for those, focus on the
hot-path / bimorphic choice above.

## What we evaluated and didn't ship

Six other candidates were considered, prototyped or mechanism-checked,
and **rejected on measured evidence**:

- Partial-conversion adapter and accessor-subclass alternatives for
  bimorphic input — within ±1 % of the shipped boundary check.
- `ProcessPoolExecutor` fan-out for `calc_roster_stats` — IPC
  break-even exceeds per-unit work; regresses on `player_large`.
- Typed-Struct game_data tables — micro-bench established ~1.3 %
  hot-path ceiling vs the 10 % bar.
- Direct consumption of v3.1 typed `/data` segments — higher refactor
  cost than the Struct-tables variant, with the plan's own estimated
  payoff range including regression.
- Hot-table index restructuring — 5.7 % vs 10 % bar; aggressive
  variant breaks parity on mod-set bonuses.

Full audit, measurements, and decision rationale in
[ADR-0006](../../adr/0006-statcalc-internals-overhaul.md).

## See also

- [`docs/v3/recipes/long-running-bot.md`](long-running-bot.md) —
  pairs `GameDataCache` with retries and a startup `healthcheck`.
- [`docs/v3/migration.md`](../migration.md) — v2 → v3 upgrade path.
- [`docs/v3/codegen.md`](../codegen.md) — the typed/dict client split.
