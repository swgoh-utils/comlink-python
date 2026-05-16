# Phase 0 — Baseline + benchmark harness

**Branch:** `v3.0-dev` (no per-phase feature branch — Phase 0 is foundation work).

**Status:** _in progress_ — fill in below as the phase wraps.

## Scope delivered

- [x] Repo bootstrapped (clone, branch, version bump, Python floor 3.11, ADRs, CONTEXT.md, plan).
- [x] `benchmarks/v3/` scaffolding: `_harness.py`, `_record.py`, `bench_baseline.py`,
      `fixtures/`, `results/`, `python-version` pin.
- [x] `docs/v3/` scaffolding: README + this report template.
- [ ] Cassettes recorded from a live comlink (requires a configured `COMLINK_URL`
      and chosen ally codes / guild ID — see `benchmarks/v3/fixtures/README.md`).
- [ ] Baseline run that produces `results/phase-0-baseline.json` with no `skip`
      entries beyond `--full`-gated ones.

## Commit SHAs

- `<sha>` — `chore(v3): bootstrap research repo with plan, glossary, and 4 ADRs`
- `<sha>` — `feat(bench): scaffold v3 benchmark harness (record + baseline runner + harness helpers)`
- `<sha>` — `chore(bench): record initial baseline cassettes` _(only after cassettes are captured)_

## Files touched

Fill from `git diff --stat 4a064f1..HEAD`.

## Deviations from the plan

| Plan said | Reality | Why |
|---|---|---|
| `benchmarks/v3/_harness.py` provides `measure / track_memory / track_import_time / Reporter` | Same surface; also added `load_cassette`, `cassette_exists`, `require_python_version`, `MeasureResult`, `MemoryResult` dataclasses, and `git_sha()` helper | Smaller call sites; pinning Python version makes phase-to-phase comparison defensible (cross-cutting principle in plan). |
| `bench_baseline.py` runs every metric | Cassette-bound metrics emit `status="skip"` when their cassette is missing | Lets the harness be runnable on a fresh clone before the operator has recorded cassettes, which preserves the "everything is reproducible from this commit" property. |
| Plan refers to `get_data` and `get_metadata` endpoints | The v2 source actually exposes `get_game_data` and `get_game_metadata` | Used the actual method names in the harness; cassette names stay as `data` / `metadata` for plan continuity. |
| Plan calls out wheel/site-packages size in baseline | Moved behind `--full` flag | The metric requires a network-free `uv build` plus venv-install dance; expensive on every run and not needed until Phase 6 extras work compares against it. |

## Open questions

- Should `bench_install_size` also measure site-packages delta (not just wheel size)? Currently only the wheel size is reported. A site-packages measurement requires creating a fresh venv and installing — defer until Phase 6 needs it.
- Cassette regeneration policy is documented (`fixtures/README.md`), but there's no automated drift detector. If upstream comlink changes a field, the cassette goes stale silently. Consider adding a "shape signature" (sorted set of top-level keys per endpoint) to the result JSON so drift is visible across phases.

## Benchmark deltas vs baseline

Phase 0 _is_ the baseline. Numbers below are from the first harness run on
`v3.0-dev` HEAD (`964a04b`) with Python 3.11.7. Cassette-bound rows will be
filled in once `_record.py` runs against a live comlink.

| Metric | Median | p95 | Unit | Notes |
|---|---|---|---|---|
| `cold_import_time` | 111.6 | — | ms | Phase 5 target: ≥10× reduction (~11 ms). |
| `httpx_loaded_on_import` | 1.0 | — | bool | Phase 5 target: 0. |
| `method_body_duplication_ratio` | **1.0** | — | ratio | Phase 4 target: <0.10. **Higher than the plan's predicted 0.65** — sync/async bodies are *literally* identical after stripping `await ` and `async ` (across all 16 paired `get_*` methods). The Phase 4 win is bigger than originally projected. |
| `get_player_small_e2e_latency` | — | — | ns | Pending cassette `player_small`. |
| `get_player_large_e2e_latency` | — | — | ns | Pending cassette `player_large`. |
| `get_data_decode_time` (json) | — | — | ns | Pending cassette `data` (Phase 3 headline). |
| `get_data_decode_peak_memory` | — | — | bytes | Pending cassette `data` (Phase 3 headline). |
| `get_data_object_size` | — | — | bytes | Pending cassette `data` (Phase 3 headline). |
| `get_player_concurrent_100x_async_wall` | — | — | ns | Pending cassette `player_small`. |
| `installed_wheel_size` (`--full`) | — | — | bytes | Pending `--full` run; needed at Phase 6 not Phase 0. |

### Notable cassette-free finding

`method_body_duplication_ratio = 1.0` (perfect duplication) across all 16
paired `get_*` methods. This is *higher* than the plan's predicted ~0.65
baseline. It means Phase 4 (sibling-on-base collapse) has even more headroom
than projected — every paired method body is identical modulo `await ` /
`async `, suggesting the sync and async classes can collapse into a single
template with sync/async dispatch happening one level deeper (likely in the
`_post` / `_get` helpers that the bodies all call).

This finding strengthens the case for Phase 4 and may simplify it: if every
body is identical post-normalization, the codemod is mechanical and could
land in a single commit rather than method-by-method.
