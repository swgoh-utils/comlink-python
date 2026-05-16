# coding=utf-8
"""Phase 7 tests — :class:`GameDataCache`.

Skipped entirely if the ``[cache]`` extra (diskcache + cachetools) isn't
installed in the test venv.

Covers:

* Cold fetch hits the client; warm fetch skips it.
* Cache is keyed by (version, segment, ...); a version bump triggers
  a fresh fetch on the next access.
* :meth:`GameDataCache.evict_old_versions` removes everything not
  tagged with the current version.
* msgspec.msgpack serialization round-trips losslessly.
* XDG-compliant :func:`default_cache_dir` returns the right path per
  platform.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from swgoh_comlink._optional import has_extra

_HAS_CACHE = has_extra("cache", "diskcache", "cachetools")

pytestmark = pytest.mark.skipif(not _HAS_CACHE, reason="[cache] extra not installed")


# Imported eagerly only when the extra is present (the skipif above makes
# this safe — pytest evaluates the marker before collection).
from swgoh_comlink._cache import (  # noqa: E402  — guarded by pytestmark
    DEFAULT_VERSION_TTL_SECONDS,
    GameDataCache,
    default_cache_dir,
)

# ── default_cache_dir ───────────────────────────────────────────────────────


def test_default_cache_dir_macos_path() -> None:
    """On macOS, default cache lives under ~/Library/Caches/swgoh-comlink/."""
    if sys.platform != "darwin":
        pytest.skip("macOS-only path check")
    p = default_cache_dir()
    assert p == Path.home() / "Library" / "Caches" / "swgoh-comlink"
    assert p.is_dir()


def test_default_cache_dir_xdg_honored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """On Linux, $XDG_CACHE_HOME overrides ~/.cache."""
    if sys.platform == "darwin" or sys.platform == "win32":
        pytest.skip("Linux-only XDG check")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    p = default_cache_dir()
    assert p == tmp_path / "swgoh-comlink"


# ── Cold / warm path ────────────────────────────────────────────────────────


def _fake_client(version: str, data_payload: dict[str, Any]) -> Any:
    """Build a stub client with the methods GameDataCache needs."""
    client = mock.MagicMock()
    # get_game_metadata returns an object with .latest_gamedata_version
    md = mock.MagicMock()
    md.latest_gamedata_version = version
    client.get_game_metadata.return_value = md
    client.get_game_data.return_value = data_payload
    return client


def test_cold_fetch_calls_client_warm_does_not(tmp_path: Path) -> None:
    """First call hits get_game_data; second call returns from cache."""
    payload = {"units": [{"id": "x"}], "ability": []}
    client = _fake_client("v1", payload)

    with GameDataCache(cache_dir=tmp_path) as cache:
        # Cold
        first = cache.get_game_data(client)
        assert first == payload
        assert client.get_game_data.call_count == 1

        # Warm — same call should NOT hit the client again
        second = cache.get_game_data(client)
        assert second == payload
        assert client.get_game_data.call_count == 1


def test_warm_path_returns_equivalent_value(tmp_path: Path) -> None:
    """msgspec.msgpack round-trip preserves the payload exactly."""
    payload = {
        "units": [{"id": "abc", "level": 85, "rarity": 7, "tags": ["scoundrel"]}],
        "ability": [{"id": "ability_1", "tier": 6}],
        "nested": {"a": {"b": [1, 2, 3]}},
    }
    client = _fake_client("v1", payload)

    with GameDataCache(cache_dir=tmp_path) as cache:
        first = cache.get_game_data(client)
        second = cache.get_game_data(client)
        assert first == second == payload


def test_metadata_probe_memoized(tmp_path: Path) -> None:
    """get_game_metadata only called once across multiple cache reads."""
    payload = {"x": 1}
    client = _fake_client("v1", payload)

    with GameDataCache(cache_dir=tmp_path) as cache:
        for _ in range(5):
            cache.get_game_data(client)
        # Metadata fetched once (then memoized in cachetools.TTLCache)
        # plus the segment fetched once.
        assert client.get_game_metadata.call_count == 1
        assert client.get_game_data.call_count == 1


# ── Version invalidation ────────────────────────────────────────────────────


def test_version_bump_triggers_fresh_fetch(tmp_path: Path) -> None:
    """When the metadata version changes, get_game_data fetches again."""
    payload_v1 = {"units": [{"id": "v1"}]}
    payload_v2 = {"units": [{"id": "v2"}]}

    client = _fake_client("v1", payload_v1)
    with GameDataCache(cache_dir=tmp_path, version_ttl_seconds=0.0) as cache:
        first = cache.get_game_data(client)
        assert first == payload_v1

        # Switch the client to a new version + payload
        client.get_game_metadata.return_value.latest_gamedata_version = "v2"
        client.get_game_data.return_value = payload_v2

        # 0s TTL on the metadata probe means we re-fetch the version on next call
        second = cache.get_game_data(client)
        assert second == payload_v2
        assert client.get_game_data.call_count == 2


def test_evict_old_versions_removes_stale(tmp_path: Path) -> None:
    """evict_old_versions deletes entries tagged with anything but current."""
    payload_v1 = {"x": 1}
    payload_v2 = {"x": 2}

    client = _fake_client("v1", payload_v1)
    with GameDataCache(cache_dir=tmp_path, version_ttl_seconds=0.0) as cache:
        cache.get_game_data(client)  # caches under tag="v1"

        client.get_game_metadata.return_value.latest_gamedata_version = "v2"
        client.get_game_data.return_value = payload_v2
        cache.get_game_data(client)  # caches under tag="v2"

        # Now both v1 and v2 entries are on disk
        removed = cache.evict_old_versions("v2")
        assert removed >= 1


# ── Localization ────────────────────────────────────────────────────────────


def test_get_localization_cached_per_locale(tmp_path: Path) -> None:
    """ENG_US and FRE_FR fetched separately; second access of either is cached."""
    eng_payload = {"locale": "ENG_US", "strings": {"hello": "Hello"}}
    fre_payload = {"locale": "FRE_FR", "strings": {"hello": "Bonjour"}}

    client = mock.MagicMock()
    md = mock.MagicMock()
    md.latest_gamedata_version = "v1"
    client.get_game_metadata.return_value = md

    # Return different payloads depending on locale arg
    def localization_router(locale: str | None = None, unzip: bool = True) -> Any:
        return eng_payload if locale == "ENG_US" else fre_payload

    client.get_localization.side_effect = localization_router

    with GameDataCache(cache_dir=tmp_path) as cache:
        a = cache.get_localization(client, locale="ENG_US")
        b = cache.get_localization(client, locale="FRE_FR")
        assert a == eng_payload
        assert b == fre_payload
        assert client.get_localization.call_count == 2

        # Warm reads
        cache.get_localization(client, locale="ENG_US")
        cache.get_localization(client, locale="FRE_FR")
        assert client.get_localization.call_count == 2  # still 2


# ── Constants ───────────────────────────────────────────────────────────────


def test_default_version_ttl_is_30_seconds() -> None:
    assert DEFAULT_VERSION_TTL_SECONDS == 30.0
