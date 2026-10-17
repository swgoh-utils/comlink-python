# Typed-client examples (v3 alpha)

These examples use the typed client at `from swgoh_comlink.typed import …`
and require the **v3.0.0a1 alpha** wheel. The PyPI `swgoh_comlink`
package is still v2.x; see the project [README "Alpha (v3) install"
section](../../README.md#alpha-v3-install) for install instructions.

## Why typed?

| Concern | Dict client (`swgoh_comlink`) | Typed client (`swgoh_comlink.typed`) |
|---|---|---|
| Return type | `dict[str, Any]` | `msgspec.Struct` instances |
| Field access | `player["name"]`, `unit["currentLevel"]` | `player.name`, `unit.current_level` |
| IDE autocomplete | none | full (per `_models.py`) |
| Decode speed | json.loads | msgspec.decode (~1.79× faster aggregate per ADR-0005) |
| Memory footprint | dict-per-field | slotted Struct (~0.66× the dict equivalent) |
| Hot-path StatCalc cost | +0 % (passes through) | +10.1 % vs dict — see `docs/v3/recipes/typed-statcalc.md` |
| v2 compatibility | byte-for-byte identical | new import path only; v2 callers unaffected |

**Rule of thumb:** use the typed client when you write to a long-
lived application surface (bot, dashboard, ETL) where IDE help and
typed attribute access pay back. Use the dict client (or
`get_player(..., raw=True)` on the typed client) when you're in a
tight per-tick loop and the +10 % bimorphic overhead compounds.

## Sync examples

| File | What it shows |
|------|---------------|
| [`Sync/get_player.py`](Sync/get_player.py) | Typed `Player` Struct — attribute access; converting back to dict via `msgspec.to_builtins` when needed. Mirrors `examples/Sync/get_player.py`. |
| [`Sync/get_game_data.py`](Sync/get_game_data.py) | Typed `/data` segments via `compat.decode_segment` + the `STOCK_SEGMENT_TYPES` registry. Mirrors `examples/Sync/get_game_data.py`. |
| [`Sync/calc_stats_local.py`](Sync/calc_stats_local.py) | Bimorphic `StatCalc.calc_player_stats(player_struct)` + `get_statcalc_game_data(client, cache=cache)` cold-start cache. Mirrors `examples/Sync/calc_stats_local.py`. |
| [`Sync/healthcheck_and_retry.py`](Sync/healthcheck_and_retry.py) | **v3-only:** `client.healthcheck(timeout=5.0)` startup probe + `profile="bot"` + opt-in `retry=RetryPolicy(...)`. |
| [`Sync/raw_request.py`](Sync/raw_request.py) | **v3-only:** `client.raw_request(method, path, payload=)` escape hatch for endpoints the typed surface doesn't cover. |

## Async examples

| File | What it shows |
|------|---------------|
| [`Async/get_player.py`](Async/get_player.py) | `SwgohComlinkAsync` (typed) basic await pattern + `asyncio.gather` parallelism. Mirrors `examples/Async/get_player.py`. |
| [`Async/streaming_guild_roster.py`](Async/streaming_guild_roster.py) | `asyncio.TaskGroup` fan-out of typed `Player` Structs across a whole guild's membership. Mirrors `examples/Async/streaming_guild_roster.py`. |

## When to look at the dict examples instead

Most v2-era patterns still apply — the dict client is byte-compatible
with v2. If you want to see the dict surface (or you're a v2 user
not ready to migrate), the parallel examples live in
[`examples/Sync/`](../Sync/) and [`examples/Async/`](../Async/).

## Filing issues

Bugs in any of these examples → file an issue with the **`v3`** label.
The bug-report template will collect this via the "Which version
line?" dropdown automatically.
