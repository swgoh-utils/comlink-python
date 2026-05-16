# coding=utf-8
"""Phase 3 — Decode memory across parsers (tracemalloc peak).

Per the Phase 3 plan: typed msgspec should hit **4-6x** lower peak
memory than stdlib ``json`` on ``/data``. Each parser × cassette pair
is measured under its own ``tracemalloc.start()`` so the numbers are
independent.

Writes results to ``benchmarks/v3/results/phase-3-decode-memory.json``.
"""

from __future__ import annotations

import gc
import json
import sys
import tracemalloc
from collections.abc import Callable
from typing import Any

from benchmarks.v3._harness import (
    Reporter,
    cassette_exists,
    load_cassette,
    require_python_version,
)
from swgoh_comlink._models import (
    LEADERBOARD_DECODER,
    METADATA_DECODER,
    PLAYER_DECODER,
    UNTYPED_DECODER,
    decode_guild,
)

try:
    import orjson  # type: ignore[import-untyped]

    _HAS_ORJSON = True
except ImportError:
    _HAS_ORJSON = False


_TYPED_DECODER_FOR: dict[str, Callable[[bytes], Any]] = {
    "metadata": METADATA_DECODER.decode,
    "player_small": PLAYER_DECODER.decode,
    "player_large": PLAYER_DECODER.decode,
    "guild": decode_guild,
    "leaderboard": LEADERBOARD_DECODER.decode,
}


def _peak_memory_for(decode: Callable[[bytes], Any], body: bytes) -> int:
    """Return peak allocation in bytes for one decode call."""
    gc.collect()
    tracemalloc.start()
    try:
        decoded = decode(body)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    del decoded
    gc.collect()
    return int(peak)


def main() -> int:
    require_python_version()
    rep = Reporter(phase="phase-3-decode-memory")

    cassettes = ["metadata", "guild", "leaderboard", "player_small", "player_large", "data"]
    for cassette in cassettes:
        if not cassette_exists(cassette):
            continue
        body = load_cassette(cassette)
        sys.stderr.write(f"--- {cassette}  ({len(body) / 1024:.1f} KiB decoded) ---\n")

        parsers: list[tuple[str, Callable[[bytes], Any]]] = [
            ("json", json.loads),
            ("msgspec_untyped", UNTYPED_DECODER.decode),
        ]
        if cassette in _TYPED_DECODER_FOR:
            parsers.append(("msgspec_typed", _TYPED_DECODER_FOR[cassette]))
        if _HAS_ORJSON:
            parsers.append(("orjson", orjson.loads))

        baseline: int | None = None
        for label, fn in parsers:
            peak = _peak_memory_for(fn, body)
            rep.add(
                f"decode_memory_{cassette}_{label}",
                value=peak,
                unit="bytes",
                cassette=cassette,
                parser=label,
            )
            mib = peak / 1024 / 1024
            if label == "json":
                baseline = peak
                sys.stderr.write(f"  {label:18s}  {mib:8.2f} MiB  (baseline)\n")
            else:
                ratio = baseline / peak if baseline and peak else 0
                sys.stderr.write(f"  {label:18s}  {mib:8.2f} MiB  ({ratio:.2f}x lower vs json)\n")

    dest = rep.write()
    sys.stderr.write(f"\nWrote {dest}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
