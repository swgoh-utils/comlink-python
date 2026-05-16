# coding=utf-8
"""v3.1 probe — typed vs untyped decode for the ``/data.units`` segment.

Compares three metrics on the **units list only** (not the full /data
response) between two paths:

* **dict** — ``UNTYPED_DECODER.decode(units_bytes)`` → ``list[dict[str, Any]]``.
* **typed** — ``UNIT_LIST_DECODER.decode(units_bytes)`` → ``list[Unit]``.

Reports for each path:

* ``decode_speed`` — wall time per decode (median + p95).
* ``decode_peak_memory`` — peak allocation during decode (``tracemalloc``).
* ``object_size`` — resident bytes of the decoded result (``pympler.asizeof``).

Plus three derived ratios (typed / dict):
``speed_ratio`` (lower=faster on typed), ``memory_ratio``, ``size_ratio``.

The bench answers a single question: **does deep-typing one /data segment
move the needle enough to justify typing the remaining 81?**  Decision
rule documented in ``docs/v3/benchmark-report.md`` (>=1.5x speed AND
<=0.7x memory → green-light v3.1 scope).

Run with::

    uv run python -m benchmarks.v3.bench_units_typed_vs_dict
"""

from __future__ import annotations

import gc
import sys

import msgspec
from pympler.asizeof import asizeof  # type: ignore[import-untyped]

from benchmarks.v3._harness import (
    Reporter,
    cassette_exists,
    load_cassette,
    measure,
    require_python_version,
    track_memory,
)

# Local imports — module-level so import cost is paid once.
from swgoh_comlink._models import UNIT_LIST_DECODER, UNTYPED_DECODER  # noqa: E402

CASSETTE = "data"
WARMUP = 1
ITERS = 5


def _units_bytes(body: bytes) -> bytes:
    """Re-encode just the units segment as a standalone JSON document."""
    full = UNTYPED_DECODER.decode(body)
    units = full.get("units", [])
    return msgspec.json.encode(units)


def main() -> int:
    require_python_version()
    rep = Reporter(phase="phase-units-typed")

    if not cassette_exists(CASSETTE):
        sys.stderr.write(f"SKIP: cassette '{CASSETTE}' missing — run benchmarks.v3._record\n")
        rep.add("units_segment_bench", value=None, unit="status", status="skip")
        rep.write()
        return 1

    body = load_cassette(CASSETTE)
    units_blob = _units_bytes(body)
    size_kib = len(units_blob) / 1024
    sys.stderr.write(f"--- /data.units segment  ({size_kib:.1f} KiB JSON)  warmup={WARMUP} iters={ITERS} ---\n")

    # ── 1. decode speed ────────────────────────────────────────────────────
    dict_speed = measure(lambda b=units_blob: UNTYPED_DECODER.decode(b), warmup=WARMUP, iters=ITERS)
    typed_speed = measure(lambda b=units_blob: UNIT_LIST_DECODER.decode(b), warmup=WARMUP, iters=ITERS)

    rep.add_measure(
        "decode_speed_units_dict",
        dict_speed,
        unit="ns",
        cassette=CASSETTE,
        bytes=len(units_blob),
    )
    rep.add_measure(
        "decode_speed_units_typed",
        typed_speed,
        unit="ns",
        cassette=CASSETTE,
        bytes=len(units_blob),
    )

    speed_ratio = typed_speed.median_ns / dict_speed.median_ns
    rep.add(
        "decode_speed_ratio_typed_over_dict",
        value=speed_ratio,
        unit="ratio",
        note="lower=faster on typed; <1 means typed is faster",
    )
    sys.stderr.write(
        f"  decode_speed dict   = {dict_speed.median_ns / 1e6:8.2f} ms\n"
        f"  decode_speed typed  = {typed_speed.median_ns / 1e6:8.2f} ms  "
        f"({1 / speed_ratio:.2f}x faster vs dict)\n"
    )

    # ── 2. decode peak memory ──────────────────────────────────────────────
    gc.collect()
    dict_mem = track_memory(lambda b=units_blob: UNTYPED_DECODER.decode(b))
    gc.collect()
    typed_mem = track_memory(lambda b=units_blob: UNIT_LIST_DECODER.decode(b))
    gc.collect()

    rep.add_memory("decode_peak_memory_units_dict", dict_mem, cassette=CASSETTE)
    rep.add_memory("decode_peak_memory_units_typed", typed_mem, cassette=CASSETTE)
    mem_ratio = typed_mem.peak_bytes / dict_mem.peak_bytes if dict_mem.peak_bytes else 0
    rep.add(
        "decode_peak_memory_ratio_typed_over_dict",
        value=mem_ratio,
        unit="ratio",
        note="lower=less memory on typed",
    )
    sys.stderr.write(
        f"  peak_memory dict    = {dict_mem.peak_bytes / 1024 / 1024:8.2f} MiB\n"
        f"  peak_memory typed   = {typed_mem.peak_bytes / 1024 / 1024:8.2f} MiB  "
        f"({mem_ratio:.2f}x vs dict)\n"
    )

    # ── 3. resident object size ────────────────────────────────────────────
    gc.collect()
    dict_obj = UNTYPED_DECODER.decode(units_blob)
    dict_size = asizeof(dict_obj)
    del dict_obj
    gc.collect()

    typed_obj = UNIT_LIST_DECODER.decode(units_blob)
    typed_size = asizeof(typed_obj)
    del typed_obj
    gc.collect()

    rep.add(
        "object_size_units_dict",
        value=int(dict_size),
        unit="bytes",
        cassette=CASSETTE,
    )
    rep.add(
        "object_size_units_typed",
        value=int(typed_size),
        unit="bytes",
        cassette=CASSETTE,
    )
    size_ratio = typed_size / dict_size if dict_size else 0
    rep.add(
        "object_size_ratio_typed_over_dict",
        value=size_ratio,
        unit="ratio",
        note="lower=smaller resident footprint on typed",
    )
    sys.stderr.write(
        f"  object_size dict    = {dict_size / 1024 / 1024:8.2f} MiB\n"
        f"  object_size typed   = {typed_size / 1024 / 1024:8.2f} MiB  "
        f"({size_ratio:.2f}x vs dict)\n"
    )

    # ── Verdict (against the documented decision rule) ────────────────────
    speed_x = 1 / speed_ratio  # typed-faster-than-dict factor (>1 means typed wins)
    if speed_x >= 1.5 and mem_ratio <= 0.7:
        verdict = "green-light v3.1 scope: type the remaining 81 segments"
    elif speed_x < 1.2 or mem_ratio > 0.9:
        verdict = "deferral validated: typing other segments unlikely to pay back"
    else:
        verdict = "judgment call: revisit with operator-demand signal"
    rep.add(
        "v3_1_scope_verdict",
        value=None,
        unit="text",
        verdict=verdict,
        speed_x=speed_x,
        memory_ratio=mem_ratio,
        size_ratio=size_ratio,
    )
    sys.stderr.write(f"\nVerdict: {verdict}\n")

    dest = rep.write()
    sys.stderr.write(f"\nWrote {dest}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
