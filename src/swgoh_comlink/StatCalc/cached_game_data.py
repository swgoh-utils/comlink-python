# coding=utf-8
"""v3.2 — Persist StatCalc-normalized game_data across process restarts.

:class:`~swgoh_comlink.StatCalc.data_builder.GameDataBuilder` takes the
raw ``/data`` payload and produces the 6 normalized tables StatCalc
needs (``unitData``, ``gearData``, ``modSetData``, ``crTables``,
``gpTables``, ``relicData``). On a 397-unit roster the rebuild runs
~25 ms at every process startup — wasted work for tools that fan a
fresh interpreter per request (cron jobs, lambdas, CLI invocations).

Phase 7's :class:`~swgoh_comlink._cache.GameDataCache` already persists
the raw ``/data`` payload via diskcache + ``msgspec.msgpack``,
version-keyed. This module extends that pattern to **also** cache the
normalized form — so every process after the first only pays the
msgpack decode (~3-5 ms) instead of rebuilding from raw (~25 ms).

Measured Phase 4 result on the 397-unit cassette:

* Cold-start baseline (``GameDataBuilder + StatCalc.__init__``): **25.7 ms**
* Disk-warm path (msgspec.msgpack decode): **3.6 ms**
* Improvement: **+85.9 % vs cold-start baseline**

That cleared the v3.2 pre-registered ``≥ 50 %`` threshold for
cold-start optimizations and ships as part of v3.2.

The hot path (``calc_player_stats`` per-unit work) is unaffected — this
is a startup-only optimization.

API surface:

* :func:`get_statcalc_game_data(client, *, cache)` — returns the
  normalized game_data ready to hand to :class:`StatCalc`. Builds and
  persists on cache miss; msgpack-decodes from disk on hit.

Example:
    >>> from swgoh_comlink import SwgohComlink
    >>> from swgoh_comlink._cache import GameDataCache
    >>> from swgoh_comlink.StatCalc import StatCalc, get_statcalc_game_data
    >>> client = SwgohComlink(url="http://comlink.local:3200")
    >>> cache = GameDataCache()
    >>> game_data = get_statcalc_game_data(client, cache=cache)
    >>> sc = StatCalc(game_data=game_data)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import msgspec

from swgoh_comlink.StatCalc.data_builder._builder_base import GameDataBuilderBase

if TYPE_CHECKING:
    from swgoh_comlink import SwgohComlink
    from swgoh_comlink._cache import GameDataCache


# Cache-key namespace — bumping the second tuple element invalidates
# all previously-persisted normalized entries (use when the normalized
# shape itself changes).
_CACHE_NAMESPACE: str = "statcalc_game_data"
_CACHE_SHAPE_VERSION: str = "v3.2"


def _statcalc_cache_key(version: str) -> tuple[str, str, str]:
    """Build the diskcache key for *version*.

    Namespaced as ``("statcalc_game_data", "v3.2", <game_version>)`` so
    it cannot collide with the raw ``/data`` entries
    :class:`~swgoh_comlink._cache.GameDataCache` stores at
    ``("game_data", ...)``.
    """
    return (_CACHE_NAMESPACE, _CACHE_SHAPE_VERSION, version)


def get_statcalc_game_data(
    client: SwgohComlink,
    *,
    cache: GameDataCache,
) -> dict[str, Any]:
    """Return StatCalc-normalized game_data, persisted across processes.

    On hit: msgspec.msgpack-decode the cached normalized form
    (~3-5 ms for a full game_data tree).

    On miss: fetch raw ``/data`` via *client*, run
    :meth:`GameDataBuilderBase._build_game_data` (~25 ms), persist the
    result, return.

    Args:
        client: Source for raw ``/data`` on cache miss. The fetch is
            routed through the supplied *cache*'s
            :meth:`~swgoh_comlink._cache.GameDataCache.get_game_data` so
            the raw payload itself remains cached too.
        cache: A :class:`~swgoh_comlink._cache.GameDataCache` instance
            (provides the underlying diskcache + version probe +
            in-process memo).

    Returns:
        The 6-key normalized dict that :class:`StatCalc` consumes:
        ``unitData``, ``gearData``, ``modSetData``, ``crTables``,
        ``gpTables``, ``relicData``.
    """
    version = cache.current_version(client)
    key = _statcalc_cache_key(version)
    diskcache_obj = cache._cache  # internal: the diskcache.Cache instance

    # Fast path 1: in-process memo (matches GameDataCache's pattern —
    # zero serialization work on the second-and-later call within the
    # same process).
    if key in cache._inmem:
        memo: dict[str, Any] = cache._inmem[key]
        return memo

    # Fast path 2: on disk — pay the msgpack decode but skip the rebuild.
    cached: bytes | None = diskcache_obj.get(key)
    if cached is not None:
        normalized: dict[str, Any] = msgspec.msgpack.decode(cached)
        cache._inmem[key] = normalized
        return normalized

    # Cold path: piggyback on the existing /data cache for raw, then
    # build the normalized form and persist it.
    raw = cache.get_game_data(client)
    normalized = GameDataBuilderBase._build_game_data(raw)
    diskcache_obj.set(key, msgspec.msgpack.encode(normalized), tag=version)
    cache._inmem[key] = normalized
    return normalized


__all__ = ["get_statcalc_game_data"]
