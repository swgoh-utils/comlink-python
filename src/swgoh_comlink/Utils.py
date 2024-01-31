"""
Helper utilities for the swgoh-python-async package and related modules
"""
from __future__ import annotations, print_function

import logging
import os
import time
from datetime import datetime, timezone
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path

from swgoh_comlink import version

logger_name = 'swgoh_comlink'
logging_instances = {}

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

MOD_SET_IDS = {
    "1": "Health",
    "2": "Offense",
    "3": "Defense",
    "4": "Speed",
    "5": "Critical Chance",
    "6": "Critical Damage",
    "7": "Potency",
    "8": "Tenacity"
}

MOD_SLOTS = {
    "2": "Square",
    "3": "Arrow",
    "4": "Diamond",
    "5": "Triangle",
    "6": "Circle",
    "7": "Plus/Cross"
}


def func_timer(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()
        logging.getLogger(logger_name).debug(f'func:{f.__name__} took: {te - ts:.6f} sec')
        return result

    return wrap


def func_debug_logger(f):
    @wraps(f)
    def wrap(*args, **kw):
        logging.getLogger(logger_name).debug("  [ function %s ] called with args: %s and kwargs: %s",
                                             f.__name__, args, kw)
        result = f(*args, **kw)
        return result

    return wrap


def validate_path(path: str) -> bool:
    """Test whether provided path exists or not"""
    return os.path.exists(path) and os.path.isfile(path)


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
    payload = {
        "payload": {},
        "enums": enums
    }
    if allycode is not None:
        allycode = sanitize_allycode(allycode)
        payload['payload']['allyCode'] = f'{allycode}'
    else:
        payload['payload']['playerId'] = f'{player_id}'
    if enums:
        payload["enums"] = True
    return payload


"""
def param_alias(param: str, alias: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Callable:
            if param in kwargs:
                kwargs[alias] = kwargs.pop(param)
            return func(*args, **kwargs)

        return wrapper

    return decorator
"""


def get_version() -> str:
    return version


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
    if name is None or name == logger_name:
        name = logger_name
    else:
        name = f"{logger_name}.{name}"
    if name in logging_instances:
        return logging_instances[name]['instance']
    logger = logging.getLogger(name)
    logger.setLevel(logging.getLevelName(logging_level.upper()))
    # Create message formatting to include module and function naming for easier debugging
    formatter = logging.Formatter(
        '{asctime} | [{levelname:^9}] | {name:25} | pid:{process} | {threadName} | ' +
        '{module:14} : {funcName:>20}()_{lineno:_^4}_ | {message}',
        style='{')
    log_base = os.path.join(os.getcwd(), 'logs')
    try:
        os.mkdir(log_base)
    except FileExistsError:
        pass
    working_dir = Path(os.getcwd())
    path_parts = list(working_dir.parts)
    path_parts.append('logs')
    path_parts.append(logger_name + '.log')
    log_path = Path(*path_parts)
    # Create a log file handler to write logs to disk
    log_file_handler = RotatingFileHandler(
        filename=log_path,
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
    # logger.info(f"Logger created with level set to {logging_level.upper()!r}.")
    logger.propagate = False
    logging_instances[name] = {'file': log_path, 'instance': logger}
    return logger


def get_log_file_path(logger_instance_name: str) -> str:
    """Retrieve the requested log file path and return it as a string"""
    return logging_instances[logger_instance_name]['file']


def human_time(unix_time: int or float) -> str:
    """Convert unix time to human readable string"""
    if isinstance(unix_time, float):
        unix_time = int(unix_time)
    if isinstance(unix_time, str):
        try:
            unix_time = int(unix_time)
        except Exception as exc:
            logging.getLogger(logger_name).exception(f"Exception caught: [{exc}]")
            raise
    return datetime.fromtimestamp(unix_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%s')


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


def create_localized_unit_name_dictionary(locale: str or list) -> dict:
    """
    Take a localization element from the SwgohComlink.get_localization() result dictionary and
    extract the UNIT_NAME entries for building a conversion dictionary for translating BASEID values to in game
    descriptive names

    :param locale: The string element or List[bytes] from the SwgohComlink.get_localization() result key value
    :type locale: str or List[bytes]
    :return: A dictionary with the UNIT_NAME BASEID as keys and the UNIT_NAME description as values
    :rtype: dict
    """
    unit_name_map = {}
    lines = []
    if isinstance(locale, str):
        lines = locale.split('\n')
    elif isinstance(locale, list):
        lines = locale
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode()
        line = line.rstrip('\n')
        if line.startswith('#') or '|' not in line:
            continue
        if line.startswith('UNIT_'):
            name_key, desc = line.split('|')
            if name_key.endswith('_NAME'):
                unit_name_map[name_key] = desc
    return unit_name_map


def get_guild_members(comlink, /, *, player_id: str = None, allycode: str or int = None) -> list:
    """Return list of guild member player allycodes based upon provided player ID or allycode

    :param comlink: Instance of SwgohComlink
    :type comlink: SwgohComlink
    :param player_id: Player's ID
    :type player_id: str
    :param allycode: Player's allycode
    :type allycode: str or int
    :return: list of guild members
    :rtype: list
    """
    if 'player_id' is None and 'allycode' is None:
        raise RuntimeError(f'player_id or allycode must be provided.')
    if player_id is not None:
        player = comlink.get_player(player_id=player_id)
    else:
        player = comlink.get_player(allycode=sanitize_allycode(allycode))
    guild = comlink.get_guild(guild_id=player['guildId'])
    return guild['member']
