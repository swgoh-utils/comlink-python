"""Time StatCalc.calc_player_stats on the committed fixture roster.

Usage:

    uv run python parity/scripts/bench_statcalc.py [--runs N] [--profile]

Each timed run works on a fresh ``copy.deepcopy`` of the 386-unit fixture player; the copy is
made outside the timed section. Not wired into CI: shared runners are too noisy for timing gates.
"""

from __future__ import annotations

import argparse
import copy
import cProfile
import json
import math
import platform
import pstats
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from swgoh_comlink import StatCalc

ROOT = Path(__file__).resolve().parents[2]
GAMEDATA_FILE = ROOT / "tests" / "resources" / "gameData.json"
PLAYER_FILE = ROOT / "tests" / "resources" / "example-player.json"
PROFILE_TOP = 15


def _percentile(samples: list[float], pct: float) -> float:
    """Nearest-rank percentile of *samples*."""
    ordered = sorted(samples)
    return ordered[max(math.ceil(pct / 100 * len(ordered)) - 1, 0)]


def _time_runs(calc: StatCalc, player: dict[str, Any], runs: int) -> list[float]:
    """Return the duration of each run in milliseconds, excluding the roster copy."""
    timings: list[float] = []
    for _ in range(runs):
        payload = copy.deepcopy(player)
        start = time.perf_counter()
        calc.calc_player_stats(payload)
        timings.append((time.perf_counter() - start) * 1000)
    return timings


def _profile_run(calc: StatCalc, player: dict[str, Any]) -> None:
    payload = copy.deepcopy(player)
    profiler = cProfile.Profile()
    profiler.runcall(calc.calc_player_stats, payload)
    print(f"\nTop {PROFILE_TOP} functions by tottime (one profiled run):")
    pstats.Stats(profiler, stream=sys.stdout).strip_dirs().sort_stats(pstats.SortKey.TIME).print_stats(PROFILE_TOP)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=20, help="timed runs (default: 20)")
    parser.add_argument("--profile", action="store_true", help=f"also print the top {PROFILE_TOP} functions by tottime")
    args = parser.parse_args(argv)
    if args.runs < 1:
        parser.error("--runs must be at least 1")

    game_data = json.loads(GAMEDATA_FILE.read_text())["data"]
    player = json.loads(PLAYER_FILE.read_text())
    calc = StatCalc(game_data=game_data)

    calc.calc_player_stats(copy.deepcopy(player))  # warm-up
    timings = _time_runs(calc, player, args.runs)

    print(f"Python:   {platform.python_implementation()} {platform.python_version()}")
    print(f"Platform: {platform.platform()} ({platform.machine()})")
    print(f"Roster:   {len(player['rosterUnit'])} units ({PLAYER_FILE.relative_to(ROOT)})")
    print(f"Runs:     {args.runs} (after 1 warm-up)")
    print(f"Median:   {statistics.median(timings):.2f} ms")
    print(f"p95:      {_percentile(timings, 95):.2f} ms")
    print(f"Min/max:  {min(timings):.2f} / {max(timings):.2f} ms")

    if args.profile:
        _profile_run(calc, player)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
