# coding=utf-8
"""DataItems IntFlag enum mapping game data collection names to bit positions."""

from __future__ import annotations

from collections.abc import KeysView
from enum import IntFlag


class DataItems(IntFlag):
    """
    Integer flag enum class mapping game data collection names to the integer values of their bit positions for use
    in the `items` parameter of the `get_game_data()` method.

    Since the member values are integers, they can be combined using normal integer arithmetic operations to specify
    more than one collection in a single call.

    Examples:
        segment1 = comlink.get_game_data(items=DataItems.SEGMENT1)
        segments_1_and_2 = comlink.get_game_data(items=(DataItems.SEGMENT1 + DataItems.SEGMENT2))
        segment3_no_pve = comlink.get_game_data(items=DataItems.SEGMENT3, include_pve_units=False)

    Note:
        Comlink servers validate `items` against the server-side `GameDataItemsEnum` and may reject
        raw single-collection bit values (e.g. `DataItems.UNITS`) with an HTTP 400. The `SEGMENT1`–
        `SEGMENT4` aggregates (and `DataItems.ALL`) are the values the server explicitly accepts.

    Some of the DataItems members are actually aliases for other members. For example, the `TABLE` member is an
    alias for the `XP_TABLE` member. This is done because both members represent the same collection in the game data.

    Other members are provided as a convenience. For example, the `SEGMENT1` member is assigned the integer value of
    all the collections that are included when using the original (request_segment=) style of calling the
    `get_game_data()` method.

    To retrieve all of the available game data, use the `DataItems.ALL` member.

    A list of the member names of the DataItems class can be retrieved using the `DataItems.members()` class method.
    """

    ALL = -1
    NONE = 0
    CATEGORY = 1
    UNLOCK_ANNOUNCEMENT_DEFINITION = 2
    SKILL = 4
    EQUIPMENT = 8
    EFFECT = 16
    XP_TABLE = 32
    TABLE = XP_TABLE
    BATTLE_ENVIRONMENTS = 64
    EVENT_SAMPLING = 128
    TARGETING_SET = 256
    REQUIREMENT = 512
    POWER_UP_BUNDLE = 1024
    GUILD_BANNER = 2048
    BATTLE_TARGETING_RULE = 4096
    PERSISTENT_VFX = 8192
    MATERIAL = 16384
    PLAYER_TITLE = 32768
    PLAYER_PORTRAIT = 65536
    TIME_ZONE_CHANGE_CONFIG = 131072
    ENVIRONMENT_COLLECTION = 262144
    EFFECT_ICON_PRIORITY = 524288
    SOCIAL_STATUS = 1048576
    ABILITY = 2097152
    STAT_PROGRESSION = 4194304
    CHALLENGE = 8388608
    CHALLENGE_STYLE = CHALLENGE
    WAR_DEFINITION = 16777216
    STAT_MOD_SET = 33554432
    STAT_MOD = STAT_MOD_SET
    RECIPE = 67108864
    MOD_RECOMMENDATION = 134217728
    SCAVENGER_CONVERSION_SET = 268435456
    GUILD = 536870912
    RAID_CONFIG = GUILD
    GUILD_RAID = GUILD
    GUILD_EXCHANGE_ITEM = GUILD
    TERRITORY_BATTLE_DEFINITION = GUILD
    TERRITORY_WAR_DEFINITION = GUILD
    STARTER_GUILD = GUILD
    TERRITORY_TOURNAMENT_DEFINITION = GUILD
    SEASON_DEFINITION = GUILD
    SEASON_LEAGUE_DEFINITION = GUILD
    SEASON_DIVISION_DEFINITION = GUILD
    SEASON_REWARD_TABLE = GUILD
    TERRITORY_TOURNAMENT_LEAGUE_DEFINITION = GUILD
    TERRITORY_TOURNAMENT_DIVISION_DEFINITION = GUILD
    SAVED_SQUAD_CONFIG = GUILD
    GUILD_RAID_GLOBAL_CONFIG = GUILD
    MYSTERY_BOX = 1073741824
    MYSTERY_STAT_MOD = MYSTERY_BOX
    COOLDOWN = 2147483648
    UBS_UPDATE = 2150109456
    DAILY_ACTION_CAP = 4294967296
    ENERGY_REWARD = 8589934592
    UNIT_GUIDE_DEFINITION = 17179869184
    GALACTIC_BUNDLE = 34359738368
    LINKED_STORE_ITEM = GALACTIC_BUNDLE
    RELIC_TIER_DEFINITION = 68719476736
    UNITS = 137438953472
    CAMPAIGN = 274877906944
    CONQUEST = 549755813888
    CONQUEST_DEFINITION = CONQUEST
    CONQUEST_MISSION = CONQUEST
    ARTIFACT_DEFINITION = CONQUEST
    CONSUMABLE_DEFINITION = CONQUEST
    CONSUMABLE_TYPE = CONQUEST
    ARTIFACT_TIER_DEFINITION = CONQUEST
    CONSUMABLE_TIER_DEFINITION = CONQUEST
    ABILITY_DECISION_TREE = 1099511627776
    RECOMMENDED_SQUAD = 2199023255552
    UNIT_GUIDE_LAYOUT = 4398046511104
    DAILY_LOGIN_REWARD_DEFINITION = 8796093022208
    CALENDAR_CATEGORY_DEFINITION = 17592186044416
    TERRITORY_TOURNAMENT_DAILY_REWARD_TABLE = 35184372088832
    DATACRON = 70368744177664
    DATACRON_SET = DATACRON
    DATACRON_TEMPLATE = DATACRON
    DATACRON_AFFIX_TEMPLATE_SET = DATACRON
    DATACRON_HELP_ENTRY = DATACRON
    DISPLAYABLE_ENEMY = 140737488355328
    EPISODE_DEFINITION = 281474976710656
    LINKING_REWARD = 562949953421312
    LIGHTSPEED_TOKEN = 1125899906842624
    ERA_DEFINITION = 2251799813685248

    SEGMENT1 = 2097151
    SEGMENT2 = 1125968624222208
    SEGMENT3 = RELIC_TIER_DEFINITION + UNITS
    SEGMENT4 = 3377424842620928

    @classmethod
    def members(cls) -> KeysView[str]:
        """Return a list of the member names of the DataItems class."""
        return cls.__members__.keys()
