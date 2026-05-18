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

from typing import Any, TypeVar, cast

import msgspec

__all__ = [
    # Decoders
    "GUILD_DECODER",
    "LEADERBOARD_DECODER",
    "METADATA_DECODER",
    "PLAYER_DECODER",
    "UNTYPED_DECODER",
    # Types — top-level
    "Guild",
    "GuildEnvelope",
    "GuildProfile",
    "LeaderboardEnvelope",
    "LeaderboardResponse",
    "Member",
    "Metadata",
    "Player",
    # Types — RosterUnit nesting
    "Mod",
    "PrimaryStat",
    "Relic",
    "RosterUnit",
    "SecondaryStat",
    "Skill",
    "StatValue",
    # Types — Player nesting
    "CurrencyCost",
    "Datacron",
    "DatacronAffix",
    "EraUnitStatus",
    "IdRef",
    "PlayerRankStatus",
    "PlayerRating",
    "PlayerSkillRating",
    "ProfileStat",
    "PvpProfileEntry",
    "SeasonStatusEntry",
    "Squad",
    "SquadCell",
    "SquadDatacron",
    # Helpers
    "decoder_for",
    "decode_guild",
    "decode_guild_dict",
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
#
# Phase 3.5 deepens these. The leaf types (StatValue, CurrencyCost,
# DatacronAffix, etc.) use ``gc=False`` because they're truly terminal —
# they reference only primitives, lists of primitives, or other gc=False
# leaves. Container types (Mod, Datacron, Squad, RosterUnit, Player)
# stay gc=True so they can be collected when referenced from cycles.


class Skill(_LeafStruct):
    """One skill on a roster unit. Just an id + tier."""

    id: str = ""
    tier: int = 0


# ── Mod stat shape ──────────────────────────────────────────────────────────


class StatValue(_LeafStruct):
    """The inner ``stat`` object of a :class:`PrimaryStat` / :class:`SecondaryStat`.

    Comlink ships scalar/unscaled in string form (BigInteger over the wire);
    we preserve that — converting to int loses precision for high-roll mods.
    """

    unit_stat_id: int = 0
    scalar: str = "0"
    stat_value_decimal: str = "0"
    ui_display_override_value: str = "-1"
    unscaled_decimal_value: str = "0"


class PrimaryStat(_LeafStruct):
    """Mod primary stat (1 per mod)."""

    stat: StatValue = msgspec.field(default_factory=StatValue)
    roll: list[str] = msgspec.field(default_factory=list)
    stat_rolls: int = 0
    stat_roller_bounds_max: str = "0"
    stat_roller_bounds_min: str = "0"
    unscaled_roll_value: list[str] = msgspec.field(default_factory=list)


class SecondaryStat(_LeafStruct):
    """Mod secondary stat (up to 4 per mod). Same shape as :class:`PrimaryStat`."""

    stat: StatValue = msgspec.field(default_factory=StatValue)
    roll: list[str] = msgspec.field(default_factory=list)
    stat_rolls: int = 0
    stat_roller_bounds_max: str = "0"
    stat_roller_bounds_min: str = "0"
    unscaled_roll_value: list[str] = msgspec.field(default_factory=list)


class CurrencyCost(_LeafStruct):
    """Reused by ``level_cost``, ``remove_cost``, ``sell_value`` (same shape)."""

    bonus_quantity: int = 0
    currency: int = 0
    quantity: str = "0"


class Mod(_LeafStruct):
    """One equipped stat mod. Big list per roster unit (typically 6 per unit).

    Phase 3.5: nested Stat / CurrencyCost types swapped in. This is the
    largest single typing change in the player graph — ~2,400 Mods per
    large-roster player x 5 typed sub-structs each = ~12,000 newly
    slotted objects.
    """

    bonus_quantity: int = 0
    converted_item: dict[str, Any] | None = None
    definition_id: str = ""
    id: str = ""
    level: int = 0
    level_cost: CurrencyCost = msgspec.field(default_factory=CurrencyCost)
    locked: bool = False
    primary_stat: PrimaryStat = msgspec.field(default_factory=PrimaryStat)
    remove_cost: CurrencyCost = msgspec.field(default_factory=CurrencyCost)
    rerolled_count: int = 0
    secondary_stat: list[SecondaryStat] = msgspec.field(default_factory=list)
    sell_value: CurrencyCost = msgspec.field(default_factory=CurrencyCost)
    tier: int = 0
    xp: int = 0


class Relic(_LeafStruct):
    """Relic tier object on a roster unit. Just ``{"currentTier": n}``."""

    current_tier: int = 0


# ── RosterUnit ──────────────────────────────────────────────────────────────


class RosterUnit(_StructBase):
    """One unit in a player's roster. Up to ~400 of these per player."""

    id: str = ""
    definition_id: str = ""
    current_level: int = 0
    current_rarity: int = 0
    current_tier: int = 0
    current_xp: int = 0
    # equipment items are always observed empty in current cassettes — leave
    # as Any. When users start hitting non-empty equipment, type this.
    equipment: list[Any] = msgspec.field(default_factory=list)
    equipped_stat_mod: list[Mod] = msgspec.field(default_factory=list)
    equipped_stat_mod_old: list[Any] = msgspec.field(default_factory=list)
    promotion_recipe_reference: str = ""
    purchased_ability_id: list[str] = msgspec.field(default_factory=list)
    relic: Relic | None = None
    skill: list[Skill] = msgspec.field(default_factory=list)
    # unit_stat is observed null across the cassette — keep flexible.
    unit_stat: dict[str, Any] | None = None


# ── Player-level nested types ───────────────────────────────────────────────


class DatacronAffix(_LeafStruct):
    """One affix on a datacron (up to 9 per datacron)."""

    ability_id: str = ""
    required_relic_tier: int = 0
    required_unit_tier: int = 0
    scope_icon: str = ""
    stat_type: int = 0
    stat_value: str = "0"
    tag: list[str] = msgspec.field(default_factory=list)
    target_rule: str = ""


class Datacron(_StructBase):
    """One datacron on a player. Player-level shape has the full reroll
    bookkeeping; squad-embedded datacrons use :class:`SquadDatacron` instead.
    """

    id: str = ""
    set_id: int = 0
    template_id: str = ""
    affix: list[DatacronAffix] = msgspec.field(default_factory=list)
    locked: bool = False
    focused: bool = False
    reroll_count: int = 0
    reroll_index: int = 0
    reroll_option: list[Any] = msgspec.field(default_factory=list)
    tag: list[str] = msgspec.field(default_factory=list)


class SquadDatacron(_StructBase):
    """Datacron as embedded in a saved squad (:class:`Squad.datacron`).

    Strict subset of :class:`Datacron`: no ``locked``, ``focused``, or
    ``reroll*`` (those live on the player-level shape only). Has its own
    ``highestTierApplied`` field which is *not* present on player-level
    datacrons. Modeled as a separate type to keep ``msgspec.to_builtins``
    round-trip byte-faithful against the wire.
    """

    id: str = ""
    set_id: int = 0
    template_id: str = ""
    affix: list[DatacronAffix] = msgspec.field(default_factory=list)
    tag: list[str] = msgspec.field(default_factory=list)
    highest_tier_applied: int = 0


class EraUnitStatus(_LeafStruct):
    """Per-era unit unlock status."""

    unit_base_id: str = ""
    era_level: int = 0


class ProfileStat(_LeafStruct):
    """One profile stat counter."""

    index: int = 0
    name_key: str = ""
    value: str = "0"
    version_key: str = ""


class SquadCell(_LeafStruct):
    """One cell in a saved-squad lineup."""

    cell_index: int = 0
    crew_battle_stat: list[Any] = msgspec.field(default_factory=list)
    forced_unit_era_level: int = 0
    inherit_from_definition_id: str = ""
    message_reticle: str = ""
    overkill_item: bool = False
    progress_item: bool = True
    selectable: bool = True
    squad_unit_type: int = 0
    unit_battle_stat: dict[str, Any] | None = None
    unit_def_id: str = ""
    unit_id: str = ""
    unit_state: dict[str, Any] | None = None


class Squad(_StructBase):
    """A saved-squad config (also embeds a datacron)."""

    cell: list[SquadCell] = msgspec.field(default_factory=list)
    datacron: SquadDatacron | None = None
    expire_time: str = "0"
    last_save_time: str = "0"
    squad_type: int = 0
    support_inherit_from_definition_id: str = ""
    targeting_set_id: str = ""
    targeting_tactic: int = 0


class PvpProfileEntry(_StructBase):
    """One PvP profile slot (arena/fleet/etc.)."""

    tab: int = 0
    rank: int = 0
    event_id: str = ""
    squad: Squad = msgspec.field(default_factory=Squad)


class SeasonStatusEntry(_LeafStruct):
    """One past/current GAC season status row."""

    season_id: str = ""
    event_instance_id: str = ""
    league: str = ""
    division: int = 0
    rank: int = 0
    wins: int = 0
    losses: int = 0
    season_points: int = 0
    join_time: str = "0"
    end_time: str = "0"
    remove: bool = False


class PlayerRankStatus(_LeafStruct):
    """Player's current league + division (inside :class:`PlayerRating`)."""

    league_id: str = ""
    division_id: int = 0


class PlayerSkillRating(_LeafStruct):
    """Player's skill rating (MMR-ish) (inside :class:`PlayerRating`)."""

    skill_rating: int = 0


class PlayerRating(_LeafStruct):
    """Aggregate of player league/division + skill rating."""

    player_rank_status: PlayerRankStatus = msgspec.field(default_factory=PlayerRankStatus)
    player_skill_rating: PlayerSkillRating = msgspec.field(default_factory=PlayerSkillRating)


class IdRef(_LeafStruct):
    """``{"id": str}`` for selected_player_portrait / title and unlocked_* lists."""

    id: str = ""


class Player(_StructBase):
    """`/player` envelope. ~26 top-level fields; the heavy nesting is roster."""

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
    # Roster + collections (Phase 3.5 typed)
    roster_unit: list[RosterUnit] = msgspec.field(default_factory=list)
    datacron: list[Datacron] = msgspec.field(default_factory=list)
    era_unit_status: list[EraUnitStatus] = msgspec.field(default_factory=list)
    loaned_unit_era_level: int = 0
    profile_stat: list[ProfileStat] = msgspec.field(default_factory=list)
    pvp_profile: list[PvpProfileEntry] = msgspec.field(default_factory=list)
    season_status: list[SeasonStatusEntry] = msgspec.field(default_factory=list)
    lifetime_season_score: str = "0"
    player_rating: PlayerRating = msgspec.field(default_factory=PlayerRating)
    # Both selectedPlayer{Portrait,Title} are null on accounts that haven't
    # picked one yet (observed on the small_roster cassette).
    selected_player_portrait: IdRef | None = None
    selected_player_title: IdRef | None = None
    unlocked_player_portrait: list[IdRef] = msgspec.field(default_factory=list)
    unlocked_player_title: list[IdRef] = msgspec.field(default_factory=list)


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


# ── /data.units segment (v3.1 probe — see decode_units_segment) ─────────────
#
# These Structs deep-type one segment of `/data` (the largest, ~11k items).
# All `_LeafStruct` (no back-references; gc=False for the ~75× GC speedup
# that matters at the per-unit scale).
#
# Field selection follows Phase 3.5 discipline:
#   - Type fields with observable shape in the cassette.
#   - Omit always-empty / always-null fields (`basicAttack`, `leaderAbility`,
#     `limitBreak`, `uniqueAbility`, `effectIconPriorityOverride`) — Comlink
#     can re-add them; `forbid_unknown_fields=False` drops silently.
#   - Sub-shapes that recur (the 12-field AbilityRef appears on basicAttackRef
#     / leaderAbilityRef / limitBreakRef[item] / uniqueAbilityRef[item]) share
#     a single Struct class.


class UnitStatEntry(_LeafStruct):
    """A single stat row inside ``baseStat.stat`` / ``unitTier[].baseStat.stat``."""

    unit_stat_id: int = 0
    stat_value_decimal: str = "0"
    unscaled_decimal_value: str = "0"
    ui_display_override_value: str = "-1"
    scalar: str = "0"


class UnitBaseStat(_LeafStruct):
    """Wraps the ``stat`` list (matches the on-the-wire ``baseStat`` shape)."""

    stat: list[UnitStatEntry] = msgspec.field(default_factory=list)


class AbilityRef(_LeafStruct):
    """Shared 12-field ref shape used by basic/leader/limit-break/unique ability refs."""

    ability_id: str = ""
    inherit_mapping_id: str = ""
    override_always_display_in_battle_ui: bool = False
    override_desc_key: str = ""
    override_icon: str = ""
    override_name_key: str = ""
    power_additive_tag: str = ""
    required_rarity: int = 0
    required_relic_tier: int = 0
    required_skill_tier: int = 0
    required_tier: int = 0
    unlock_recipe_id: str = ""


class SkillReference(_LeafStruct):
    skill_id: str = ""
    required_tier: int = 0
    required_rarity: int = 0
    required_relic_tier: int = 0


class RelicDefinition(_LeafStruct):
    relic_tier_definition_id: list[str] = msgspec.field(default_factory=list)
    upgrade_table_id: str = ""
    alignment_color_override: str = ""
    texture: str = ""
    name_key: str = ""


class UnitTierEntry(_LeafStruct):
    """One entry in ``unitTier`` — per-rarity gear+stat baseline."""

    tier: int = 0
    equipment_set: list[str] = msgspec.field(default_factory=list)
    base_stat: UnitBaseStat = msgspec.field(default_factory=UnitBaseStat)


class ModRecommendation(_LeafStruct):
    recommendation_set_id: str = ""
    unit_tier: int = 0


class ExampleSquadEntry(_LeafStruct):
    id: str = ""
    name: str = ""
    description_key: str = ""
    thumbnail: str = ""
    unit_def_id: list[str] = msgspec.field(default_factory=list)
    action_link: str | None = None
    show_requirement: dict[str, Any] | None = None
    hide_requirement: dict[str, Any] | None = None


class CrewMember(_LeafStruct):
    unit_id: str = ""
    slot: int = 0
    skilless_crew_ability_id: str = ""
    skill_reference: list[SkillReference] = msgspec.field(default_factory=list)


class SummonStatTableEntry(_LeafStruct):
    rarity: int = 0
    stat_table: str = ""


class Unit(_LeafStruct):
    """One unit definition from ``/data.units``.

    `forbid_unknown_fields=False` means future Comlink additions don't
    break decoding. Always-empty/always-null fields from the recording
    are deliberately omitted from this Struct — call `get_game_data`
    without `decode_units_segment` if you need them.
    """

    # Identity / display
    id: str = ""
    base_id: str = ""
    name_key: str = ""
    desc_key: str = ""
    unit_prefab: str = ""
    thumbnail_name: str = ""
    thumb_image_turn_order: str = ""
    era_thumbnail_name: str = ""
    battle_portrait_prefab: str = ""
    battle_portrait_name_key: str = ""
    battle_portrait_texture: str = ""

    # Game-mechanics scalars
    rarity: int = 0
    max_rarity: int = 0
    force_alignment: int = 0
    combat_type: int = 0
    unit_class: int = 0
    threat_level: int = 0
    base_power: int = 0
    primary_stat: str = ""
    primary_unit_stat: int = 0
    action_count_min: int = 0
    action_count_max: int = 0
    command_cost: int = 0
    squad_position_priority: int = 0
    max_level_override: int = 0
    training_xp_worth_base_value_override: int = 0
    training_cost_multiplier_override: int = 0

    # Booleans
    obtainable: bool = False
    legend: bool = False
    big: bool = False
    hide_in_turn_order: bool = False
    require_ultimate_unlock: bool = False
    loaned_unit: bool = False

    # String IDs / references
    xp_table_id: str = ""
    stat_progression_id: str = ""
    crew_contribution_table_id: str = ""
    promotion_recipe_reference: str = ""
    creation_recipe_reference: str = ""
    capital_unlock_key: str = ""
    associated_event_id: str = ""
    obtainable_time: str = "0"
    grant_start_time: str = "0"
    featured_end_time: str = "0"

    # Typed nesting (well-known shapes)
    base_stat: UnitBaseStat = msgspec.field(default_factory=UnitBaseStat)
    skill_reference: list[SkillReference] = msgspec.field(default_factory=list)
    relic_definition: RelicDefinition | None = None
    unit_tier: list[UnitTierEntry] = msgspec.field(default_factory=list)
    mod_recommendation: list[ModRecommendation] = msgspec.field(default_factory=list)
    example_squad: list[ExampleSquadEntry] = msgspec.field(default_factory=list)
    crew: list[CrewMember] = msgspec.field(default_factory=list)
    summon_stat_table: list[SummonStatTableEntry] = msgspec.field(default_factory=list)
    category_id: list[str] = msgspec.field(default_factory=list)

    # Ability refs — share the 12-field AbilityRef shape.
    basic_attack_ref: AbilityRef = msgspec.field(default_factory=AbilityRef)
    leader_ability_ref: AbilityRef | None = None
    limit_break_ref: list[AbilityRef] = msgspec.field(default_factory=list)
    unique_ability_ref: list[AbilityRef] = msgspec.field(default_factory=list)


# ── Shared /data sub-types (used across multiple segments) ──────────────────
#
# These leaf shapes recur across the 13 typed /data segments. Defined
# once here so the segment Structs below can compose them.


class MissionIdentifier(_LeafStruct):
    """5-field identifier on ``material.lookupMission[].missionIdentifier`` /
    ``equipment.lookupMission[].missionIdentifier`` / ``statMod.missionLookup[].missionIdentifier``."""

    campaign_id: str = ""
    campaign_map_id: str = ""
    campaign_mission_id: str = ""
    campaign_node_difficulty: int = 0
    campaign_node_id: str = ""


class MissionLookupEntry(_LeafStruct):
    """``lookupMission[]`` and ``missionLookup[]`` wrapper (mission + requirement IDs)."""

    mission_identifier: MissionIdentifier = msgspec.field(default_factory=MissionIdentifier)
    requirement_id: list[str] = msgspec.field(default_factory=list)


class EffectReference(_LeafStruct):
    """3-field reference on ``ability.effectReference[]`` and ``effect.effectReference[]``.

    Distinct from :class:`AbilityRef` (which has 12 fields and a different role).
    ``contextIndex`` is always empty in the recorded cassette → omitted.
    """

    id: str = ""
    max_bonus_move: int = 0


class DescriptiveTag(_LeafStruct):
    """2-field tag shape used as ``descriptiveTag[]``, ``effectedTag[]``,
    ``interactsWithTag[]`` across ability + effect segments."""

    exclude: bool = False
    tag: str = ""


class EffectTriggerCondition(_LeafStruct):
    """3-field condition on ``triggerCondition[]`` and ``expirationCondition[]``."""

    condition_type: int = 0
    condition_value: str = ""
    priority: int = 0


# ── /data.skill ─────────────────────────────────────────────────────────────


class SkillTier(_LeafStruct):
    is_omicron_tier: bool = False
    is_zeta_tier: bool = False
    power_override_tag: str = ""
    recipe_id: str = ""
    required_unit_level: int = 0
    required_unit_rarity: int = 0
    required_unit_relic_tier: int = 0
    required_unit_tier: int = 0


class SkillDefinition(_LeafStruct):
    """``/data.skill[]`` — the catalog entry. Distinct from the per-roster
    :class:`Skill` shape (which is just ``id + tier``)."""

    id: str = ""
    name_key: str = ""
    ability_reference: str = ""
    icon_key: str = ""
    is_zeta: bool = False
    omicron_mode: int = 0
    skill_type: int = 0
    tier: list[SkillTier] = msgspec.field(default_factory=list)


# ── /data.material ──────────────────────────────────────────────────────────


class Material(_LeafStruct):
    id: str = ""
    name_key: str = ""
    desc_key: str = ""
    icon_key: str = ""
    rarity: int = 0
    tier: int = 0
    type: int = 0
    obtainable_time: str = "0"
    recipe_id: str = ""
    unit_def_reference: str = ""
    sell_value: CurrencyCost = msgspec.field(default_factory=CurrencyCost)
    training_cost: int = 0
    training_cost_max_level: int = 0
    xp_value: int = 0
    lookup_mission: list[MissionLookupEntry] = msgspec.field(default_factory=list)
    # actionLinkLookup + raidLookup are populated only 3/858 times in the
    # cassette with a different shape; left as dict for fidelity.
    action_link_lookup: list[dict[str, Any]] = msgspec.field(default_factory=list)
    raid_lookup: list[dict[str, Any]] = msgspec.field(default_factory=list)


# ── /data.ability ───────────────────────────────────────────────────────────


class Ability(_LeafStruct):
    id: str = ""
    name_key: str = ""
    desc_key: str = ""
    short_desc_key: str = ""
    ability_type: int = 0
    icon: str = ""
    sub_icon: str = ""
    prefab_name: str = ""
    cooldown: int = 0
    cooldown_type: int = 0
    granted_priority: int = 0
    button_location: int = 0
    detail_location: int = 0
    stacking_line_override: str = ""
    apply_type_tooltip_key: str = ""
    blocked_loc_key: str = ""
    blocking_effect_id: str = ""
    ally_targeting_rule_id: str = ""
    always_display_in_battle_ui: bool = False
    hide_cooldown_description: bool = False
    highlight_when_ready_in_battle_ui: bool = False
    use_as_reinforcement_desc: bool = False
    effect_reference: list[EffectReference] = msgspec.field(default_factory=list)
    descriptive_tag: list[DescriptiveTag] = msgspec.field(default_factory=list)
    interacts_with_tag: list[DescriptiveTag] = msgspec.field(default_factory=list)
    triggered_condition: list[EffectTriggerCondition] = msgspec.field(default_factory=list)
    # Sparse / variable-shape sub-objects → keep as raw dicts.
    ai_params: dict[str, Any] | None = None
    confirmation_message: dict[str, Any] | None = None
    synergy: dict[str, Any] | None = None
    visual_target: dict[str, Any] | None = None
    tier: list[dict[str, Any]] = msgspec.field(default_factory=list)
    ultimate_charge_required: list[int] = msgspec.field(default_factory=list)


# ── /data.campaign ──────────────────────────────────────────────────────────


class CampaignNodeDifficultyGroup(_LeafStruct):
    campaign_node_difficulty: int = 0
    daily_battle_cap_key: str = ""
    grind_enabled: bool = False
    progress: int = 0
    unlock_requirement_localization_key: str = ""
    campaign_node: list[dict[str, Any]] = msgspec.field(default_factory=list)


class CampaignMap(_LeafStruct):
    id: str = ""
    daily_battle_cap_key: str = ""
    game_mode_key: str = ""
    grind_enabled: bool = False
    is_player_squad_supplied: bool = False
    progress: int = 0
    unlock_requirement_localization_key: str = ""
    campaign_node_difficulty_group: list[CampaignNodeDifficultyGroup] = msgspec.field(default_factory=list)


class Campaign(_LeafStruct):
    id: str = ""
    name_key: str = ""
    description_key: str = ""
    image: str = ""
    campaign_type: int = 0
    daily_battle_cap_key: str = ""
    grind_enabled: bool = False
    progress: int = 0
    unlock_requirement_localization_key: str = ""
    campaign_map: list[CampaignMap] = msgspec.field(default_factory=list)


# ── /data.effect ────────────────────────────────────────────────────────────


class EffectTarget(_LeafStruct):
    id: str = ""
    battle_deployment_state: int = 0
    battle_side: int = 0
    exclude_selected_target: bool = False
    exclude_self: bool = False
    health_state: int = 0
    unit_select: int = 0
    category: dict[str, Any] | None = None
    required_category: dict[str, Any] | None = None
    active_effect_tag_criteria: list[dict[str, Any]] = msgspec.field(default_factory=list)
    required_active_effect_tag_criteria: list[dict[str, Any]] = msgspec.field(default_factory=list)
    force_alignment: list[int] = msgspec.field(default_factory=list)
    unit_class: list[int] = msgspec.field(default_factory=list)
    stat_value: list[dict[str, Any]] = msgspec.field(default_factory=list)


class Effect(_LeafStruct):
    id: str = ""
    type: int = 0
    apply_type: int = 0
    apply_effect_enabled: bool = False
    apply_effect_label: str = ""
    blackboard_compare_name: str = ""
    blackboard_name: str = ""
    chance: int = 0
    damage_type: int = 0
    expire_on_application: bool = False
    icon_color: str = ""
    ignore_damage_animation: bool = False
    max_bonus_moves: int = 0
    additive_amount_decimal: str = "0"
    context_multiplier_decimal: int = 0
    multiplier_amount_decimal: int = 0
    result_variance_decimal: int = 0
    persistent_icon: str = ""
    persistent_icon_overlay: str = ""
    persistent_icon_groupable: bool = False
    persistent_icon_priority: int = 0
    persistent_loc_key: str = ""
    replace_table_id: str = ""
    stacking_line_override: str = ""
    trigger_on_application: bool = False
    triggered_loc_key: str = ""
    triggered_vfx: str = ""
    # Summon-related scalars.
    summon_count: int = 0
    summon_enable_initial_vfx: bool = False
    summon_era_level: int = 0
    summon_id: str = ""
    summon_level: int = 0
    summon_marker_index: int = 0
    summon_rarity: int = 0
    summon_squad_increase: int = 0
    summon_tier: int = 0
    # Typed nesting.
    target: list[EffectTarget] = msgspec.field(default_factory=list)
    trigger_condition: list[EffectTriggerCondition] = msgspec.field(default_factory=list)
    expiration_condition: list[EffectTriggerCondition] = msgspec.field(default_factory=list)
    effect_reference: list[EffectReference] = msgspec.field(default_factory=list)
    descriptive_tag: list[DescriptiveTag] = msgspec.field(default_factory=list)
    effected_tag: list[DescriptiveTag] = msgspec.field(default_factory=list)
    # Sparse / mixed-shape sub-fields → dicts.
    persistent_vfx_reference: dict[str, Any] | None = None
    context_index: list[int] = msgspec.field(default_factory=list)
    param: list[str] = msgspec.field(default_factory=list)
    infinite_cycle_effect: list[str] = msgspec.field(default_factory=list)
    # summonEffect recursively embeds Effect (19/60015 entries); keep as dict
    # to avoid recursive-type complexity for a sparse field.
    summon_effect: list[dict[str, Any]] = msgspec.field(default_factory=list)


# ── /data.equipment ─────────────────────────────────────────────────────────


class EquipmentStat(_LeafStruct):
    """Wrapper holding the ``stat`` list (UnitStatEntry reused from units probe)."""

    stat: list[UnitStatEntry] = msgspec.field(default_factory=list)


class Equipment(_LeafStruct):
    id: str = ""
    name_key: str = ""
    icon_key: str = ""
    mark: str = ""
    type: int = 0
    tier: int = 0
    required_level: int = 0
    required_rarity: int = 0
    find_flow_disabled: bool = False
    obtainable_time: str = "0"
    recipe_id: str = ""
    equipment_stat: EquipmentStat = msgspec.field(default_factory=EquipmentStat)
    sell_value: CurrencyCost = msgspec.field(default_factory=CurrencyCost)
    lookup_mission: list[MissionLookupEntry] = msgspec.field(default_factory=list)


# ── /data.recipe ────────────────────────────────────────────────────────────


class RecipeIngredient(_LeafStruct):
    """Reused for both ``recipe.ingredients[]`` and ``recipe.result`` (identical shape)."""

    id: str = ""
    type: int = 0
    rarity: int = 0
    min_quantity: int = 0
    max_quantity: int = 0
    preview_priority: int = 0
    primary_reward: bool = False
    unit_level: int = 0
    unit_tier: int = 0


class CraftRequirement(_LeafStruct):
    id: str = ""
    desc_key: str = ""
    eval_type: int = 0
    requirement_item: list[dict[str, Any]] = msgspec.field(default_factory=list)


class Recipe(_LeafStruct):
    id: str = ""
    desc_key: str = ""
    type: int = 0
    unlock_level: int = 0
    required_era_level: int = 0
    ingredients: list[RecipeIngredient] = msgspec.field(default_factory=list)
    craft_requirement: CraftRequirement | None = None
    result: RecipeIngredient | None = None


# ── /data.statMod ───────────────────────────────────────────────────────────


class StatMod(_LeafStruct):
    """All fields here are scalar references (FKs into other /data segments)."""

    id: str = ""
    name_key: str = ""
    desc_key: str = ""
    rarity: int = 0
    slot: int = 0
    set_id: str = ""
    level_table_id: str = ""
    overclock_recipe_table_id: str = ""
    promotion_id: str = ""
    promotion_recipe_id: str = ""
    reroll_cap_table_id: str = ""
    tier_up_recipe_table_id: str = ""
    mission_lookup: list[MissionLookupEntry] = msgspec.field(default_factory=list)


# ── /data.statModSet ────────────────────────────────────────────────────────


class StatModSetBonus(_LeafStruct):
    """Bonus carrier on ``completeBonus`` / ``maxLevelBonus`` (stat is a single
    UnitStatEntry, not a list)."""

    ability_id: list[str] = msgspec.field(default_factory=list)
    stat: UnitStatEntry = msgspec.field(default_factory=UnitStatEntry)


class StatModSet(_LeafStruct):
    id: str = ""
    name: str = ""
    icon: str = ""
    set_count: int = 0
    complete_bonus: StatModSetBonus = msgspec.field(default_factory=StatModSetBonus)
    max_level_bonus: StatModSetBonus = msgspec.field(default_factory=StatModSetBonus)


# ── /data.datacron* ─────────────────────────────────────────────────────────
#
# Fresh Structs — wire shapes diverge from the /player Datacron / DatacronAffix
# already defined in this module (e.g. /data carries min_tier/max_tier bounds
# and statValueMin/Max strings vs /player's single statValue).


class DataDatacronAffix(_LeafStruct):
    """``datacronAffixTemplateSet.affix[]`` — distinct from /player ``DatacronAffix``."""

    ability_id: str = ""
    max_tier: int = 0
    min_tier: int = 0
    scope_icon: str = ""
    stat_type: int = 0
    stat_value_max: str = "0"
    stat_value_min: str = "0"
    target_rule: str = ""
    tag: list[str] = msgspec.field(default_factory=list)


class DatacronAffixTemplateSet(_LeafStruct):
    id: str = ""
    affix: list[DataDatacronAffix] = msgspec.field(default_factory=list)


class DatacronTemplateTier(_LeafStruct):
    id: int = 0
    override_scope_identifier: int = 0
    override_upgrade_cost_recipe_id: str = ""
    required_relic_tier: int = 0
    required_unit_tier: int = 0
    affix_template_set_id: list[str] = msgspec.field(default_factory=list)
    initial_affix_template_set_ids: list[str] = msgspec.field(default_factory=list)


class DatacronTemplate(_LeafStruct):
    id: str = ""
    set_id: int = 0
    reference_template_id: str = ""
    focused_icon: str = ""
    focused_prefab: str = ""
    focused: bool = False
    allow_reroll: bool = False
    initial_tiers: int = 0
    max_rerolls: int = 0
    fixed_tag: list[str] = msgspec.field(default_factory=list)
    tier: list[DatacronTemplateTier] = msgspec.field(default_factory=list)


class DatacronSetTier(_LeafStruct):
    id: int = 0
    scope_identifier: int = 0
    dust_grant_recipe_id: str = ""
    upgrade_cost_recipe_id: str = ""
    reroll_cost_recipe_id: list[str] = msgspec.field(default_factory=list)


class DatacronSetMaterial(_LeafStruct):
    dust_grant_recipe_id: str = ""
    material_id: str = ""
    quantity_per_dust_grant: int = 0


class DatacronSet(_LeafStruct):
    id: int = 0
    display_name: str = ""
    detail_prefab: str = ""
    icon: str = ""
    expiration_time_ms: str = "0"
    tier: list[DatacronSetTier] = msgspec.field(default_factory=list)
    focused_tier: list[DatacronSetTier] = msgspec.field(default_factory=list)
    set_material: list[DatacronSetMaterial] = msgspec.field(default_factory=list)


class DatacronHelpEntry(_LeafStruct):
    title: str = ""
    body: str = ""


# ── Decoders (one per response type; cached at module load) ─────────────────

PLAYER_DECODER: msgspec.json.Decoder[Player] = msgspec.json.Decoder(Player)
METADATA_DECODER: msgspec.json.Decoder[Metadata] = msgspec.json.Decoder(Metadata)
GUILD_DECODER: msgspec.json.Decoder[Guild] = msgspec.json.Decoder(Guild)
_GUILD_ENVELOPE_DECODER: msgspec.json.Decoder[GuildEnvelope] = msgspec.json.Decoder(GuildEnvelope)
LEADERBOARD_DECODER: msgspec.json.Decoder[LeaderboardResponse] = msgspec.json.Decoder(LeaderboardResponse)
UNIT_LIST_DECODER: msgspec.json.Decoder[list[Unit]] = msgspec.json.Decoder(list[Unit])
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


def decode_guild_dict(content: bytes) -> dict[str, Any]:
    """Dict-shape twin of :func:`decode_guild` — unwraps the envelope, returns dict.

    Used by the dict-default client to preserve v2 wire compatibility:
    callers always see the inner guild dict, never the ``{"guild": ...}``
    envelope wrap.
    """
    decoded = UNTYPED_DECODER.decode(content)
    if isinstance(decoded, dict) and "guild" in decoded and isinstance(decoded["guild"], dict):
        return cast(dict[str, Any], decoded["guild"])
    return cast(dict[str, Any], decoded)
