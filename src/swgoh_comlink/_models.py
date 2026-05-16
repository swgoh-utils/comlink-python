# coding=utf-8
"""Typed response models (``msgspec.Struct``) + cached decoders.

Phase 3 design notes:

* **Naming.** ``rename="camel"`` lets fields be defined in snake_case
  Python (``roster_unit``) while matching comlink's camelCase wire format
  (``rosterUnit``) without per-field aliases.
* **Unknown fields.** ``forbid_unknown_fields=False`` so comlink adding
  new fields doesn't break v3 clients overnight. The known fields are
  the contract; extras are silently dropped.
* **`gc=False`.** Per msgspec docs, leaf structs with no back-references
  to other Structs get a ~75x GC speedup. We apply it to "leaf" types
  (:class:`Skill`, :class:`Mod`, etc.) and leave container types
  (:class:`Player`, :class:`Guild`) at the default ``gc=True``.
* **Typing depth.** v3.0 ships *medium-depth* typing: the top-level
  response shape is fully typed, the big-list sub-types (RosterUnit,
  Mod) are typed, and fully-dynamic sub-fields stay as ``dict[str, Any]``
  to keep the surface manageable. Deeper typing of e.g. ``primaryStat``
  shapes is a v3.1 candidate once real users tell us what they touch.
* **/data and /localization** stay untyped: 82 segments and arbitrary
  locale shapes respectively. They still get msgspec's parser-speed win
  via the shared untyped decoder.

Public exports: every Struct type plus module-level decoders. Endpoint
methods on :class:`SwgohComlink` / :class:`SwgohComlinkAsync` pick a
decoder via :func:`decoder_for`.
"""

from __future__ import annotations

from typing import Any, TypeVar

import msgspec

__all__ = [
    # Decoders
    "GUILD_DECODER",
    "LEADERBOARD_DECODER",
    "METADATA_DECODER",
    "PLAYER_DECODER",
    "UNTYPED_DECODER",
    # Types
    "Guild",
    "GuildEnvelope",
    "GuildProfile",
    "LeaderboardEnvelope",
    "LeaderboardResponse",
    "Member",
    "Metadata",
    "Mod",
    "ModStat",
    "Player",
    "Relic",
    "RosterUnit",
    "Skill",
    # Helpers
    "decoder_for",
]

T = TypeVar("T")


# ── Base config ─────────────────────────────────────────────────────────────


class _StructBase(
    msgspec.Struct,
    rename="camel",
    forbid_unknown_fields=False,
):
    """Common base: camelCase wire mapping, ignore unknown fields."""


class _LeafStruct(
    msgspec.Struct,
    rename="camel",
    forbid_unknown_fields=False,
    gc=False,
):
    """Leaf-flavored base: opts into the ``gc=False`` ~75x GC speedup.

    Use for Structs that *don't* hold references back into longer-lived
    container Structs (otherwise GC would not be able to collect cycles).
    """


# ── /metadata ───────────────────────────────────────────────────────────────


class Metadata(_StructBase):
    """`/metadata` envelope. Small (19 fields)."""

    asset_path: str = ""
    asset_subpath: str = ""
    asset_version: int = 0
    client_cache: list[Any] = msgspec.field(default_factory=list)
    config: list[Any] = msgspec.field(default_factory=list)
    debug_mode: bool = False
    eadp_parameters: dict[str, Any] = msgspec.field(default_factory=dict)
    gamedata_revision: str = ""
    latest_gamedata_version: str = ""
    latest_localization_bundle_version: str = ""
    latest_localization_revision: str = ""
    latest_segmented_content_version: str = ""
    mono_extra_memory_allocation_divisor: int = 0
    quality_data: dict[str, Any] = msgspec.field(default_factory=dict)
    resource_cache_memory_limit: int = 0
    server_property: list[Any] = msgspec.field(default_factory=list)
    server_timestamp: str = ""
    server_version: str = ""
    tex_format: str = ""


# ── /player and nested ──────────────────────────────────────────────────────


class Skill(_LeafStruct):
    """One skill on a roster unit. Just an id + tier."""

    id: str = ""
    tier: int = 0


class ModStat(_LeafStruct):
    """Mod stat. Used in :class:`Mod`."""

    stat: dict[str, Any] = msgspec.field(default_factory=dict)
    roll: list[int] = msgspec.field(default_factory=list)
    stat_rolls: int = 0
    stat_roller_bounds_max: str = ""
    stat_roller_bounds_min: str = ""
    unscaled_roll_value: list[str] = msgspec.field(default_factory=list)


class Mod(_LeafStruct):
    """One equipped stat mod. Big list per roster unit (typically 6 per unit)."""

    bonus_quantity: int = 0
    converted_item: dict[str, Any] | None = None
    definition_id: str = ""
    id: str = ""
    level: int = 0
    level_cost: dict[str, Any] = msgspec.field(default_factory=dict)
    locked: bool = False
    primary_stat: dict[str, Any] = msgspec.field(default_factory=dict)
    remove_cost: dict[str, Any] = msgspec.field(default_factory=dict)
    rerolled_count: int = 0
    secondary_stat: list[dict[str, Any]] = msgspec.field(default_factory=list)
    sell_value: dict[str, Any] = msgspec.field(default_factory=dict)
    tier: int = 0
    xp: int = 0


class Relic(_LeafStruct):
    """Relic tier object on a roster unit. Just ``{"currentTier": n}``."""

    current_tier: int = 0


class RosterUnit(_StructBase):
    """One unit in a player's roster. Up to ~400 of these per player."""

    id: str = ""
    definition_id: str = ""
    current_level: int = 0
    current_rarity: int = 0
    current_tier: int = 0
    current_xp: int = 0
    equipment: list[dict[str, Any]] = msgspec.field(default_factory=list)
    equipped_stat_mod: list[Mod] = msgspec.field(default_factory=list)
    equipped_stat_mod_old: list[Any] = msgspec.field(default_factory=list)
    promotion_recipe_reference: str = ""
    purchased_ability_id: list[str] = msgspec.field(default_factory=list)
    relic: Relic | None = None
    skill: list[Skill] = msgspec.field(default_factory=list)
    unit_stat: dict[str, Any] | None = None


class Player(_StructBase):
    """`/player` envelope. ~26 top-level fields; deepest nesting is roster."""

    # Identity
    name: str = ""
    ally_code: str = ""
    player_id: str = ""
    nucleus_id: str = ""
    level: int = 0
    last_activity_time: str = ""
    local_time_zone_offset_minutes: int = 0
    # Guild affiliation
    guild_id: str = ""
    guild_name: str = ""
    guild_type_id: str = ""
    guild_banner_color: str = ""
    guild_banner_logo: str = ""
    guild_logo_background: str = ""
    # Roster + collections
    roster_unit: list[RosterUnit] = msgspec.field(default_factory=list)
    datacron: list[dict[str, Any]] = msgspec.field(default_factory=list)
    era_unit_status: list[dict[str, Any]] = msgspec.field(default_factory=list)
    loaned_unit_era_level: int = 0
    profile_stat: list[dict[str, Any]] = msgspec.field(default_factory=list)
    pvp_profile: list[dict[str, Any]] = msgspec.field(default_factory=list)
    season_status: list[dict[str, Any]] = msgspec.field(default_factory=list)
    lifetime_season_score: str = ""
    player_rating: dict[str, Any] = msgspec.field(default_factory=dict)
    # Both selectedPlayer{Portrait,Title} are null on accounts that
    # haven't picked one yet — observed on the small_roster cassette.
    selected_player_portrait: dict[str, Any] | None = None
    selected_player_title: dict[str, Any] | None = None
    unlocked_player_portrait: list[dict[str, Any]] = msgspec.field(default_factory=list)
    unlocked_player_title: list[dict[str, Any]] = msgspec.field(default_factory=list)


# ── /guild and nested ───────────────────────────────────────────────────────


class Member(_StructBase):
    """One guild member entry. Up to 50 per guild.

    Field shapes verified against the recorded cassette — strings where
    comlink returns strings, dict[str, Any] reserved for genuinely
    nested data.
    """

    player_id: str = ""
    nucleus_id: str = ""
    player_name: str = ""
    player_level: int = 0
    member_level: int = 0
    galactic_power: str = ""
    ship_galactic_power: str = ""
    character_galactic_power: str = ""
    squad_power: int = 0
    league_id: str = ""
    last_activity_time: str = ""
    guild_join_time: str = ""
    guild_xp: int = 0
    lifetime_season_score: str = ""
    player_title: str = ""
    player_portrait: str = ""
    member_contribution: list[dict[str, Any]] = msgspec.field(default_factory=list)
    season_status: list[dict[str, Any]] = msgspec.field(default_factory=list)


class GuildProfile(_StructBase):
    """Guild profile (the rich metadata)."""

    id: str = ""
    name: str = ""
    level: int = 0
    level_requirement: int = 0
    member_count: int = 0
    member_max: int = 0
    rank: int = 0
    trophy: int = 0
    raid_win: int = 0
    enrollment_status: int = 0
    banner_color_id: str = ""
    banner_logo_id: str = ""
    logo_background: str = ""
    chat_channel_id: str = ""
    external_message_key: str = ""
    guild_type: str = ""
    guild_galactic_power: str = ""
    guild_galactic_power_for_requirement: str = ""
    leaderboard_score: str = ""
    auto_launch_config: dict[str, Any] = msgspec.field(default_factory=dict)
    single_launch_config: dict[str, Any] = msgspec.field(default_factory=dict)
    raid_launch_config: list[dict[str, Any]] = msgspec.field(default_factory=list)
    guild_event_tracker: list[dict[str, Any]] = msgspec.field(default_factory=list)
    message_criteria_key: list[str] = msgspec.field(default_factory=list)


class Guild(_StructBase):
    """`/guild` envelope after the SDK's `"guild"` unwrap."""

    profile: GuildProfile = msgspec.field(default_factory=GuildProfile)
    member: list[Member] = msgspec.field(default_factory=list)
    guild_events: list[dict[str, Any]] = msgspec.field(default_factory=list)
    next_challenges_refresh: str = ""
    inventory: dict[str, Any] | None = None
    invite_status: list[dict[str, Any]] = msgspec.field(default_factory=list)
    progress: dict[str, Any] | None = None
    room_available: list[dict[str, Any]] = msgspec.field(default_factory=list)
    raid_status: list[dict[str, Any]] = msgspec.field(default_factory=list)
    raid_result: list[dict[str, Any]] = msgspec.field(default_factory=list)
    last_raid_points_summary: list[dict[str, Any]] = msgspec.field(default_factory=list)
    recent_raid_result: list[dict[str, Any]] = msgspec.field(default_factory=list)
    recent_territory_battle_result: list[dict[str, Any]] = msgspec.field(default_factory=list)
    recent_territory_war_result: list[dict[str, Any]] = msgspec.field(default_factory=list)
    territory_battle_result: list[dict[str, Any]] = msgspec.field(default_factory=list)
    territory_battle_status: list[dict[str, Any]] = msgspec.field(default_factory=list)
    territory_war_status: list[dict[str, Any]] = msgspec.field(default_factory=list)
    stat: list[dict[str, Any]] = msgspec.field(default_factory=list)


class GuildEnvelope(_StructBase):
    """Some comlink versions wrap guild data in a `"guild"` field; some don't.

    The decoder tries this envelope first; if ``guild`` is None, the
    response was already unwrapped and falls back to a direct
    :class:`Guild` decode.
    """

    guild: Guild | None = None


# ── /getLeaderboard ─────────────────────────────────────────────────────────


class LeaderboardEnvelope(_StructBase):
    """One leaderboard within the response (when there are multiple).

    Note on typing depth: each player entry has many shape variants
    depending on whether the entry is a current player, a placeholder,
    or a guild-affiliated user. Rather than enumerate all fields (and
    drop unknown ones via msgspec's default), entries stay as
    ``dict[str, Any]`` — full fidelity preserved. Phase 3 prioritized
    Player and Guild for deep typing; Leaderboard's entry shape is a
    later candidate when there's a real user need.
    """

    id: str = ""
    player: list[dict[str, Any]] = msgspec.field(default_factory=list)
    player_status: dict[str, Any] | None = None


class LeaderboardResponse(_StructBase):
    """`/getLeaderboard` envelope."""

    leaderboard: list[LeaderboardEnvelope] = msgspec.field(default_factory=list)
    player: list[dict[str, Any]] = msgspec.field(default_factory=list)
    player_status: dict[str, Any] | None = None


# ── Decoders (one per response type; cached at module load) ─────────────────

PLAYER_DECODER: msgspec.json.Decoder[Player] = msgspec.json.Decoder(Player)
METADATA_DECODER: msgspec.json.Decoder[Metadata] = msgspec.json.Decoder(Metadata)
GUILD_DECODER: msgspec.json.Decoder[Guild] = msgspec.json.Decoder(Guild)
_GUILD_ENVELOPE_DECODER: msgspec.json.Decoder[GuildEnvelope] = msgspec.json.Decoder(GuildEnvelope)
LEADERBOARD_DECODER: msgspec.json.Decoder[LeaderboardResponse] = msgspec.json.Decoder(LeaderboardResponse)
UNTYPED_DECODER: msgspec.json.Decoder[Any] = msgspec.json.Decoder()


# Lookup so the request path can pick a decoder by target type.
_DECODER_BY_TYPE: dict[type, msgspec.json.Decoder[Any]] = {
    Player: PLAYER_DECODER,
    Metadata: METADATA_DECODER,
    Guild: GUILD_DECODER,
    LeaderboardResponse: LEADERBOARD_DECODER,
}


def decoder_for(target: type | None) -> msgspec.json.Decoder[Any]:
    """Return the cached decoder for *target*, or the untyped decoder for ``None``."""
    if target is None:
        return UNTYPED_DECODER
    decoder = _DECODER_BY_TYPE.get(target)
    if decoder is None:
        # Build + cache on first use for ad-hoc types (Phase 7 cache may want this).
        decoder = msgspec.json.Decoder(target)
        _DECODER_BY_TYPE[target] = decoder
    return decoder


# ── Guild decode helper (handles the optional "guild" envelope wrap) ────────


def decode_guild(content: bytes) -> Guild:
    """Decode a `/guild` response, accepting both wrapped and unwrapped forms.

    Comlink may return either ``{"guild": {...}}`` or ``{...}`` (the inner
    guild fields at top level). v2's SDK had a defensive unwrap; v3
    preserves that behavior here so downstream callers always receive a
    :class:`Guild` representing the guild itself, never an envelope.
    """
    envelope = _GUILD_ENVELOPE_DECODER.decode(content)
    if envelope.guild is not None:
        return envelope.guild
    return GUILD_DECODER.decode(content)
