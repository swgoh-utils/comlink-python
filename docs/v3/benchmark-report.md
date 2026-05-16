# v3 Benchmark Report

Consolidated v2.0.x baseline vs v3.0 final numbers across every phase.
Raw JSON results live in `benchmarks/v3/results/`; this document is
the human-readable summary.

All numbers measured on the same machine: **macOS aarch64, Python
3.11.15 (uv-managed), 16-inch MacBook Pro M-series**. Same comlink
cassettes (recorded Phase 0) used as inputs throughout. Timings are
medians of N=10–50 iterations depending on the bench; cold-import
numbers are particularly noisy on a working laptop (documented in
the Phase 0/1 reports' "open questions" sections — variance can be
30–50% run-to-run from system load).

## Headlines

| Metric | v2.0.x baseline | v3.0 final | Δ |
|---|---:|---:|---:|
| Cold `import swgoh_comlink` | 65.4 ms | **~7 ms** | **9.3× faster** (Phase 5) |
| `httpx` loaded on `import` | True | **False** | (Phase 5) |
| `get_player` decode speed (large roster) | 1× (json baseline) | **2.67× faster** | (Phase 3.5) |
| `get_player` decode peak memory | 1× | **1.83× lower** | (Phase 3.5) |
| `get_player` object size | 1× | **30% smaller** | (Phase 3.5) |
| `GameDataCache` warm path (same instance) | n/a | **10⁷× faster than cold** | (Phase 7) |
| Method-body duplication ratio (sync/async) | 1.0 | 0.98 (essentially 1.0) | unchanged by design (Phase 4) |
| Endpoint method total SLOC per client | 125 | **89** | **−29%** (Phase 4) |
| Coverage gate (`fail_under`) | 40 | **95** | (Phase 9) |
| Test count (full suite) | 654 | **742+** | new tests for every phase |

## Per-metric breakdown vs Phase 0 baseline

Cassette: see `benchmarks/v3/fixtures/`. Tagged `data` ≈ 380 MiB JSON;
`player_large` ≈ 3.6 MiB JSON (397 units); `player_small` ≈ 58 KiB
(115 units); others smaller.

### Phase 0 baseline (recorded against v2.0.x code at SHA `cb8a512`)

Source: `benchmarks/v3/results/phase-0-baseline.json`.

| Metric | Value |
|---|---:|
| `cold_import_time` | 65.4 ms |
| `httpx_loaded_on_import` | True |
| `method_body_duplication_ratio` | 1.0 (16/16 paired methods) |
| `get_player_small_e2e_latency` | 0.29 ms (115-unit roster) |
| `get_player_large_e2e_latency` | 40.1 ms (397-unit roster) |
| `get_data_decode_time` (json) | 7,120 ms |
| `get_data_decode_peak_memory` | 1,392 MiB |
| `get_data_object_size` | 1,034 MiB |

### Phase 2 — Resilience layer

`bench_retry_overhead`: **−1.10 %** overhead with `max_retries=3` vs
`0` on the happy path (target <2 %).

`bench_retry_recovery`: `429 + Retry-After: 1` → 200 takes 1.011 s
wall (expected ~1.0 s). 503 (no header) → exp-jitter wait ≈ 0.35 s.

### Phase 3 + 3.5 — msgspec.Struct typing

Best-case wins on `player_large` after Phase 3.5 deep typing:

| Bench | v2 (json) | v3 typed | win |
|---|---:|---:|---:|
| `bench_decode_speed` (player_large) | 16.8 ms | **6.3 ms** | **2.67× faster** |
| `bench_decode_speed` (player_small) | 0.18 ms | **0.07 ms** | **2.49× faster** |
| `bench_decode_memory` (player_large peak) | 17.7 MiB | **9.7 MiB** | **1.83× lower** |
| `bench_decode_memory` (player_small peak) | 0.31 MiB | **0.13 MiB** | **2.45× lower** |
| `bench_object_size` (player_large resident) | 14.4 MiB | **10.0 MiB** | **1.43× smaller** |
| `bench_object_size` (player_small resident) | 0.25 MiB | **0.13 MiB** | **1.94× smaller** |

Plan's original projection was 3–5× faster + 4–6× lower memory + 40–60% smaller
object size. Phase 3.5 closed most of the gap; the remaining shortfall is
from fields still typed as `dict[str, Any]` (uniformly empty/null in the
cassettes — `equipment`, `unit_stat`, `Mod.converted_item`).

`/data` decode speed: **1.00×** (no improvement). Documented in phase-3 report
as the partial-typing tradeoff — /data segments aren't deeply typed (deferred
to Phase 7's GameDataCache and beyond). Object size for `/data` actually
worsens 9% with msgspec untyped — msgspec's dict graph is marginally heavier
than `json.loads` in this specific case.

### Phase 4 — SLOC reduction

Endpoint method bodies per client: **125 → 89 SLOC (-29%)**. Biggest
methods:

| Method | v2 | v3 |
|---|---:|---:|
| `get_leaderboard` | 19 | **4** |
| `get_guild` | 10 | **6** |
| `get_localization` | 9 | **4** |
| `get_game_metadata` | 8 | **3** |

Duplication ratio (sync vs async, post-`await`-stripping) stays at
**0.98** (≈1.0). Achieving <10% per the plan requires code generation
(unasync-style); deferred. See Phase 4 report for the analysis.

### Phase 5 — Lazy imports

| Metric | v2 | v3 |
|---|---:|---:|
| `cold_import_time` | 65.4 ms | **7.0 ms** (9.3× reduction) |
| `httpx_loaded_on_import` | True | **False** |
| `import_then_construct` (first SDK call) | n/a | ~80 ms (deferred cost paid on first construct) |

`import swgoh_comlink` no longer pulls httpx, msgspec, or StatCalc.
PEP 562 `__getattr__` resolves + caches names on first access.

### Phase 6 — Extras taxonomy

No perf benchmarks. Test counts: +7 (test_optional.py).

### Phase 7 — GameDataCache

| Path | Time | vs cold |
|---|---:|---:|
| Cold (fresh on-disk cache; full pipeline) | 3,549 ms | 1× |
| Disk-warm (new GameDataCache per call) | 3,503 ms | ~1× |
| **In-memory warm** (same instance, hot loop) | **0.0003 ms** | **10,659,556×** |

The plan's 100–1000× target is met on the realistic operator path
(one cache instance per process). The disk-only warm path is bound by
the cost of constructing 11k+ Python dicts — msgspec.msgpack vs
msgspec.json doesn't matter when structure dominates.

### Phase 8 — Ergonomics

No perf benchmarks. Test counts: +18 (test_ergonomics.py covering
healthcheck, raw_request, stream_game_data, stream_localization on
both sync and async clients).

### Phase 9 — Migration tooling + docs

| Deliverable | What |
|---|---|
| `docs/v3/migration.md` | Side-by-side v2 → v3 examples |
| `docs/v3/recipes/*.md` | 4 recipes (long-running bot, bulk analyst, CLI script, operator-side concurrency) |
| `swgoh-migrate` v2→v3 rules | 5 new rules (V3001–V3005) in `_rules.py` |
| Coverage ratchet | 92 → **95** (current actual ~96.5%) |
| `bench_v3_final.py` | Re-runs the headline benches; produces consolidated JSON |

## What v3 didn't deliver (deferred to v3.1)

- **`[ratelimit]`** + `[circuitbreaker]` extras — ADR-0004
- **Async-aware StatCalc** with threshold-based `ProcessPoolExecutor`
- **`StatCalc/` → `statcalc/`** PEP 8 rename
- **Deeper `Mod.equipment` / `unit_stat`** typing (needs non-empty cassette samples)
- **Async-aware `GameDataCache`** for `SwgohComlinkAsync`
- **`GameDataBuilder` rewrite** atop GameDataCache
- **`unasync`-style codegen** to actually eliminate sync/async duplication
- **`stamina` dependency** — never added (Phase 2 hand-rolled the retry loop)
- **`globals.py` rename** — collides with the builtin `globals()` function
  inside `__init__.py`; works today but is a known foot-gun

## What v3 delivered beyond plan

- **`compat.to_pydantic(struct, model_class)`** — dynamic adapter without
  doubling the type surface. The plan called for `as_model=True` per
  endpoint method; the helper form serves the same need with zero kwarg
  explosion.
- **GameDataCache in-memory memo** — the plan only specified disk caching.
  The realistic 10⁷× win comes from same-instance dict lookups; disk
  alone gives ~1×.

## How to reproduce

```bash
# Fresh checkout + native ARM Python 3.11
git clone <repo>
cd comlink-python-v3
uv venv --python 3.11
uv sync --group dev

# Record cassettes (once, with a live comlink + ally codes)
COMLINK_URL=http://your.comlink.local:3000 \
SMALL_ROSTER_ALLYCODE=<small> \
LARGE_ROSTER_ALLYCODE=<large> \
GUILD_ID=<guild-id> \
uv run python -m benchmarks.v3._record

# Run every bench from this report
uv run python -m benchmarks.v3.bench_v3_final
```

Per-phase per-bench results land in `benchmarks/v3/results/phase-*.json`.

## Caveats

- All numbers are on one machine. Phase-to-phase comparisons are valid
  (same hardware, same Python, same cassettes); cross-platform / cross-CPU
  comparisons aren't.
- Timing benches drift 30–50% run-to-run on a working laptop. Memory
  baselines (deterministic — same bytes in, same allocations out) are
  the stable signal. Documented per-phase as an open question.
- The Phase 3 plan's "Mann-Whitney U at p<0.05 on every comparative
  claim" was downgraded to "MWU only on Phase 3 headlines" (Plan D10).
  This report relies on consistent direction-of-change across multiple
  runs rather than statistical hypothesis testing per metric.
