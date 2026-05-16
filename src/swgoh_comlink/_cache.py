# coding=utf-8
"""On-disk, version-aware cache for ``/data`` and ``/localization`` responses.

Phase 7 — behind the ``[cache]`` extra
(``pip install swgoh-comlink[cache]``).

Eliminates ~99% of ``/data`` and ``/localization`` traffic for repeat
users via a persistent diskcache keyed by the comlink's current game
version. The headline win is on the *warm* path: a second-and-later
call to :meth:`GameDataCache.get_game_data` skips the network entirely
and pays only a msgpack decode (~5 ms vs ~7 s for the cold fetch in
Phase 0).

Public surface:

* :class:`GameDataCache` — the cache itself. Construct once per
  process; share between calls and between threads (diskcache is
  thread-safe).
* :func:`default_cache_dir` — XDG-compliant resolver returning
  ``~/.cache/swgoh-comlink/`` on Linux/BSD,
  ``~/Library/Caches/swgoh-comlink/`` on macOS, and
  ``%LOCALAPPDATA%\\swgoh-comlink\\Cache`` on Windows.

Storage format: msgspec.msgpack (binary, ~2-3x smaller than json on disk
for the SWGOH payloads). Entries are tagged with their game version,
so :meth:`GameDataCache.evict_old_versions` can wipe stale data in one
call when the upstream version bumps.

The metadata probe (``client.get_game_metadata()`` to find the current
version) is memoized in an in-memory :class:`cachetools.TTLCache` for
30 seconds, so a tight loop of cache hits doesn't hammer comlink with
metadata requests.

This module imports ``diskcache`` and ``cachetools`` lazily inside
:meth:`GameDataCache.__init__` — base installs (no ``[cache]``) can
still import :mod:`swgoh_comlink` without pulling either dep.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import msgspec

from ._optional import require

if TYPE_CHECKING:
    from .swgoh_comlink import SwgohComlink

__all__ = [
    "DEFAULT_VERSION_TTL_SECONDS",
    "GameDataCache",
    "default_cache_dir",
]


DEFAULT_VERSION_TTL_SECONDS: float = 30.0
"""How long the in-memory metadata probe is reused before re-checking."""


# ── XDG-compliant cache directory resolution ────────────────────────────────


def default_cache_dir() -> Path:
    """Return the platform-appropriate cache directory for swgoh-comlink.

    * **Linux / BSD:** ``$XDG_CACHE_HOME/swgoh-comlink/`` (defaults to
      ``~/.cache/swgoh-comlink/``).
    * **macOS:** ``~/Library/Caches/swgoh-comlink/``.
    * **Windows:** ``%LOCALAPPDATA%\\swgoh-comlink\\Cache``, falling
      back to ``%TEMP%`` if LOCALAPPDATA isn't set.

    Created if missing.
    """
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", str(Path.home()))))
        # Windows convention: extra "Cache" subdir under the app dir.
        d = base / "swgoh-comlink" / "Cache"
        d.mkdir(parents=True, exist_ok=True)
        return d
    else:
        # Linux / BSD / WSL — honor XDG_CACHE_HOME.
        base = Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache"))

    d = base / "swgoh-comlink"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── Cache class ─────────────────────────────────────────────────────────────


class GameDataCache:
    """Version-aware on-disk cache for ``/data`` and ``/localization``.

    Backed by :class:`diskcache.Cache` (lazy-imported; requires the
    ``[cache]`` extra). Serializes payloads as msgspec.msgpack — ~2-3x
    smaller than json on disk for the SWGOH shapes.

    Args:
        cache_dir: Where to store the cache. ``None`` → :func:`default_cache_dir`.
        version_ttl_seconds: How long the in-memory metadata probe is
            reused before re-checking. Default 30 s.

    Thread-safety: diskcache.Cache is thread-safe; this wrapper is too
    (the cachetools.TTLCache calls are guarded by the GIL). Sharing a
    single GameDataCache across threads is the expected pattern.

    Async clients: not supported in v3.0. The cache itself is sync;
    pairing it with :class:`SwgohComlinkAsync` would require an async
    wrapper. Carry-forward for v3.1.
    """

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        *,
        version_ttl_seconds: float = DEFAULT_VERSION_TTL_SECONDS,
    ) -> None:
        diskcache, cachetools = require("cache", "diskcache", "cachetools")
        if cache_dir is None:
            cache_dir = default_cache_dir()
        else:
            cache_dir = Path(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache_dir = Path(cache_dir)
        self._cache = diskcache.Cache(directory=str(cache_dir))
        self._metadata_cache: Any = cachetools.TTLCache(maxsize=1, ttl=version_ttl_seconds)
        self._last_seen_version: str | None = None
        # In-process memoization of decoded payloads. Repeated reads on the
        # *same* GameDataCache instance skip the msgpack-decode entirely.
        # Bot operators keep one cache instance alive for the process
        # lifetime, so this is the realistic warm path. Cleared on
        # evict_old_versions().
        self._inmem: dict[Any, Any] = {}

    # ── Metadata version (memoized) ────────────────────────────────────────

    def current_version(self, client: SwgohComlink) -> str:
        """Return the current game version, refreshing every ``version_ttl_seconds``.

        Caches in an in-memory :class:`cachetools.TTLCache` so tight
        loops of cache reads don't hammer comlink with metadata
        requests. Also stores the last seen version for the
        :meth:`evict_old_versions` cleanup.
        """
        try:
            return str(self._metadata_cache["v"])
        except KeyError:
            pass
        md = client.get_game_metadata()
        # Metadata may be a Struct (raw=False) or dict (raw=True).
        version = getattr(md, "latest_gamedata_version", None) or md["latestGamedataVersion"]  # type: ignore[index]
        version = str(version)
        self._metadata_cache["v"] = version
        self._last_seen_version = version
        return version

    # ── /data ──────────────────────────────────────────────────────────────

    def get_game_data(
        self,
        client: SwgohComlink,
        *,
        request_segment: int = 0,
        include_pve_units: bool = True,
        enums: bool = False,
    ) -> dict[str, Any]:
        """Return the ``/data`` payload, cached by ``(version, request_segment)``.

        On hit: msgpack-decode the stored bytes (~5 ms for the full dump
        vs ~7 s for a cold fetch + decode).

        On miss: fetch via ``client.get_game_data(raw=True, ...)``
        (raw shape preserves the full segment dict the cache stores)
        and write to disk.
        """
        version = self.current_version(client)
        key = ("data", version, request_segment, include_pve_units, enums)
        # Fast path 1: in-process memo
        if key in self._inmem:
            return self._inmem[key]  # type: ignore[no-any-return]
        # Fast path 2: on-disk cache
        cached: bytes | None = self._cache.get(key)
        if cached is not None:
            data = msgspec.msgpack.decode(cached)
            self._inmem[key] = data
            return data  # type: ignore[no-any-return]

        # Cold path: fetch + decode + encode + store.
        try:
            data = client.get_game_data(
                version=version,
                request_segment=request_segment,
                include_pve_units=include_pve_units,
                enums=enums,
            )
        except TypeError:
            # Older client signature; let the SDK choose defaults.
            data = client.get_game_data(version=version, request_segment=request_segment)

        self._cache.set(key, msgspec.msgpack.encode(data), tag=version)
        self._inmem[key] = data
        return data

    # ── /localization ──────────────────────────────────────────────────────

    def get_localization(
        self,
        client: SwgohComlink,
        *,
        locale: str | None = None,
        unzip: bool = True,
    ) -> dict[str, Any]:
        """Return ``/localization`` for *locale*, cached by ``(version, locale, unzip)``.

        ``locale=None`` defers to comlink's default. Always uses
        ``unzip=True`` semantics in the cached form unless overridden.
        """
        version = self.current_version(client)
        key = ("localization", version, locale or "", unzip)
        if key in self._inmem:
            return self._inmem[key]  # type: ignore[no-any-return]
        cached: bytes | None = self._cache.get(key)
        if cached is not None:
            data = msgspec.msgpack.decode(cached)
            self._inmem[key] = data
            return data  # type: ignore[no-any-return]

        # Localization needs the bundle id from metadata; client handles
        # the fallback when localization_id is None.
        data = client.get_localization(locale=locale, unzip=unzip)
        self._cache.set(key, msgspec.msgpack.encode(data), tag=version)
        self._inmem[key] = data
        return data

    # ── Eviction ───────────────────────────────────────────────────────────

    def evict_old_versions(self, current_version: str) -> int:
        """Remove every cached entry whose tag != *current_version*.

        Diskcache supports evict-by-tag directly. Returns the number of
        entries removed.

        Usage::

            cache.evict_old_versions(cache.current_version(client))
        """
        # diskcache's evict(tag=X) removes items WITH tag X. To remove
        # everything NOT tagged with current_version, iterate distinct
        # tags. The set of seen tags isn't directly indexed, so we walk
        # the cache once collecting tags.
        removed = 0
        for key in list(self._cache.iterkeys()):
            _value, tag = self._cache.get(key, tag=True, default=(None, None))
            if tag is None:
                continue
            if tag != current_version and self._cache.delete(key):
                removed += 1
        # Eviction may have invalidated in-memory entries — clear conservatively.
        self._inmem.clear()
        return removed

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying diskcache. Safe to call multiple times."""
        self._cache.close()

    def __enter__(self) -> GameDataCache:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"GameDataCache(cache_dir={str(self.cache_dir)!r})"
