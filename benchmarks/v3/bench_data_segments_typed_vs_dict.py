# coding=utf-8
"""v3.1 — typed vs untyped decode across every stock ``/data`` segment.

Iterates :data:`compat.STOCK_SEGMENT_TYPES` (14 segments: units + 13
others). For each, encodes the segment to JSON bytes once and compares
two **bytes-based** decode paths (apples-to-apples; matches the units
probe methodology):

* **dict** — ``msgspec.json.Decoder().decode(bytes)`` → ``list[dict]``.
* **typed** — ``msgspec.json.Decoder(list[StockType]).decode(bytes)``
  → ``list[StockType]``.

Bytes-based both sides because that's what realistic users pay: when
the SDK reads from the network or from a cached payload, parser cost
is real. The runtime helper :func:`compat.decode_segment` uses
``msgspec.convert`` (no JSON hop) since its input is already a dict —
but for **comparison-of-decoders** the fair test is bytes-in, structured-
out on both sides.

Reports per segment:

* ``decode_speed`` (median + p95)
* ``decode_peak_memory`` (``tracemalloc``)
* ``object_size`` (``pympler.asizeof``)
* Three ratios (typed / dict): ``*_ratio_typed_over_dict``

Plus three aggregate ratios across all 14 segments (sum-of-typed /
sum-of-dict for time/memory; weighted-avg for size) and a green-light
verdict (>=1.5x faster AND <=0.7x memory -> type the rest of /data;
matches the units-only probe's decision rule).

Writes ``benchmarks/v3/results/phase-v3_1-data-segments.json``.

Run with::

    uv run python -m benchmarks.v3.bench_data_segments_typed_vs_dict
"""

from __future__ import annotations

import gc
import gzip
import json
import sys
from types import GenericAlias
from typing import Any

import msgspec
from pympler.asizeof import asizeof  # type: ignore[import-untyped]

from benchmarks.v3._harness import (
    FIXTURES_DIR,
    Reporter,
    measure,
    require_python_version,
    track_memory,
)
from swgoh_comlink.compat import STOCK_SEGMENT_TYPES  # noqa: E402

CASSETTE_PATH = FIXTURES_DIR / "data.json.gz"
WARMUP = 1
ITERS = 5


def _load_segments() -> dict[str, list[dict[str, Any]]]:
    """Decompress + parse the /data cassette once, keep only the segments we time."""
    if not CASSETTE_PATH.exists():
        sys.stderr.write(f"SKIP: cassette {CASSETTE_PATH} missing - run benchmarks.v3._record\n")
        return {}
    with gzip.open(CASSETTE_PATH, "rb") as fh:
        full = json.load(fh)
    return {seg: full.get(seg, []) for seg in STOCK_SEGMENT_TYPES}


def _bench_one(
    rep: Reporter,
    segment: str,
    target: type,
    items: list[dict[str, Any]],
) -> tuple[float, float, int, int, int, int]:
    """Return (dict_ns, typed_ns, dict_peak, typed_peak, dict_size, typed_size)."""
    sys.stderr.write(f"  {segment:32s} count={len(items):>6}\n")

    # Encode the segment to JSON bytes once; both decoders consume bytes.
    blob = msgspec.json.encode(items)
    dict_decoder = msgspec.json.Decoder()
    # ``list[target]`` built at runtime: *target* is a value, not a static type.
    typed_decoder = msgspec.json.Decoder(GenericAlias(list, (target,)))

    # decode speed (bytes -> result, both sides)
    dict_speed = measure(
        lambda b=blob, d=dict_decoder: d.decode(b),
        warmup=WARMUP,
        iters=ITERS,
    )
    typed_speed = measure(
        lambda b=blob, d=typed_decoder: d.decode(b),
        warmup=WARMUP,
        iters=ITERS,
    )
    rep.add_measure(
        f"decode_speed_{segment}_dict",
        dict_speed,
        unit="ns",
        segment=segment,
        count=len(items),
        bytes=len(blob),
    )
    rep.add_measure(
        f"decode_speed_{segment}_typed",
        typed_speed,
        unit="ns",
        segment=segment,
        count=len(items),
        bytes=len(blob),
        type=target.__name__,
    )
    speed_ratio = typed_speed.median_ns / dict_speed.median_ns if dict_speed.median_ns else 0.0
    rep.add(
        f"decode_speed_ratio_{segment}_typed_over_dict",
        value=speed_ratio,
        unit="ratio",
    )

    # decode peak memory (bytes -> result, both sides)
    gc.collect()
    dict_mem = track_memory(lambda b=blob, d=dict_decoder: d.decode(b))
    gc.collect()
    typed_mem = track_memory(lambda b=blob, d=typed_decoder: d.decode(b))
    gc.collect()
    rep.add_memory(f"decode_peak_memory_{segment}_dict", dict_mem, segment=segment)
    rep.add_memory(f"decode_peak_memory_{segment}_typed", typed_mem, segment=segment)
    mem_ratio = typed_mem.peak_bytes / dict_mem.peak_bytes if dict_mem.peak_bytes else 0.0
    rep.add(
        f"decode_peak_memory_ratio_{segment}_typed_over_dict",
        value=mem_ratio,
        unit="ratio",
    )

    # resident object size (decoded result, both sides)
    gc.collect()
    dict_obj = dict_decoder.decode(blob)
    dict_size = int(asizeof(dict_obj))
    del dict_obj
    gc.collect()
    typed_obj = typed_decoder.decode(blob)
    typed_size = int(asizeof(typed_obj))
    del typed_obj
    gc.collect()
    rep.add(f"object_size_{segment}_dict", value=dict_size, unit="bytes", segment=segment)
    rep.add(
        f"object_size_{segment}_typed",
        value=typed_size,
        unit="bytes",
        segment=segment,
    )
    size_ratio = typed_size / dict_size if dict_size else 0.0
    rep.add(
        f"object_size_ratio_{segment}_typed_over_dict",
        value=size_ratio,
        unit="ratio",
    )

    sys.stderr.write(
        f"    speed:  dict={dict_speed.median_ns / 1e6:>7.2f} ms  "
        f"typed={typed_speed.median_ns / 1e6:>7.2f} ms  "
        f"({1 / speed_ratio if speed_ratio else 0:.2f}x faster)\n"
        f"    memory: dict={dict_mem.peak_bytes / 1024 / 1024:>7.2f} MiB  "
        f"typed={typed_mem.peak_bytes / 1024 / 1024:>7.2f} MiB  ({mem_ratio:.2f}x)\n"
        f"    size:   dict={dict_size / 1024 / 1024:>7.2f} MiB  "
        f"typed={typed_size / 1024 / 1024:>7.2f} MiB  ({size_ratio:.2f}x)\n"
    )

    return (
        dict_speed.median_ns,
        typed_speed.median_ns,
        dict_mem.peak_bytes,
        typed_mem.peak_bytes,
        dict_size,
        typed_size,
    )


def main() -> int:
    require_python_version()
    rep = Reporter(phase="phase-v3_1-data-segments")
    segments = _load_segments()
    if not segments:
        rep.add("data_segments_bench", value=None, unit="status", status="skip")
        rep.write()
        return 1

    sys.stderr.write(f"--- /data segments - {len(segments)} stock types, warmup={WARMUP}, iters={ITERS} ---\n")

    total_dict_ns = 0.0
    total_typed_ns = 0.0
    total_dict_peak = 0
    total_typed_peak = 0
    total_dict_size = 0
    total_typed_size = 0

    for segment, target in STOCK_SEGMENT_TYPES.items():
        items = segments.get(segment, [])
        if not items:
            sys.stderr.write(f"  {segment:32s} SKIP (empty)\n")
            continue
        dict_ns, typed_ns, dict_peak, typed_peak, dict_size, typed_size = _bench_one(rep, segment, target, items)
        total_dict_ns += dict_ns
        total_typed_ns += typed_ns
        total_dict_peak += dict_peak
        total_typed_peak += typed_peak
        total_dict_size += dict_size
        total_typed_size += typed_size

    # Aggregate
    agg_speed_ratio = total_typed_ns / total_dict_ns if total_dict_ns else 0.0
    agg_mem_ratio = total_typed_peak / total_dict_peak if total_dict_peak else 0.0
    agg_size_ratio = total_typed_size / total_dict_size if total_dict_size else 0.0
    rep.add("aggregate_decode_speed_ratio", value=agg_speed_ratio, unit="ratio")
    rep.add("aggregate_peak_memory_ratio", value=agg_mem_ratio, unit="ratio")
    rep.add("aggregate_object_size_ratio", value=agg_size_ratio, unit="ratio")

    speed_x = 1 / agg_speed_ratio if agg_speed_ratio else 0.0
    if speed_x >= 1.5 and agg_mem_ratio <= 0.7:
        verdict = "green-light: type the remaining /data segments in v3.1"
    elif speed_x < 1.2 or agg_mem_ratio > 0.9:
        verdict = "stop here: remaining-segment typing unlikely to pay back"
    else:
        verdict = "judgment call: revisit with operator-demand signal"
    rep.add(
        "v3_1_aggregate_verdict",
        value=None,
        unit="text",
        verdict=verdict,
        aggregate_speed_x=speed_x,
        aggregate_memory_ratio=agg_mem_ratio,
        aggregate_size_ratio=agg_size_ratio,
        segments_benched=len(STOCK_SEGMENT_TYPES),
    )

    sys.stderr.write(
        f"\n=== aggregate across {len(STOCK_SEGMENT_TYPES)} segments ===\n"
        f"  speed:  {speed_x:.2f}x faster (typed vs dict)\n"
        f"  memory: {agg_mem_ratio:.2f}x (typed vs dict)\n"
        f"  size:   {agg_size_ratio:.2f}x (typed vs dict)\n"
        f"\nVerdict: {verdict}\n"
    )

    dest = rep.write()
    sys.stderr.write(f"\nWrote {dest}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
