# coding=utf-8
"""Phase 3 — Decode speed across parsers.

For each cassette × parser, measure decode time:

* ``json`` (stdlib)
* ``msgspec.json`` untyped
* ``msgspec.json`` typed (where a Struct is defined)
* ``orjson`` (optional; skipped if not installed)

Phase 3 headline projections:
* On ``/data`` the typed msgspec path is expected to be **3-5x** faster
  than stdlib ``json``. If msgspec-typed comes in slower than
  msgspec-untyped that's a red flag — the Struct schema has
  ``dict[str, Any]`` fields defeating the optimization.
* Other cassettes get a smaller but still meaningful win.

Writes results to ``benchmarks/v3/results/phase-3-decode-speed.json``.
"""

from __future__ import annotations

import importlib
import json
import sys
from collections.abc import Callable
from typing import Any

from benchmarks.v3._harness import (
    Reporter,
    cassette_exists,
    load_cassette,
    measure,
    require_python_version,
)

# Optional comparison
# orjson is an optional comparator (not a project dependency), so it is
# loaded dynamically rather than imported statically.
try:
    _orjson_loads: Callable[[bytes], Any] | None = importlib.import_module("orjson").loads
except ImportError:
    _orjson_loads = None


# ── Cassette × decoder catalog ──────────────────────────────────────────────

# Local imports of typed decoders. Module-level so the import cost is
# paid once and amortized over all iterations.
from swgoh_comlink._models import (  # noqa: E402
    LEADERBOARD_DECODER,
    METADATA_DECODER,
    PLAYER_DECODER,
    UNTYPED_DECODER,
    decode_guild,
)

_TYPED_DECODER_FOR: dict[str, Callable[[bytes], Any]] = {
    "metadata": METADATA_DECODER.decode,
    "player_small": PLAYER_DECODER.decode,
    "player_large": PLAYER_DECODER.decode,
    "guild": decode_guild,
    "leaderboard": LEADERBOARD_DECODER.decode,
}


def _parsers_for(cassette: str) -> list[tuple[str, Callable[[bytes], Any]]]:
    """List of (label, callable) parsers to time against this cassette."""
    parsers: list[tuple[str, Callable[[bytes], Any]]] = [
        ("json", lambda b: json.loads(b)),
        ("msgspec_untyped", UNTYPED_DECODER.decode),
    ]
    if cassette in _TYPED_DECODER_FOR:
        parsers.append(("msgspec_typed", _TYPED_DECODER_FOR[cassette]))
    if _orjson_loads is not None:
        parsers.append(("orjson", _orjson_loads))
    return parsers


# ── Iteration counts per cassette ────────────────────────────────────────────

# /data is 15 MiB — fewer iters keeps total wall time sane.
# Small cassettes (metadata, guild, leaderboard) get more iters for tighter stats.
_ITERS_FOR: dict[str, tuple[int, int]] = {
    # (warmup, iters)
    "metadata": (3, 50),
    "guild": (3, 50),
    "leaderboard": (3, 50),
    "player_small": (3, 30),
    "player_large": (3, 10),
    "data": (1, 3),
    "localization_eng_us": (1, 5),
}


CASSETTES = [
    "metadata",
    "guild",
    "leaderboard",
    "player_small",
    "player_large",
    "data",
    "localization_eng_us",
]


def main() -> int:
    require_python_version()
    rep = Reporter(phase="phase-3-decode-speed")

    for cassette in CASSETTES:
        if not cassette_exists(cassette):
            sys.stderr.write(f"  SKIP {cassette}: cassette missing\n")
            continue
        body = load_cassette(cassette)
        size_kib = len(body) / 1024
        warmup, iters = _ITERS_FOR.get(cassette, (3, 20))
        sys.stderr.write(f"--- {cassette}  ({size_kib:.1f} KiB decoded)  warmup={warmup} iters={iters} ---\n")

        baseline_ns: float | None = None
        for label, fn in _parsers_for(cassette):
            result = measure(lambda f=fn, b=body: f(b), warmup=warmup, iters=iters)
            rep.add_measure(
                f"decode_{cassette}_{label}",
                result,
                unit="ns",
                cassette=cassette,
                cassette_bytes=len(body),
                parser=label,
            )
            ms = result.median_ns / 1e6
            if label == "json":
                baseline_ns = result.median_ns
                sys.stderr.write(f"  {label:18s}  {ms:8.2f} ms  (baseline)\n")
            else:
                ratio = baseline_ns / result.median_ns if baseline_ns else 0
                sys.stderr.write(f"  {label:18s}  {ms:8.2f} ms  ({ratio:.2f}x vs json)\n")

    dest = rep.write()
    sys.stderr.write(f"\nWrote {dest}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
