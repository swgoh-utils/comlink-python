# coding=utf-8
"""
helpers subpackage — backward-compatible re-export of all public names.

All existing ``from swgoh_comlink.helpers import X`` imports continue to work.
"""

from __future__ import annotations

from ._arena import get_arena_payout, get_max_rank_jump
from ._constants import Constants
from ._data_items import DataItems
from ._decorators import func_debug_logger, func_timer
from ._gac import (
    convert_divisions_to_int,
    convert_league_to_int,
    get_current_gac_event,
    get_gac_brackets,
    search_gac_brackets,
)
from ._game_data import (
    create_localized_unit_name_dictionary,
    get_current_datacron_sets,
    get_datacron_dismantle_total,
    get_datacron_dismantle_value,
    get_playable_units,
    get_raid_leaderboard_ids,
)
from ._guild import get_guild_members
from ._omicron import (
    get_omicron_skill_tier,
    get_omicron_skills,
    get_tw_omicrons,
    get_unit_from_skill,
    is_omicron_skill,
)
from ._sentinels import (
    EMPTY,
    GIVEN,
    MISSING,
    OPTIONAL,
    REQUIRED,
    SET,
    MutualExclusiveRequired,
    MutualRequiredNotSet,
    NotGiven,
    NotSet,
)
from ._utils import (
    convert_relic_tier,
    get_enum_key_by_value,
    get_function_name,
    human_time,
    sanitize_allycode,
    validate_file_path,
)

__all__ = [
    # Sentinels
    "EMPTY",
    "GIVEN",
    "MISSING",
    "MutualExclusiveRequired",
    "MutualRequiredNotSet",
    "NotGiven",
    "NotSet",
    "OPTIONAL",
    "REQUIRED",
    "SET",
    # Enums and constants
    "Constants",
    "DataItems",
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
    # Arena
    "get_arena_payout",
    "get_max_rank_jump",
    # GAC
    "convert_divisions_to_int",
    "convert_league_to_int",
    "get_current_gac_event",
    "get_gac_brackets",
    "search_gac_brackets",
    # Game data
    "create_localized_unit_name_dictionary",
    "get_current_datacron_sets",
    "get_datacron_dismantle_total",
    "get_datacron_dismantle_value",
    "get_playable_units",
    "get_raid_leaderboard_ids",
    # Guild
    "get_guild_members",
    # Omicron
    "get_omicron_skill_tier",
    "get_omicron_skills",
    "get_tw_omicrons",
    "get_unit_from_skill",
    "is_omicron_skill",
]
