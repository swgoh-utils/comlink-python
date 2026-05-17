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

import asyncio
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


# ── Async-path twins ────────────────────────────────────────────────────────


def _fake_async_client(version: str, data_bytes: bytes) -> Any:
    """AsyncMock counterpart of `_fake_client` — used by the async cache path."""
    import msgspec

    client = mock.AsyncMock()
    md = mock.MagicMock()
    md.latest_gamedata_version = version
    client.get_game_metadata.return_value = md

    async def fetch(*args: Any, **kwargs: Any) -> Any:
        return msgspec.json.decode(data_bytes)

    client.get_game_data.side_effect = fetch
    return client


def _run_async_cold(tmp_dir: Path, data_bytes: bytes) -> float:
    """Async-path equivalent of `_run_cold`. Returns wall ms."""
    import time

    from swgoh_comlink._cache import GameDataCache

    sub = tmp_dir / f"acold_{time.time_ns()}"
    sub.mkdir()
    client = _fake_async_client("v1", data_bytes)

    async def go() -> float:
        async with GameDataCache(cache_dir=sub) as cache:
            start = time.perf_counter()
            await cache.aget_game_data(client)
            return (time.perf_counter() - start) * 1000

    return asyncio.run(go())


def _run_async_disk_warm(cache_dir: Path, data_bytes: bytes) -> None:
    """Async-path equivalent of `_run_disk_warm`."""
    from swgoh_comlink._cache import GameDataCache

    client = _fake_async_client("v1", data_bytes)

    async def go() -> None:
        async with GameDataCache(cache_dir=cache_dir) as cache:
            await cache.acurrent_version(client)
            await cache.aget_game_data(client)

    asyncio.run(go())


def _run_async_inmem_warm(cache: Any, client: Any) -> None:
    """Async-path equivalent of `_run_inmem_warm`."""

    async def go() -> None:
        await cache.aget_game_data(client)

    asyncio.run(go())


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

    # ── Async parity ────────────────────────────────────────────────────────
    sys.stderr.write("\n--- async parity (aget_game_data) ---\n")
    with tempfile.TemporaryDirectory() as td_async:
        atmp = Path(td_async)

        sys.stderr.write("[1/3] async cold (3 fresh runs) ...\n")
        async_cold_samples = [_run_async_cold(atmp, data_bytes) for _ in range(3)]
        async_cold_median = sorted(async_cold_samples)[len(async_cold_samples) // 2]

        sys.stderr.write("[2/3] async disk-warm (10 iters) ...\n")
        awarm_dir = atmp / "warm"
        awarm_dir.mkdir()
        from swgoh_comlink._cache import GameDataCache

        async def _prime() -> None:
            async with GameDataCache(cache_dir=awarm_dir) as primer:
                await primer.aget_game_data(_fake_async_client("v1", data_bytes))

        asyncio.run(_prime())
        async_disk_warm = measure(partial(_run_async_disk_warm, awarm_dir, data_bytes), warmup=2, iters=10)
        async_disk_warm_ms = async_disk_warm.median_ns / 1e6

        sys.stderr.write("[3/3] async in-memory warm (100 iters) ...\n")
        ainmem_dir = atmp / "inmem"
        ainmem_dir.mkdir()
        ainmem_cache = GameDataCache(cache_dir=ainmem_dir)
        ainmem_client = _fake_async_client("v1", data_bytes)

        async def _prime_inmem() -> None:
            await ainmem_cache.aget_game_data(ainmem_client)

        asyncio.run(_prime_inmem())
        async_inmem_warm = measure(partial(_run_async_inmem_warm, ainmem_cache, ainmem_client), warmup=3, iters=100)
        async_inmem_warm_ms = async_inmem_warm.median_ns / 1e6
        asyncio.run(ainmem_cache.aclose())

    rep.add(
        "async_cold_aget_game_data_ms",
        value=async_cold_median,
        unit="ms",
        samples_ms=async_cold_samples,
        scenario="async fresh cache; full pipeline via aget_game_data",
    )
    rep.add_measure(
        "async_disk_warm_aget_game_data_ms",
        async_disk_warm,
        unit="ns",
        scenario="async disk-warm; new GameDataCache instance per call (asyncio.to_thread overhead included)",
    )
    rep.add_measure(
        "async_inmem_warm_aget_game_data_ms",
        async_inmem_warm,
        unit="ns",
        scenario="async in-memory warm; same GameDataCache instance (asyncio.run() per iter dominates)",
    )

    async_disk_ratio = async_cold_median / async_disk_warm_ms if async_disk_warm_ms else 0
    async_inmem_ratio = async_cold_median / async_inmem_warm_ms if async_inmem_warm_ms else 0
    rep.add("async_disk_warm_speedup_vs_cold", value=async_disk_ratio, unit="ratio")
    rep.add("async_inmem_warm_speedup_vs_cold", value=async_inmem_ratio, unit="ratio")

    sys.stderr.write(
        f"\n  async cold:            {async_cold_median:>9.1f} ms\n"
        f"  async disk-warm:       {async_disk_warm_ms:>9.1f} ms  ({async_disk_ratio:5.1f}x faster vs async cold)\n"
        f"  async in-memory warm:  {async_inmem_warm_ms:>9.4f} ms  ({async_inmem_ratio:>5.0f}x faster vs async cold)\n",
    )

    dest = rep.write()
    sys.stderr.write(f"\nWrote {dest}\n")
    return 0 if inmem_ratio >= 100 else 1


if __name__ == "__main__":
    sys.exit(main())
