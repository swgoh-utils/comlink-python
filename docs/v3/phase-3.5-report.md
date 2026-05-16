# Phase 3.5 — Deepen Player Struct nesting

**Branch:** `v3/phase-3.5-deepen-player-typing` (off `v3.0-dev`)

**Status:** complete; ready to merge.

This phase closes the partial-typing gap Phase 3 documented. Heavy
nested fields under Player — Mod sub-stats, costs, datacrons,
pvp_profile, season_status, profile_stat, player_rating, portraits —
were previously `dict[str, Any]` for surface-area reasons. Phase 3.5
types them with the same `gc=False` leaf pattern Phase 3 used, picking
up the memory + speed wins that depth requires.

## Scope delivered

- [x] **Mod sub-types** (~2,400 instances per large player):
      `StatValue`, `PrimaryStat`, `SecondaryStat`, `CurrencyCost` (shared
      by level_cost / remove_cost / sell_value). `Mod` now references
      them in place of `dict[str, Any]`.
- [x] **Player-level sub-types:**
      - `Datacron` + `DatacronAffix` (player-level shape)
      - `SquadDatacron` (squad-embedded shape; distinct subset + `highestTierApplied`)
      - `EraUnitStatus`, `ProfileStat`, `SeasonStatusEntry`
      - `PvpProfileEntry` → `Squad` → `SquadCell`
      - `PlayerRating` → `PlayerRankStatus` + `PlayerSkillRating`
      - `IdRef` (used by `selected_player_*` and `unlocked_player_*` lists)
- [x] `Player` and `RosterUnit` updated to reference all new types.
      `equipment` and `unit_stat` stay as `list[Any]` / `dict[str, Any] | None`
      because both are uniformly empty/null across the recorded cassettes.
- [x] All 84 v3 tests + 709 full-suite tests still green.
- [x] `tests/v3/test_memory_budgets.py` `PLAYER_LARGE_BUDGET_BYTES`
      tightened **35 MiB → 15 MiB** (Phase 3.5 measured peak: ~9.7 MiB
      with ~50% headroom).
- [x] Phase 3 benchmarks re-run; results captured in
      `benchmarks/v3/results/phase-3.5-*.json`.
- [x] Phase plan updated with Phase 3.5 section.

## Commit SHAs

- `<TBD>` — `feat(msgspec): deepen Player Struct nesting (Mod sub-stats, datacron, pvp_profile, season_status, ...)`

## Files modified

```
MOD   src/swgoh_comlink/_models.py
        +160 lines: new Struct types
        Mod, RosterUnit, Player updated to reference new types
MOD   tests/v3/test_memory_budgets.py
        PLAYER_LARGE_BUDGET_BYTES: 35 MiB -> 15 MiB
MOD   v3_implementation_plan.md
        New Phase 3.5 section between Phase 3 and Phase 4
NEW   docs/v3/phase-3.5-report.md
NEW   benchmarks/v3/results/phase-3.5-{decode-speed,decode-memory,object-size}.json
```

## Benchmark deltas — Phase 3.5 vs Phase 3

### Decode speed

Median decode time. **Bold** = Phase 3.5 movement vs Phase 3.

| Cassette | json (baseline) | msgspec typed (Phase 3) | msgspec typed (Phase 3.5) | Δ |
|---|---:|---:|---:|---|
| metadata | 0.08 ms | 1.74x | 1.71x | — (unchanged Struct) |
| guild | 0.07 ms | 1.66x | 1.65x | — (unchanged) |
| leaderboard | 0.09 ms | 2.04x | 2.01x | — (unchanged) |
| player_small | 0.18 ms | 2.45x | **2.49x** | small bump |
| player_large | 16.8 ms | 1.57x | **2.67x** | **+70% improvement** ← headline |
| /data | 3,130 ms | n/a (untyped only) | 1.26x untyped | — (no typing change) |

### Decode peak memory (tracemalloc)

Ratio = json / parser. Higher = better.

| Cassette | json (baseline) | typed (Phase 3) | typed (Phase 3.5) | Δ |
|---|---:|---:|---:|---|
| metadata | 0.22 MiB | 1.21x | 1.21x | — |
| guild | 0.10 MiB | 1.23x | 1.23x | — |
| leaderboard | 0.14 MiB | 1.29x | 1.29x | — |
| player_small | 0.31 MiB | 2.26x | **2.45x** | +8% |
| player_large | 17.7 MiB | 1.28x | **1.83x** | **+43% improvement** ← headline |
| /data | 1,392 MiB | 1.25x (untyped) | 1.25x (untyped) | — |

### Object size (pympler.asizeof)

Ratio = json / parser. Higher = better.

| Cassette | json (baseline) | typed (Phase 3) | typed (Phase 3.5) | Δ |
|---|---:|---:|---:|---|
| metadata | 0.19 MiB | 0.99x | 0.99x | — |
| guild | 0.07 MiB | 0.83x | 0.83x | — |
| leaderboard | 0.12 MiB | 1.00x | 1.00x | — |
| player_small | 0.25 MiB | 1.76x | **1.94x** | +10% |
| player_large | 14.4 MiB | 1.02x | **1.43x** | **+40% improvement** ← headline |
| /data | 1,034 MiB | 0.91x (untyped) | 0.91x (untyped) | — |

### Distance from plan projection

| Metric (player) | Plan target | Phase 3 result | **Phase 3.5 result** |
|---|---|---:|---:|
| Decode speed | 3–5x | 1.57x | **2.67x** (closer; still under) |
| Memory peak | 4–6x lower | 1.28x | **1.83x** (closer; still under) |
| Object size | 40–60% smaller | 2% smaller | **30% smaller** (hits low end) |

Phase 3.5 substantially closes the gap on every player metric. The
remaining shortfall vs the plan's 3–5x / 4–6x projections is the cost
of fields still typed as `dict[str, Any]` for content we can't usefully
constrain (e.g. `equipment` items observed empty across cassettes,
opaque `unit_stat` shape). Those would be the next typing-depth
candidates if a user surface request demanded another shave.

## Deviations from the plan section

| Plan said | Reality | Why |
|---|---|---|
| Single `Datacron` type for both player and squad use | Split into `Datacron` (player-level) and `SquadDatacron` (squad-embedded) | The two wire shapes are genuinely different — player datacrons have `locked`/`focused`/`reroll*` fields; squad-embedded datacrons have `highestTierApplied` instead. A single type would either drop fields or pollute one shape with the other's defaults, both of which break `msgspec.to_builtins` round-trip fidelity. |
| Type `RosterUnit.equipment` and `RosterUnit.unit_stat` | Left as `list[Any]` and `dict[str, Any] \| None` | Both are uniformly empty / null across both recorded cassettes (small and large player). Defining types without seeing real shapes risks the same wrong-default round-trip bugs we hit with Datacron. Re-record when non-empty data appears, then type. |
| `ConvertedItem` Struct on `Mod.converted_item` | Left as `dict[str, Any] \| None` | Always observed null in cassettes. Same reasoning. |

## Test counts

```
$ uv run pytest tests/v3/ -q
84 passed in 47s     # was 84 from Phase 3 (test count unchanged; coverage tightened)

$ uv run pytest tests/ -q
709 passed, 28 skipped in 49s
```

Memory budget test now enforces ≤15 MiB for typed Player decode (down
from 35 MiB), giving Phase 4 / Phase 5 a tighter regression net.

## Coverage

Gate unchanged at 90; actual ≈96%.

## Open questions

- **The remaining gap to the plan's 4–6x memory target.** Would close
  further if `Mod.converted_item`, `RosterUnit.equipment`, and
  `RosterUnit.unit_stat` get typed. All three are uniformly empty in
  current cassettes; deferring until real non-empty shapes are seen.
- **/data typing for Phase 7.** Same logic as before — segments will
  get typed in Phase 7 (`GameDataCache`) where the per-segment cache
  surface gives a natural place to attach types.
- **Bench JSON naming.** Phase 3 + Phase 3.5 numbers both live at
  `benchmarks/v3/results/phase-3-*.json` (latest run wins). Phase 3.5
  numbers are also copied to `phase-3.5-*.json` for historical record.
  Future phases that re-run these benches should also `--phase`-rename
  the result file; bench scripts currently lack that arg.

## Phase 3.5 exit criteria check

- [x] All v3 tests still green (84 passed).
- [x] Benchmark deltas move in the right direction (player_large
      gained 70% decode speed, 43% memory peak, 40% object size).
- [x] Memory budget tightened to a realistic post-Phase-3.5 number.
- [x] `msgspec.to_builtins(typed) == raw cassette` round-trip preserved
      (the player_large_passthrough golden test passes).
- [x] No public API surface changes (typed endpoints still return
      Player/Metadata/etc.; `raw=True` path untouched).

Ready to merge `v3/phase-3.5-deepen-player-typing` → `v3.0-dev` (`--no-ff`).
