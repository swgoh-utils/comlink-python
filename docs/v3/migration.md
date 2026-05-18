# v2 → v3 Migration Guide

v3 is a major version with one breaking change (Python floor bumped to
3.11) and a handful of non-breaking additions. **v2 dict semantics are
preserved on the default import path** — `from swgoh_comlink import
SwgohComlink` returns dicts exactly like v2. Opt into the typed
`msgspec.Struct` surface by switching to `from swgoh_comlink.typed
import SwgohComlink`.

If you ever did rely on `raw=True` on the typed surface (a v3-early
intermediate state), it still works — and the dict-default surface
accepts the same kwarg as a no-op so library code remains portable
across both surfaces.

For automated detection of patterns that need updating, run::

    swgoh-migrate path/to/your/code

The migration tool flags v2 patterns as ERROR / WARNING / INFO.
v2→v3 rule ids start with `V3*` (vs `DEP*` for the v1→v2 rules).

## Quick reference

| Concern | v2 | v3 |
|---|---|---|
| Python version | ≥3.10 | **≥3.11** (ADR-0002) |
| `import swgoh_comlink` cold time | ~65 ms | **~7 ms** (lazy via PEP 562) |
| `get_player(...)` from `swgoh_comlink` | `dict` | `dict` (unchanged) |
| `get_player(...)` from `swgoh_comlink.typed` | n/a | `Player` (msgspec.Struct) |
| Same pattern for `get_guild`, `get_game_metadata`, `get_leaderboard` | `dict` | dict OR typed Struct per import path |
| Other endpoints (`get_game_data`, `get_localization`, `get_enums`, …) | `dict` | `dict` (both import paths) |
| Retry on transient errors | none | **on by default** (3 retries) |
| HMAC auth | unchanged | unchanged |
| Connection pool | httpx defaults | `profile="default"` preset |
| HTTP client injection | n/a | `http_client=` kwarg |
| Cache for `/data` + `/localization` | n/a | `GameDataCache` (`[cache]` extra) |
| Pydantic adapter | n/a | `compat.to_pydantic(struct, BaseModel)` (`[pydantic]` extra) |
| Sync/async parity | identical signatures | identical signatures |

## Two import paths: dict-default vs typed

`v3.1-research` ships two parallel client surfaces. Pick by import path;
the underlying transport, retry, and caching are shared.

```python
# Dict-default surface (matches v2 wire shape exactly)
from swgoh_comlink import SwgohComlink, SwgohComlinkAsync

with SwgohComlink(url="...") as client:
    player = client.get_player(allycode=123456789)
    name = player["name"]              # dict indexing — v2 style
    guild_id = player["guildId"]
    roster = player["rosterUnit"]
```

```python
# Typed surface (msgspec.Struct attribute access)
from swgoh_comlink.typed import SwgohComlink, SwgohComlinkAsync

with SwgohComlink(url="...") as client:
    player = client.get_player(allycode=123456789)
    name = player.name                 # attribute access — typed
    guild_id = player.guild_id         # snake_case Python; camelCase on the wire
    roster = player.roster_unit
    first_def = player.roster_unit[0].definition_id
```

The typed surface uses `msgspec`'s `rename="camel"` so wire camelCase
maps to PEP-8 snake_case fields automatically.

## Why two surfaces

ADR-0005 records the rationale. Short version:

- v2 wire compat preserved on the default import — no behavior change
  for existing v2 callers.
- Typed access opt-in via a one-line import change.
- Both surfaces share transport, retry, decoding, caching code; only
  the response shape differs.
- All four client classes (sync/async × dict/typed) are code-generated
  from a single manifest (`src/swgoh_comlink/_codegen/endpoints.py`)
  via Jinja + ruff. See `docs/v3/codegen.md`.

## Soft migration: `raw=True`

If you can't (or don't want to) migrate dict-indexing code yet, every
typed endpoint accepts `raw=True` to return the v2 dict shape unchanged:

```python
# v3 with raw=True — v2 semantics preserved
player = client.get_player(allycode=123456789, raw=True)
name = player["name"]  # works exactly like v2
```

Same for `get_guild`, `get_game_metadata`, `get_leaderboard`. The dict
shape is byte-identical with v2 (we test this via the Phase 1 golden
suite).

## Soft migration: `compat.to_dict()`

For one-shot conversions where you have a Struct but need a dict:

```python
from swgoh_comlink import compat

p = client.get_player(allycode=123456789)
as_dict = compat.to_dict(p)  # warns DeprecationWarning
name = as_dict["name"]
```

`compat.to_dict()` is marked for removal in **v3.2**. Prefer attribute
access or `raw=True`.

## New client kwargs

```python
# v2
client = SwgohComlink(url="http://localhost:3000")

# v3 — new optional kwargs
client = SwgohComlink(
    url="http://localhost:3000",
    http_client=my_httpx_client,   # inject your own; SDK won't close it
    profile="bot",                  # connection pool preset
    max_retries=3,                  # set to 0 to disable retries entirely
)
```

* `http_client=` lets you inject your own `httpx.Client`/`httpx.AsyncClient`.
  When supplied, the SDK does NOT auto-close it.
* `profile="default" | "bot" | "bulk"` selects a connection-pool preset
  (keepalive 30s / 120s / 60s; pool sizes tuned for each use case).
* `max_retries=3` is the new default. Set to `0` for v2-equivalent
  no-retry behavior.

## Retry semantics

v3 retries on transient errors by default (429, 5xx, connection drops).
`Retry-After` headers are honored verbatim; non-retryable status (4xx
other than 408/425/429) passes through after one attempt.

```python
# v2 — no retry
try:
    player = client.get_player(allycode=...)
except SwgohComlinkException:
    # connection error or 5xx → one attempt, then raise
    ...

# v3 — retried 3 times by default
try:
    player = client.get_player(allycode=...)
except SwgohComlinkException:
    # connection error or 5xx → 4 attempts (1 + 3 retries), then raise
    ...

# v3 with v2-equivalent semantics:
client = SwgohComlink(url=..., max_retries=0)
```

## `with_options(...)` for one-off tweaks

```python
# v3 — shallow clone with overrides; underlying httpx client is SHARED
no_retry = client.with_options(max_retries=0)
no_retry.get_player(allycode=...)  # one attempt, then raise
```

## Internal `_get_game_version` / `get_latest_game_data_version`

These helpers now use attribute access internally — if you ever shadowed
them in your own code, switch to the same pattern:

```python
# v2
md = client.get_game_metadata()
version = md["latestGamedataVersion"]

# v3
md = client.get_game_metadata()
version = md.latest_gamedata_version
```

## New: ergonomics methods

```python
# v3: bot startup probe
if not client.healthcheck(timeout=5.0):
    raise SystemExit("comlink unreachable")

# v3: escape hatch for endpoints the SDK doesn't model
response = client.raw_request("POST", "/custom/path", payload={...})

# v3: stream large /data without materializing in memory
with client.stream_game_data(version="...") as r:
    r.raise_for_status()
    for chunk in r.iter_bytes():
        process(chunk)
```

## New: GameDataCache for repeated `/data` / `/localization`

```python
# v3 with [cache] extra
from swgoh_comlink import SwgohComlink
from swgoh_comlink._cache import GameDataCache

client = SwgohComlink(url="...")
cache = GameDataCache()  # XDG-compliant default cache dir

# First call: full fetch + decode + msgpack encode + disk write (~3.5s for /data)
data = cache.get_game_data(client)

# Subsequent calls on the same cache instance: in-memory dict hit (~0.0003ms)
data = cache.get_game_data(client)
```

The cache is version-aware. When comlink's game version bumps, the
metadata probe (memoized in a 30s TTLCache) notices, fetches fresh data,
and tags it with the new version. Call `cache.evict_old_versions(...)`
to clean up stale entries.

## New: Pydantic adapter

```python
# v3 with [pydantic] extra
from pydantic import BaseModel, Field
from swgoh_comlink import compat

class MyPlayer(BaseModel):
    name: str
    ally_code: str = Field(alias="allyCode")
    level: int
    model_config = {"populate_by_name": True}

player = client.get_player(allycode=...)
my_player = compat.to_pydantic(player, MyPlayer)  # full pydantic validation
```

The bridge goes Struct → dict (via `msgspec.to_builtins`) → BaseModel
(via `model_validate`). User-defined `BaseModel` keeps the type surface
on YOUR side — the SDK doesn't ship parallel pydantic types per
endpoint.

## Helper functions (`helpers/`)

`get_guild_members`, `async_get_guild_members`, and the GAC helpers
(`get_gac_brackets`, `async_get_gac_brackets`, `get_current_gac_event`)
still exist with their v2 signatures. They internally pass `raw=True`
to the typed endpoints so their dict-shape contract is preserved.

If you call them directly, no migration needed. If you call them and
then index into the result (`get_guild_members(...)[0]["playerId"]`),
that still works.

## Imports

```python
# v2
from swgoh_comlink import SwgohComlink, SwgohComlinkAsync, StatCalc, GameDataBuilder

# v3 — same imports work, but they're now LAZY (PEP 562 __getattr__)
# First access triggers the import + caches; subsequent accesses are O(1).
from swgoh_comlink import SwgohComlink, SwgohComlinkAsync, StatCalc, GameDataBuilder
```

`import swgoh_comlink` no longer pulls in httpx, msgspec, or the
StatCalc subpackage. They load on first use of the public name they
gate.

## What was removed / deprecated

| Removed | Replacement |
|---|---|
| Python 3.10 support | Bump to 3.11+ |
| Implicit retry-off behavior | Pass `max_retries=0` explicitly |
| (none) | (no public API was actually removed in v3.0) |

| Deprecated | Removed in |
|---|---|
| `swgoh_comlink.compat.to_dict()` | v3.2 |

## Not in v3.0 (deferred to v3.1)

- `[ratelimit]` extra with `aiometer` / `aiolimiter` integration
  (ADR-0004). For now, use vanilla `asyncio.Semaphore` — see
  `docs/v3/recipes/operator-side-concurrency.md`.
- `[circuitbreaker]` extra with `purgatory` integration (ADR-0004).
- Async-aware StatCalc (`calc_roster_stats_async` with threshold-based
  ProcessPoolExecutor).
- Deeper `Mod.primary_stat` / `equipment` typing (Phase 3.5 hit the
  level of typing that produces real wins; deeper still moves the
  needle slowly).
- `StatCalc/` → `statcalc/` directory rename (PEP 8 cleanup; deferred
  for the import-site churn).

## Want the v2 behavior in v3?

The fastest path:

```python
client = SwgohComlink(url="...", max_retries=0)
player = client.get_player(allycode=..., raw=True)
# `player` is dict; index it like v2.
```

You lose typed Structs (the headline v3 win) and the retry safety net,
but you don't have to change a single line of dict-indexing code.

## Need help?

`swgoh-migrate path/to/your/code` flags every v2 pattern with a
human-readable suggestion. Run it pre-flight before you cut over.
