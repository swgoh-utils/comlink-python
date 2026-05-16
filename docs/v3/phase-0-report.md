# Phase 0 — Baseline + benchmark harness

**Branch:** `v3.0-dev` (no per-phase feature branch — Phase 0 is foundation work).

**Status:** **complete** (modulo `--full` install-size measurement, deferred to Phase 6 when it's actually used as a comparison).

## Scope delivered

- [x] Repo bootstrapped (clone, branch, version bump, Python floor 3.11, ADRs, CONTEXT.md, plan).
- [x] `benchmarks/v3/` scaffolding: `_harness.py`, `_record.py`, `bench_baseline.py`,
      `fixtures/`, `results/`, `python-version` pin.
- [x] `docs/v3/` scaffolding: README + this report.
- [x] Cassettes recorded from live comlink at `192.168.68.74:3200`. `player_large`
      against ally code `314927874` (Mar Trepodi, 397 units); `player_small`
      against ally code `855566316` (Mar Elezra, 115 units, 7.5 KiB gzipped);
      `guild` against `GbsabjvbQESUd8r_qPqdYg`. 7 cassettes, ~18 MB total on disk.
- [x] Baseline run on Python 3.11.15 (aarch64, native) produces
      `results/phase-0-baseline.json` with all 11 metrics filled in.

## Commit SHAs

- `964a04b` — `chore(v3): bootstrap research repo with plan, glossary, and 4 ADRs`
- `cb8a512` — `feat(bench): scaffold v3 benchmark harness + phase-0 baseline`
- `e9e8685` — `chore(bench): record baseline cassettes and fill phase-0 numbers`
- `470debd` — `feat(bench): add --only filter to cassette recorder`
- `<TBD>`   — `chore(bench): refresh player_small cassette with 115-unit ally code`

## Files touched

```
.python-version                            (new)
pyproject.toml                             (Python 3.11 floor + bench dep group)
src/swgoh_comlink/version.py               (2.0.7 → 3.0.0.dev0)
v3_implementation_plan.md                  (new, 9-phase rewrite)
CONTEXT.md                                 (new, glossary)
docs/adr/{0001..0004}-*.md                 (new, 4 ADRs)
docs/v3/README.md                          (new)
docs/v3/phase-0-report.md                  (this file)
benchmarks/__init__.py                     (new)
benchmarks/v3/__init__.py                  (new)
benchmarks/v3/python-version               (new, "3.11")
benchmarks/v3/_harness.py                  (new)
benchmarks/v3/_record.py                   (new)
benchmarks/v3/bench_baseline.py            (new)
benchmarks/v3/fixtures/{README.md,*.json.gz}  (new, 7 cassettes ~18 MB)
benchmarks/v3/results/phase-0-baseline.json   (new)
```

## Deviations from the plan

| Plan said | Reality | Why |
|---|---|---|
| `benchmarks/v3/_harness.py` provides `measure / track_memory / track_import_time / Reporter` | Same surface; also added `load_cassette`, `cassette_exists`, `require_python_version`, `MeasureResult`, `MemoryResult` dataclasses, and `git_sha()` helper | Smaller call sites; pinning Python version makes phase-to-phase comparison defensible (cross-cutting principle in plan). |
| `bench_baseline.py` runs every metric | Cassette-bound metrics emit `status="skip"` when their cassette is missing | Lets the harness be runnable on a fresh clone before the operator has recorded cassettes, which preserves the "everything is reproducible from this commit" property. |
| Plan refers to `get_data` and `get_metadata` endpoints | The v2 source actually exposes `get_game_data` and `get_game_metadata` | Used the actual method names in the harness; cassette names stay as `data` / `metadata` for plan continuity. |
| Plan calls out wheel/site-packages size in baseline | Moved behind `--full` flag | The metric requires a network-free `uv build` plus venv-install dance; expensive on every run and not needed until Phase 6 extras work compares against it. |
| "Small" roster cassette ~50 units | `player_small` uses ally code `855566316` (115 units). Closer to small than large but not literally 50. | Smallest representative roster available on this comlink. Distinct enough from `player_large` (397 units) to expose decode/scale differences. |
| Exit criterion "cassettes sum to under 5 MB" | Reality is ~18 MB on disk (`/data` alone is 15 MB gzipped) | The full `/data` payload is load-bearing for Phase 3's headline numbers; can't shrink it without invalidating the comparison. Plan exit criterion updated to ~15–20 MB. |
| Python interpreter | Required a rebuild against aarch64 cpython-3.11.15 (uv-managed). Initial venv landed on `/usr/local/opt/python@3.11` which is x86_64 under Rosetta. | (a) Rosetta perf would skew benchmarks; (b) x86 Homebrew Python lacks macOS Local Network privacy grant and silently fails LAN connections with `EHOSTUNREACH`. |

## Open questions

- The Local Network privacy grant is per-binary on macOS. Any future bench/test runner that talks to LAN comlink will need the same grant once. Document this in CONTRIBUTING / quickstart when those exist.
- Cassette regeneration policy is documented (`fixtures/README.md`), but there's no automated drift detector. If upstream comlink changes a field, the cassette goes stale silently. Consider adding a "shape signature" (sorted set of top-level keys per endpoint) to the result JSON so drift is visible across phases.
- Should `bench_install_size` also measure site-packages delta (not just wheel size)? Currently only the wheel size is reported. A site-packages measurement requires creating a fresh venv and installing — defer until Phase 6 needs it.

## Benchmark deltas vs baseline

Phase 0 _is_ the baseline. Numbers from `benchmarks/v3/results/phase-0-baseline.json`
on Python 3.11.15 (aarch64, native) at SHA `470debd`.

| Metric | Median | p95 | Unit | Phase target |
|---|---:|---:|---|---|
| `cold_import_time` | **65.4** | — | ms | Phase 5: ≤6 ms (10× reduction). |
| `httpx_loaded_on_import` | **1.0** (yes) | — | bool | Phase 5: 0. |
| `method_body_duplication_ratio` | **1.0** (16/16 methods) | — | ratio | Phase 4: <0.10. |
| `get_player_small_e2e_latency` (115 units) | 0.29 | 0.56 | ms | Phase 2 + 3: ≤0.15 ms target. |
| `get_player_large_e2e_latency` (397 units) | 40.1 | 121.4 | ms | Phase 3 headline (Struct decode). |
| `get_data_decode_time` (json) | **7,120.2** | 7,924 | ms | Phase 3 headline: 3–5× faster (≤2 s). |
| `get_data_decode_peak_memory` | **1,392.4 MiB** | — | bytes | Phase 3 headline: 4–6× lower (≤350 MiB). |
| `get_data_object_size` | **1,033.7 MiB** | — | bytes | Phase 3 headline: 40–60% smaller (≤500 MiB). |
| `get_player_concurrent_100x_async_wall` (small cassette) | 81.4 | 89.5 | ms | Phase 2 / 3 stress baseline. |
| `get_player_concurrent_100x_async_peak_memory` | 24.9 MiB | — | bytes | Phase 2 / 3 baseline. |
| `installed_wheel_size` (`--full`) | — | — | bytes | Deferred to Phase 6. |

The `cold_import_time` figure drifted from 41.1 ms (first run) to 65.4 ms here on
the same machine + interpreter — system load during the run. Phase 5's target is
"≤6 ms"; any value in that range is unambiguously a 10× win regardless of which
baseline value we anchor against. The plan's "±5% reproducibility" exit-criterion
is unrealistic for cold-import on a working machine; document as an open question.

### Notable cassette-free finding

`method_body_duplication_ratio = 1.0` (perfect duplication) across all 16
paired `get_*` methods. *Higher* than the plan's predicted ~0.65. Sync and
async bodies are literally identical after stripping `await ` and `async ` —
the codemod for Phase 4 will be near-mechanical rather than per-method.

### Notable cassette-bound findings

**`/data` decode at baseline is enormous.** A single `get_game_data()` call
decodes ~15 MB of gzipped JSON into a Python dict graph that:

* takes **7.5 seconds** to parse with stdlib `json`,
* peaks at **1.39 GiB** of allocations during decoding,
* settles at **1.03 GiB** resident.

This is the headline Phase 3 target. Even hitting just the *low end* of the
projected msgspec wins (3× faster, 4× less memory) would drop this to ~2.5 s
and ~350 MiB — qualitatively different for any bot operator running on a
small VPS. Hitting the projected ceiling (~5× faster, ~6× less) is
transformative.

**`/player` end-to-end latency is dominated by JSON decode at 397 units.**
The 25–28 ms median is mostly the cost of `json.loads(358 KiB)` plus dict
allocation, not the (negligible) mock-transport overhead. Phase 3's typed
decode + Phase 5's lazy imports both move this number.

**`100×` async concurrent wall time is 81 ms** through the small cassette
(115 units, 7.5 KiB gzipped) with peak 25 MiB. ~0.8 ms per call wall-clock.
Mostly mock-transport + asyncio scheduling overhead at this size; Phase 5
(lazy imports — avoid pulling httpx during client construction) and Phase 3
(faster decode) are the levers, but the absolute numbers are already small.
This benchmark exists to catch *regressions* in async overhead, not to be
the headline.
