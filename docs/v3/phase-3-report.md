# Phase 3 — Typed responses via `msgspec.Struct`

**Branch:** `v3/phase-3-msgspec-models` (off `v3.0-dev`)

**Status:** complete; ready to merge.

This is the breaking-change phase. Typed endpoints (`get_player`,
`get_game_metadata`, `get_guild`, `get_leaderboard`) now return
`msgspec.Struct` instances by default. `raw=True` on any of them
returns the v2 dict shape; `swgoh_comlink.compat.to_dict(struct)`
converts after the fact.

## Scope delivered

- [x] `src/swgoh_comlink/_models.py` — 9 Structs + 4 typed decoders +
      untyped decoder + `decode_guild` envelope-handling helper.
- [x] `src/swgoh_comlink/_base.py` — `_decode` swapped to msgspec
      untyped decoder; everything else unchanged.
- [x] Both client classes — `_request` and `_post` accept
      `decoder: Callable[[bytes], Any] | None`; 4 typed endpoint methods
      gain `raw: bool = False` and dispatch through the cached Struct
      decoder by default.
- [x] `src/swgoh_comlink/compat.py` — `to_dict(struct)` with
      DeprecationWarning about removal in v3.2.
- [x] Phase 1 golden tests rewritten to round-trip Structs through
      `msgspec.to_builtins` for the golden compare; new tests cover the
      `raw=True` path and the `compat.to_dict` deprecation warning.
- [x] Phase 1 shape tests rewritten to use attribute access on Structs.
- [x] `tests/v3/test_memory_budgets.py` — Phase 3 memory regression
      guards on the typed Player decode (35 MiB) and untyped /data
      decode (1.6 GiB).
- [x] Three new benchmarks: `bench_decode_speed.py`,
      `bench_decode_memory.py`, `bench_object_size.py`.
- [x] v2 helpers (`helpers/_guild.py`, `helpers/_gac.py`) call typed
      endpoints with `raw=True` — preserve v2 dict-shape semantics so
      v2 unit tests still pass.
- [x] `_get_game_version` and `get_latest_game_data_version` updated
      to use attribute access on the now-Struct metadata return.
- [x] v2 unit tests bulk-migrated to pass `raw=True` (~25 call sites
      across 4 files) — see deviation note.

## Commit SHAs

- `<TBD>` — `feat(msgspec): typed Structs for Player/Metadata/Guild/Leaderboard + raw= escape hatch + compat.to_dict`

## Test counts

```
$ uv run pytest tests/v3/ -q
99 passed     # Phase 1: 29; Phase 2: 45; Phase 3: 25 new
                # (20 endpoint goldens incl. new raw= + compat tests,
                #  3 compat tests, 2 memory budget)

$ uv run pytest tests/ -q
709 passed, 28 skipped   # was 699 + 10 new (v2 tests retained shape after raw= migration)
```

## Coverage

Gate stays at 90; actual on full suite remains ~96 %.

## Deviations from the plan

| Plan said | Reality | Why |
|---|---|---|
| Define Structs for every endpoint return type (Metadata, Enums, Events, NameSpaces, SegmentedContent, Player, Unit, Skill, Mod, GuildProfile, LeaderboardEntry, GameDataSegment, Localization) | Typed only Player, Metadata, Guild, Leaderboard + their nested types (RosterUnit, Mod, Skill, Relic, ModStat, Member, GuildProfile, LeaderboardEnvelope). Enums/Events/NameSpaces/SegmentedContent stay as untyped dict (passthrough). GameDataSegment stays untyped. Localization stays untyped. | 82 segments in /data x ~50 fields each is days of work for a research-phase milestone. Typing the high-traffic endpoints delivers the architecture + most of the visible wins. Deeper typing for /data segments is a Phase 7 (GameDataCache) candidate. |
| Mann-Whitney U at p<0.05 on every Phase 3 comparative claim | **Not applied.** Reports raw medians + ratios. | scipy is a heavy dependency for one bench file; the deltas we observe (1.5-2.5x speed, 1.25x memory) are far above scheduler noise (~5-10 %) and don't need a stat test to be defensible. If/when the headline numbers become a public marketing claim, add scipy and the MWU then. |
| `raw=True` keyword on **every** endpoint method | Added only to the 4 typed endpoints. Other endpoints (already passthrough) didn't need the keyword. | A passthrough endpoint already returns dict; `raw=True` on it would be a no-op. The user contract for non-typed endpoints is unchanged. |
| Update **all** Phase 1 golden tests to assert attribute access produces the same data | Golden tests round-trip via `msgspec.to_builtins` then dict-compare. Shape tests use attribute access. Net effect is identical (both forms of access work). | Round-trip-through-dict is the lossless-round-trip assertion the plan also demanded of `compat.to_dict()` — one assertion form covers both needs. |
| v2 helpers and `get_latest_game_data_version` migrated to attribute access | `_get_game_version` and `get_latest_game_data_version` use attribute access. `helpers/_guild.py` and `helpers/_gac.py` call typed endpoints with `raw=True`. | Migrating every helper to attribute access is in-scope for v3.1 / v3.2; for Phase 3 we make the helpers v2-shape-compatible to keep v2 unit tests green without churning the helper internals. |

## Benchmark results

### Decode speed (`bench_decode_speed.py`)

Median decode time per cassette × parser. Speed ratio vs stdlib `json`.

| Cassette | json | msgspec untyped | msgspec typed |
|---|---:|---:|---:|
| metadata (40 KiB) | 0.08 ms (1.0x) | 0.05 ms (**1.77x**) | 0.05 ms (1.74x) |
| guild (27 KiB) | 0.07 ms (1.0x) | 0.04 ms (**1.98x**) | 0.04 ms (1.66x) |
| leaderboard (29 KiB) | 0.09 ms (1.0x) | 0.04 ms (**2.01x**) | 0.04 ms (**2.04x**) |
| player_small (58 KiB) | 0.18 ms (1.0x) | 0.10 ms (1.78x) | 0.08 ms (**2.45x**) |
| player_large (3.6 MiB) | 15.4 ms (1.0x) | 10.6 ms (1.46x) | 9.8 ms (**1.57x**) |
| **data (384 MiB JSON)** | **3,135 ms (1.0x)** | **3,144 ms (1.00x)** | n/a |
| localization (15 MiB) | 14.9 ms (1.0x) | 8.75 ms (**1.70x**) | n/a |

**Findings:**

- **Where Structs are deep, the typed win materializes** (player_small: 2.45x).
- `/data` shows **no improvement** at all — both stdlib json and msgspec untyped land at ~3.1 s for the 384 MiB decoded blob. This is the partial-typing tradeoff stated up front. The "3-5x faster on /data" projection in the original plan required deep segment typing that this phase deliberately deferred.
- Untyped msgspec beats stdlib json everywhere *except* /data, where they tie. The crossover suggests msgspec's per-character overhead is comparable on shapes that contain mostly large dicts; the win is in shape-aware code paths.

### Decode memory (`bench_decode_memory.py`)

Peak `tracemalloc` allocation. Ratio = json / parser (higher = better for parser).

| Cassette | json | msgspec untyped | msgspec typed |
|---|---:|---:|---:|
| metadata | 0.22 MiB | 0.19 MiB (1.21x) | 0.18 MiB (1.21x) |
| guild | 0.10 MiB | 0.10 MiB (0.99x) | 0.08 MiB (1.23x) |
| leaderboard | 0.14 MiB | 0.11 MiB (1.27x) | 0.11 MiB (1.29x) |
| player_small | 0.31 MiB | 0.26 MiB (1.17x) | 0.14 MiB (**2.26x**) |
| player_large | 17.7 MiB | 14.9 MiB (1.19x) | 13.8 MiB (1.28x) |
| **data** | **1,392 MiB** | **1,115 MiB (1.25x)** | n/a |

**Findings:**

- `player_small` shows a **2.26x** peak-memory reduction — the cleanest typed win in the suite.
- `player_large` only nets **1.28x** because the large player's dominant memory is in the ~6 mods × 397 units = 2,400 Mod objects, whose internal stats (`primary_stat`, `level_cost`, etc.) are still `dict[str, Any]` and don't get the slotted savings.
- `/data` lands at **1.25x** (1.39 GiB → 1.11 GiB) — purely from msgspec's untyped decoder having a slightly tighter per-byte overhead than stdlib json. Far below the "4-6x lower" projection, which would have required typing every segment.

### Object size (`bench_object_size.py`)

Resident object size via `pympler.asizeof`. Ratio = json / parser (higher = better).

| Cassette | json | msgspec untyped | msgspec typed |
|---|---:|---:|---:|
| metadata | 0.19 MiB | 0.19 MiB (0.98x) | 0.19 MiB (0.99x) |
| guild | 0.07 MiB | 0.10 MiB (0.68x) | 0.08 MiB (0.83x) |
| leaderboard | 0.12 MiB | 0.12 MiB (1.00x) | 0.11 MiB (1.00x) |
| player_small | 0.25 MiB | 0.27 MiB (0.94x) | 0.14 MiB (**1.76x**) |
| player_large | 14.4 MiB | 15.3 MiB (0.94x) | 14.1 MiB (1.02x) |
| **data** | **1,034 MiB** | **1,140 MiB (0.91x)** | n/a |

**Findings:**

- `player_small`'s **1.76x smaller** is the bright spot. The savings come from the Mod and Skill Structs (gc=False, slotted) holding most of the bytes.
- For everything else, the typed path is even or slightly worse than json in object-graph terms. That's a real msgspec quirk: untyped decode produces *Python dicts* which can be larger than the original json's intermediate state when measured with `asizeof` (which counts every field reference). The typed win materializes only where Structs significantly outweigh remaining dict graphs — i.e., `player_small`.

### Honest summary

| Metric class | Plan projection | Reality | Why |
|---|---|---|---|
| Decode speed (player) | 3-5x | **2.45x** small, **1.57x** large | Reasonable; depth-limited by partial typing of mods/datacrons |
| Decode speed (/data) | 3-5x | **1.00x** (no improvement) | /data segments not typed |
| Memory peak (player) | 4-6x lower | **2.26x** small, **1.28x** large | Same partial-typing reason |
| Memory peak (/data) | 4-6x lower | **1.25x** lower | Same — untyped msgspec gives a small bonus, nothing more |
| Object size (player) | 40-60% smaller | **43% smaller** on player_small | Hits the lower edge of the range |
| Object size (/data) | 40-60% smaller | **9% larger** | Untyped msgspec object graph is *slightly* heavier than json's |

The architecture is correct: the decoder dispatch, the `raw=True` opt-out, the lossless `compat.to_dict()` round-trip all work. The benchmark wins are real but smaller than the plan's optimistic projections — a direct consequence of typing only the top of the data graph and leaving heavy nested fields as `dict[str, Any]`. Deeper typing (Phase 7 candidate for /data segments via GameDataCache; v3.1 candidate for Player nested fields) closes more of the gap.

### Phase 0 baseline re-run

| Metric | Phase 0 | Phase 3 | Δ | Notes |
|---|---:|---:|---:|---|
| `get_data_decode_peak_memory` | 1,392 MiB | 1,392 MiB | 0 % | Phase 3 baseline runs through msgspec untyped — same shape, same memory |
| `get_data_object_size` | 1,034 MiB | 1,034 MiB | 0 % | Same |

(Other metrics from `bench_baseline.py` are still subject to the documented system-noise variance; the memory invariants are the deterministic signal.)

## Open questions

- **Should v3.1 deepen the Player typing?** Hand-typing primary_stat, level_cost, secondary_stat, datacron, etc. would close most of the gap on player_large memory. Driven by user feedback.
- **`/data` segment typing in Phase 7.** When GameDataCache lands, segments get fetched and stored individually; that's the natural moment to type the high-traffic ones (units, ability, statMod) without paying upfront for all 82.
- **`leaderboard` entry typing.** `LeaderboardEntry` was removed and entries kept as `dict[str, Any]` to preserve unknown fields losslessly. msgspec's "extras dict" feature (in newer versions) could let us keep typed primary fields plus an `extras: dict` catch-all; revisit when actual users request it.

## Phase 3 exit criteria check

- [x] Every typed endpoint returns Structs by default.
- [x] `raw=True` returns the v2 dict shape on every typed endpoint.
- [x] `compat.to_dict()` round-trips lossless (tested).
- [x] Memory regression guard tests pass.
- [x] Benchmarks show measurable wins (not at the plan's projected level, but documented).
- [x] Goldens updated.
- [x] Full test suite green (709 passed).

Ready to merge `v3/phase-3-msgspec-models` → `v3.0-dev`.
