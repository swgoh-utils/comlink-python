"""
Helper utilities for the swgoh-python-async package and related modules
"""
from __future__ import annotations, print_function

import functools
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Callable

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync

logger_name = 'swgoh_comlink'

LEAGUES: dict[str, int] = {
    'kyber': 100,
    'aurodium': 80,
    'chromium': 60,
    'bronzium': 40,
    'carbonite': 20
}

DIVISIONS: dict[str, int] = {
    '1': 25,
    '2': 20,
    '3': 15,
    '4': 10,
    '5': 5
}

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
    "61": "UNIT_STAT_STAT_VIEW_MASTERY"
}

UNIT_STAT_ENUMS_MAP: dict[str, dict[str, str]] = {
    "0": {
        "enum": "UnitStat_DEFAULT",
        "nameKey": "None"
    },
    "1": {
        "enum": "UNITSTATMAXHEALTH",
        "nameKey": "UnitStat_Health",
        "tableKey": "MAX_HEALTH"
    },
    "2": {
        "enum": "UNITSTATSTRENGTH",
        "nameKey": "UnitStat_Strength",
        "tableKey": "STRENGTH"
    },
    "3": {
        "enum": "UNITSTATAGILITY",
        "nameKey": "UnitStat_Agility",
        "tableKey": "AGILITY"
    },
    "4": {
        "enum": "UNITSTATINTELLIGENCE",
        "nameKey": "UnitStat_Intelligence",
        "tableKey": "INTELLIGENCE"
    },
    "5": {
        "enum": "UNITSTATSPEED",
        "nameKey": "UnitStat_Speed",
        "tableKey": "SPEED"
    },
    "6": {
        "enum": "UNITSTATATTACKDAMAGE",
        "nameKey": "UnitStat_AttackDamage",
        "tableKey": "ATTACK_DAMAGE"
    },
    "7": {
        "enum": "UNITSTATABILITYPOWER",
        "nameKey": "UnitStat_AbilityPower",
        "tableKey": "ABILITY_POWER"
    },
    "8": {
        "enum": "UNITSTATARMOR",
        "nameKey": "UnitStat_Armor",
        "tableKey": "ARMOR"
    },
    "9": {
        "enum": "UNITSTATSUPPRESSION",
        "nameKey": "UnitStat_Suppression",
        "tableKey": "SUPPRESSION"
    },
    "10": {
        "enum": "UNITSTATARMORPENETRATION",
        "nameKey": "UnitStat_ArmorPenetration",
        "tableKey": "ARMOR_PENETRATION"
    },
    "11": {
        "enum": "UNITSTATSUPPRESSIONPENETRATION",
        "nameKey": "UnitStat_SuppressionPenetration",
        "tableKey": "SUPPRESSION_PENETRATION"
    },
    "12": {
        "enum": "UNITSTATDODGERATING",
        "nameKey": "UnitStat_DodgeRating_TU5V",
        "tableKey": "DODGE_RATING"
    },
    "13": {
        "enum": "UNITSTATDEFLECTIONRATING",
        "nameKey": "UnitStat_DeflectionRating_TU5V",
        "tableKey": "DEFLECTION_RATING"
    },
    "14": {
        "enum": "UNITSTATATTACKCRITICALRATING",
        "nameKey": "UnitStat_AttackCriticalRating_TU5V",
        "tableKey": "ATTACK_CRITICAL_RATING"
    },
    "15": {
        "enum": "UNITSTATABILITYCRITICALRATING",
        "nameKey": "UnitStat_AbilityCriticalRating_TU5V",
        "tableKey": "ABILITY_CRITICAL_RATING"
    },
    "16": {
        "enum": "UNITSTATCRITICALDAMAGE",
        "nameKey": "UnitStat_CriticalDamage",
        "tableKey": "CRITICAL_DAMAGE"
    },
    "17": {
        "enum": "UNITSTATACCURACY",
        "nameKey": "UnitStat_Accuracy",
        "tableKey": "ACCURACY"
    },
    "18": {
        "enum": "UNITSTATRESISTANCE",
        "nameKey": "UnitStat_Resistance",
        "tableKey": "RESISTANCE"
    },
    "19": {
        "enum": "UNITSTATDODGEPERCENTADDITIVE",
        "nameKey": "UnitStat_DodgePercentAdditive",
        "tableKey": "DODGE_PERCENT_ADDITIVE"
    },
    "20": {
        "enum": "UNITSTATDEFLECTIONPERCENTADDITIVE",
        "nameKey": "UnitStat_DeflectionPercentAdditive",
        "tableKey": "DEFLECTION_PERCENT_ADDITIVE"
    },
    "21": {
        "enum": "UNITSTATATTACKCRITICALPERCENTADDITIVE",
        "nameKey": "UnitStat_AttackCriticalPercentAdditive",
        "tableKey": "ATTACK_CRITICAL_PERCENT_ADDITIVE"
    },
    "22": {
        "enum": "UNITSTATABILITYCRITICALPERCENTADDITIVE",
        "nameKey": "UnitStat_AbilityCriticalPercentAdditive",
        "tableKey": "ABILITY_CRITICAL_PERCENT_ADDITIVE"
    },
    "23": {
        "enum": "UNITSTATARMORPERCENTADDITIVE",
        "nameKey": "UnitStat_ArmorPercentAdditive",
        "tableKey": "ARMOR_PERCENT_ADDITIVE"
    },
    "24": {
        "enum": "UNITSTATSUPPRESSIONPERCENTADDITIVE",
        "nameKey": "UnitStat_SuppressionPercentAdditive",
        "tableKey": "SUPPRESSION_PERCENT_ADDITIVE"
    },
    "25": {
        "enum": "UNITSTATARMORPENETRATIONPERCENTADDITIVE",
        "nameKey": "UnitStat_ArmorPenetrationPercentAdditive",
        "tableKey": "ARMOR_PENETRATION_PERCENT_ADDITIVE"
    },
    "26": {
        "enum": "UNITSTATSUPPRESSIONPENETRATIONPERCENTADDITIVE",
        "nameKey": "UnitStat_SuppressionPenetrationPercentAdditive",
        "tableKey": "SUPPRESSION_PENETRATION_PERCENT_ADDITIVE"
    },
    "27": {
        "enum": "UNITSTATHEALTHSTEAL",
        "nameKey": "UnitStat_HealthSteal",
        "tableKey": "HEALTH_STEAL"
    },
    "28": {
        "enum": "UNITSTATMAXSHIELD",
        "nameKey": "UnitStat_MaxShield",
        "tableKey": "MAX_SHIELD"
    },
    "29": {
        "enum": "UNITSTATSHIELDPENETRATION",
        "nameKey": "UnitStat_ShieldPenetration",
        "tableKey": "SHIELD_PENETRATION"
    },
    "30": {
        "enum": "UNITSTATHEALTHREGEN",
        "nameKey": "UnitStat_HealthRegen",
        "tableKey": "HEALTH_REGEN"
    },
    "31": {
        "enum": "UNITSTATATTACKDAMAGEPERCENTADDITIVE",
        "nameKey": "UnitStat_AttackDamagePercentAdditive",
        "tableKey": "ATTACK_DAMAGE_PERCENT_ADDITIVE"
    },
    "32": {
        "enum": "UNITSTATABILITYPOWERPERCENTADDITIVE",
        "nameKey": "UnitStat_AbilityPowerPercentAdditive",
        "tableKey": "ABILITY_POWER_PERCENT_ADDITIVE"
    },
    "33": {
        "enum": "UNITSTATDODGENEGATEPERCENTADDITIVE",
        "nameKey": "UnitStat_DodgeNegatePercentAdditive",
        "tableKey": "DODGE_NEGATE_PERCENT_ADDITIVE"
    },
    "34": {
        "enum": "UNITSTATDEFLECTIONNEGATEPERCENTADDITIVE",
        "nameKey": "UnitStat_DeflectionNegatePercentAdditive",
        "tableKey": "DEFLECTION_NEGATE_PERCENT_ADDITIVE"
    },
    "35": {
        "enum": "UNITSTATATTACKCRITICALNEGATEPERCENTADDITIVE",
        "nameKey": "UnitStat_AttackCriticalNegatePercentAdditive",
        "tableKey": "ATTACK_CRITICAL_NEGATE_PERCENT_ADDITIVE"
    },
    "36": {
        "enum": "UNITSTATABILITYCRITICALNEGATEPERCENTADDITIVE",
        "nameKey": "UnitStat_AbilityCriticalNegatePercentAdditive",
        "tableKey": "ABILITY_CRITICAL_NEGATE_PERCENT_ADDITIVE"
    },
    "37": {
        "enum": "UNITSTATDODGENEGATERATING",
        "nameKey": "UnitStat_DodgeNegateRating",
        "tableKey": "DODGE_NEGATE_RATING"
    },
    "38": {
        "enum": "UNITSTATDEFLECTIONNEGATERATING",
        "nameKey": "UnitStat_DeflectionNegateRating",
        "tableKey": "DEFLECTION_NEGATE_RATING"
    },
    "39": {
        "enum": "UNITSTATATTACKCRITICALNEGATERATING",
        "nameKey": "UnitStat_AttackCriticalNegateRating",
        "tableKey": "ATTACK_CRITICAL_NEGATE_RATING"
    },
    "40": {
        "enum": "UNITSTATABILITYCRITICALNEGATERATING",
        "nameKey": "UnitStat_AbilityCriticalNegateRating",
        "tableKey": "ABILITY_CRITICAL_NEGATE_RATING"
    },
    "41": {
        "enum": "UNITSTATOFFENSE",
        "nameKey": "UnitStat_Offense",
        "tableKey": "OFFENSE"
    },
    "42": {
        "enum": "UNITSTATDEFENSE",
        "nameKey": "UnitStat_Defense",
        "tableKey": "DEFENSE"
    },
    "43": {
        "enum": "UNITSTATDEFENSEPENETRATION",
        "nameKey": "UnitStat_DefensePenetration",
        "tableKey": "DEFENSE_PENETRATION"
    },
    "44": {
        "enum": "UNITSTATEVASIONRATING",
        "nameKey": "UnitStat_EvasionRating",
        "tableKey": "EVASION_RATING"
    },
    "45": {
        "enum": "UNITSTATCRITICALRATING",
        "nameKey": "UnitStat_CriticalRating",
        "tableKey": "CRITICAL_RATING"
    },
    "46": {
        "enum": "UNITSTATEVASIONNEGATERATING",
        "nameKey": "UnitStat_EvasionNegateRating",
        "tableKey": "EVASION_NEGATE_RATING"
    },
    "47": {
        "enum": "UNITSTATCRITICALNEGATERATING",
        "nameKey": "UnitStat_CriticalNegateRating",
        "tableKey": "CRITICAL_NEGATE_RATING"
    },
    "48": {
        "enum": "UNITSTATOFFENSEPERCENTADDITIVE",
        "nameKey": "UnitStat_OffensePercentAdditive",
        "tableKey": "OFFENSE_PERCENT_ADDITIVE"
    },
    "49": {
        "enum": "UNITSTATDEFENSEPERCENTADDITIVE",
        "nameKey": "UnitStat_DefensePercentAdditive",
        "tableKey": "DEFENSE_PERCENT_ADDITIVE"
    },
    "50": {
        "enum": "UNITSTATDEFENSEPENETRATIONPERCENTADDITIVE",
        "nameKey": "UnitStat_DefensePenetrationPercentAdditive",
        "tableKey": "DEFENSE_PENETRATION_PERCENT_ADDITIVE"
    },
    "51": {
        "enum": "UNITSTATEVASIONPERCENTADDITIVE",
        "nameKey": "UnitStat_EvasionPercentAdditive",
        "tableKey": "EVASION_PERCENT_ADDITIVE"
    },
    "52": {
        "enum": "UNITSTATEVASIONNEGATEPERCENTADDITIVE",
        "nameKey": "UnitStat_EvasionNegatePercentAdditive",
        "tableKey": "EVASION_NEGATE_PERCENT_ADDITIVE"
    },
    "53": {
        "enum": "UNITSTATCRITICALCHANCEPERCENTADDITIVE",
        "nameKey": "UnitStat_CriticalChancePercentAdditive",
        "tableKey": "CRITICAL_CHANCE_PERCENT_ADDITIVE"
    },
    "54": {
        "enum": "UNITSTATCRITICALNEGATECHANCEPERCENTADDITIVE",
        "nameKey": "UnitStat_CriticalNegateChancePercentAdditive",
        "tableKey": "CRITICAL_NEGATE_CHANCE_PERCENT_ADDITIVE"
    },
    "55": {
        "enum": "UNITSTATMAXHEALTHPERCENTADDITIVE",
        "nameKey": "UnitStat_MaxHealthPercentAdditive",
        "tableKey": "MAX_HEALTH_PERCENT_ADDITIVE"
    },
    "56": {
        "enum": "UNITSTATMAXSHIELDPERCENTADDITIVE",
        "nameKey": "UnitStat_MaxShieldPercentAdditive",
        "tableKey": "MAX_SHIELD_PERCENT_ADDITIVE"
    },
    "57": {
        "enum": "UNITSTATSPEEDPERCENTADDITIVE",
        "nameKey": "UnitStat_SpeedPercentAdditive",
        "tableKey": "SPEED_PERCENT_ADDITIVE"
    },
    "58": {
        "enum": "UNITSTATCOUNTERATTACKRATING",
        "nameKey": "UnitStat_CounterAttackRating",
        "tableKey": "COUNTER_ATTACK_RATING"
    },
    "59": {
        "enum": "UNITSTATTAUNT",
        "nameKey": "UnitStat_Taunt",
        "tableKey": "TAUNT"
    },
    "60": {
        "enum": "UNITSTATDEFENSEPENETRATIONTARGETPERCENTADDITIVE",
        "nameKey": "UnitStat_DefensePenetrationTargetPercentAdditive",
        "tableKey": "DEFENSE_PENETRATION_TARGET_PERCENT_ADDITIVE"
    },
    "61": {
        "enum": "UNITSTATMASTERY",
        "nameKey": "UNIT_STAT_STAT_VIEW_MASTERY",
        "tableKey": "MASTERY"
    }
}


def sanitize_allycode(allycode: str | int) -> str:
    if isinstance(allycode, int):
        allycode = str(allycode)
    allycode = allycode.replace('-', '')
    if not allycode.isdigit() or len(allycode) != 9:
        raise ValueError(f"Invalid ally code: {allycode}")
    return allycode


def get_player_payload(allycode: str | int = None, player_id: str = None, enums: bool = False) -> dict:
    if allycode is None and player_id is None:
        raise ValueError("Either allycode or player_id must be provided.")
    if allycode is not None and player_id is not None:
        raise ValueError("Only one of allycode or player_id can be provided.")
    if allycode is not None:
        allycode = sanitize_allycode(allycode)
        payload = {"allycodes": [allycode]}
    else:
        payload = {"playerIds": [player_id]}
    if enums:
        payload["enums"] = 1
    return payload


def param_alias(param: str, alias: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if param in kwargs:
                kwargs[alias] = kwargs.pop(param)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_logger(name: str = None, logging_level: str = 'INFO', terminal: bool = False) -> logging.Logger:
    """Create logger instance for writing messages to log files.

    :param name: Name of the log file to create. [Default: swgoh-comlink-async.log]
    :type name: str
    :param logging_level: Level of messages to log. [Default: INFO]
    :type logging_level: str
    :param terminal: Flag to determine if messages should be logged to terminal and to log file. [Default: False]
    :type terminal: bool
    :return: Logger instance
    :rtype: Logger
    """
    if name is None:
        name = logger_name
    logger = logging.getLogger(name)
    logger.setLevel(logging.getLevelName(logging_level.upper()))
    # Create message formatting to include module and function naming for easier debugging
    formatter = logging.Formatter('{asctime} [ {levelname:^9}] {module:25} : {funcName:20}({lineno}) - {message}',
                                  style='{')
    log_base = os.path.join(os.getcwd(), 'logs')
    try:
        os.mkdir(log_base)
    except FileExistsError:
        pass
    log_base_name = os.path.join(log_base, f'{logger_name}.log')
    # Create a log file handler to write logs to disk
    log_file_handler = RotatingFileHandler(
        log_base_name,
        maxBytes=25000000,
        backupCount=5
    )
    log_file_handler.setFormatter(formatter)
    logger.addHandler(log_file_handler)
    # Create a second handler for output to terminal
    if terminal is True:
        log_console_handler = logging.StreamHandler()
        log_console_handler.setFormatter(formatter)
        logger.addHandler(log_console_handler)
    logger.info(f"Logger created with level set to {logging_level.upper()!r}.")
    return logger


def human_time(time: int or float) -> str:
    """Convert unix time to human readable string"""
    if isinstance(time, float):
        time = int(time)
    if isinstance(time, str):
        try:
            time = int(time)
        except Exception as exc:
            logging.getLogger(logger_name).exception(f"Exception caught: [{exc}]")
            raise
    return datetime.fromtimestamp(time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%s')


def construct_unit_stats_query_string(flags: list, language: str) -> str:
    """
    Constructs query string from provided flags and language to be used with the get_unit_stats function
    """
    flag_string = f'flags={",".join(flags)}' if flags else None
    language_string = f'language={language}' if language else None
    constructed_string = '&'.join(filter(None, [flag_string, language_string]))
    return f'?{constructed_string}' if constructed_string else None


def update_hmac_obj(hmac_obj, values: list):
    for value in values:
        hmac_obj.update(value.encode())


def convert_league_to_int(league: int | str) -> int:
    if isinstance(league, str):
        return LEAGUES[league.lower()]
    return league


def convert_divisions_to_int(division: int | str) -> int:
    if isinstance(division, str):
        return DIVISIONS[division.lower()]
    if isinstance(division, int) and len(str(division)) == 1:
        return DIVISIONS[str(division)]
    return division


def construct_url_base(protocol: str, host: str, port: int) -> str:
    return f"{protocol}://{host}:{port}"


def get_guild_members(comlink: SwgohComlink or SwgohComlinkAsync, **kwargs) -> list:
    """Return list of guild member player allycodes based upon provided player ID or allycode"""
    guild_members = []
    if 'player_id' or 'allycode' not in kwargs:
        raise f'player_id or allycode must be provided.'
    # TODO: check if player_id or allycode provided
    if isinstance(comlink, SwgohComlink):
        # player = comlink.get_player_arena(allycode=)
        # guild = comlink
        pass
    return guild_members