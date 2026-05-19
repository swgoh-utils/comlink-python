# coding=utf-8
"""v3.3 — shared memory-measurement helpers for bench scripts.

The v3.3 StatCalc rewrite plan adds a memory axis to the existing
benchmark harness (see ``benchmarks/v3/bench_statcalc.py``). Two
quantities matter:

1. **Resident game_data size.** How big is the normalized game_data
   tree once :class:`~swgoh_comlink.StatCalc.StatCalc` finishes
   initialising? This is the one-time RAM cost a caller pays for a
   live StatCalc instance. Targeted by the v3.3 ≥ 20 % reduction bar.

2. **Per-roster transient peak.** How much additional allocation does
   a single ``calc_player_stats(player_large)`` invocation churn
   through? Informational only — no pre-registered bar, but useful
   for spotting accidental quadratic behaviour or copy-heavy
   intermediates a rewrite might introduce.

This module wraps :mod:`tracemalloc` (always-available stdlib;
allocator-level so it sees everything Python does) and cross-checks
with :func:`pympler.asizeof.asizeof` (slow but deep; walks the entire
object graph) on a single final snapshot.

**Important measurement hygiene** — :mod:`tracemalloc` adds 5-30 %
overhead to allocations it tracks, so memory and speed must NOT be
measured in the same pass. Speed measurements run with tracemalloc
off; memory measurements run in a separate pass.

API:

* :func:`measure_resident(callable)` — run *callable*, return the
  resident size of its result (or whatever the caller designates as
  "the kept object"). Pairs an internal :func:`tracemalloc`
  snapshot-delta with a single :func:`pympler.asizeof.asizeof` walk
  for cross-check.
* :func:`peak_transient(callable)` — run *callable* with
  :func:`tracemalloc.start` → ``get_traced_memory`` to capture the
  transient peak allocation observed during the call. Returns
  ``(peak_bytes, current_bytes_at_exit)``.
"""

from __future__ import annotations

import gc
import tracemalloc
from collections.abc import Callable
from typing import Any, NamedTuple

try:
    from pympler import asizeof as _pympler_asizeof

    _HAVE_PYMPLER = True
except ImportError:  # pragma: no cover — pympler is a dev dep
    _HAVE_PYMPLER = False


class ResidentSize(NamedTuple):
    """Two independent measurements of an object's resident size.

    Both numbers should be in the same ballpark; large divergence
    (> 30 %) suggests the wrong object is being measured (e.g. a
    shallow view vs the underlying buffer).
    """

    tracemalloc_bytes: int
    """Delta of allocator-tracked bytes from before to after the call.
    Counts everything :mod:`tracemalloc` saw allocated and didn't see
    freed. Sensitive to GC timing; we call :func:`gc.collect` before
    snapshotting to minimise transient survivors."""

    asizeof_bytes: int | None
    """Deep-walk size of the kept object via :func:`pympler.asizeof`.
    Counts every reachable object's :func:`sys.getsizeof` recursively,
    deduplicating by ``id``. ``None`` if pympler isn't installed
    (it's a dev-dep, not a runtime dep)."""

    @property
    def best(self) -> int:
        """Prefer ``asizeof`` (deeper, more accurate for the
        as-laid-out-in-memory question); fall back to ``tracemalloc``."""
        if self.asizeof_bytes is not None:
            return self.asizeof_bytes
        return self.tracemalloc_bytes


class TransientPeak(NamedTuple):
    """Peak observed transient allocation across a callable's lifetime.

    ``peak_bytes`` is the high-water mark of tracemalloc-tracked
    allocations during the call; ``residual_bytes`` is what's left
    allocated at exit (any objects the call returned or stored).
    Big residual + small peak: the call kept most of its allocations.
    Small residual + large peak: the call churned (intermediates were
    freed before exit).
    """

    peak_bytes: int
    residual_bytes: int


def measure_resident(builder: Callable[[], Any]) -> ResidentSize:
    """Run *builder*, return the resident size of its return value.

    Calls :func:`gc.collect` before + after to keep cycle-collectable
    survivors out of the delta. Disables :mod:`tracemalloc` for the
    pympler walk (its tracking would otherwise inflate the deep-size
    measurement).
    """
    gc.collect()
    tracemalloc.start()
    before = tracemalloc.get_traced_memory()[0]
    result = builder()
    gc.collect()
    after = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    tm_delta = max(0, after - before)

    asizeof_bytes: int | None = None
    if _HAVE_PYMPLER:
        # pympler.asizeof is O(reachable objects) and can take seconds
        # on a 50-100 MB game_data tree. The bench harness only
        # invokes this helper once per candidate, so the cost is
        # acceptable.
        asizeof_bytes = int(_pympler_asizeof.asizeof(result))  # type: ignore[no-untyped-call]

    return ResidentSize(tracemalloc_bytes=tm_delta, asizeof_bytes=asizeof_bytes)


def peak_transient(callable_: Callable[[], Any]) -> TransientPeak:
    """Run *callable_*, return ``(peak_bytes, residual_bytes)`` observed
    during the call.

    Wraps :func:`tracemalloc.start` → invoke → ``get_traced_memory()``.
    No pympler cross-check — the transient peak is inherently a
    sample-over-time measurement and pympler only gives a single
    point-in-time deep walk.
    """
    gc.collect()
    tracemalloc.start()
    callable_()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return TransientPeak(peak_bytes=peak, residual_bytes=current)


__all__ = [
    "ResidentSize",
    "TransientPeak",
    "measure_resident",
    "peak_transient",
]
