# StatCalc rewrite evaluation — three-axis research with pre-registered decision rule

**Status:** pre-registered (v3.3-research, Phase 1) — measured outcomes
appended in Phase 5 before the integration commit lands.

ADR-0006 closed v3.2 with the explicit deferral: *"Cython / Rust /
native acceleration of inner math loops. Out of scope; will revisit
only when caller demand data warrants a v3.3 conversation."* This ADR
records that conversation and the decision rule that will govern which
v3.3 candidates ship.

This ADR is **written and committed before any prototype lands**.
Phase 5 appends measured outcomes; the integration commit lands only
candidates that cleared their pre-registered bar.

## The three axes

| Axis | Problem | Candidates considered |
|---|---|---|
| **Pure-Python restructure** | `_calculate_mod_stats` is 165 lines with 11 hard-coded stat-ID branches; `_table_get` is a polymorphic dispatcher with a 28 % cProfile tax; `_format_stats` is 127 lines with 4 nested scopes; char and ship paths share no abstraction. | Phase 2 — single throwaway prototype that table-drives mod stats, replaces `_table_get` with 6 typed accessors, decomposes `_format_stats`, and dedups char/ship dispatch. |
| **Native acceleration** | ADR-0006 deferred native code; v3.2's `_calculate_mod_stats` inner-kernel costs are pure Python interpretation. | Phase 3a — Cython `.pyx` inner kernel. Phase 3b — mypyc whole-module compilation. Phase 3c — Rust/PyO3 kernel via maturin. |
| **Algorithmic / data-shape rewrite** | v3.2 Candidate H delivered 5.7 % targeted; aggressive variant broke parity on mod-set bonuses. v3.2 Candidate A's bimorphic path costs +22.9 % almost entirely from per-Mod `msgspec.to_builtins`. | Phase 4a — H re-attack with parity-test-first discipline. Phase 4b — typed-fastpath reading Struct slots directly, skipping `to_builtins`. |

## Pre-registered decision rule

Locked in **this ADR** before any v3.3 prototype is implemented. Same
"research-first, measure-then-ship" discipline that ADR-0006 codified
for v3.2.

Each axis has its own threshold; the three are orthogonal — each
ships independently when its bar is met. Every shipped path must
also pass byte-for-byte parity against the v3.2 dict baseline on
every recorded cassette.

| Axis | Threshold |
|---|---|
| **Hot-path speed** | `hot_path_improvement ≥ 10 %` vs v3.2 dict baseline on `calc_player_stats(player_large)` warm. Memory regression ≤ 5 %. Build/distribution overhead acceptable per Phase 3 analysis. If only native variants clear 10 %, ship the cheapest distribution profile (typically mypyc < Cython < Rust). |
| **Memory footprint** | `resident_game_data_reduction ≥ 20 %` (new metric for v3.3; baseline measured in Phase 1). Hot path regression ≤ 2 %. |
| **Typed-client ergonomics** | `bimorphic_struct_overhead ≤ 5 %` (vs v3.2 +22.9 %). Bimorphic parity preserved (dict input continues to work). Replaces the v3.2 Candidate A internal dispatcher; external behaviour unchanged. |

If no candidate clears its axis bar, that axis ships nothing and
defers to v3.4. ADR-0007 is updated to record the measured outcome
either way.

## Build / distribution as a decision-rule input

Native variants (Phase 3) must ship a written build/distribution
analysis on their prototype branch covering:

- Wheels matrix (5 OSes × 3 Pythons = 15 wheels per release).
- cibuildwheel config + GitHub Actions CI cost estimate.
- Pure-Python fallback contract — `STATCALC_NO_NATIVE=1` hides the
  extension and the test suite asserts identical output via the
  fallback path.
- Source-build path preservation — `pip install swgoh-comlink` from
  sdist must continue to succeed without a C compiler / Rust toolchain.
  Native build is opt-in via `pip install swgoh-comlink[native]`.
- CI complexity impact — v3.2 baseline is ~3 min per push; full
  cibuildwheel matrix is 30–60 min. Mitigation: build wheels on
  release-tag push only.

**A native variant that clears the 10 % speed bar but adds
30-minute-per-push CI overhead loses to a pure-Python winner that
also clears 10 %.** This is part of the hot-path decision rule, not
a soft consideration.

## Out of scope (explicit)

- `StatCalc/` → `statcalc/` PEP 8 rename. Sibling effort, doesn't
  interact, cleaner to land independently.
- `v3.0-dev` branch (frozen per ADR-0001).
- `v3.1-research` shipped surfaces (typed segments, codegen, async cache).
- v3.2 shipped surfaces — Candidate A bimorphic + Candidate E cache
  must continue to work and pass their parity tests. If typed-fastpath
  (Phase 4b) ships, it replaces A's internal dispatcher; A's external
  behaviour stays.
- Readability / maintainability as a primary metric. Cyclomatic
  complexity and method-length tracking are informational only.
- Candidate D (parallelism, v3.2). Stays settled unless Phase 3
  introduces a Python-version axis (3.13t free-threaded or PEP 684
  sub-interpreters) that flips the IPC math. If so, re-measure D
  under the new mechanism.
- Candidate G (direct typed-segment consumption, v3.2). Stays
  "deferred without prototyping" unless Phase 1 surfaces new
  information.
- v3.2 Candidates B / C / F — measured and rejected for mechanism
  reasons that don't change under any v3.3 axis. Re-measure only if
  the *mechanism* itself shifts (e.g. F-tables under mypyc compilation
  may resurface; F-tables alone won't).

## Process

- Branch: `v3.3-research` off `v3.2-research` (HEAD `ef7a542`). v3.0-dev
  and v3.1-research untouched.
- Phase 1 (`v3.3/statcalc-bench-extensions`) is the only phase that
  always merges — adds memory + ergonomics axes to the existing
  benchmark harness and this ADR.
- Phases 2–4 live on throwaway prototype branches that may or may not
  merge. Phase 5 lands ONLY the winners on
  `v3.3/statcalc-final-integration` → `--no-ff` to `v3.3-research`.
- Parity-test discipline carries forward from v3.2 (the GREATMOTHERS
  lesson: field-access audits lie; parity tests are load-bearing).
  Phase 4a writes the regression fixture FIRST.

## Phase 5 measured outcomes (filled before integration commit)

*To be appended after Phases 2–4 complete and before
`v3.3/statcalc-final-integration` merges. Will record measured
numbers per candidate, which ones cleared their bar, which ones
didn't, and the rationale for each ship/defer decision under the
pre-registered rule above. Same format as ADR-0006's "Measured
outcomes" section.*

| Candidate | Metric | Measured | Threshold | Verdict |
|---|---|---:|---|---|
| Phase 2 — pure-Python restructure | hot-path | _TBD_ | ≥ 10 % | _TBD_ |
| Phase 3a — Cython | hot-path | _TBD_ | ≥ 10 % | _TBD_ |
| Phase 3b — mypyc | hot-path | _TBD_ | ≥ 10 % | _TBD_ |
| Phase 3c — Rust/PyO3 | hot-path | _TBD_ | ≥ 10 % | _TBD_ |
| Phase 4a — H re-attack | hot-path | _TBD_ | ≥ 10 % | _TBD_ |
| Phase 4b — typed-fastpath | ergonomics | _TBD_ | ≤ 5 % overhead | _TBD_ |
| (any candidate) | memory | _TBD_ | ≥ 20 % game_data reduction | _TBD_ |
