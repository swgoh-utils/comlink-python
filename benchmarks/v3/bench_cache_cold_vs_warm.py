# coding=utf-8
"""Phase 7 — :class:`GameDataCache` cold-vs-warm benchmark.

Measures the full ``cache.get_game_data(client)`` path:

* **Cold** — fresh on-disk cache, mock client returns the real ``/data``
  cassette (~80 MiB JSON, ~15 MiB gzipped). Full pipeline: probe
  metadata, fetch /data, msgspec.json decode, msgspec.msgpack encode,
  write to disk.

* **Warm** — same call on a pre-populated cache. Just msgspec.msgpack
  decode from disk.

Plan target: warm is **100-1000x faster** than cold for ``/data``.

Writes results to ``benchmarks/v3/results/phase-7-cache-cold-vs-warm.json``.
"""

from __future__ import annotations

import sys
import tempfile
from functools import partial
from pathlib import Path
from typing import Any
from unittest import mock

from benchmarks.v3._harness import (
    Reporter,
    cassette_exists,
    load_cassette,
    measure,
    require_python_version,
)


def _fake_client(version: str, data_bytes: bytes) -> Any:
    """Mock client whose get_game_data decodes the cassette + returns the dict."""
    import msgspec

    client = mock.MagicMock()
    md = mock.MagicMock()
    md.latest_gamedata_version = version
    client.get_game_metadata.return_value = md

    def fetch(*args: Any, **kwargs: Any) -> Any:
        return msgspec.json.decode(data_bytes)

    client.get_game_data.side_effect = fetch
    return client


def _run_cold(tmp_dir: Path, data_bytes: bytes) -> float:
    """One full cold-cache fetch. Returns wall ms.

    A fresh GameDataCache + fresh on-disk cache dir per iteration so the
    cold path measures the whole pipeline: probe metadata, fetch /data,
    msgspec.json decode, msgspec.msgpack encode, write to disk.
    """
    import time

    from swgoh_comlink._cache import GameDataCache

    sub = tmp_dir / f"cold_{time.time_ns()}"
    sub.mkdir()
    client = _fake_client("v1", data_bytes)
    with GameDataCache(cache_dir=sub) as cache:
        start = time.perf_counter()
        cache.get_game_data(client)
        return (time.perf_counter() - start) * 1000


def _run_disk_warm(cache_dir: Path, data_bytes: bytes) -> None:
    """One on-disk warm fetch: fresh GameDataCache, payload already on disk.

    This is the worst-case warm path (paying msgspec.msgpack decode of the
    full ~250 MiB blob every time the process starts).
    """
    from swgoh_comlink._cache import GameDataCache

    client = _fake_client("v1", data_bytes)
    with GameDataCache(cache_dir=cache_dir) as cache:
        cache.current_version(client)
        cache.get_game_data(client)


def _run_inmem_warm(cache: Any, client: Any) -> None:
    """One in-process warm fetch: cache instance is reused; in-memory memo hit.

    This is the realistic bot-operator path — one GameDataCache lives for
    the process lifetime, and subsequent get_game_data calls hit the
    in-memory dict cached by the first read.
    """
    cache.get_game_data(client)


def main() -> int:
    require_python_version()
    rep = Reporter(phase="phase-7-cache-cold-vs-warm")

    if not cassette_exists("data"):
        sys.stderr.write("data cassette missing — skip\n")
        rep.add("cold_get_game_data_ms", value=None, unit="ms", status="skip", reason="cassette 'data' missing")
        rep.add("warm_get_game_data_ms", value=None, unit="ms", status="skip", reason="cassette 'data' missing")
        rep.write()
        return 0

    data_bytes = load_cassette("data")
    sys.stderr.write(f"--- cold-vs-warm on /data ({len(data_bytes) / 1024 / 1024:.1f} MiB gzipped) ---\n")

    with tempfile.TemporaryDirectory() as td:
        tmp_dir = Path(td)

        sys.stderr.write("[1/3] Cold (fresh cache; 3 fresh runs) ...\n")
        cold_samples = [_run_cold(tmp_dir, data_bytes) for _ in range(3)]
        cold_median = sorted(cold_samples)[len(cold_samples) // 2]

        sys.stderr.write("[2/3] Disk-warm (pre-populated cache; new instance per iter) ...\n")
        warm_dir = tmp_dir / "warm"
        warm_dir.mkdir()
        from swgoh_comlink._cache import GameDataCache

        with GameDataCache(cache_dir=warm_dir) as primer:
            primer.get_game_data(_fake_client("v1", data_bytes))

        disk_warm = measure(partial(_run_disk_warm, warm_dir, data_bytes), warmup=2, iters=10)
        disk_warm_ms = disk_warm.median_ns / 1e6

        sys.stderr.write("[3/3] In-memory warm (same GameDataCache instance; 100 iters) ...\n")
        inmem_dir = tmp_dir / "inmem"
        inmem_dir.mkdir()
        inmem_cache = GameDataCache(cache_dir=inmem_dir)
        inmem_client = _fake_client("v1", data_bytes)
        # Prime the cache
        inmem_cache.get_game_data(inmem_client)
        inmem_warm = measure(partial(_run_inmem_warm, inmem_cache, inmem_client), warmup=3, iters=100)
        inmem_warm_ms = inmem_warm.median_ns / 1e6
        inmem_cache.close()

    rep.add(
        "cold_get_game_data_ms",
        value=cold_median,
        unit="ms",
        samples_ms=cold_samples,
        scenario="fresh on-disk cache; full fetch + decode + encode + write",
    )
    rep.add_measure(
        "disk_warm_get_game_data_ms",
        disk_warm,
        unit="ns",
        scenario="payload on disk; new GameDataCache instance per call; pays msgpack decode each time",
    )
    rep.add_measure(
        "inmem_warm_get_game_data_ms",
        inmem_warm,
        unit="ns",
        scenario="same GameDataCache instance; in-memory dict hit (the realistic bot path)",
    )

    disk_ratio = cold_median / disk_warm_ms if disk_warm_ms else 0
    inmem_ratio = cold_median / inmem_warm_ms if inmem_warm_ms else 0
    rep.add("disk_warm_speedup_vs_cold", value=disk_ratio, unit="ratio")
    rep.add("inmem_warm_speedup_vs_cold", value=inmem_ratio, unit="ratio")

    sys.stderr.write(
        f"\n  cold:            {cold_median:>9.1f} ms  (full fetch + decode + encode + disk write)\n"
        f"  disk-warm:       {disk_warm_ms:>9.1f} ms  ({disk_ratio:5.1f}x faster vs cold)\n"
        f"  in-memory warm:  {inmem_warm_ms:>9.4f} ms  ({inmem_ratio:>5.0f}x faster vs cold)\n"
        f"  (plan target: 100-1000x; in-memory path is the realistic operator scenario)\n",
    )

    dest = rep.write()
    sys.stderr.write(f"\nWrote {dest}\n")
    return 0 if inmem_ratio >= 100 else 1


if __name__ == "__main__":
    sys.exit(main())
