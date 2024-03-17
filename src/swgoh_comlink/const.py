# coding=utf-8
"""
Constants used throughout the comlink_python package
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import LiteralString

default_logger_name = "swgoh_comlink"
logging_instances = {}

__all__ = ("Constants",)


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


def _get_new_logger(
        name: str = default_logger_name,
        /,
        *,
        log_level: str = "INFO",
        log_to_console: bool = False,
        log_to_file: bool = True,
        logfile_name: str = None,
) -> logging.Logger:
    """Get logger instance

    Args:
        name: Name of the logger instance to create or retrieve
        log_level: The message severity level to assign to the new logger instance
        log_to_console: Flag to enable console logging
        log_to_file: Flag to enable file logging
        logfile_name: Log file name if logging to file enabled

    Returns:
        logger instance

    """
    print(f"[DEBUG] Default logger name: {default_logger_name}")
    """Create a logging instance and return a logger"""
    if name != default_logger_name:
        print("logger name is None or DEFAULT")
        name = f"{default_logger_name}.{name}"
    else:
        name = default_logger_name
    print(f"[DEBUG] Logger name: {name}")
    if name in logging_instances:
        print(f"[DEBUG] Existing logger instance for {name} found. Using that.")
        logging_instances[name]["instance"].info(
            "Existing logger instance for %s found. Using that.", name
        )
        return logging_instances[name]["instance"]
    else:
        logger = logging.getLogger(name)
    logger.setLevel(logging.getLevelName(log_level))

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(LoggingFormatter())
        logger.addHandler(console_handler)

    # File handler
    log_path = None
    if log_to_file:
        if logfile_name is None:
            logfile_name = name + ".log"
        print(f"[DEBUG] {logfile_name=}")
        root_log_path = os.path.join(os.getcwd(), "logs")
        Path(root_log_path).mkdir(parents=True, exist_ok=True)
        log_path = os.path.join(root_log_path, logfile_name)
        file_handler = RotatingFileHandler(filename=log_path, encoding="utf-8")
        file_handler_formatter = LoggingFormatter()
        file_handler.setFormatter(file_handler_formatter)
        logger.addHandler(file_handler)
    logger.info(" --- [ Logging started for %s ] ---", name)
    logging_instances[name] = {"file": log_path, "instance": logger}
    print(f"[DEBUG] {logging_instances[name]=}")
    return logger


class Constants:
    """Package wide constants"""

    _logger_name = default_logger_name
    logger: logging.Logger = _get_new_logger(default_logger_name)
    DATA_PATH: LiteralString = os.path.join(os.getcwd(), "data")

    @property
    def logger_name(self) -> str:
        """Return the logger name"""
        return self._logger_name

    @classmethod
    def get_logger(cls) -> logging.Logger:
        """Return the active logger instance"""
        return cls.logger

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
