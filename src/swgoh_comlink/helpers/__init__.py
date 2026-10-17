# coding=utf-8
"""
helpers subpackage — backward-compatible re-export of all public names.

All existing ``from swgoh_comlink.helpers import X`` imports continue to work.
"""

from __future__ import annotations

from ._abilities import AbilityTier, NamedEffect, UnitAbility, get_named_effects, get_unit_abilities
from ._arena import get_arena_payout, get_max_rank_jump
from ._conquest import ConquestFeat, calc_current_stamina, calc_stamina_full_time, get_conquest_feats
from ._constants import Constants
from ._data_items import DataItems
from ._decorators import func_debug_logger, func_timer
from ._events import ScheduledEvent, get_event_schedule
from ._gac import (
    async_get_current_gac_event,
    async_get_gac_brackets,
    convert_divisions_to_int,
    convert_league_to_int,
    get_current_gac_event,
    get_gac_brackets,
    search_gac_brackets,
)
from ._game_config import get_game_config, get_game_config_int
from ._game_data import (
    async_get_localization_dictionary,
    create_localized_unit_name_dictionary,
    get_current_datacron_sets,
    get_datacron_dismantle_total,
    get_datacron_dismantle_value,
    get_localization_dictionary,
    get_playable_units,
    get_raid_leaderboard_ids,
)
from ._guild import (
    GuildActivity,
    GuildMemberActivity,
    RaidResult,
    TerritoryBattleResult,
    TerritoryWarResult,
    async_get_guild_members,
    get_guild_activity,
    get_guild_members,
)
from ._items import (
    ItemNames,
    ModCatalog,
    ModDefinition,
    ModSet,
    NamedReward,
    get_data_disc_names,
    get_mod_catalog,
    get_named_rewards,
    get_player_title_names,
)
from ._localization import (
    parse_swgoh_string,
)
from ._omicron import (
    get_omicron_skill_tier,
    get_omicron_skills,
    get_tw_omicrons,
    get_unit_from_skill,
    is_omicron_skill,
)
from ._stat_data import (
    CURRENCY_NAMES,
    CURRENCY_TYPES,
    ITEM_TYPES,
    LANGUAGES,
    MOD_SET_IDS,
    MOD_SLOTS,
    OMICRON_MODE,
    STAT_ENUMS,
    STATS,
    UNIT_RARITY,
    UNIT_RARITY_NAMES,
    UNIT_STAT_ENUMS_MAP,
)
from ._territory_battle import (
    TBCategory,
    TBMandatoryUnit,
    TBMissionRequirement,
    TBMissionScore,
    TBPlatoon,
    TBReconZone,
    TBZoneStars,
    get_tb_mission_requirements,
    get_tb_mission_scores,
    get_tb_platoon_definitions,
    get_tb_star_thresholds,
)
from ._upgrades import (
    AbilityUpgradeCosts,
    AbilityUpgradeTier,
    GearCraftNode,
    GearTier,
    RelicPromotionCost,
    UpgradeCost,
    get_ability_upgrade_costs,
    get_gear_craft_tree,
    get_relic_promotion_costs,
    get_unit_gear_tiers,
    sum_upgrade_costs,
)
from ._utils import (
    convert_relic_tier,
    get_enum_key_by_value,
    get_function_name,
    human_time,
    sanitize_allycode,
    validate_file_path,
)
from ._wire import as_epoch, as_id, as_int, as_list, as_scalar, as_str, base_id, parse_enum

__all__ = [
    # Enums and constants
    "Constants",
    "DataItems",
    # Stat data
    "CURRENCY_NAMES",
    "CURRENCY_TYPES",
    "ITEM_TYPES",
    "LANGUAGES",
    "MOD_SET_IDS",
    "MOD_SLOTS",
    "OMICRON_MODE",
    "STAT_ENUMS",
    "STATS",
    "UNIT_RARITY",
    "UNIT_RARITY_NAMES",
    "UNIT_STAT_ENUMS_MAP",
    # Decorators
    "func_debug_logger",
    "func_timer",
    # Utility functions
    "convert_relic_tier",
    "get_enum_key_by_value",
    "get_function_name",
    "human_time",
    "sanitize_allycode",
    "validate_file_path",
    "parse_swgoh_string",
    # Abilities and effects
    "AbilityTier",
    "NamedEffect",
    "UnitAbility",
    "get_named_effects",
    "get_unit_abilities",
    # Arena
    "get_arena_payout",
    "get_max_rank_jump",
    # GAC
    "async_get_current_gac_event",
    "async_get_gac_brackets",
    "convert_divisions_to_int",
    "convert_league_to_int",
    "get_current_gac_event",
    "get_gac_brackets",
    "search_gac_brackets",
    # Conquest
    "ConquestFeat",
    "calc_current_stamina",
    "calc_stamina_full_time",
    "get_conquest_feats",
    # Territory Battle definitions
    "TBCategory",
    "TBMandatoryUnit",
    "TBMissionRequirement",
    "TBMissionScore",
    "TBPlatoon",
    "TBReconZone",
    "TBZoneStars",
    "get_tb_mission_requirements",
    "get_tb_mission_scores",
    "get_tb_platoon_definitions",
    "get_tb_star_thresholds",
    # Events
    "ScheduledEvent",
    "get_event_schedule",
    # Game configuration
    "get_game_config",
    "get_game_config_int",
    # Game data
    "async_get_localization_dictionary",
    "create_localized_unit_name_dictionary",
    "get_current_datacron_sets",
    "get_datacron_dismantle_total",
    "get_datacron_dismantle_value",
    "get_localization_dictionary",
    "get_playable_units",
    "get_raid_leaderboard_ids",
    # Guild
    "GuildActivity",
    "GuildMemberActivity",
    "RaidResult",
    "TerritoryBattleResult",
    "TerritoryWarResult",
    "async_get_guild_members",
    "get_guild_activity",
    "get_guild_members",
    # Items, rewards and catalogs
    "ItemNames",
    "ModCatalog",
    "ModDefinition",
    "ModSet",
    "NamedReward",
    "get_data_disc_names",
    "get_mod_catalog",
    "get_named_rewards",
    "get_player_title_names",
    # Omicron
    "get_omicron_skill_tier",
    "get_omicron_skills",
    "get_tw_omicrons",
    "get_unit_from_skill",
    "is_omicron_skill",
    # Wire values
    "as_epoch",
    "as_id",
    "as_int",
    "as_list",
    "as_scalar",
    "as_str",
    "base_id",
    "parse_enum",
    # Upgrade costs
    "AbilityUpgradeCosts",
    "AbilityUpgradeTier",
    "GearCraftNode",
    "GearTier",
    "RelicPromotionCost",
    "UpgradeCost",
    "get_ability_upgrade_costs",
    "get_gear_craft_tree",
    "get_relic_promotion_costs",
    "get_unit_gear_tiers",
    "sum_upgrade_costs",
]
