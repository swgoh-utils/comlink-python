# coding=utf-8
"""v3.2 / v3.3 — StatCalc benchmark harness.

Originally landed in v3.2 Phase 1 as a 3-axis grid (input format ×
game-data shape × execution). v3.3 Phase 1 extends it with two more
axes that the v3.3 rewrite-research plan needs to gate its decision
rule on:

* **Memory axis (new in v3.3).** Records resident game_data RAM
  (via :mod:`tracemalloc` + :func:`pympler.asizeof`) and per-roster
  transient allocation peak. Drives the v3.3 ≥ 20 % memory-reduction
  bar.
* **Ergonomics axis (new in v3.3).** Standalone micro-bench of
  ``msgspec.to_builtins(roster_unit)`` at 1 / 6 / 50 / all-Mod counts,
  so the per-Mod conversion cost is visible separate from StatCalc's
  math. Drives the v3.3 ≤ 5 % bimorphic-Struct-overhead bar.
* **cProfile bimorphic dump (new in v3.3).** v3.2 dumped attribution
  for the dict path; v3.3 also dumps for the bimorphic Struct path so
  Phase 4b's typed-fastpath has a clear baseline to attack.

Existing v3.2 axes (all preserved):

* **Input format**
  - ``dict_baseline`` — current dict-only path (the v3.1 baseline).
  - ``struct_full_adapter`` — typed Player + ``msgspec.to_builtins`` (A, shipped).
  - ``struct_partial_adapter`` — stub (v3.2 Candidate B, deferred).
  - ``struct_accessor`` — stub (v3.2 Candidate C, deferred).

* **Game data shape**
  - ``legacy_dict_tables`` — current ``GameDataBuilder`` output.
  - ``cached_normalized`` — v3.2 Candidate E (shipped).
  - ``typed_structs`` / ``direct_segments`` / ``flat_indexed`` — stubs.

* **Execution**
  - ``serial`` — current single-threaded path.
  - ``parallel_{2,4,8}`` — stubs (v3.2 Candidate D, deferred).

Player sizes: ``player_small`` (115 units) + ``player_large`` (397).

Iterations: 20 warm + 7 measured per cell. Memory and speed
measurements run in separate passes — :mod:`tracemalloc` overhead
distorts timing.

Cold-start (one-time): the ``GameDataBuilder`` → ``StatCalc`` pipeline
is timed separately so Candidate E (cached normalized form) can prove
its cold-start win against this baseline.

Writes ``benchmarks/v3/results/phase-v3_3-baseline.json`` (was
``phase-v3_2-statcalc-baseline.json`` in v3.2; the renamed file makes
the v3.3 baseline a new artefact while leaving the v3.2 numbers
unchanged on disk).

Run with::

    uv run python -m benchmarks.v3.bench_statcalc
"""

from __future__ import annotations

import cProfile
import gzip
import io
import json
import pstats
import sys
import time
from collections.abc import Callable
from typing import Any

import msgspec

from benchmarks.v3._harness import (
    Reporter,
    cassette_exists,
    measure,
    require_python_version,
)
from benchmarks.v3._memory import measure_resident, peak_transient
from swgoh_comlink._models import PLAYER_DECODER  # noqa: E402
from swgoh_comlink.StatCalc import StatCalc  # noqa: E402
from swgoh_comlink.StatCalc.data_builder._builder_base import (  # noqa: E402
    GameDataBuilderBase,
)

# ── Constants ───────────────────────────────────────────────────────────────

PLAYER_SIZES = ("player_small", "player_large")
WARMUP = 20
ITERS = 7
PARALLEL_WORKER_COUNTS = (2, 4, 8)


# ── Cassette + game-data loading ────────────────────────────────────────────


def _load_player(name: str) -> tuple[bytes, dict[str, Any], Any]:
    """Return (json bytes, dict shape, typed Struct) for cassette *name*."""
    path = f"benchmarks/v3/fixtures/{name}.json.gz"
    with gzip.open(path, "rb") as fh:
        body = fh.read()
    return body, json.loads(body), PLAYER_DECODER.decode(body)


def _normalized_game_data() -> dict[str, Any]:
    """Build the legacy normalized game_data once."""
    with gzip.open("benchmarks/v3/fixtures/data.json.gz", "rb") as fh:
        raw = json.load(fh)
    return GameDataBuilderBase._build_game_data(raw)


# ── Measurement helpers ─────────────────────────────────────────────────────


def _median_ms(fn: Callable[[], Any], warmup: int = WARMUP, iters: int = ITERS) -> float:
    for _ in range(warmup):
        fn()
    result = measure(fn, warmup=0, iters=iters)
    return float(result.median_ns / 1e6)


def _profile_dump(fn: Callable[[], Any], top_n: int = 20) -> str:
    """Run *fn* under cProfile, return the top-N by cumulative time."""
    pr = cProfile.Profile()
    pr.enable()
    for _ in range(5):
        fn()
    pr.disable()
    buf = io.StringIO()
    stats = pstats.Stats(pr, stream=buf).sort_stats("cumulative")
    stats.print_stats(top_n)
    return buf.getvalue()


# ── Bench cells ─────────────────────────────────────────────────────────────


def _bench_input_format(
    rep: Reporter,
    sc: StatCalc,
    player_dict: dict[str, Any],
    player_struct: Any,
    size: str,
) -> None:
    """Measure the four input-format paths."""

    # dict_baseline — the v3.1 floor
    dict_ms = _median_ms(lambda: sc.calc_player_stats(player_dict))
    rep.add(
        f"calc_player_stats_{size}_input_format_dict_baseline",
        value=dict_ms,
        unit="ms",
        axis="input_format",
        candidate="dict_baseline",
        size=size,
    )

    # struct_full_adapter (A) — measurable today
    adapter_ms = _median_ms(lambda: sc.calc_player_stats(msgspec.to_builtins(player_struct)))
    rep.add(
        f"calc_player_stats_{size}_input_format_struct_full_adapter",
        value=adapter_ms,
        unit="ms",
        axis="input_format",
        candidate="struct_full_adapter",
        size=size,
        overhead_pct=(adapter_ms / dict_ms - 1) * 100,
    )

    # struct_partial_adapter (B) and struct_accessor (C) — stubs.
    for stub in ("struct_partial_adapter", "struct_accessor"):
        rep.add(
            f"calc_player_stats_{size}_input_format_{stub}",
            value=None,
            unit="ms",
            status="skip",
            reason="candidate not implemented yet (Phase 2)",
            axis="input_format",
            candidate=stub,
            size=size,
        )

    sys.stderr.write(
        f"  [{size}] input_format: dict={dict_ms:7.2f} ms  adapter={adapter_ms:7.2f} ms  "
        f"(+{(adapter_ms / dict_ms - 1) * 100:.1f}%)\n"
    )


def _bench_game_data_shape(
    rep: Reporter,
    sc: StatCalc,
    player_dict: dict[str, Any],
    size: str,
) -> None:
    """Measure the legacy game-data shape; stub the four candidates."""
    # legacy_dict_tables — current production
    ms = _median_ms(lambda: sc.calc_player_stats(player_dict))
    rep.add(
        f"calc_player_stats_{size}_game_data_legacy_dict_tables",
        value=ms,
        unit="ms",
        axis="game_data_shape",
        candidate="legacy_dict_tables",
        size=size,
    )

    for stub in (
        "cached_normalized",
        "typed_structs",
        "direct_segments",
        "flat_indexed",
    ):
        rep.add(
            f"calc_player_stats_{size}_game_data_{stub}",
            value=None,
            unit="ms",
            status="skip",
            reason="candidate not implemented yet (Phase 4)",
            axis="game_data_shape",
            candidate=stub,
            size=size,
        )


def _bench_execution(
    rep: Reporter,
    sc: StatCalc,
    player_dict: dict[str, Any],
    size: str,
) -> None:
    """Measure serial execution; stub the parallel workers."""
    ms = _median_ms(lambda: sc.calc_player_stats(player_dict))
    rep.add(
        f"calc_player_stats_{size}_execution_serial",
        value=ms,
        unit="ms",
        axis="execution",
        candidate="serial",
        size=size,
    )

    for workers in PARALLEL_WORKER_COUNTS:
        rep.add(
            f"calc_player_stats_{size}_execution_parallel_{workers}_workers",
            value=None,
            unit="ms",
            status="skip",
            reason="candidate not implemented yet (Phase 3)",
            axis="execution",
            candidate=f"parallel_{workers}_workers",
            workers=workers,
            size=size,
        )


def _bench_memory_game_data(rep: Reporter, raw_data: dict[str, Any]) -> None:
    """Record resident game_data size for the legacy dict shape.

    Stubs the same candidate axis as :func:`_bench_game_data_shape`
    so Phase 4 prototypes can plug in their alternative shapes.
    v3.3 ≥ 20 % game_data RAM reduction is the pre-registered bar.
    """
    sized = measure_resident(lambda: GameDataBuilderBase._build_game_data(raw_data))
    rep.add(
        "game_data_resident_legacy_dict_tables",
        value=sized.best,
        unit="bytes",
        axis="memory",
        candidate="legacy_dict_tables",
        tracemalloc_bytes=sized.tracemalloc_bytes,
        asizeof_bytes=sized.asizeof_bytes,
    )
    sys.stderr.write(
        f"  game_data resident (legacy dict): "
        f"asizeof={sized.asizeof_bytes / 1024 / 1024 if sized.asizeof_bytes else 0:.1f} MB  "
        f"tracemalloc={sized.tracemalloc_bytes / 1024 / 1024:.1f} MB\n"
    )

    for stub in ("cached_normalized", "typed_structs", "direct_segments", "flat_indexed"):
        rep.add(
            f"game_data_resident_{stub}",
            value=None,
            unit="bytes",
            status="skip",
            reason="candidate not implemented yet (v3.3 Phase 2-4)",
            axis="memory",
            candidate=stub,
        )


def _bench_memory_transient(
    rep: Reporter,
    sc: StatCalc,
    player_dict: dict[str, Any],
    size: str,
) -> None:
    """Per-roster transient allocation peak for `calc_player_stats`.

    Informational (no pre-registered bar). A copy-heavy rewrite would
    show up here as a peak spike vs the v3.2 baseline.
    """
    # Re-parse the player JSON each iteration — calc_player_stats
    # mutates in place, and we want to measure a fresh-input call.
    body = json.dumps(player_dict).encode()

    def _one() -> None:
        sc.calc_player_stats(json.loads(body))

    peak = peak_transient(_one)
    rep.add(
        f"calc_player_stats_{size}_transient_peak_legacy_dict",
        value=peak.peak_bytes,
        unit="bytes",
        axis="memory",
        candidate="dict_baseline",
        size=size,
        residual_bytes=peak.residual_bytes,
    )
    sys.stderr.write(
        f"  [{size}] transient peak: {peak.peak_bytes / 1024 / 1024:.2f} MB  "
        f"(residual {peak.residual_bytes / 1024:.1f} KB)\n"
    )


def _bench_ergonomics_to_builtins(
    rep: Reporter,
    player_struct: Any,
    size: str,
) -> None:
    """Standalone per-RosterUnit `msgspec.to_builtins` micro-bench.

    v3.2 Candidate A's +22.9 % overhead is almost entirely this
    function called once per Mod (and per unit). v3.3 Phase 4b
    (typed-fastpath) attacks this cost directly; measuring it in
    isolation tells us how much budget is available.

    Records per-call cost at 4 Mod counts:
    1 mod, 6 mods (typical), 50 mods (heavy roster slice), and full
    roster (the v3.2 bimorphic path's actual load).
    """
    roster: list[Any] = list(player_struct.roster_unit)
    sys.stderr.write(f"  [{size}] ergonomics — per-RosterUnit to_builtins cost:\n")

    sample_sizes = (1, 6, 50, len(roster))
    for take in sample_sizes:
        if take > len(roster):
            continue
        sample = roster[:take]

        def _convert(_sample: list[Any] = sample) -> None:
            for u in _sample:
                msgspec.to_builtins(u)

        ms = _median_ms(_convert)
        per_unit_us = (ms * 1000) / max(1, take)
        rep.add(
            f"to_builtins_{size}_n{take}",
            value=ms,
            unit="ms",
            axis="ergonomics",
            candidate="to_builtins_baseline",
            size=size,
            sample_count=take,
            per_unit_us=per_unit_us,
        )
        sys.stderr.write(f"    n={take:3d}: {ms:7.3f} ms  ({per_unit_us:.2f} µs/unit)\n")


def _bench_cprofile_bimorphic(
    rep: Reporter,
    sc: StatCalc,
    player_struct: Any,
) -> None:
    """Dump cProfile attribution for the v3.2-shipped BIMORPHIC path
    (Struct input → boundary conversion → calc_player_stats).

    The v3.2 dict-path attribution lives in
    ``_bench_cprofile_attribution``; this is the typed-input twin.
    Phase 4b's typed-fastpath uses this dump to identify which Struct→
    dict conversion calls dominate the per-roster cost.
    """

    def _bimorphic() -> None:
        sc.calc_player_stats(player_struct)

    dump = _profile_dump(_bimorphic, top_n=25)
    rep.add(
        "cprofile_attribution_bimorphic_struct_player_large",
        value=None,
        unit="text",
        cprofile_top_25=dump,
        scenario="cumulative-time breakdown for 5 iters of calc_player_stats(Player_struct) — v3.2 Candidate A path",
    )
    sys.stderr.write("\n--- cProfile attribution (bimorphic Struct, player_large, 5 iters) ---\n")
    sys.stderr.write(dump)


def _bench_cold_start(rep: Reporter, raw_data: dict[str, Any]) -> None:
    """Time the full GameDataBuilder → StatCalc(game_data=…) cold pipeline.

    Candidate E (cached normalized form) targets this number; today
    every process pays it on startup.
    """

    def cold() -> None:
        gd = GameDataBuilderBase._build_game_data(raw_data)
        StatCalc(game_data=gd)

    samples_ms: list[float] = []
    for _ in range(5):
        t0 = time.perf_counter_ns()
        cold()
        samples_ms.append((time.perf_counter_ns() - t0) / 1e6)
    samples_ms.sort()
    median_ms = samples_ms[len(samples_ms) // 2]
    rep.add(
        "cold_start_game_data_builder_plus_statcalc_init",
        value=median_ms,
        unit="ms",
        samples_ms=samples_ms,
        scenario="cold: GameDataBuilder._build_game_data() + StatCalc(game_data=...) per process startup",
    )
    sys.stderr.write(f"  cold-start (GameDataBuilder + StatCalc init): {median_ms:.2f} ms\n")


def _bench_cprofile_attribution(
    rep: Reporter,
    sc: StatCalc,
    player_dict: dict[str, Any],
) -> None:
    """Dump cProfile attribution for the dict baseline (large player only)."""
    dump = _profile_dump(lambda: sc.calc_player_stats(player_dict), top_n=25)
    rep.add(
        "cprofile_attribution_dict_baseline_player_large",
        value=None,
        unit="text",
        cprofile_top_25=dump,
        scenario="cumulative-time breakdown for 5 iterations of calc_player_stats(dict)",
    )
    sys.stderr.write("\n--- cProfile attribution (player_large, 5 iters) ---\n")
    sys.stderr.write(dump)


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> int:
    require_python_version()
    rep = Reporter(phase="phase-v3_3-baseline")

    if not cassette_exists("data"):
        sys.stderr.write("SKIP: /data cassette missing — run benchmarks.v3._record\n")
        rep.add("statcalc_bench", value=None, unit="status", status="skip")
        rep.write()
        return 1

    sys.stderr.write("--- v3.2 + v3.3 StatCalc benchmark harness ---\n\n")

    sys.stderr.write("Loading + building game_data (one-time setup)...\n")
    with gzip.open("benchmarks/v3/fixtures/data.json.gz", "rb") as fh:
        raw_data = json.load(fh)
    game_data = GameDataBuilderBase._build_game_data(raw_data)
    sc = StatCalc(game_data=game_data)

    # Cold-start measurement
    _bench_cold_start(rep, raw_data)
    sys.stderr.write("\n")

    # ── PASS 1: speed-sensitive measurements (tracemalloc OFF) ─────────────
    sys.stderr.write("--- Pass 1: timing (tracemalloc off) ---\n\n")
    for size in PLAYER_SIZES:
        if not cassette_exists(size):
            sys.stderr.write(f"  SKIP {size}: cassette missing\n")
            continue
        _body, player_dict, player_struct = _load_player(size)
        sys.stderr.write(f"--- {size} ({len(player_dict.get('rosterUnit', []))} units) ---\n")

        # Warm StatCalc once for this player (caches internal lookups)
        sc.calc_player_stats(player_dict)

        _bench_input_format(rep, sc, player_dict, player_struct, size)
        _bench_game_data_shape(rep, sc, player_dict, size)
        _bench_execution(rep, sc, player_dict, size)
        _bench_ergonomics_to_builtins(rep, player_struct, size)
        sys.stderr.write("\n")

    # ── PASS 2: memory-sensitive measurements (tracemalloc ON) ─────────────
    #
    # tracemalloc adds 5-30% overhead to tracked allocations; running
    # it in the same pass as timing would skew the numbers we just
    # recorded. Do all memory work here, in its own pass.
    sys.stderr.write("--- Pass 2: memory (tracemalloc on; speed numbers in pass 1) ---\n\n")
    _bench_memory_game_data(rep, raw_data)
    for size in PLAYER_SIZES:
        if not cassette_exists(size):
            continue
        _body, player_dict, _struct = _load_player(size)
        _bench_memory_transient(rep, sc, player_dict, size)
    sys.stderr.write("\n")

    # cProfile attribution (large player only — small one is too short
    # to be informative). Two dumps: dict baseline + v3.2 bimorphic
    # Struct path.
    if cassette_exists("player_large"):
        _, player_dict_large, player_struct_large = _load_player("player_large")
        _bench_cprofile_attribution(rep, sc, player_dict_large)
        _bench_cprofile_bimorphic(rep, sc, player_struct_large)

    dest = rep.write()
    sys.stderr.write(f"\nWrote {dest}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
