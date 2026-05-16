# Phase 9 — Migration tooling, docs, consolidated benchmark report

**Branch:** `v3/phase-9-migration-docs` (off `v3.0-dev`)

**Status:** complete; the final phase. Ready to merge.

Pure documentation + tooling phase. No new runtime features; the
v3 surface is frozen as of Phase 8. This phase makes v3 *legible* —
to future-self, to any eventual upstream reviewer, to operators on
a migration path.

## Scope delivered

- [x] **`docs/v3/migration.md`** (~200 lines) — comprehensive side-by-side
      v2 → v3 cookbook covering every public-surface change. Hard
      breaks, soft migrations, new kwargs, removed/deprecated items.
- [x] **`docs/v3/recipes/`** (4 documents):
      - `long-running-bot.md` — `profile="bot"` + retries + GameDataCache
      - `bulk-analyst.md` — `profile="bulk"` + Semaphore fan-out + pydantic
      - `cli-script.md` — lazy imports + `max_retries=0`
      - `operator-side-concurrency.md` — Semaphore / TokenBucket /
        FailureCounter patterns in lieu of deferred `[ratelimit]` / `[circuitbreaker]`
- [x] **5 new v2 → v3 rules** in `src/swgoh_comlink/migrate/_rules.py`
      (V3001–V3005): dict-indexing on typed endpoints, `swgoh_comlink.globals`
      foot-gun.
- [x] **`benchmarks/v3/bench_v3_final.py`** — re-runs the headline
      benches and consolidates into `phase-9-final.json`.
- [x] **`docs/v3/benchmark-report.md`** — v2-vs-v3 consolidated table
      across every phase.
- [x] **Coverage gate: 92 → 95** in `pyproject.toml`. Current actual
      ~96.5%.
- [x] **`tests/unit/test_migrate.py`** updated to accept `V3*` rule
      IDs alongside `DEP*`.
- [x] All 742 tests still pass.

## Commit SHAs

- `<TBD>` — `docs(migration): v3 migration guide + recipes + benchmark report; migrate v2→v3 rules; coverage 92→95`

## Files modified

```
NEW   docs/v3/migration.md                       comprehensive v2→v3 cookbook
NEW   docs/v3/recipes/long-running-bot.md
NEW   docs/v3/recipes/bulk-analyst.md
NEW   docs/v3/recipes/cli-script.md
NEW   docs/v3/recipes/operator-side-concurrency.md
NEW   docs/v3/benchmark-report.md                consolidated v2-vs-v3 numbers
NEW   docs/v3/phase-9-report.md                  this file
NEW   benchmarks/v3/bench_v3_final.py
MOD   src/swgoh_comlink/migrate/_rules.py        +5 V3xxx rules
MOD   tests/unit/test_migrate.py                 accept V3* rule IDs
MOD   pyproject.toml                             coverage fail_under: 92 → 95
```

## Deviations from the plan

| Plan said | Reality | Why |
|---|---|---|
| Extend `swgoh-migrate` with v2 → v3 ruleset including codemod-style rewrites via `libcst` or `redbaron` | **5 regex-based ERROR/WARNING rules; no codemod tool integration.** | The existing `migrate/_rules.py` is regex-based (~14 v1→v2 rules). Adding `libcst`/`redbaron` would have added a dep, doubled the architecture, and pushed the phase past Phase-9 scope. The regex rules tell users WHAT to fix; the migration guide tells them HOW. v3.1 candidate to add real codemod rewrites if user feedback says the manual fixes are painful at scale. |
| Document the cache directory location for users | Done in `migration.md` *and* in `_cache.py`'s `default_cache_dir()` docstring. | (No deviation; just noting completeness.) |
| Run `bench_v3_final.py` against every prior bench (decode_speed, decode_memory, object_size, retry_overhead, retry_recovery) | **Subset: bench_baseline + bench_import_time + bench_cache_cold_vs_warm.** | Phase 9 doesn't touch the code paths the other benches exercise (msgspec decode, retry loop). Re-running them would burn ~3 minutes of CPU for numbers we already have in `benchmarks/v3/results/phase-{3,3.5,7}-*.json`. The benchmark report references the historical JSONs directly. |
| `compat.to_dict()` round-trips every Struct losslessly (Plan #2 of Phase 9) | **Already covered** by `test_compat_to_dict_round_trips_player` (Phase 3) and `test_warm_path_returns_equivalent_value` (Phase 7's cache test, which exercises msgpack round-trip on the same dict shape). | No new code needed. |

## v3 development retrospective

Across 11 phases (0, 1, 2, 3, 3.5, 4, 5, 6, 7, 8, 9):

**Headline deliveries:**
- 9.3× faster cold import (Phase 5)
- 2.67× faster `get_player` decode (Phase 3+3.5)
- 1.83× lower peak decode memory (Phase 3.5)
- 10⁷× warm-path cache (Phase 7)
- 29% fewer SLOC per client (Phase 4)
- 42 → 742 tests; coverage 40% → 96.5%

**Decisions held under pressure:**
- D5 — no `__getitem__` shim, even though it was the obvious soft on-ramp
- ADR-0004 — Phase 8 (`[ratelimit]` / `[circuitbreaker]`) deferred even when
  the original 10-phase plan envisioned them; v3.0 is tighter
- D9 — Phase 1 coverage gate **90**, not literal `max(96,50)=96` — the
  difference between an "honest ratchet" and a "no-budget regression trap"
- ADR-0003 (no `__getitem__` shim) sat in tension with D6 (keep `[pydantic]`).
  The two combined produced a clean story: typed Structs by default,
  `raw=True` and `compat.to_dict()` as soft on-ramps, `compat.to_pydantic`
  as the pydantic bridge — no surface explosion.

**Decisions reversed:**
- D6 implementation: the plan said `as_model=True` kwarg per endpoint.
  Phase 6 shipped `compat.to_pydantic()` helper instead — same user value,
  zero kwarg-explosion.
- Plan: stamina-based retry. Phase 2: hand-rolled retry (~50 stdlib lines).
  Stamina v24 couldn't influence per-attempt sleep duration, which
  `Retry-After` requires.

**Scope cuts the plan didn't anticipate but that were the right call:**
- **`StatCalc/` left untouched through every phase.** Phase 3.5, 7, 8 each
  considered touching it; each deferred. The subpackage works as-is and
  carries no v3 architectural debt. Async StatCalc with threshold-based
  ProcessPoolExecutor is the most prominent v3.1 candidate.
- **`unasync` codegen.** Plan called for `<10%` sync/async duplication ratio.
  Achievable only via codegen. Phase 4 hit `0.98` instead — bilaterally
  symmetric bodies are unavoidable without unasync. The 29% SLOC reduction
  was the real win.
- **The Phase 3 "Mann-Whitney U at p<0.05 on every comparative claim"**
  was downgraded to MWU only on Phase 3 headlines (Plan D10) before Phase
  3 ran. Phase 3's per-metric direction-of-change was strong enough across
  multiple runs that p-value rigor would have been ceremony.

**Where the headline numbers fell short:**
- `/data` decode speed: plan 3-5×, got **1.00×**. Partial-typing tradeoff:
  82 segments would need hand-typing.
- `/data` memory peak: plan 4-6× lower, got **1.25× lower**. Same.
- `player_large` decode speed: plan 3-5×, got **2.67×**. Closer; Phase 3.5
  closed most of the gap.
- Method-body duplication ratio: plan <10%, got **0.98**. Not achievable
  without codegen.

Honest documentation of these shortfalls is in the per-phase reports.
The benchmark report's "What v3 didn't deliver" section names them.

## Phase 9 exit criteria check

- [x] Migration guide written.
- [x] 4 recipes written.
- [x] `swgoh-migrate` v2 → v3 rules in place.
- [x] Coverage gate at 95 (current actual 96.5%).
- [x] Final benchmark report consolidates v2-vs-v3 numbers.
- [x] All tests green (742 passed, 30 skipped).
- [x] No new runtime features; the v3 surface is frozen.

## v3.0 — what it is

`swgoh-comlink-v3` is a **standalone research repo** at
`/Users/marktripod/code/comlink-python-v3/` (ADR-0001). It has been
developed over 11 phases against a real comlink instance. The `v3.0-dev`
branch HEAD is the artifact handed off for whatever comes next —
reintegration with the public repo, fork, or shelf.

The repo carries:
- 742 tests covering the v3 surface end-to-end via recorded cassettes
- 16 markdown documents under `docs/v3/` (this one is the 12th phase report)
- 4 ADRs under `docs/adr/`
- A pytest-httpx test harness that any future phase can extend
- A benchmark harness whose results are reproducible across machines
  (per-phase JSONs are committed)

The next decision is outside the scope of v3 development:
**reintegration vs. fork vs. shelf**. ADR-0001 deliberately left that
open for a later, separate evaluation.

Ready to merge `v3/phase-9-migration-docs` → `v3.0-dev` (`--no-ff`).
This is the final phase.
