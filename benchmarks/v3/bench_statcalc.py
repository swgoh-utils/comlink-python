# coding=utf-8
"""v3.2 — StatCalc benchmark harness (3-axis grid).

Phase 1 deliverable. The harness measures `calc_player_stats` across
three orthogonal axes — input format, game-data shape, and execution
mode — so subsequent v3.2 phases can prototype candidates against a
canonical baseline.

Axes (all measured today; stubs for candidates that don't exist yet):

* **Input format**
  - ``dict_baseline`` — current dict-only path (the v3.1 baseline).
  - ``struct_full_adapter`` — typed Player + ``msgspec.to_builtins`` (A).
  - ``struct_partial_adapter`` — stub until Candidate B exists.
  - ``struct_accessor`` — stub until Candidate C exists.

* **Game data shape**
  - ``legacy_dict_tables`` — current ``GameDataBuilder`` output.
  - ``cached_normalized`` — stub until Candidate E exists.
  - ``typed_structs`` — stub until Candidate F exists.
  - ``direct_segments`` — stub until Candidate G exists.
  - ``flat_indexed`` — stub until Candidate H exists.

* **Execution**
  - ``serial`` — current single-threaded path.
  - ``parallel_{2,4,8}`` — stubs until Candidate D exists.

Player sizes: ``player_small`` (115 units) + ``player_large`` (397).

Iterations: 20 warm + 7 measured per cell.

Cold-start (one-time): the ``GameDataBuilder`` → ``StatCalc`` pipeline
is timed separately so Candidate E (cached normalized form) can prove
its cold-start win against this baseline.

cProfile attribution: the dict baseline gets a cProfile dump so Phase
4 Candidate H (flat-index restructuring) knows which fields to
flatten.

Writes ``benchmarks/v3/results/phase-v3_2-statcalc-baseline.json``.

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
    rep = Reporter(phase="phase-v3_2-statcalc-baseline")

    if not cassette_exists("data"):
        sys.stderr.write("SKIP: /data cassette missing — run benchmarks.v3._record\n")
        rep.add("statcalc_bench", value=None, unit="status", status="skip")
        rep.write()
        return 1

    sys.stderr.write("--- v3.2 StatCalc benchmark harness ---\n\n")

    sys.stderr.write("Loading + building game_data (one-time setup)...\n")
    with gzip.open("benchmarks/v3/fixtures/data.json.gz", "rb") as fh:
        raw_data = json.load(fh)
    game_data = GameDataBuilderBase._build_game_data(raw_data)
    sc = StatCalc(game_data=game_data)

    # Cold-start measurement
    _bench_cold_start(rep, raw_data)
    sys.stderr.write("\n")

    # Per-size benchmarks
    for size in PLAYER_SIZES:
        if not cassette_exists(size):
            sys.stderr.write(f"  SKIP {size}: cassette missing\n")
            continue
        body, player_dict, player_struct = _load_player(size)
        sys.stderr.write(f"--- {size} ({len(player_dict.get('rosterUnit', []))} units) ---\n")

        # Warm StatCalc once for this player (caches internal lookups)
        sc.calc_player_stats(player_dict)

        _bench_input_format(rep, sc, player_dict, player_struct, size)
        _bench_game_data_shape(rep, sc, player_dict, size)
        _bench_execution(rep, sc, player_dict, size)
        sys.stderr.write("\n")

    # cProfile attribution (large player only — small one is too short to be informative)
    if cassette_exists("player_large"):
        _, player_dict_large, _ = _load_player("player_large")
        _bench_cprofile_attribution(rep, sc, player_dict_large)

    dest = rep.write()
    sys.stderr.write(f"\nWrote {dest}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
