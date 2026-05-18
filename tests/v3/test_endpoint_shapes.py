# coding=utf-8
"""Shape-level sanity tests — less brittle than full goldens.

Goldens (in :mod:`test_endpoint_goldens`) catch *any* drift. These tests
encode the structural promises the v3 SDK makes to callers — the contracts
Phase 4 and beyond inherit. A failure here is a louder signal than a
golden diff: it means a *semantically* important field changed.

Attribute-access tests use the ``recorded_comlink_typed`` fixture (typed
:class:`swgoh_comlink.typed.SwgohComlink`). Dict-passthrough tests
(``/data``, ``/localization``) use the default :func:`recorded_comlink`
(dict-default :class:`swgoh_comlink.SwgohComlink`).

The ``raw=True`` path on the typed client still returns dict-shaped data
and is covered separately.
"""

from __future__ import annotations

from typing import Any

import pytest

# ── /metadata ────────────────────────────────────────────────────────────────


def test_metadata_has_version_fields(recorded_comlink_typed: Any) -> None:
    """Both ``latest_gamedata_version`` and ``latest_localization_bundle_version``
    must be present — `GameDataCache` (Phase 7) keys on these."""
    md = recorded_comlink_typed.get_game_metadata()
    assert md.latest_gamedata_version, "metadata missing gamedata version"
    assert md.latest_localization_bundle_version, "metadata missing localization version"
    assert isinstance(md.latest_segmented_content_version, str)


# ── /player ──────────────────────────────────────────────────────────────────


def test_player_has_identity_and_roster(cassette_server: Any, recorded_comlink_typed: Any) -> None:
    """``get_player`` returns the canonical player envelope.

    Phase 3 turns the dict into a Struct; the *names* (snake_case) and
    *types* below are part of the v3 API contract.
    """
    cassette_server.use("player", "player_large")
    p = recorded_comlink_typed.get_player(allycode=314927874)
    # Identity
    assert p.name
    assert p.ally_code
    assert isinstance(p.level, int) and p.level > 0
    # Guild affiliation (fields exist; may be empty)
    assert hasattr(p, "guild_id")
    assert hasattr(p, "guild_name")
    # Roster
    assert isinstance(p.roster_unit, list)
    assert len(p.roster_unit) > 0


def test_player_roster_units_have_required_fields(cassette_server: Any, recorded_comlink_typed: Any) -> None:
    """Each unit in ``roster_unit`` carries the keys StatCalc relies on."""
    cassette_server.use("player", "player_large")
    p = recorded_comlink_typed.get_player(allycode=314927874)
    unit = p.roster_unit[0]
    assert unit.definition_id
    assert isinstance(unit.current_level, int)
    assert isinstance(unit.current_rarity, int)
    assert isinstance(unit.current_tier, int)
    # Equipped mods are typed Mods
    assert isinstance(unit.equipped_stat_mod, list)


def test_player_small_smaller_than_large(cassette_server: Any, recorded_comlink_typed: Any) -> None:
    """The two cassettes represent meaningfully different scale.

    Phase 3 / Phase 4 latency comparisons rely on this distinction.
    """
    cassette_server.use("player", "player_small")
    small = recorded_comlink_typed.get_player(allycode=855566316)
    cassette_server.use("player", "player_large")
    large = recorded_comlink_typed.get_player(allycode=314927874)
    assert len(small.roster_unit) < len(large.roster_unit) // 2


def test_player_raw_returns_dict_unchanged(cassette_server: Any, recorded_comlink_typed: Any) -> None:
    """``raw=True`` on the typed client returns the v2 dict shape unchanged."""
    cassette_server.use("player", "player_large")
    p = recorded_comlink_typed.get_player(allycode=314927874, raw=True)
    assert isinstance(p, dict)
    assert p["name"]
    assert isinstance(p["rosterUnit"], list)


# ── /guild ───────────────────────────────────────────────────────────────────


def test_guild_unwrapped_envelope(recorded_comlink_typed: Any) -> None:
    """``get_guild`` returns a :class:`Guild` Struct (not the raw envelope)."""
    g = recorded_comlink_typed.get_guild(guild_id="GbsabjvbQESUd8r_qPqdYg")
    # Should expose guild fields directly (no nested "guild" attribute).
    assert g.profile.name
    assert isinstance(g.member, list)
    assert len(g.member) > 0
    # Members are typed
    m = g.member[0]
    assert m.player_id


def test_guild_raw_keeps_dict_shape(recorded_comlink_typed: Any) -> None:
    g = recorded_comlink_typed.get_guild(guild_id="GbsabjvbQESUd8r_qPqdYg", raw=True)
    assert isinstance(g, dict)
    assert "profile" in g
    assert isinstance(g["member"], list)


# ── /getLeaderboard ──────────────────────────────────────────────────────────


def test_leaderboard_envelope(recorded_comlink_typed: Any) -> None:
    """Type-6 (global) leaderboard returns a typed envelope with raw player entries."""
    lb = recorded_comlink_typed.get_leaderboard(leaderboard_type=6, league="kyber", division=1)
    assert isinstance(lb.leaderboard, list)
    assert isinstance(lb.player, list)
    # Per-leaderboard player list (entries kept as dict to preserve full content)
    if lb.leaderboard and lb.leaderboard[0].player:
        row = lb.leaderboard[0].player[0]
        assert "name" in row or "playerId" in row


# ── /data (passthrough — dict return) ───────────────────────────────────────


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
    """``get_game_data`` returns every load-bearing segment as a passthrough dict."""
    data = recorded_comlink.get_game_data(request_segment=0, version="x")
    assert segment_key in data, f"/data missing segment '{segment_key}'"
    assert isinstance(data[segment_key], list)


# ── /localization (passthrough) ─────────────────────────────────────────────


def test_localization_has_locale_content(recorded_comlink: Any) -> None:
    """``get_localization(locale='ENG_US', unzip=True)`` returns the locale payload."""
    loc = recorded_comlink.get_localization(localization_id="x", locale="ENG_US", unzip=True)
    assert loc, "/localization returned empty payload"
    if isinstance(loc, str | bytes):
        assert len(loc) > 1024
    elif isinstance(loc, dict | list):
        assert len(loc) > 0
