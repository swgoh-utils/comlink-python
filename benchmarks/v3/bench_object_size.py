# coding=utf-8
"""Phase 3 — Resident object size of decoded results.

Uses ``pympler.asizeof`` to measure the size of the decoded object graph
at rest (i.e., post-decode allocation, before any references are dropped).

Per the plan: typed Struct graph is expected to be **40-60%** smaller
than the equivalent dict graph thanks to slotted layout.

Writes results to ``benchmarks/v3/results/phase-3-object-size.json``.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any

from pympler.asizeof import asizeof

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

_TYPED_DECODER_FOR: dict[str, Callable[[bytes], Any]] = {
    "metadata": METADATA_DECODER.decode,
    "player_small": PLAYER_DECODER.decode,
    "player_large": PLAYER_DECODER.decode,
    "guild": decode_guild,
    "leaderboard": LEADERBOARD_DECODER.decode,
}


def main() -> int:
    require_python_version()
    rep = Reporter(phase="phase-3-object-size")

    cassettes = ["metadata", "guild", "leaderboard", "player_small", "player_large", "data"]
    for cassette in cassettes:
        if not cassette_exists(cassette):
            continue
        body = load_cassette(cassette)
        sys.stderr.write(f"--- {cassette}  ({len(body) / 1024:.1f} KiB decoded) ---\n")

        # Baseline: stdlib json -> Python dict graph.
        json_obj = json.loads(body)
        json_size = asizeof(json_obj)
        rep.add(
            f"object_size_{cassette}_json",
            value=json_size,
            unit="bytes",
            cassette=cassette,
            parser="json",
        )
        sys.stderr.write(f"  json              {json_size / 1024 / 1024:8.2f} MiB  (baseline)\n")
        del json_obj

        # msgspec untyped (still dict/list graph)
        m_untyped = UNTYPED_DECODER.decode(body)
        m_untyped_size = asizeof(m_untyped)
        rep.add(
            f"object_size_{cassette}_msgspec_untyped",
            value=m_untyped_size,
            unit="bytes",
            cassette=cassette,
            parser="msgspec_untyped",
        )
        ratio = json_size / m_untyped_size if m_untyped_size else 0
        sys.stderr.write(f"  msgspec_untyped   {m_untyped_size / 1024 / 1024:8.2f} MiB  ({ratio:.2f}x smaller)\n")
        del m_untyped

        # msgspec typed (slotted Struct graph)
        if cassette in _TYPED_DECODER_FOR:
            m_typed = _TYPED_DECODER_FOR[cassette](body)
            m_typed_size = asizeof(m_typed)
            rep.add(
                f"object_size_{cassette}_msgspec_typed",
                value=m_typed_size,
                unit="bytes",
                cassette=cassette,
                parser="msgspec_typed",
            )
            ratio_t = json_size / m_typed_size if m_typed_size else 0
            sys.stderr.write(f"  msgspec_typed     {m_typed_size / 1024 / 1024:8.2f} MiB  ({ratio_t:.2f}x smaller)\n")
            del m_typed

    dest = rep.write()
    sys.stderr.write(f"\nWrote {dest}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
