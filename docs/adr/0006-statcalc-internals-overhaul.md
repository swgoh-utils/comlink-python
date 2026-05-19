# StatCalc internals overhaul — three-axis research; ship A + E

**Status:** accepted (v3.2-research)

`swgoh_comlink.StatCalc` was the deferred-since-Phase-3.5 subpackage —
v3 Phases 3.5, 7, 8, and 9 each considered touching it and declined
("StatCalc internals carry no v3 architectural debt — they work as-is
with the new client surface."). v3.2-research revisits that decision
along three orthogonal axes, with **research-first / measure-then-ship
discipline** and pre-registered decision rules.

This ADR records what the eight candidates across three axes
delivered and which two shipped.

## The three axes

| Axis | Problem | Candidates considered |
|---|---|---|
| **Input format** | `StatCalc` is dict-only. Typed-client users pay a `msgspec.to_builtins(player)` ≈ +25 % conversion tax to hand it a `Player` Struct. | A — full `to_builtins` adapter at boundary. B — partial conversion (only StatCalc-read fields). C — accessor-abstraction subclass. |
| **Parallelism** | `calc_player_stats` runs serially in ~21 ms for a 397-unit roster despite being embarrassingly parallel. | D — `ProcessPoolExecutor` with threshold-gated fan-out + worker initializer. |
| **Game-data shape** | `GameDataBuilder._build_game_data` runs ~25 ms at every process startup. `_table_get` is a polymorphic dispatcher called ~72k times per `calc_player_stats` iteration. | E — persist normalized game_data via `GameDataCache`. F — typed-Struct game_data tables. G — direct consumption of v3.1 typed `/data` segments. H — hot-table index restructuring. |

## Pre-registered decision rule

Locked in **before** any prototype landed (per the
"research-first / measure-then-ship" discipline; the rule pre-empts
post-hoc rationalization). Each candidate ships iff it clears its
threshold AND parity passes byte-for-byte against the dict-baseline on
every cassette.

| Axis | Threshold |
|---|---|
| Input format | `dict_overhead ≤ 2 %` AND `struct_overhead ≤ 10 %`. If no candidate clears the Struct bar, ship Candidate A (floor option) and recommend `raw=True` for hot paths. |
| Parallelism | `parallel_speedup ≥ 2×` on 397-unit roster at optimal worker count AND `serial_path_regression ≤ 1 %`. |
| Game-data shape (cold-start: E) | `cold_start_improvement ≥ 50 %`. |
| Game-data shape (hot path: F, G, H) | `hot_path_improvement ≥ 10 %` AND `parallelism (D) regression ≤ 5 %`. |

F and G are mutually exclusive (F enhances `GameDataBuilder`; G
replaces it). E and H are additive with each other and with F/G.

## Measured outcomes

All numbers on the 397-unit `player_large` cassette unless noted.
Baseline `calc_player_stats` (dict path): **22.6 ms warm**.

### Input format

| Candidate | Struct overhead | Dict overhead | Verdict |
|---|---:|---:|---|
| **A. Full `to_builtins` adapter** | +22.9 % | 0 % | **SHIPS** (floor option) |
| B. Partial-conversion adapter | +21.4 % | 0 % | Defer (no win over A) |
| C. Accessor abstraction subclass | +23.6 % | 0 % | Defer (slightly worse than A) |

**Finding.** The bulk of the conversion cost is `msgspec.to_builtins`
on the per-Mod sub-Structs — all three candidates pay this cost
equivalently. B's "skip Player metadata" optimization saves only
~0.3 ms; C's "interleave with calc" hypothesis added isinstance
overhead that cancelled the win.

**All three failed the ≤ 10 % Struct-overhead threshold.** Under the
floor-option rule, Candidate A ships as the cleanest minimum-viable
bimorphic surface; the recipe (`docs/v3/recipes/typed-statcalc.md`)
documents `client.get_player(..., raw=True)` as the zero-overhead path
for hot loops.

Bug surfaced by parity testing during this work: the original audit
declared `RosterUnit.equipment` "always empty in cassettes." False —
GREATMOTHERS (a ship) carries 4 equipment pieces, and
`_get_crew_rating` reads `len(equipped)` for crew rating. The
prototype's partial-conversion adapter had to add `equipment` to
match GP and final stats. **Lesson recorded:** parity testing is
load-bearing; field-access audits lie.

### Parallelism

| Worker count | player_small (115u) | player_large (397u) |
|---|---:|---:|
| Serial | 3.24 ms | 21.59 ms |
| 2 workers | 2.78 ms (1.16×) | 26.84 ms (0.80×) |
| 4 workers | 2.02 ms (1.60×) | 25.40 ms (0.85×) |
| 8 workers | 2.41 ms (1.34×) | 25.94 ms (0.83×) |

**Verdict: D does not ship.** On `player_large`, parallel is
consistently *slower* than serial despite a counterintuitive win on
`player_small`. Root cause: Python `ProcessPoolExecutor` IPC
break-even (~500 µs/task even with batching) exceeds StatCalc's
per-unit work (~70 µs). The serial ship-pass tail (ships need
character results first) further eats into the parallel chars-pass
gain on large rosters.

D fails the `≥ 2×` speedup bar AND the `≤ 1 %` serial-regression bar
(adding the async surface adds ~1.5 % overhead even on the sync
fast-path). Deferred without ship.

### Game-data shape

| Candidate | Cold-start | Hot path | Verdict |
|---|---:|---:|---|
| **E. Cached normalized game_data** | 25.74 ms → 3.62 ms (**+85.9 %**) | 0 % | **SHIPS** |
| F. Typed-Struct tables | 0 % | est. 1.3 % (mechanism-bound) | Defer (no prototype) |
| G. Direct typed-segment consumption | est. 100 % (no rebuild) | est. -5 % to +10 % | Defer (no prototype) |
| H. Hot-table index restructuring | 0 % | +5.7 % | Defer |

**E ships.** Cleared the ≥ 50 % cold-start threshold with margin. Cuts
process startup from ~26 ms to ~4 ms by persisting the normalized form
alongside the raw `/data` payload via `GameDataCache`. Major win for
cron jobs, lambdas, CLI invocations.

**H deferred.** Targeted variant (pre-alias 7 hottest CR tables;
pre-flatten the `(pips, level)` mod-rarity lookup; lightweight
`_table_get` override) delivered 5.7 % — below the 10 % bar. An
aggressive variant (`_normalize_nested_dict_keys` recursive
normalization + dict-only `_table_get`) delivered 8-15 % but **broke
parity** on units with mod-set bonuses (Strength 451 → 368 on
GREATMOTHERS). The bug is somewhere in nested-key normalization
conflicting with mixed str/int key access elsewhere in the codebase.
The plan's "low effort" estimate for H did not anticipate that
debugging cost.

**F deferred without prototyping.** A micro-bench established that
msgspec Struct attribute access saves only ~3.8 ns per call vs
`dict.get`. At 72k `_table_get` calls per iter, that yields ~0.28 ms
savings on a 22 ms baseline = 1.3 % improvement. The plan's 10-20 %
estimate was off by an order of magnitude. Mechanism-bound below
threshold.

**G deferred without prototyping.** Higher refactor cost than F
(rewrite every internal table lookup to traverse the typed `/data`
Struct graph), with the plan's own estimated payoff range of "-5 % to
+10 %" suggesting it could *regress* performance. The pattern of
candidate overestimation across the plan + the mechanism analysis from
F's micro-bench together argue G would not deliver. Effort:payoff
ratio rules it out.

## What ships in v3.2

Two changes land on `v3.2-research`:

1. **Candidate A** — `StatCalc.calc_player_stats` and
   `StatCalc.calc_roster_stats` accept either a Comlink-format dict
   tree OR a `msgspec.Struct` (single `Player` or list of `Player`,
   single `RosterUnit` list, etc.). Conversion happens once at the
   boundary via `msgspec.to_builtins`; everything downstream stays
   dict-only.

2. **Candidate E** — `from swgoh_comlink.StatCalc import
   get_statcalc_game_data`. Drop-in helper that takes a client + a
   `GameDataCache` and returns the normalized game_data ready to hand
   to `StatCalc(game_data=...)`. On cold start, builds + persists.
   On every subsequent process, msgpack-decodes from disk
   (~4 ms vs ~26 ms cold).

Parity tests live at `tests/unit/test_statcalc_v3_2.py` — assert
byte-identical per-unit stats and GP for both shipped surfaces against
the dict-baseline on every cassette.

## Rejected alternatives (explicit)

- **Candidate B / C** (partial / accessor input adapters). Don't beat
  A — measured. Conversion cost is dominated by per-Mod
  `to_builtins`, which all three pay. Carrying additional candidate
  modules for ~1 % margin would have been pure complexity.
- **Candidate D** (`ProcessPoolExecutor`). IPC break-even exceeds
  per-unit work. Regresses on `player_large` despite winning on
  `player_small` — wrong shape for this workload. Defer until either
  per-unit work grows (e.g. Cython inner loops shipped) OR Python's
  IPC cost shrinks (sub-interpreters, free-threaded build).
- **Candidate F / G / H** (game-data hot-path reshape). None cleared
  the 10 % hot-path bar. F's mechanism is bounded below threshold; G
  has higher cost than F with negative-bound payoff; H's targeted
  variant misses, aggressive variant breaks parity.
- **Cython / Rust / native acceleration** of inner math loops. Out of
  scope; will revisit only when caller demand data warrants a v3.3
  conversation.
- **`StatCalc/` → `statcalc/` PEP 8 rename.** Sibling effort; doesn't
  interact with the bimorphic / parallelism / game-data work; cleaner
  to land independently.

## Process notes

- One integration branch (`v3.2/statcalc-final-integration`) lands
  ONLY the winning candidates. Throwaway prototype branches
  (`v3.2/statcalc-{bimorphic-prototypes,prototype-d,prototype-efgh}`)
  stay around for reference and do not merge.
- Every plan estimate proved optimistic. Across Phases 2-4, none of
  the eight candidates exceeded its plan-stated estimate — six fell
  short or failed entirely. The honest pre-registered decision rules
  saved us from shipping things that didn't pay back.
- Branch ordering: `v3.1-research` ← `v3.2-research` ← phase
  branches. `v3.0-dev` remains frozen per ADR-0001.
