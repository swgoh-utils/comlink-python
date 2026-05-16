# coding=utf-8
"""Shape-level sanity tests — less brittle than full goldens.

Goldens (in :mod:`test_endpoint_goldens`) catch *any* drift. These tests
encode the structural promises the SDK makes to callers — the contracts
Phase 3's Struct rewrite must preserve. A failure here is a louder signal
than a golden diff: it means a *semantically* important field changed,
not just a value within an expected shape.

Each test calls the SDK exactly the same way as the corresponding golden
test, then asserts on top-level keys, expected types, and a handful of
load-bearing path values. Keep these tests small — every assertion is a
constraint Phase 3 inherits.
"""

from __future__ import annotations

from typing import Any

import pytest

# ── /metadata ────────────────────────────────────────────────────────────────


def test_metadata_has_version_fields(recorded_comlink: Any) -> None:
    """Both ``latestGamedataVersion`` and ``latestLocalizationBundleVersion``
    must be present — `GameDataCache` (Phase 7) keys on these."""
    md = recorded_comlink.get_game_metadata()
    assert isinstance(md, dict)
    assert isinstance(md.get("latestGamedataVersion"), str) and md["latestGamedataVersion"]
    assert isinstance(md.get("latestLocalizationBundleVersion"), str) and md["latestLocalizationBundleVersion"]
    assert isinstance(md.get("latestSegmentedContentVersion"), str)


# ── /player ──────────────────────────────────────────────────────────────────


def test_player_has_identity_and_roster(cassette_server: Any, recorded_comlink: Any) -> None:
    """``get_player`` returns the canonical player envelope.

    These fields anchor every downstream caller (bots, stat calc, builders).
    Phase 3 turns the dict into a Struct but the *names* and *types* below
    are part of the v3 API contract.
    """
    cassette_server.use("player", "player_large")
    p = recorded_comlink.get_player(allycode=314927874)
    assert isinstance(p, dict)
    # Identity
    assert isinstance(p.get("name"), str) and p["name"]
    assert isinstance(p.get("allyCode"), str)
    assert isinstance(p.get("level"), int)
    # Guild affiliation (may be empty string but key must exist)
    assert "guildId" in p
    assert "guildName" in p
    # Roster
    assert isinstance(p.get("rosterUnit"), list)
    assert len(p["rosterUnit"]) > 0


def test_player_roster_units_have_required_fields(cassette_server: Any, recorded_comlink: Any) -> None:
    """Each unit in ``rosterUnit`` must carry the keys StatCalc relies on."""
    cassette_server.use("player", "player_large")
    p = recorded_comlink.get_player(allycode=314927874)
    unit = p["rosterUnit"][0]
    for required in ("definitionId", "currentLevel", "currentRarity", "currentTier"):
        assert required in unit, f"player.rosterUnit[0] missing required key '{required}'"
    # Equipped mods carry their own shape
    assert isinstance(unit.get("equippedStatMod"), list)


def test_player_small_smaller_than_large(cassette_server: Any, recorded_comlink: Any) -> None:
    """The two cassettes represent meaningfully different scale.

    Phase 3 / Phase 4 latency comparisons rely on this distinction holding.
    """
    cassette_server.use("player", "player_small")
    small = recorded_comlink.get_player(allycode=855566316)
    cassette_server.use("player", "player_large")
    large = recorded_comlink.get_player(allycode=314927874)
    assert len(small["rosterUnit"]) < len(large["rosterUnit"]) // 2


# ── /guild ───────────────────────────────────────────────────────────────────


def test_guild_unwrapped_envelope(recorded_comlink: Any) -> None:
    """``get_guild`` must unwrap the comlink ``"guild"`` envelope.

    The raw cassette wraps the payload in ``{"guild": {...}}``; the SDK
    contract is to return the inner dict directly. Phase 3 inherits this
    contract — the Struct returned from ``get_guild`` represents the guild
    itself, not the envelope.
    """
    g = recorded_comlink.get_guild(guild_id="GbsabjvbQESUd8r_qPqdYg")
    assert isinstance(g, dict)
    # Should NOT have a nested "guild" key (that would mean the unwrap regressed)
    assert "guild" not in g, "get_guild() leaked the envelope back to the caller"
    # Must have the actual guild fields
    assert "profile" in g
    assert isinstance(g.get("member"), list)


# ── /getLeaderboard ──────────────────────────────────────────────────────────


def test_leaderboard_envelope(recorded_comlink: Any) -> None:
    """Type-6 (global) leaderboard returns a list of leaderboard rows under ``"player"``."""
    lb = recorded_comlink.get_leaderboard(leaderboard_type=6, league="kyber", division=1)
    assert isinstance(lb, dict)
    assert "leaderboard" in lb
    assert isinstance(lb.get("player"), list)
    if lb["player"]:
        row = lb["player"][0]
        assert "name" in row
        assert "memberId" in row or "playerId" in row


# ── /data ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "segment_key",
    [
        "ability",
        "units",  # character/ship definitions (~11k items)
        "skill",
        "category",
        "effect",
        "equipment",
        "statMod",
        "statModSet",
    ],
)
def test_data_segment_key_exists(recorded_comlink: Any, segment_key: str) -> None:
    """``get_game_data`` returns every load-bearing segment.

    Phase 7's :class:`GameDataCache` slices ``/data`` by these keys. Missing
    one means the cache loses an entire segment silently.
    """
    data = recorded_comlink.get_game_data(request_segment=0, version="x")
    assert segment_key in data, f"/data missing segment '{segment_key}'"
    assert isinstance(data[segment_key], list)


# ── /localization ────────────────────────────────────────────────────────────


def test_localization_has_locale_content(recorded_comlink: Any) -> None:
    """``get_localization(locale='ENG_US', unzip=True)`` returns the locale payload.

    The unzipped form is the decoded bytes from the comlink's gzipped bundle;
    the SDK returns whatever the upstream sends. Shape varies (dict / str /
    list); the contract is non-empty.
    """
    loc = recorded_comlink.get_localization(localization_id="x", locale="ENG_US", unzip=True)
    assert loc, "/localization returned empty payload"
    # Whatever shape it is, it should be substantial
    if isinstance(loc, str | bytes):
        assert len(loc) > 1024
    elif isinstance(loc, dict | list):
        assert len(loc) > 0
