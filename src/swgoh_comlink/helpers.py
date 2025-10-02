# coding=utf-8
"""
Helper objects and functions for swgoh_comlink
"""
from __future__ import annotations

import inspect
import os
import time
from collections import namedtuple
from datetime import datetime, timedelta
from enum import IntFlag
from functools import wraps
from os import PathLike
from pathlib import Path
from typing import Any, NamedTuple, Optional, TYPE_CHECKING

from math import floor
from sentinels import Sentinel

from .exceptions import SwgohComlinkValueError
from .globals import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from swgoh_comlink import SwgohComlink, SwgohComlinkAsync  # noqa: ignore

# Define sentinels used in parameter checking
OPTIONAL = Sentinel('NotSet')
NotSet = Sentinel('NotSet')
EMPTY = Sentinel('NotSet')
NotGiven = Sentinel('NotGiven')
REQUIRED = Sentinel('REQUIRED')
GIVEN = Sentinel('REQUIRED')
MISSING = Sentinel('REQUIRED')
SET = Sentinel('NotMissing')
MutualExclusiveRequired = Sentinel('MutualExclusiveRequired')
MutualRequiredNotSet = Sentinel('MutualExclusiveRequired')


class DataItems(IntFlag):
    """
    Integer flag enum class mapping game data collection names to the integer values of their bit positions for use
    in the `items` parameter of the `get_game_data()` method.

    Since the member values are integers, they can be combined using normal integer arithmetic operations to specify
    more than one collection in a single call.

    Examples:
        effect = comlink.get_game_data(items=DataItems.EFFECT)
        skill_equipment = comlink.get_game_data(items=(DataItems.SKILL + DataItems.EQUIPMENT))
        units_no_pve = comlink.get_game_data(items=DataItems.UNITS, include_pve_units=False)

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

    SEGMENT1 = 2097151
    SEGMENT2 = 68717379584
    SEGMENT3 = RELIC_TIER_DEFINITION + UNITS
    SEGMENT4 = 281200098803712

    @classmethod
    def members(cls):
        """Return a list of the member names of the DataItems class."""
        return cls.__members__.keys()


class Constants:
    """Collection of constants used throughout the SwgohComlink project."""
    ALL = -1
    CategoryDefinitions = 1
    UnlockAnnouncements = 2
    SkillDefinitions = 4
    EquipmentDefinitions = 8
    BattleEffectDefinitions = 16
    AllTables = 32
    EnvironmentDefinitions = 64
    EventSampling = 128
    BattleTargetingSets = 256
    Requirements = 512
    PowerUpBundles = 1024
    GuildBannerDefinition = 2048
    BattleTargetingRules = 4096
    PersistentVFX = 8192
    CraftingMaterialDefinitions = 16384
    PlayerTitleDefinitions = 32768
    PlayerPortraitDefinitions = 65536
    TimeZoneChangeConfig = 131072
    EnvironmentCollections = 262144
    PersistentEffectPriorities = 524288
    SocialStatus = 1048576

    AbilityDefinitions = 2097152
    StatProgression = 4194304
    Challenge = 8388608
    WarDefinitions = 16777216
    StatMod = 33554432
    RecipeDefinitions = 67108864
    ModRecommendations = 134217728
    ScavengerConversionSets = 268435456
    Guild = 536870912
    Mystery = 1073741824
    CooldownDefinitions = 2147483648
    DailyActionCapDefinitions = 4294967296
    EnergyRewards = 8589934592
    UnitGuideDefinitions = 17179869184
    GalacticBundleDefinitions = 34359738368

    RelicTierDefinitions = 68719476736
    UnitDefinitions = 137438953472

    CampaignDefinitions = 274877906944
    Conquest = 549755813888
    AbilityDecisionTrees = 1099511627776
    RecommendedSquads = 2199023255552
    UnitGuideLayouts = 4398046511104
    DailyLoginRewardDefinitions = 8796093022208
    CalendarCategories = 17592186044416
    TerritoryTournamentDailyRewards = 35184372088832
    DatacronDefinitions = 70368744177664
    DisplayableEnemyDefinitions = 140737488355328

    EpisodeDefinition = 281474976710656
    LinkingReward = 562949953421312

    Help = -9223372036854775808
    Segment1 = 2097151
    Segment2 = 68717379584
    Segment3 = 206158430208
    Segment4 = 281200098803712
    UBSUpdate = 2150109456

    RELIC_OFFSET = 2

    MAX_VALUES: dict[str, int] = {
            "GEAR_TIER": 13,
            "UNIT_LEVEL": 85,
            "RELIC_TIER": 10,
            "UNIT_RARITY": 7,
            "MOD_TIER": 5,  # Color
            "MOD_LEVEL": 15,
            "MOD_RARITY": 6,  # Pips
            }

    LEAGUES: dict[str, int] = {
            "kyber": 100,
            "aurodium": 80,
            "chromium": 60,
            "bronzium": 40,
            "carbonite": 20,
            }

    DIVISIONS: dict[str, int] = {"1": 25, "2": 20, "3": 15, "4": 10, "5": 5}

    STAT_ENUMS: dict[str, str] = {
            "0": "None",
            "1": "UnitStat_Health",
            "2": "UnitStat_Strength",
            "3": "UnitStat_Agility",
            "4": "UnitStat_Intelligence",
            "5": "UnitStat_Speed",
            "6": "UnitStat_AttackDamage",
            "7": "UnitStat_AbilityPower",
            "8": "UnitStat_Armor",
            "9": "UnitStat_Suppression",
            "10": "UnitStat_ArmorPenetration",
            "11": "UnitStat_SuppressionPenetration",
            "12": "UnitStat_DodgeRating_TU5V",
            "13": "UnitStat_DeflectionRating_TU5V",
            "14": "UnitStat_AttackCriticalRating_TU5V",
            "15": "UnitStat_AbilityCriticalRating_TU5V",
            "16": "UnitStat_CriticalDamage",
            "17": "UnitStat_Accuracy",
            "18": "UnitStat_Resistance",
            "19": "UnitStat_DodgePercentAdditive",
            "20": "UnitStat_DeflectionPercentAdditive",
            "21": "UnitStat_AttackCriticalPercentAdditive",
            "22": "UnitStat_AbilityCriticalPercentAdditive",
            "23": "UnitStat_ArmorPercentAdditive",
            "24": "UnitStat_SuppressionPercentAdditive",
            "25": "UnitStat_ArmorPenetrationPercentAdditive",
            "26": "UnitStat_SuppressionPenetrationPercentAdditive",
            "27": "UnitStat_HealthSteal",
            "28": "UnitStat_MaxShield",
            "29": "UnitStat_ShieldPenetration",
            "30": "UnitStat_HealthRegen",
            "31": "UnitStat_AttackDamagePercentAdditive",
            "32": "UnitStat_AbilityPowerPercentAdditive",
            "33": "UnitStat_DodgeNegatePercentAdditive",
            "34": "UnitStat_DeflectionNegatePercentAdditive",
            "35": "UnitStat_AttackCriticalNegatePercentAdditive",
            "36": "UnitStat_AbilityCriticalNegatePercentAdditive",
            "37": "UnitStat_DodgeNegateRating",
            "38": "UnitStat_DeflectionNegateRating",
            "39": "UnitStat_AttackCriticalNegateRating",
            "40": "UnitStat_AbilityCriticalNegateRating",
            "41": "UnitStat_Offense",
            "42": "UnitStat_Defense",
            "43": "UnitStat_DefensePenetration",
            "44": "UnitStat_EvasionRating",
            "45": "UnitStat_CriticalRating",
            "46": "UnitStat_EvasionNegateRating",
            "47": "UnitStat_CriticalNegateRating",
            "48": "UnitStat_OffensePercentAdditive",
            "49": "UnitStat_DefensePercentAdditive",
            "50": "UnitStat_DefensePenetrationPercentAdditive",
            "51": "UnitStat_EvasionPercentAdditive",
            "52": "UnitStat_EvasionNegatePercentAdditive",
            "53": "UnitStat_CriticalChancePercentAdditive",
            "54": "UnitStat_CriticalNegateChancePercentAdditive",
            "55": "UnitStat_MaxHealthPercentAdditive",
            "56": "UnitStat_MaxShieldPercentAdditive",
            "57": "UnitStat_SpeedPercentAdditive",
            "58": "UnitStat_CounterAttackRating",
            "59": "UnitStat_Taunt",
            "60": "UnitStat_DefensePenetrationTargetPercentAdditive",
            "61": "UNIT_STAT_STAT_VIEW_MASTERY",
            }

    UNIT_STAT_ENUMS_MAP: dict[str, dict[str, str]] = {
            "0": {"enum": "UnitStat_DEFAULT", "nameKey": "None"},
            "1": {
                    "enum": "UNITSTATMAXHEALTH",
                    "nameKey": "UnitStat_Health",
                    "tableKey": "MAX_HEALTH",
                    },
            "2": {
                    "enum": "UNITSTATSTRENGTH",
                    "nameKey": "UnitStat_Strength",
                    "tableKey": "STRENGTH",
                    },
            "3": {
                    "enum": "UNITSTATAGILITY",
                    "nameKey": "UnitStat_Agility",
                    "tableKey": "AGILITY",
                    },
            "4": {
                    "enum": "UNITSTATINTELLIGENCE",
                    "nameKey": "UnitStat_Intelligence",
                    "tableKey": "INTELLIGENCE",
                    },
            "5": {
                    "enum": "UNITSTATSPEED",
                    "nameKey": "UnitStat_Speed",
                    "tableKey": "SPEED",
                    },
            "6": {
                    "enum": "UNITSTATATTACKDAMAGE",
                    "nameKey": "UnitStat_AttackDamage",
                    "tableKey": "ATTACK_DAMAGE",
                    },
            "7": {
                    "enum": "UNITSTATABILITYPOWER",
                    "nameKey": "UnitStat_AbilityPower",
                    "tableKey": "ABILITY_POWER",
                    },
            "8": {
                    "enum": "UNITSTATARMOR",
                    "nameKey": "UnitStat_Armor",
                    "tableKey": "ARMOR",
                    },
            "9": {
                    "enum": "UNITSTATSUPPRESSION",
                    "nameKey": "UnitStat_Suppression",
                    "tableKey": "SUPPRESSION",
                    },
            "10": {
                    "enum": "UNITSTATARMORPENETRATION",
                    "nameKey": "UnitStat_ArmorPenetration",
                    "tableKey": "ARMOR_PENETRATION",
                    },
            "11": {
                    "enum": "UNITSTATSUPPRESSIONPENETRATION",
                    "nameKey": "UnitStat_SuppressionPenetration",
                    "tableKey": "SUPPRESSION_PENETRATION",
                    },
            "12": {
                    "enum": "UNITSTATDODGERATING",
                    "nameKey": "UnitStat_DodgeRating_TU5V",
                    "tableKey": "DODGE_RATING",
                    },
            "13": {
                    "enum": "UNITSTATDEFLECTIONRATING",
                    "nameKey": "UnitStat_DeflectionRating_TU5V",
                    "tableKey": "DEFLECTION_RATING",
                    },
            "14": {
                    "enum": "UNITSTATATTACKCRITICALRATING",
                    "nameKey": "UnitStat_AttackCriticalRating_TU5V",
                    "tableKey": "ATTACK_CRITICAL_RATING",
                    },
            "15": {
                    "enum": "UNITSTATABILITYCRITICALRATING",
                    "nameKey": "UnitStat_AbilityCriticalRating_TU5V",
                    "tableKey": "ABILITY_CRITICAL_RATING",
                    },
            "16": {
                    "enum": "UNITSTATCRITICALDAMAGE",
                    "nameKey": "UnitStat_CriticalDamage",
                    "tableKey": "CRITICAL_DAMAGE",
                    },
            "17": {
                    "enum": "UNITSTATACCURACY",
                    "nameKey": "UnitStat_Accuracy",
                    "tableKey": "ACCURACY",
                    },
            "18": {
                    "enum": "UNITSTATRESISTANCE",
                    "nameKey": "UnitStat_Resistance",
                    "tableKey": "RESISTANCE",
                    },
            "19": {
                    "enum": "UNITSTATDODGEPERCENTADDITIVE",
                    "nameKey": "UnitStat_DodgePercentAdditive",
                    "tableKey": "DODGE_PERCENT_ADDITIVE",
                    },
            "20": {
                    "enum": "UNITSTATDEFLECTIONPERCENTADDITIVE",
                    "nameKey": "UnitStat_DeflectionPercentAdditive",
                    "tableKey": "DEFLECTION_PERCENT_ADDITIVE",
                    },
            "21": {
                    "enum": "UNITSTATATTACKCRITICALPERCENTADDITIVE",
                    "nameKey": "UnitStat_AttackCriticalPercentAdditive",
                    "tableKey": "ATTACK_CRITICAL_PERCENT_ADDITIVE",
                    },
            "22": {
                    "enum": "UNITSTATABILITYCRITICALPERCENTADDITIVE",
                    "nameKey": "UnitStat_AbilityCriticalPercentAdditive",
                    "tableKey": "ABILITY_CRITICAL_PERCENT_ADDITIVE",
                    },
            "23": {
                    "enum": "UNITSTATARMORPERCENTADDITIVE",
                    "nameKey": "UnitStat_ArmorPercentAdditive",
                    "tableKey": "ARMOR_PERCENT_ADDITIVE",
                    },
            "24": {
                    "enum": "UNITSTATSUPPRESSIONPERCENTADDITIVE",
                    "nameKey": "UnitStat_SuppressionPercentAdditive",
                    "tableKey": "SUPPRESSION_PERCENT_ADDITIVE",
                    },
            "25": {
                    "enum": "UNITSTATARMORPENETRATIONPERCENTADDITIVE",
                    "nameKey": "UnitStat_ArmorPenetrationPercentAdditive",
                    "tableKey": "ARMOR_PENETRATION_PERCENT_ADDITIVE",
                    },
            "26": {
                    "enum": "UNITSTATSUPPRESSIONPENETRATIONPERCENTADDITIVE",
                    "nameKey": "UnitStat_SuppressionPenetrationPercentAdditive",
                    "tableKey": "SUPPRESSION_PENETRATION_PERCENT_ADDITIVE",
                    },
            "27": {
                    "enum": "UNITSTATHEALTHSTEAL",
                    "nameKey": "UnitStat_HealthSteal",
                    "tableKey": "HEALTH_STEAL",
                    },
            "28": {
                    "enum": "UNITSTATMAXSHIELD",
                    "nameKey": "UnitStat_MaxShield",
                    "tableKey": "MAX_SHIELD",
                    },
            "29": {
                    "enum": "UNITSTATSHIELDPENETRATION",
                    "nameKey": "UnitStat_ShieldPenetration",
                    "tableKey": "SHIELD_PENETRATION",
                    },
            "30": {
                    "enum": "UNITSTATHEALTHREGEN",
                    "nameKey": "UnitStat_HealthRegen",
                    "tableKey": "HEALTH_REGEN",
                    },
            "31": {
                    "enum": "UNITSTATATTACKDAMAGEPERCENTADDITIVE",
                    "nameKey": "UnitStat_AttackDamagePercentAdditive",
                    "tableKey": "ATTACK_DAMAGE_PERCENT_ADDITIVE",
                    },
            "32": {
                    "enum": "UNITSTATABILITYPOWERPERCENTADDITIVE",
                    "nameKey": "UnitStat_AbilityPowerPercentAdditive",
                    "tableKey": "ABILITY_POWER_PERCENT_ADDITIVE",
                    },
            "33": {
                    "enum": "UNITSTATDODGENEGATEPERCENTADDITIVE",
                    "nameKey": "UnitStat_DodgeNegatePercentAdditive",
                    "tableKey": "DODGE_NEGATE_PERCENT_ADDITIVE",
                    },
            "34": {
                    "enum": "UNITSTATDEFLECTIONNEGATEPERCENTADDITIVE",
                    "nameKey": "UnitStat_DeflectionNegatePercentAdditive",
                    "tableKey": "DEFLECTION_NEGATE_PERCENT_ADDITIVE",
                    },
            "35": {
                    "enum": "UNITSTATATTACKCRITICALNEGATEPERCENTADDITIVE",
                    "nameKey": "UnitStat_AttackCriticalNegatePercentAdditive",
                    "tableKey": "ATTACK_CRITICAL_NEGATE_PERCENT_ADDITIVE",
                    },
            "36": {
                    "enum": "UNITSTATABILITYCRITICALNEGATEPERCENTADDITIVE",
                    "nameKey": "UnitStat_AbilityCriticalNegatePercentAdditive",
                    "tableKey": "ABILITY_CRITICAL_NEGATE_PERCENT_ADDITIVE",
                    },
            "37": {
                    "enum": "UNITSTATDODGENEGATERATING",
                    "nameKey": "UnitStat_DodgeNegateRating",
                    "tableKey": "DODGE_NEGATE_RATING",
                    },
            "38": {
                    "enum": "UNITSTATDEFLECTIONNEGATERATING",
                    "nameKey": "UnitStat_DeflectionNegateRating",
                    "tableKey": "DEFLECTION_NEGATE_RATING",
                    },
            "39": {
                    "enum": "UNITSTATATTACKCRITICALNEGATERATING",
                    "nameKey": "UnitStat_AttackCriticalNegateRating",
                    "tableKey": "ATTACK_CRITICAL_NEGATE_RATING",
                    },
            "40": {
                    "enum": "UNITSTATABILITYCRITICALNEGATERATING",
                    "nameKey": "UnitStat_AbilityCriticalNegateRating",
                    "tableKey": "ABILITY_CRITICAL_NEGATE_RATING",
                    },
            "41": {
                    "enum": "UNITSTATOFFENSE",
                    "nameKey": "UnitStat_Offense",
                    "tableKey": "OFFENSE",
                    },
            "42": {
                    "enum": "UNITSTATDEFENSE",
                    "nameKey": "UnitStat_Defense",
                    "tableKey": "DEFENSE",
                    },
            "43": {
                    "enum": "UNITSTATDEFENSEPENETRATION",
                    "nameKey": "UnitStat_DefensePenetration",
                    "tableKey": "DEFENSE_PENETRATION",
                    },
            "44": {
                    "enum": "UNITSTATEVASIONRATING",
                    "nameKey": "UnitStat_EvasionRating",
                    "tableKey": "EVASION_RATING",
                    },
            "45": {
                    "enum": "UNITSTATCRITICALRATING",
                    "nameKey": "UnitStat_CriticalRating",
                    "tableKey": "CRITICAL_RATING",
                    },
            "46": {
                    "enum": "UNITSTATEVASIONNEGATERATING",
                    "nameKey": "UnitStat_EvasionNegateRating",
                    "tableKey": "EVASION_NEGATE_RATING",
                    },
            "47": {
                    "enum": "UNITSTATCRITICALNEGATERATING",
                    "nameKey": "UnitStat_CriticalNegateRating",
                    "tableKey": "CRITICAL_NEGATE_RATING",
                    },
            "48": {
                    "enum": "UNITSTATOFFENSEPERCENTADDITIVE",
                    "nameKey": "UnitStat_OffensePercentAdditive",
                    "tableKey": "OFFENSE_PERCENT_ADDITIVE",
                    },
            "49": {
                    "enum": "UNITSTATDEFENSEPERCENTADDITIVE",
                    "nameKey": "UnitStat_DefensePercentAdditive",
                    "tableKey": "DEFENSE_PERCENT_ADDITIVE",
                    },
            "50": {
                    "enum": "UNITSTATDEFENSEPENETRATIONPERCENTADDITIVE",
                    "nameKey": "UnitStat_DefensePenetrationPercentAdditive",
                    "tableKey": "DEFENSE_PENETRATION_PERCENT_ADDITIVE",
                    },
            "51": {
                    "enum": "UNITSTATEVASIONPERCENTADDITIVE",
                    "nameKey": "UnitStat_EvasionPercentAdditive",
                    "tableKey": "EVASION_PERCENT_ADDITIVE",
                    },
            "52": {
                    "enum": "UNITSTATEVASIONNEGATEPERCENTADDITIVE",
                    "nameKey": "UnitStat_EvasionNegatePercentAdditive",
                    "tableKey": "EVASION_NEGATE_PERCENT_ADDITIVE",
                    },
            "53": {
                    "enum": "UNITSTATCRITICALCHANCEPERCENTADDITIVE",
                    "nameKey": "UnitStat_CriticalChancePercentAdditive",
                    "tableKey": "CRITICAL_CHANCE_PERCENT_ADDITIVE",
                    },
            "54": {
                    "enum": "UNITSTATCRITICALNEGATECHANCEPERCENTADDITIVE",
                    "nameKey": "UnitStat_CriticalNegateChancePercentAdditive",
                    "tableKey": "CRITICAL_NEGATE_CHANCE_PERCENT_ADDITIVE",
                    },
            "55": {
                    "enum": "UNITSTATMAXHEALTHPERCENTADDITIVE",
                    "nameKey": "UnitStat_MaxHealthPercentAdditive",
                    "tableKey": "MAX_HEALTH_PERCENT_ADDITIVE",
                    },
            "56": {
                    "enum": "UNITSTATMAXSHIELDPERCENTADDITIVE",
                    "nameKey": "UnitStat_MaxShieldPercentAdditive",
                    "tableKey": "MAX_SHIELD_PERCENT_ADDITIVE",
                    },
            "57": {
                    "enum": "UNITSTATSPEEDPERCENTADDITIVE",
                    "nameKey": "UnitStat_SpeedPercentAdditive",
                    "tableKey": "SPEED_PERCENT_ADDITIVE",
                    },
            "58": {
                    "enum": "UNITSTATCOUNTERATTACKRATING",
                    "nameKey": "UnitStat_CounterAttackRating",
                    "tableKey": "COUNTER_ATTACK_RATING",
                    },
            "59": {
                    "enum": "UNITSTATTAUNT",
                    "nameKey": "UnitStat_Taunt",
                    "tableKey": "TAUNT",
                    },
            "60": {
                    "enum": "UNITSTATDEFENSEPENETRATIONTARGETPERCENTADDITIVE",
                    "nameKey": "UnitStat_DefensePenetrationTargetPercentAdditive",
                    "tableKey": "DEFENSE_PENETRATION_TARGET_PERCENT_ADDITIVE",
                    },
            "61": {
                    "enum": "UNITSTATMASTERY",
                    "nameKey": "UNIT_STAT_STAT_VIEW_MASTERY",
                    "tableKey": "MASTERY",
                    },
            }

    MOD_SET_IDS: dict[str, str] = {
            "1": "Health",
            "2": "Offense",
            "3": "Defense",
            "4": "Speed",
            "5": "Critical Chance",
            "6": "Critical Damage",
            "7": "Potency",
            "8": "Tenacity",
            }

    MOD_SLOTS: dict[str, str] = {
            "2": "Square",
            "3": "Arrow",
            "4": "Diamond",
            "5": "Triangle",
            "6": "Circle",
            "7": "Plus/Cross",
            }

    STATS: dict[str, dict] = {
            "1": {
                    "statId": 1,
                    "nameKey": "UnitStat_Health",
                    "descKey": "UnitStatDescription_Health_TU7",
                    "isDecimal": False,
                    "name": "Health",
                    "detailedName": "Max Health"
                    },
            "2": {
                    "statId": 2,
                    "nameKey": "UnitStat_Strength",
                    "descKey": "UnitStatDescription_Strength",
                    "isDecimal": False,
                    "name": "Strength",
                    "detailedName": "Strength"
                    },
            "3": {
                    "statId": 3,
                    "nameKey": "UnitStat_Agility",
                    "descKey": "UnitStatDescription_Agility",
                    "isDecimal": False,
                    "name": "Agility",
                    "detailedName": "Agility"
                    },
            "4": {
                    "statId": 4,
                    "nameKey": "UnitStat_Intelligence_TU7",
                    "descKey": "UnitStatDescription_Intelligence",
                    "isDecimal": False,
                    "name": "Tactics",
                    "detailedName": "Tactics"
                    },
            "5": {
                    "statId": 5,
                    "nameKey": "UnitStat_Speed",
                    "descKey": "UnitStatDescription_Speed",
                    "isDecimal": False,
                    "name": "Speed",
                    "detailedName": "Speed"
                    },
            "6": {
                    "statId": 6,
                    "nameKey": "UnitStat_AttackDamage",
                    "descKey": "UnitStatDescription_AttackDamage",
                    "isDecimal": False,
                    "name": "Physical Damage",
                    "detailedName": "Physical Damage"
                    },
            "7": {
                    "statId": 7,
                    "nameKey": "UnitStat_AbilityPower",
                    "descKey": "UnitStatDescription_AbilityPower",
                    "isDecimal": False,
                    "name": "Special Damage",
                    "detailedName": "Special Damage"
                    },
            "8": {
                    "statId": 8,
                    "nameKey": "UnitStat_Armor",
                    "descKey": "UnitStatDescription_Armor",
                    "isDecimal": False,
                    "name": "Armor",
                    "detailedName": "Armor"
                    },
            "9": {
                    "statId": 9,
                    "nameKey": "UnitStat_Suppression",
                    "descKey": "UnitStatDescription_Suppression",
                    "isDecimal": False,
                    "name": "Resistance",
                    "detailedName": "Resistance"
                    },
            "10": {
                    "statId": 10,
                    "nameKey": "UnitStat_ArmorPenetration",
                    "descKey": "UnitStatDescription_ArmorPenetration",
                    "isDecimal": False,
                    "name": "Armor Penetration",
                    "detailedName": "Armor Penetration"
                    },
            "11": {
                    "statId": 11,
                    "nameKey": "UnitStat_SuppressionPenetration",
                    "descKey": "UnitStatDescription_SuppressionPenetration",
                    "isDecimal": False,
                    "name": "Resistance Penetration",
                    "detailedName": "Resistance Penetration"
                    },
            "12": {
                    "statId": 12,
                    "nameKey": "UnitStat_DodgeRating_TU5V",
                    "descKey": "UnitStatDescription_DodgeRating",
                    "isDecimal": False,
                    "name": "Dodge Chance",
                    "detailedName": "Dodge Rating"
                    },
            "13": {
                    "statId": 13,
                    "nameKey": "UnitStat_DeflectionRating_TU5V",
                    "descKey": "UnitStatDescription_DeflectionRating",
                    "isDecimal": False,
                    "name": "Deflection Chance",
                    "detailedName": "Deflection Rating"
                    },
            "14": {
                    "statId": 14,
                    "nameKey": "UnitStat_AttackCriticalRating_TU5V",
                    "descKey": "UnitStatDescription_AttackCriticalRating",
                    "isDecimal": False,
                    "name": "Physical Critical Chance",
                    "detailedName": "Physical Critical Rating"
                    },
            "15": {
                    "statId": 15,
                    "nameKey": "UnitStat_AbilityCriticalRating_TU5V",
                    "descKey": "UnitStatDescription_AbilityCriticalRating",
                    "isDecimal": False,
                    "name": "Special Critical Chance",
                    "detailedName": "Special Critical Rating"
                    },
            "16": {
                    "statId": 16,
                    "nameKey": "UnitStat_CriticalDamage",
                    "descKey": "UnitStatDescription_CriticalDamage",
                    "isDecimal": True,
                    "name": "Critical Damage",
                    "detailedName": "Critical Damage"
                    },
            "17": {
                    "statId": 17,
                    "nameKey": "UnitStat_Accuracy",
                    "descKey": "UnitStatDescription_Accuracy",
                    "isDecimal": True,
                    "name": "Potency",
                    "detailedName": "Potency"
                    },
            "18": {
                    "statId": 18,
                    "nameKey": "UnitStat_Resistance",
                    "descKey": "UnitStatDescription_Resistance",
                    "isDecimal": True,
                    "name": "Tenacity",
                    "detailedName": "Tenacity"
                    },
            "19": {
                    "statId": 19,
                    "nameKey": "UnitStat_DodgePercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Dodge",
                    "detailedName": "Dodge Percent Additive"
                    },
            "20": {
                    "statId": 20,
                    "nameKey": "UnitStat_DeflectionPercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Deflection",
                    "detailedName": "Deflection Percent Additive"
                    },
            "21": {
                    "statId": 21,
                    "nameKey": "UnitStat_AttackCriticalPercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Physical Critical Chance",
                    "detailedName": "Physical Critical Percent Additive"
                    },
            "22": {
                    "statId": 22,
                    "nameKey": "UnitStat_AbilityCriticalPercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Special Critical Chance",
                    "detailedName": "Special Critical Percent Additive"
                    },
            "23": {
                    "statId": 23,
                    "nameKey": "UnitStat_ArmorPercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Armor",
                    "detailedName": "Armor Percent Additive"
                    },
            "24": {
                    "statId": 24,
                    "nameKey": "UnitStat_SuppressionPercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Resistance",
                    "detailedName": "Resistance Percent Additive"
                    },
            "25": {
                    "statId": 25,
                    "nameKey": "UnitStat_ArmorPenetrationPercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Armor Penetration",
                    "detailedName": "Armor Penetration Percent Additive"
                    },
            "26": {
                    "statId": 26,
                    "nameKey": "UnitStat_SuppressionPenetrationPercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Resistance Penetration",
                    "detailedName": "Resistance Penetration Percent Additive"
                    },
            "27": {
                    "statId": 27,
                    "nameKey": "UnitStat_HealthSteal",
                    "descKey": "UnitStatDescription_HealthSteal",
                    "isDecimal": True,
                    "name": "Health Steal",
                    "detailedName": "Health Steal"
                    },
            "28": {
                    "statId": 28,
                    "nameKey": "UnitStat_MaxShield",
                    "descKey": "UnitStatDescription_MaxShield",
                    "isDecimal": False,
                    "name": "Protection",
                    "detailedName": "Max Protection"
                    },
            "29": {
                    "statId": 29,
                    "nameKey": "UnitStat_ShieldPenetration",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Protection Ignore",
                    "detailedName": "Protection Ignore"
                    },
            "30": {
                    "statId": 30,
                    "nameKey": "UnitStat_HealthRegen",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Health Regeneration",
                    "detailedName": "Health Regen"
                    },
            "31": {
                    "statId": 31,
                    "nameKey": "UnitStat_AttackDamagePercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Physical Damage",
                    "detailedName": "Physical Damage Percent Additive"
                    },
            "32": {
                    "statId": 32,
                    "nameKey": "UnitStat_AbilityPowerPercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Special Damage",
                    "detailedName": "Special Damage Percent Additive"
                    },
            "33": {
                    "statId": 33,
                    "nameKey": "UnitStat_DodgeNegatePercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Physical Accuracy",
                    "detailedName": "Dodge Negate Percent Additive"
                    },
            "34": {
                    "statId": 34,
                    "nameKey": "UnitStat_DeflectionNegatePercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Special Accuracy",
                    "detailedName": "Deflection Negate Percent Additive"
                    },
            "35": {
                    "statId": 35,
                    "nameKey": "UnitStat_AttackCriticalNegatePercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Physical Critical Avoidance",
                    "detailedName": "Physical Critical Negate Percent Additive"
                    },
            "36": {
                    "statId": 36,
                    "nameKey": "UnitStat_AbilityCriticalNegatePercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Special Critical Avoidance",
                    "detailedName": "Special Critical Negate Percent Additive"
                    },
            "37": {
                    "statId": 37,
                    "nameKey": "UnitStat_DodgeNegateRating",
                    "descKey": "UnitStatDescription_DodgeNegateRating",
                    "isDecimal": False,
                    "name": "Physical Accuracy",
                    "detailedName": "Dodge Negate Rating"
                    },
            "38": {
                    "statId": 38,
                    "nameKey": "UnitStat_DeflectionNegateRating",
                    "descKey": "UnitStatDescription_DeflectionNegateRating",
                    "isDecimal": False,
                    "name": "Special Accuracy",
                    "detailedName": "Deflection Negate Rating"
                    },
            "39": {
                    "statId": 39,
                    "nameKey": "UnitStat_AttackCriticalNegateRating",
                    "descKey": "UnitStatDescription_AttackCriticalNegateRating",
                    "isDecimal": False,
                    "name": "Physical Critical Avoidance",
                    "detailedName": "Physical Critical Negate Rating"
                    },
            "40": {
                    "statId": 40,
                    "nameKey": "UnitStat_AbilityCriticalNegateRating",
                    "descKey": "UnitStatDescription_AbilityCriticalNegateRating",
                    "isDecimal": False,
                    "name": "Special Critical Avoidance",
                    "detailedName": "Special Critical Negate Rating"
                    },
            "41": {
                    "statId": 41,
                    "nameKey": "UnitStat_Offense",
                    "descKey": "UnitStatDescription_Offense",
                    "isDecimal": False,
                    "name": "Offense",
                    "detailedName": "Offense"
                    },
            "42": {
                    "statId": 42,
                    "nameKey": "UnitStat_Defense",
                    "descKey": "UnitStatDescription_Defense",
                    "isDecimal": False, "name": "Defense",
                    "detailedName": "Defense"
                    },
            "43": {
                    "statId": 43,
                    "nameKey": "UnitStat_DefensePenetration",
                    "descKey": "UnitStatDescription_DefensePenetration",
                    "isDecimal": False,
                    "name": "Defense Penetration",
                    "detailedName": "Defense Penetration"
                    },
            "44": {
                    "statId": 44,
                    "nameKey": "UnitStat_EvasionRating",
                    "descKey": "UnitStatDescription_EvasionRating",
                    "isDecimal": False,
                    "name": "Evasion",
                    "detailedName": "Evasion Rating"
                    },
            "45": {
                    "statId": 45,
                    "nameKey": "UnitStat_CriticalRating",
                    "descKey": "UnitStatDescription_CriticalRating",
                    "isDecimal": False,
                    "name": "Critical Chance",
                    "detailedName": "Critical Rating"
                    },
            "46": {
                    "statId": 46,
                    "nameKey": "UnitStat_EvasionNegateRating",
                    "descKey": "UnitStatDescription_EvasionNegateRating",
                    "isDecimal": False,
                    "name": "Accuracy",
                    "detailedName": "Evasion Negate Rating"
                    },
            "47": {
                    "statId": 47,
                    "nameKey": "UnitStat_CriticalNegateRating",
                    "descKey": "UnitStatDescription_CriticalNegateRating",
                    "isDecimal": False,
                    "name": "Critical Avoidance",
                    "detailedName": "Critical Negate Rating"
                    },
            "48": {
                    "statId": 48,
                    "nameKey": "UnitStat_OffensePercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Offense",
                    "detailedName": "Offense Percent Additive"
                    },
            "49": {
                    "statId": 49,
                    "nameKey": "UnitStat_DefensePercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Defense",
                    "detailedName": "Defense Percent Additive"
                    },
            "50": {
                    "statId": 50,
                    "nameKey": "UnitStat_DefensePenetrationPercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Defense Penetration",
                    "detailedName": "Defense Penetration Percent Additive"
                    },
            "51": {
                    "statId": 51,
                    "nameKey": "UnitStat_EvasionPercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Evasion",
                    "detailedName": "Evasion Percent Additive"
                    },
            "52": {
                    "statId": 52,
                    "nameKey": "UnitStat_EvasionNegatePercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Accuracy",
                    "detailedName": "Evasion Negate Percent Additive"
                    },
            "53": {
                    "statId": 53,
                    "nameKey": "UnitStat_CriticalChancePercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Critical Chance",
                    "detailedName": "Critical Chance Percent Additive"
                    },
            "54": {
                    "statId": 54,
                    "nameKey": "UnitStat_CriticalNegateChancePercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Critical Avoidance",
                    "detailedName": "Critical Negate Chance Percent Additive"
                    },
            "55": {
                    "statId": 55,
                    "nameKey": "UnitStat_MaxHealthPercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Health",
                    "detailedName": "Max Health Percent Additive"
                    },
            "56": {
                    "statId": 56,
                    "nameKey": "UnitStat_MaxShieldPercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Protection",
                    "detailedName": "Max Protection Percent Additive"
                    },
            "57": {
                    "statId": 57,
                    "nameKey": "UnitStat_SpeedPercentAdditive",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Speed",
                    "detailedName": "Speed Percent Additive"
                    },
            "58": {
                    "statId": 58,
                    "nameKey": "UnitStat_CounterAttackRating",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Counter Attack",
                    "detailedName": "Counter Attack Rating"
                    },
            "59": {
                    "statId": 59,
                    "nameKey": "Combat_Buffs_TASK_NAME_2",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Taunt",
                    "detailedName": "Taunt"
                    },
            "60": {
                    "statId": 60,
                    "nameKey": "UnitStat_DefensePenetrationTargetPercentAdditive",
                    "descKey": "UnitStatDescription_DefensePenetrationTargetPercentAdditive",
                    "isDecimal": True,
                    "name": "Defense Penetration",
                    "detailedName": "Target Defense Penetration Percent Additive"
                    },
            "61": {
                    "statId": 61,
                    "nameKey": "UNIT_STAT_STAT_VIEW_MASTERY",
                    "descKey": "",
                    "isDecimal": True,
                    "name": "Mastery",
                    "detailedName": "Mastery"
                    }
            }

    UNIT_RARITY: dict[int, str] = {
            1: "ONE_STAR",
            2: "TWO_STAR",
            3: "THREE_STAR",
            4: "FOUR_STAR",
            5: "FIVE_STAR",
            6: "SIX_STAR",
            7: "SEVEN_STAR",
            }

    UNIT_RARITY_NAMES: dict[str, str] = {
            "ONE_STAR": "1",
            "TWO_STAR": "2",
            "THREE_STAR": "3",
            "FOUR_STAR": "4",
            "FIVE_STAR": "5",
            "SIX_STAR": "6",
            "SEVEN_STAR": "7",
            }

    LANGUAGES: list[str] = ["chs_cn", "cht_cn", "eng_us", "fre_fr", "ger_de", "ind_id", "ita_it", "jpn_jp", "kor_kr",
                            "por_br", "rus_ru", "spa_xm", "tha_th", "tur_tr"]

    RELIC_TIERS: dict[str, str] = {
            "0": "LOCKED",
            "1": "UNLOCKED",
            "2": "1",
            "3": "2",
            "4": "3",
            "5": "4",
            "6": "5",
            "7": "6",
            "8": "7",
            "9": "8",
            "10": "9",
            "11": "10"
            }

    OMICRON_MODE: dict[int, str] = {
            0: 'Default',
            1: 'ALL',
            4: 'Raid',
            7: 'TB',
            8: 'TW',
            9: 'GAC',
            11: 'Conquest',
            12: 'Galactic Challenge',
            14: 'GAC (3v3)',
            15: 'GAC (5v5)'
            }

    @classmethod
    def get(cls, item):
        return str(getattr(cls, item)) if getattr(cls, item, None) else None

    @classmethod
    def get_names(cls):
        return [x for x in list(cls.__dict__.keys()) if not x.startswith('_') and
                not isinstance(cls.__dict__[x], classmethod)]


def get_raid_leaderboard_ids(campaign_data: list) -> list[str]:
    """
    Extracts and returns the raid leaderboard IDs from the provided campaign data.

    This function processes the `campaign_data` to find and extract the IDs of
    raids associated with the guild campaigns. The IDs are formatted as a string
    specifying the type and structure of the raid. The function specifically works
    with the "GUILD" campaign type and retrieves IDs from the "NORMAL_DIFF"
    difficulty group.

    Args:
        campaign_data (list): A list of campaign data structures, where each
            structure represents campaign information. The input data is
            expected to have nested dictionaries and lists with specific keys
            such as 'id', 'campaignMap', 'campaignNodeDifficultyGroup', and
            'campaignNode'.

    Returns:
        list: A list containing formatted raid leaderboard IDs extracted from the
        guild campaign data. Each ID is constructed as a string containing the
        relevant identifiers for the campaign and its raids.

    Raises:
        KeyError: If any of the required keys (shared_status_event_object.g., 'id', 'campaignMap',
            etc.) are missing in the input data.
        TypeError: If `campaign_data` is not structured as expected, such as if
            it is not a list or contains improperly formatted elements.
    """
    raid_ids = []
    guild_campaigns = next((item for item in campaign_data if item.get('id') == 'GUILD'), None)
    for raid in guild_campaigns['campaignMap'][0]['campaignNodeDifficultyGroup'][0]['campaignNode']:
        for mission in raid['campaignNodeMission']:
            elements = [
                    guild_campaigns['id'],
                    guild_campaigns['campaignMap'][0]['id'],
                    "NORMAL_DIFF",
                    raid['id'],
                    mission['id']
                    ]
            raid_ids.append(":".join(elements))
    return raid_ids


def get_max_rank_jump(current_rank: int) -> int:
    """
    Calculates the maximum rank jump a player can achieve based on their current rank.
    The calculation is determined by applying different logic according to ranges of
    the current rank.

    Args:
        current_rank (int): The player's current rank.

    Returns:
        int: The maximum rank jump the player can achieve.
    """
    if current_rank < 6:
        return 1
    elif current_rank < 55:
        return current_rank - (3 + max(floor((current_rank - 1) / 6), 1))
    else:
        return int(round(current_rank * 0.85 - 1))


def get_arena_payout(offset: int, fleet: bool = False) -> datetime:
    """
    Calculate the next arena payout time.

    This function computes the next payout time based on the given offset, considering
    whether the requested payout is for fleet or squad arena. It adjusts for time zone
    offsets and ensures that the computed payout time is always in the future relative
    to the current time.

    Args:
        offset (int): Time offset in minutes to adjust the payout time.
        fleet (bool): Indicates if the payout is for fleet arena (True) or regular arena
            (False). Defaults to False.

    Returns:
        datetime: The computed next payout time as a datetime object.
    """
    payout = datetime.now()
    local_offset = -(payout.astimezone().utcoffset().total_seconds() / 60)
    if fleet:
        payout = payout.replace(hour=19, minute=0, second=0, microsecond=0)
    else:
        payout = payout.replace(hour=18, minute=0, second=0, microsecond=0)
    payout = payout - timedelta(minutes=(offset + local_offset))
    if payout < datetime.now():
        payout = payout + timedelta(days=1)
    return payout


def get_function_name() -> str:
    """Return the name of the calling function"""
    return f"{inspect.stack()[1].function}()"


def func_timer(func):
    """Decorator to record total execution time of a function to the configured logger using level DEBUG"""

    @wraps(func)
    def wrap(*args, **kw):
        """Wrapper function"""
        result = func(*args, **kw)
        return result

    return wrap


def func_debug_logger(func):
    """Decorator for applying DEBUG logging to a function"""

    @wraps(func)
    def wrap(*args, **kw):
        """Wrapper function"""
        logger.debug(f"{func.__name__()} called with args: {args} and kwargs: {kw}")
        result = func(*args, **kw)
        logger.debug(f"{func.__name__()} Result: {result}")
        return result

    return wrap


def get_enum_key_by_value(enum_dict: dict, category: Any, enum_value: Any, default_return: Any = None) -> Any:
    """
    Return the key from enum_dict for the given enum_value.
    """
    enum_values: Optional[dict] = enum_dict.get(category)
    if enum_values:
        enum_value_match: Optional[list] = [key for key, value in enum_values.items() if value == enum_value]
        return enum_value_match[0] if enum_value_match else default_return
    else:
        return default_return


def validate_file_path(path: str | Path | PathLike) -> bool:
    """Test whether provided path exists or not

    Args:
        path: path of file to validate

    Returns:
        True if exists, False otherwise.

    """
    if path is MISSING or not path:
        err_msg = f"{get_function_name()}: 'path' argument is required."
        raise SwgohComlinkValueError(err_msg)
    return os.path.exists(path) and os.path.isfile(path)


def sanitize_allycode(allycode: str | int | Sentinel = REQUIRED) -> str:
    """Sanitize a player allycode

    Ensure that allycode does not:
        - contain dashes
        - is the proper length
        - contains only digits

    Args:
        allycode: Player allycode to sanitize

    Returns:
        Player allycode in the proper format

    """
    _orig_ac = allycode
    if not allycode and allycode is not GIVEN:
        return str()
    if isinstance(allycode, int):
        allycode = str(allycode)
    if "-" in str(allycode):
        allycode = allycode.replace("-", "")
    if not allycode.isdigit() or len(allycode) != 9:
        err_msg = f"{get_function_name()}: Invalid ally code: {allycode}"
        raise SwgohComlinkValueError(err_msg)
    return allycode


def human_time(unix_time: int | float | Sentinel = REQUIRED) -> str:
    """Convert unix time to human-readable string

    Args:
        unix_time (int|float): standard unix time in seconds or milliseconds

    Returns:
        str: human-readable time string

    Notes:
        If the provided unix time is invalid or an error occurs, the default time string returned
        is 1970-01-01 00:00:00

    """
    print(f"unix_time: {unix_time}")
    if unix_time is MISSING or not str(unix_time):
        err_msg = f"{get_function_name()}: The 'unix_time' argument is required."
        raise SwgohComlinkValueError(err_msg)
    from datetime import datetime, timezone
    if isinstance(unix_time, float):
        unix_time = int(unix_time)
    if isinstance(unix_time, str):
        try:
            unix_time = int(unix_time)
        except SwgohComlinkValueError:
            err_msg = f"{get_function_name()}: Unable to convert unix time from {type(unix_time)} to type <int>"
            raise SwgohComlinkValueError(err_msg)
    if len(str(unix_time)) >= 13:
        unix_time /= 1000
    return datetime.fromtimestamp(unix_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def convert_league_to_int(league: str | Sentinel = REQUIRED) -> int | None:
    """Convert GAC leagues to integer

    Args:
        league (str): GAC league name

    Returns:
        GAC league identifier as used in game data

    """
    if league is MISSING or not league:
        err_msg = f"{get_function_name()}: The 'league' argument is required."
        raise SwgohComlinkValueError(err_msg)

    if isinstance(league, str) and league.lower() in Constants.LEAGUES:
        return Constants.LEAGUES[league.lower()]
    else:
        return None


def convert_divisions_to_int(division: int | str | Sentinel = REQUIRED) -> int | None:
    """Convert GAC divisions to integer

    Args:
        division: GAC division ID as seen in game

    Returns:
        GAC division identifier as used within game data

    """
    if division is MISSING or not division:
        err_msg = f"{get_function_name()}: The 'division' argument is required."
        raise SwgohComlinkValueError(err_msg)

    if isinstance(division, str):
        if division in Constants.DIVISIONS:
            return Constants.DIVISIONS[division]
    if isinstance(division, int) and len(str(division)) == 1:
        if str(division) in Constants.DIVISIONS:
            return Constants.DIVISIONS[str(division)]
    return None


def convert_relic_tier(relic_tier: str | int | Sentinel = REQUIRED) -> str | None:
    """Convert character relic tier to offset string in-game value.

    Conversion is done based on a zero based table indicating both the relic tier status and achieved level.

    Args:
        relic_tier (str | int): The relic tier from character game data to convert to in-game equivalent.

    Returns:
        String representing the relic status and tier

    Raises:
        TypeError: If the provided 'relic_tier' cannot be converted to a string using the Python
                    built-in str() method.

    Examples:
        Relic tier is '0' indicates the character has not yet achieved a level where access to relics have been
            unlocked.
        Relic tier of '1', indicates that the character has achieved the required level to access relics,
            but has not yet upgraded to the first level.
    """
    if not isinstance(relic_tier, str) and not isinstance(relic_tier, int):
        err_msg = f"{get_function_name()}: 'relic_tier' argument is required for conversion."
        raise SwgohComlinkValueError(err_msg)
    relic_value = None
    if isinstance(relic_tier, int):
        relic_tier = str(relic_tier)
    if relic_tier in Constants.RELIC_TIERS:
        relic_value = Constants.RELIC_TIERS[relic_tier]
    return relic_value


def create_localized_unit_name_dictionary(locale: str | list | Sentinel = REQUIRED) -> dict:
    """Create localized translation mapping for unit names

    Take a localization element from the SwgohComlink.get_localization() result dictionary and
    extract the UNIT_NAME entries for building a conversion dictionary to translate BASEID values to in game
    descriptive names

    Args:
        locale: The string element or List[bytes] from the SwgohComlink.get_localization()
                                        result key value

    Returns:
        A dictionary with the UNIT_NAME BASEID as keys and the UNIT_NAME description as values

    """
    if not isinstance(locale, list) and not isinstance(locale, str):
        raise SwgohComlinkValueError(f"'locale' must be a list of strings or string containing newlines.")

    unit_name_map = {}
    lines = []
    if isinstance(locale, str):
        lines = locale.split("\n")
    elif isinstance(locale, list):
        lines = locale
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode()
        line = line.rstrip("\n")
        if line.startswith("#") or "|" not in line:
            continue
        if line.startswith("UNIT_"):
            name_key, desc = line.split("|")
            if name_key.endswith("_NAME"):
                unit_name_map[name_key] = desc
    return unit_name_map


def get_guild_members(
        comlink: SwgohComlink | Sentinel = REQUIRED,
        player_id: str | Sentinel = MutualExclusiveRequired,
        allycode: str | int | Sentinel = MutualExclusiveRequired,
        ) -> list:
    """Return list of guild member player allycodes based upon provided player ID or allycode

    Args:
        comlink: Instance of SwgohComlink
        player_id: Player's ID
        allycode: Player's allycode

    Returns:
        list of guild members objects

    Note:
        A player_id or allycode argument is REQUIRED

    """
    if hasattr(comlink, '__comlink_type__'):
        comlink_type = comlink.__comlink_type__
    else:
        comlink_type = MISSING
    if comlink is MISSING or comlink_type != 'SwgohComlink':
        err_msg = (f"{get_function_name()}: The 'comlink' argument is required and must be an "
                   f"instance of SwgohComlink.")
        raise SwgohComlinkValueError(err_msg)

    if player_id is not MutualExclusiveRequired and allycode is not MutualExclusiveRequired:
        err_msg = f"{get_function_name()}: Either 'player_id' or 'allycode' are allowed arguments, not both."
        raise SwgohComlinkValueError(err_msg)

    if player_id is MutualExclusiveRequired and allycode is MutualExclusiveRequired:
        err_msg = f"{get_function_name()}: One of either 'player_id' or 'allycode' is required."
        raise SwgohComlinkValueError(err_msg)

    if isinstance(player_id, str):
        player = comlink.get_player(player_id=player_id)
    else:
        player = comlink.get_player(allycode=sanitize_allycode(allycode))
    guild = comlink.get_guild(guild_id=player["guildId"])
    return guild["member"] or []


def get_current_gac_event(
        comlink: SwgohComlink | Sentinel = REQUIRED
        ) -> dict:
    """Return the event object for the current gac season

    Args:
        comlink: Instance of SwgohComlink

    Returns:
        Current GAC event object or empty if no event is running

    """
    if hasattr(comlink, '__comlink_type__'):
        comlink_type = comlink.__comlink_type__
    else:
        comlink_type = MISSING

    if comlink is MISSING or comlink_type is MISSING:
        err_str = f"{get_function_name()}: comlink instance must be provided."
        raise SwgohComlinkValueError(err_str)

    current_events = comlink.get_events()

    return [event for event in current_events['gameEvent'] if event['type'] == 10][0]


def get_gac_brackets(
        comlink: SwgohComlink | Sentinel = REQUIRED,
        league: str | Sentinel = REQUIRED,
        limit: int | Sentinel = OPTIONAL
        ) -> dict | None:
    """Scan currently running GAC brackets for the requested league and return them as a dictionary

    Args:
        comlink: Instance of SwgohComlink
        league: League to scan
        limit: Number of brackets to return

    Returns:
        Dictionary containing each GAC bracket as a key

    """
    if hasattr(comlink, '__comlink_type__'):
        comlink_type = comlink.__comlink_type__
    else:
        comlink_type = MISSING
    if comlink is MISSING or comlink_type != 'SwgohComlink':
        err_msg = f"{get_function_name()}: Invalid comlink instance."
        raise SwgohComlinkValueError(err_msg)

    if league is MISSING or not isinstance(league, str):
        err_msg = f"{get_function_name()}: 'league' type <str> argument is required."
        raise SwgohComlinkValueError(err_msg)

    bracket_iteration_limit: int | None = None if limit is NotSet else int(limit)

    current_gac_event = get_current_gac_event(comlink)

    if current_gac_event:
        current_event_instance = f"{current_gac_event['id']}:{current_gac_event['instance'][0]['id']}"
    else:
        # No current GAC season running
        return None
    bracket = 0
    # Use brackets to store the results for each bracket for processing once all brackets have been scanned
    brackets: dict = {}
    number_of_players_in_bracket = 8
    while number_of_players_in_bracket > 0 and bracket_iteration_limit != bracket:
        group_id = f"{current_event_instance}:{league}:{bracket}"
        group_of_8_players = comlink.get_gac_leaderboard(
                leaderboard_type=4,
                event_instance_id=current_event_instance,
                group_id=group_id,
                )
        brackets[bracket] = brackets.get(bracket, group_of_8_players["player"])
        bracket += 1
        number_of_players_in_bracket = len(group_of_8_players["player"])
    return brackets


def search_gac_brackets(gac_brackets: dict, player_name: str) -> dict:
    """Search the provided gac brackets data for a specific player

    Args:
        gac_brackets (dict): GAC bracket data to search
        player_name (str): Player name to search for

    Returns:
        dict: GAC bracket and player information or empty if no match is found

    """
    match_data: dict = {}
    for bracket in gac_brackets:
        for player in gac_brackets[bracket]:
            if player_name.lower() == player["name"].lower():
                match_data = {"player": player, "bracket": bracket}
    return match_data


def get_current_datacron_sets(datacron_list: list) -> list:
    """Get the currently active datacron sets

    Args:
        datacron_list (list): List of 'datacronSet' from game data

    Returns:
        Filtered list of only active datacron sets

    Raises:
        SwgohComlinkValueError: If datacron list is not a list

    """
    if not isinstance(datacron_list, list):
        raise SwgohComlinkValueError(
                f"{get_function_name()}, 'datacron_list' must be a list, not {type(datacron_list)}"
                )
    import math
    current_datacron_sets = []
    for datacron in datacron_list:
        if int(datacron["expirationTimeMs"]) > math.floor(time.time() * 1000):
            current_datacron_sets.append(datacron)
    return current_datacron_sets


def get_tw_omicrons(skill_list: list) -> list:
    """Return a list of territory war omicrons

    Args:
        skill_list (list): List of character abilities/skills

    Returns:
        List of territory war omicron abilities

    Raises:
        SwgohComlinkValueError: If skill_list is not a list

    """
    if not isinstance(skill_list, list):
        raise SwgohComlinkValueError(
                f"'skill_list' must be a list, not {type(skill_list)}"
                )

    return get_omicron_skills(skill_list, 8)


def get_playable_units(units_collection: list[dict]) -> list[dict]:
    """Return a list of playable units from game data 'units' collection"""
    if not isinstance(units_collection, list):
        raise SwgohComlinkValueError(f"'units_collection' must be a list, not {type(units_collection)}")

    return [unit for unit in units_collection
            if unit['rarity'] == 7
            and unit['obtainable'] is True
            and unit['obtainableTime'] == '0']


def get_omicron_skills(skill_list: list, omicron_type: int | list[int]) -> list:
    """
    Filters and retrieves omicron skills from a given skill list based on the specified omicron type.

    Args:
        skill_list (list): A list of dictionaries representing skills. The 'skill' collection in game data.
        omicron_type (int | list): The omicron mode type to filter the skills by. The 'OmicronMode' in the game data
        enums.

    Returns:
        list: A list of dictionaries representing skills that match the specified omicron type.

    Raises:
        SwgohComlinkValueError: If either of the arguments is not of the expected type.
    """

    if not isinstance(skill_list, list):
        raise SwgohComlinkValueError(f"'skill_list' must be a list, not {type(skill_list)}")

    if not isinstance(omicron_type, (int, list)):
        raise SwgohComlinkValueError(f"'omicron_type' must be an integer or list of integers, not {type(omicron_type)}")

    omicron_type_list = [omicron_type] if isinstance(omicron_type, int) else omicron_type

    return [skill for skill in skill_list if skill['omicronMode'] in omicron_type_list]


def get_omicron_skill_tier(skill: dict) -> int | None:
    """
    Return the omicron tier index for the given skill.

    This function identifies and returns the index of the skill tier marked as
    an Omicron tier by checking the 'isOmicronTier' property in each tier.
    It assumes that the 'skill' dictionary contains a 'tier' key which
    is a list of dictionaries, each describing a skill tier.

    Raises a SwgohComlinkValueError for invalid input types or missing required keys.

    Parameters:
        skill (dict): A dictionary representing the skill, containing
                      a 'tier' key which holds a list of tier dictionaries.

    Returns:
        int: The index of the Omicron skill tier within the 'tier' list or None if not found.

    Raises:
        SwgohComlinkValueError: If the input 'skill' is not a dictionary.
        SwgohComlinkValueError: If the required 'tier' key is not present in the 'skill' dictionary.
    """
    if not isinstance(skill, dict):
        raise SwgohComlinkValueError(f"'skill' must be a dictionary, not {type(skill)}")

    if 'tier' not in skill:
        raise SwgohComlinkValueError(f"'skill' must contain 'tier' key")

    skill_tier = [idx for idx, tier in enumerate(skill['tier']) if tier['isOmicronTier'] is True]

    return skill_tier[0] if skill_tier else None


def is_omicron_skill(
        omicron_skill_list: list[dict],
        skill_id: str | None = None,
        skill_tier: int | None = None,
        *,
        roster_unit_skill: Optional[dict] = None
        ) -> bool:
    """
    Check if a given skill is an Omicron skill based on its ID and tier.

    Args:
        omicron_skill_list (list[dict]): List of skills from game data that have omicron tiers. Ideally,
                                          this is the output from the get_omicron_skills() function.
        skill_id (str): ID of the skill to check.
        skill_tier (int): Tier index of the skill to check.
        roster_unit_skill (Optional[dict]): Optional dictionary containing the skill data for the roster unit.

    Returns:
        bool: True if the skill is an Omicron skill, False otherwise.

    Raises:
        SwgohComlinkValueError: If either of the arguments is not of the expected type.
    """
    if not isinstance(omicron_skill_list, list):
        raise SwgohComlinkValueError(f"'omicron_skill_list' must be a list, not {type(omicron_skill_list)}")

    if not isinstance(skill_id, str):
        raise SwgohComlinkValueError(f"'skill_id' must be a string, not {type(skill_id)}")

    if not (skill_id and skill_tier and roster_unit_skill):
        raise SwgohComlinkValueError("Invalid 'skill_id', 'skill_tier', or 'roster_unit_skill' argument.")

    if roster_unit_skill is not None:
        skill_id = roster_unit_skill.get('id')
        skill_tier = roster_unit_skill.get('tier')
        if not skill_id or not skill_tier:
            raise SwgohComlinkValueError("Invalid 'roster_unit_skill' argument.")

    omicron_skill = [omi_skill for omi_skill in omicron_skill_list if omi_skill['id'] == skill_id]

    if not omicron_skill:
        return False

    skill_omicron_tier = get_omicron_skill_tier(omicron_skill[0])

    if skill_omicron_tier is None:
        return False

    return skill_omicron_tier == skill_tier


def get_unit_from_skill(unit_list: list[dict], skill: str) -> NamedTuple | None:
    """
    Extracts the base ID and name key of a unit from a list of units based on a specific skill.

    This function iterates through a list of unit dictionaries, identifies the units
    that reference a given skill in their 'skillReference' field, and returns the
    first matching unit's 'baseId' and 'nameKey'. If no unit matches, the function returns None.

    Parameters:
      unit_list (list[dict]): The list of units to search within. Each dictionary
        represents a unit, which must include a 'skillReference' field and a
        'baseId' field.
      skill (str): The skill to search for in the 'skillReference' field of each
        unit.

    Returns:
      NamedTuple | None: Returns a namedtuple containing the 'baseId' and 'nameKey' of the first unit that matches the
        specified skill, or None if no such unit is found.

    Raises:
      SwgohComlinkValueError: If 'unit_list' is not of type list.
      SwgohComlinkValueError: If 'skill' is not of type string.
    """
    if not isinstance(unit_list, list):
        raise SwgohComlinkValueError(f"'unit_list' must be a list, not {type(unit_list)}")

    if not isinstance(skill, str):
        raise SwgohComlinkValueError(f"'skill' must be a string, not {type(skill)}")

    def skill_exists(value, dict_list: list[dict]) -> bool:
        if not dict_list:
            return False
        return any(value in d.values() for d in dict_list)

    Unit = namedtuple("Unit", "baseId nameKey")
    base_ids: list[NamedTuple] = [Unit(unit.get('baseId'), unit.get('nameKey'))
                                  for unit in unit_list if skill_exists(skill, unit.get('skillReference'))]
    if base_ids:
        return base_ids[0]
    else:
        return None


def get_datacron_dismantle_value(datacron: dict, datacron_set_list: list, recipe_list: list) -> dict:
    """
    Retrieves datacron dismantle materials based on the input datacron, datacron sets, and recipes.

    This function calculates the necessary materials required to dismantle a given
    datacron by leveraging its set information and specific recipes tied to its tier.
    If proper references are not found in the provided datacron set list or recipe
    list, the function will return an empty dictionary.

    Arguments:
        datacron (dict): The datacron object from a player object.
        datacron_set_list (list): The game data 'datacronSet' collection.
        recipe_list (list): The game data 'recipe' collection.

    Returns:
        dict: A dictionary mapping ingredient IDs to their required dismantle material
              details, which include the quantity and type.
    """
    dismantle_materials = {}
    set_id = datacron.get('setId')
    focused: bool = datacron.get('focused', False)
    affix_tier = len(datacron.get('affix', []))

    # Helper function to retrieve an object based on its ID
    def find_object_by_id(obj_list, obj_id):
        return next((obj for obj in obj_list if obj.get('id') == obj_id), None)

    # Find datacron set by setId
    datacron_set = find_object_by_id(datacron_set_list, set_id)
    if not datacron_set:
        return dismantle_materials

    # Find dust recipe ID by affix tier
    tier_element = 'focusedTier' if focused else 'tier'
    dust_recipe_id = next(
            (tier.get('dustGrantRecipeId')
             for tier in datacron_set.get(tier_element, []) if tier.get('id') == affix_tier),
            None
            )
    if not dust_recipe_id:
        return dismantle_materials

    # Find recipe by dust recipe ID
    dust_recipe = find_object_by_id(recipe_list, dust_recipe_id)
    if not dust_recipe:
        return dismantle_materials

    # Collect dismantle materials
    for ingredient in dust_recipe.get('ingredients', []):
        dismantle_materials[ingredient.get('id')] = {
                "quantity": ingredient.get('maxQuantity'),
                "type": ingredient.get('type'),
                "focused": focused,
                }
    return dismantle_materials


def get_datacron_dismantle_total(datacrons: list, datacron_set_list: list, recipe_list: list) -> list:
    dismantle_set_list = []
    for datacron in datacrons:
        ...
    return dismantle_set_list
