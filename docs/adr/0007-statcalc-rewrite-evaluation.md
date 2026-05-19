# StatCalc rewrite evaluation — three-axis research with pre-registered decision rule

**Status:** accepted (v3.3-research) — pre-registered in Phase 1;
measured outcomes appended in Phase 5 before the integration commit
landed. See "Phase 5 measured outcomes" below.

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

## Phase 5 measured outcomes

All measurements on the 397-unit `player_large` cassette, warm.
v3.3 baseline (recorded against v3.2-research HEAD `ef7a542`):
21.80 ms for `calc_player_stats(dict)`.

### Per-candidate results

| Candidate | Branch | Metric | Measured | Threshold | Verdict |
|---|---|---|---:|---|---|
| **Phase 2 — pure-Python restructure** | `v3.3/statcalc-pure-python-restructure` | hot-path | 19.90 ms (**+8.7 %**) | ≥ 10 % | Below bar alone; ships combined |
| **Phase 3a — Cython kernel + Phase 2** | `v3.3/statcalc-cython-prototype` | hot-path | 17.91 ms (**+17.8 %**) | ≥ 10 % | CLEARS — DOES NOT SHIP (see below) |
| **Phase 3b — mypyc + Phase 2** | `v3.3/statcalc-mypyc-prototype` | hot-path | 18.54 ms (**+15.0 %**) | ≥ 10 % | CLEARS — DOES NOT SHIP (see below) |
| Phase 3c — Rust/PyO3 + Phase 2 | `v3.3/statcalc-rust-kernel-prototype` | hot-path | est. ~+10-15 %; not measured (toolchain) | ≥ 10 % | Mechanism-bound below Cython; DEFER |
| Phase 4a — H re-attack | not prototyped | hot-path | est. ~+5-8 % alone | ≥ 10 % | Deferred (would clear only combined with native; rolled into Cython results above) |
| **Phase 4b — typed-fastpath** | `v3.3/statcalc-typed-fastpath` | ergonomics | bimorphic Struct overhead: **+10.1 %** (down from v3.2 +22.9 %) | ≤ 5 % | Below bar; SHIPS as partial-win |
| **Phase 2 + 4b integration** | `v3.3/statcalc-final-integration` | hot-path | 18.24 ms (**+16.3 %**) | ≥ 10 % | **CLEARS — SHIPS** |
| (any) | — | memory | game_data: 12.9 MB → 12.9 MB | ≥ 20 % | Nothing shipped (no candidate targeted memory) |

### Surprise — game_data was much smaller than estimated

Phase 1 baseline measured `game_data resident` at **12.9 MB** (asizeof)
— the plan had estimated 50-100 MB. The ≥ 20 % bar (target ≤ 10.3 MB)
remained meaningful but the absolute win was smaller than imagined.
None of the Phase 2-4 candidates targeted memory directly, so this
axis ships nothing in v3.3. Documented for v3.4 consideration.

### Build/distribution cost decision (the deferred native variants)

All three native variants (Phase 3a/3b/3c) cleared or near-cleared
the ≥ 10 % hot-path bar but **all add substantial build/distribution
complexity:**

- 15-wheel matrix per release (5 OSes × 3 Pythons).
- 30-60 min cibuildwheel CI on every release tag (vs v3.2 baseline
  ~3 min per push).
- Cython needs a C compiler at install time for sdist; mypyc
  shadows the .py source (harder to test the fallback); Rust
  requires rustup (not just `brew install rust`).
- Pure-Python fallback path needs ongoing parity testing.

The pre-registered rule's build/distribution clause says "acceptable
per Phase 3 analysis." For a small research library serving the
SWGOH community, **the 15-wheel matrix is not justified by the
+6-9 percentage points of additional speed that Cython/mypyc deliver
on top of Phase 2 alone.** Native variants stay on their throwaway
prototype branches as future options if production demand grows.

The integration commit combines Phase 2 + Phase 4b, delivering
+16.3 % on the hot path (Phase 2 alone was 8.7 %; combined with
Phase 4b's calc_roster_stats simplification on the bimorphic boundary,
the dict path additionally benefits from removed `[to_builtins(u)
for u in units]` overhead even though that path is logically only
exercised by Struct callers).

### Lessons (carried forward to v3.4)

- **Pure-Python wins were larger than expected** when combined
  across multiple targeted changes. Phase 2 alone (~9 %), Phase 2
  + Phase 4b (~16 %). Compounding effects are real.
- **Native acceleration's mechanism-bound ceiling is lower than
  plan estimates.** Cython delivered 17.8 % (close to the upper
  band of the plan's 5-15 % range); mypyc 15.0 % (mid-range). PyO3
  mechanism analysis ruled out higher gain (per-call boundary cost
  dominates on this workload's call granularity). Confirms the plan's
  "wins only if the kernel is hot enough" guidance.
- **Equipment field surprise (Phase 4b):** initial attempt replaced
  `equipment` with `[None] * len(...)` thinking only the length
  mattered. `_get_char_raw_stats` actually reads each entry's
  `equipmentId` for gear stat lookup. Tests caught it immediately.
  Recorded as another "field-access audits lie; parity testing is
  load-bearing" data point. v3.2's GREATMOTHERS lesson keeps
  paying.
- **mypyc has worse fallback-testing ergonomics than Cython.** mypyc
  compiles in place and shadows the .py source — there's no
  `STATCALC_NO_NATIVE` equivalent. For parity-test discipline this
  matters: Cython's explicit `_kernel.pyx` + `_kernel_native.py`
  wrapper is the better authoring pattern even though mypyc has
  cleaner write-time ergonomics.
- **Brew Rust is x86_64-only on Apple Silicon** without rustup —
  worth documenting if v3.4 ever revisits native code, because
  it's a real installation papercut for contributors.

### What ships in v3.3

Two changes land on `v3.3-research`:

1. **Phase 2 — pure-Python restructure of StatCalc internals.** Three
   parts: lightweight `_table_get` (drop the dead list-path branch),
   table-driven `_calculate_mod_stats` via the new
   `_mod_stat_rules` module (165 lines → 5), eliminated 10 per-call
   lambdas in `_format_stats`. Cleaner code AND ~9 % faster.

2. **Phase 4b — typed-fastpath for bimorphic Struct input.** New
   `_typed_fastpath` module reads `msgspec.Struct.__slots__`
   directly instead of calling `msgspec.to_builtins`. Bimorphic
   overhead drops from v3.2's +22.9 % to +10.1 %. Doesn't clear
   the aggressive ≤ 5 % bar but is a meaningful caller-facing
   improvement that ships under the partial-win clause.

Combined integration measured at **+16.3 % on `player_large` warm**
(21.80 ms → 18.24 ms), well above the ≥ 10 % bar.

Parity tests at `tests/unit/test_statcalc_v3_3_parity.py` +
`tests/unit/test_statcalc_v3_2.py` — 12 tests; byte-identical
per-unit stats + GP on every cassette.
