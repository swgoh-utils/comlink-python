# coding=utf-8
"""
Constants used throughout the swgoh_comlink package
"""

from __future__ import annotations

import inspect
import logging
import os
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable

from sentinels import Sentinel

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

_DEFAULT_LOGGER_NAME: str = "swgoh_comlink"
_DEFAULT_LOGGER_ENABLED: bool = False
_LOGGER_REGISTRY = {}

__all__ = [
    GIVEN,  # Sentinel
    OPTIONAL,  # Sentinel
    MISSING,  # Sentinel
    NotGiven,  # Sentinel
    REQUIRED,  # Sentinel
    MutualExclusiveRequired,  # Sentinel
    MutualRequiredNotSet,
    NotSet,  # Sentinel
    SET,
    EMPTY,
    "DataItemConstants",
    "DATA_PATH",
    "DIVISIONS",  # Lookup dictionary
    "enable_default_logger",
    "get_logger",
    "LANGUAGES",
    "LEAGUES",  # Lookup dictionary
    "MOD_SET_IDS",  # Lookup dictionary
    "MOD_SLOTS",  # Lookup dictionary
    "param_alias",  # Decorator
    "RELIC_TIERS",  # Lookup dictionary
    "STAT_ENUMS",  # Lookup dictionary
    "UNIT_STAT_ENUMS_MAP",  # Lookup dictionary
]

DATA_PATH = os.path.join(os.getcwd(), "data")


class DataItemConstants:
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
    PlayerPortaitDefinitions = 65536
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
    Help = -9223372036854775808
    Segment1 = 2097151
    Segment2 = 68717379584
    Segment3 = 206158430208
    Segment4 = 281200098803712
    UBSUpdate = 2150109456

    @classmethod
    def get(cls, item):
        return str(getattr(cls, item)) if getattr(cls, item, None) else None

    @classmethod
    def get_names(cls):
        return [x for x in list(cls.__dict__.keys()) if not x.startswith('_') and
                not isinstance(cls.__dict__[x], classmethod)]


class LoggingFormatter(logging.Formatter):
    """Custom logging formatter class with colored output"""

    # Colors
    black = "\x1b[30m"
    white = "\x1b[37m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    gray = "\x1b[38m"
    # Styles
    reset = "\x1b[0m"
    bold = "\x1b[1m"

    # ANSI color reference https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797

    COLORS = {
        logging.DEBUG: gray + bold,
        logging.INFO: blue + bold,
        logging.WARNING: yellow + bold,
        logging.ERROR: red,
        logging.CRITICAL: "\x1b[1;31;43m",  # Bold (1) Red (31) with Yellow (43) background
    }

    def format(self, record):
        """Method to dynamically color log messages for console output based on message severity"""
        log_color = self.COLORS[record.levelno]
        time_color = "\x1b[1;30;47m"
        format_str = (
                "(black){asctime}(reset) | (lvl_color){levelname:8}(reset) | "
                + "(green){name:<25} | {threadName} | "
                + "(green){module:<14}(reset) | (green){funcName:>20}:{lineno:^4}(reset) | {message}"
        )
        """
        log_message_format = ('{asctime} | [{levelname:^9}] | {name:25} | pid:{process} | {threadName} | ' +
                              '{filename:<15} | {module:<14} : {funcName:>20}()_{lineno:_^4}_ | {message}')
        """
        format_str = format_str.replace("(black)", time_color)
        format_str = format_str.replace("(reset)", self.reset)
        format_str = format_str.replace("(lvl_color)", log_color)
        format_str = format_str.replace("(green)", self.green + self.bold)
        formatter = logging.Formatter(format_str, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


def _get_function_name() -> str:
    """Return the name for the calling function"""
    return f"{inspect.stack()[1].function}()"


def enable_default_logger():
    global _DEFAULT_LOGGER_ENABLED
    get_logger().debug("Enabled default default_logger")
    _DEFAULT_LOGGER_ENABLED = True


def param_alias(param: str, alias: str) -> Callable:
    """Decorator for aliasing function parameters"""

    def decorator(func: Callable) -> Callable:
        """Decorating function"""

        @wraps(func)
        def wrapper(*args, **kwargs) -> Callable:
            """Wrapper function"""
            if alias in kwargs:
                kwargs[param] = kwargs.pop(alias)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def _get_new_logger(
        name: str | Sentinel = OPTIONAL,
        *,
        log_level: str = "DEBUG",
        log_to_console: bool = True,
        log_to_file: bool = True,
) -> logging.Logger:
    """Get default_logger instance

    Args:
        name: Name of the default_logger instance to create or retrieve
        log_level: The message severity level to assign to the new default_logger instance
        log_to_console: Flag to enable console logging
        log_to_file: Flag to enable file logging

    Returns:
        default_logger instance

    """
    if name is NotSet:
        name = _DEFAULT_LOGGER_NAME

    tmp_logger: logging.Logger = logging.getLogger(name)
    tmp_logger.setLevel(logging.getLevelName(log_level))

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(LoggingFormatter())
        tmp_logger.addHandler(console_handler)

    log_path = NotSet
    # File handler
    if log_to_file:
        logfile_name = name + ".log"
        root_log_path = os.path.join(os.getcwd(), "logs")
        Path(root_log_path).mkdir(parents=True, exist_ok=True)
        log_path = os.path.join(root_log_path, logfile_name)
        file_handler = RotatingFileHandler(filename=log_path, encoding="utf-8")
        file_handler_formatter = LoggingFormatter()
        file_handler.setFormatter(file_handler_formatter)
        tmp_logger.addHandler(file_handler)
    tmp_logger.info("")
    tmp_logger.info(" --- [ Logging started for %s ] ---", name)
    tmp_logger.info(" Log file path: %s", log_path)
    global _LOGGER_REGISTRY
    _LOGGER_REGISTRY[name] = tmp_logger
    tmp_logger.debug(f"{_LOGGER_REGISTRY[name]} added to the global default_logger registry under the key '{name}'.")
    tmp_logger.debug(f"New default_logger name: {name} - Instance: {tmp_logger}")
    return tmp_logger


def get_logger(
        name: str = _DEFAULT_LOGGER_NAME,
        default_logger: bool = _DEFAULT_LOGGER_ENABLED,
        **kwargs,
) -> logging.Logger:
    """Returns a default_logger"""
    queued_msgs = [f"Received default_logger request from {_get_function_name()}"]
    if name in _LOGGER_REGISTRY:
        queued_msgs.append(f"Found default_logger in registry. Returning {_LOGGER_REGISTRY[name]}")
        for msg in queued_msgs:
            _LOGGER_REGISTRY[name].debug(msg)
        return _LOGGER_REGISTRY[name]
    if default_logger:
        global _DEFAULT_LOGGER_ENABLED
        _DEFAULT_LOGGER_ENABLED = True
        queued_msgs.append(f"Creating new default_logger with {name=} {default_logger=}")
        new_logger = _get_new_logger(name, **kwargs)
        for msg in queued_msgs:
            new_logger.debug(msg)
        return new_logger
    else:
        # If the default default_logger is disabled, log messages to NULL handler
        # This allows library users to implement their own loggers, if desired
        base_logger: logging.Logger = logging.getLogger(_DEFAULT_LOGGER_NAME)
        base_logger.addHandler(logging.NullHandler())
        queued_msgs.append(f"Return base NULL default_logger instance.")
        return base_logger


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
}

LANGUAGES: list[str] = ["chs_cn", "cht_cn", "eng_us", "fre_fr", "ger_de", "ind_id", "ita_it", "jpn_jp", "kor_kr",
                        "por_br", "rus_ru", "spa_xm", "tha_th", "tur_tr"]
