# coding=utf-8
"""
Constants used throughout the swgoh_comlink package
"""

from __future__ import annotations, absolute_import

import inspect
import logging
import os
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable
from enum import IntFlag, auto

from sentinels import Sentinel

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


class Config:
    """Container class for global configuration items"""
    DEFAULT_LOGGER_NAME = "swgoh_comlink"
    DEFAULT_LOGGER_ENABLED = False
    DEBUG = False
    DATA_PATH = os.path.join(os.getcwd(), "data")
    LOG_PATH = os.path.join(os.getcwd(), "logs")
    LOGGER: logging.Logger | None = None


# noinspection SpellCheckingInspection
class Constants:
    """Package wide constants"""

    MODULE_NAME = "SwgohComlink"

    RELIC_OFFSET = 2

    MAX_VALUES: dict[str, int] = {
            "GEAR_TIER": 13,
            "UNIT_LEVEL": 85,
            "RELIC_TIER": 9,
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

    UNIT_RARITY_NAMES: dict[str, int] = {
            "ONE_STAR": 1,
            "TWO_STAR": 2,
            "THREE_STAR": 3,
            "FOUR_STAR": 4,
            "FIVE_STAR": 5,
            "SIX_STAR": 6,
            "SEVEN_STAR": 7,
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
    CATEGORY = 1
    UNLOCK_ANNOUNCEMENT_DEFINITION = auto()
    SKILL = auto()
    EQUIPMENT = auto()
    EFFECT = auto()
    XP_TABLE = auto()
    TABLE = XP_TABLE
    BATTLE_ENVIRONMENTS = auto()
    EVENT_SAMPLING = auto()
    TARGETING_SET = auto()
    REQUIREMENT = auto()
    POWER_UP_BUNDLE = auto()
    GUILD_BANNER = auto()
    BATTLE_TARGETING_RULE = auto()
    PERSISTENT_VFX = auto()
    MATERIAL = auto()
    PLAYER_TITLE = auto()
    PLAYER_PORTRAIT = auto()
    TIME_ZONE_CHANGE_CONFIG = auto()
    ENVIRONMENT_COLLECTION = auto()
    EFFECT_ICON_PRIORITY = auto()
    SOCIAL_STATUS = auto()
    ABILITY = auto()
    STAT_PROGRESSION = auto()
    CHALLENGE = auto()
    CHALLENGE_STYLE = CHALLENGE
    WAR_DEFINITION = auto()
    STAT_MOD_SET = auto()
    STAT_MOD = STAT_MOD_SET
    RECIPE = auto()
    MOD_RECOMMENDATION = auto()
    SCAVENGER_CONVERSION_SET = auto()
    GUILD = auto()
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
    MYSTERY_BOX = auto()
    MYSTERY_STAT_MOD = MYSTERY_BOX
    COOLDOWN = auto()
    DAILY_ACTION_CAP = auto()
    ENERGY_REWARD = auto()
    UNIT_GUIDE_DEFINITION = auto()
    GALACTIC_BUNDLE = auto()
    LINKED_STORE_ITEM = GALACTIC_BUNDLE
    RELIC_TIER_DEFINITION = auto()
    UNITS = auto()
    CAMPAIGN = auto()
    CONQUEST = auto()
    CONQUEST_DEFINITION = CONQUEST
    CONQUEST_MISSION = CONQUEST
    ARTIFACT_DEFINITION = CONQUEST
    CONSUMABLE_DEFINITION = CONQUEST
    CONSUMABLE_TYPE = CONQUEST
    ARTIFACT_TIER_DEFINITION = CONQUEST
    CONSUMABLE_TIER_DEFINITION = CONQUEST
    RECOMMENDED_SQUAD = auto()
    UNIT_GUIDE_LAYOUT = auto()
    DAILY_LOGIN_REWARD_DEFINITION = auto()
    CALENDAR_CATEGORY_DEFINITION = auto()
    TERRITORY_TOURNAMENT_DAILY_REWARD_TABLE = auto()
    DATACRON = auto()
    DATACRON_SET = DATACRON
    DATACRON_TEMPLATE = DATACRON
    DATACRON_AFFIX_TEMPLATE_SET = DATACRON
    DATACRON_HELP_ENTRY = DATACRON
    DISPLAYABLE_ENEMY = auto()
    EPISODE_DEFINITION = auto()
    LINKING_REWARD = auto()

    SEGMENT1 = 2097151
    SEGMENT2 = 68717379584
    SEGMENT3 = 206158430208
    SEGMENT4 = 281200098803712

    DATA_BUILDER = STAT_PROGRESSION + STAT_MOD + TABLE + XP_TABLE + EQUIPMENT + RELIC_TIER_DEFINITION + UNITS + SKILL

    @classmethod
    def members(cls):
        """Return a list of the member names of the DataItems class."""
        return cls.__members__.keys()

    @classmethod
    def get(cls, item):
        return str(getattr(cls, item)) if getattr(cls, item, None) else None

    @classmethod
    def get_data_collection_names(cls) -> list:
        """
            This class method retrieves the names of all class attributes that are instances
            of the `DataItems` type.

            Returns:
                list: A list containing the names of attributes in the class that are instances
                of the `DataItems` type.
        """
        return [x for x in list(cls.__dict__.keys()) if isinstance(cls.__dict__[x], DataItems)]


class LoggingFormatterColor(logging.Formatter):
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
        format_str = format_str.replace("(black)", time_color)
        format_str = format_str.replace("(reset)", self.reset)
        format_str = format_str.replace("(lvl_color)", log_color)
        format_str = format_str.replace("(green)", self.green + self.bold)
        formatter = logging.Formatter(format_str, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


class LoggingFormatter(logging.Formatter):
    """Custom logging formatter class"""

    def format(self, record):
        log_message_format = \
            '{asctime} | {levelname:<9} | {name:15} | {module:<14} : {funcName:>30}() [{lineno:_>5}] | {message}'
        formatter = logging.Formatter(log_message_format, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


def get_function_name() -> str:
    return f"{inspect.stack()[1].function}()"


def get_called_by() -> str:
    return f"{inspect.stack()[2].function}() in {inspect.stack()[2].filename}"


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
        log_level: str = "INFO",
        log_to_console: bool = True,
        log_to_file: bool = True,
        max_log_bytes: int = 25000000,
        backup_log_count: int = 3,
        colorize: bool = False,
        ) -> logging.Logger:
    """Get default_logger instance

    Args:
        name: Name of the default_logger instance to create or retrieve
        log_level: The message severity level to assign to the new default_logger instance
        log_to_console: Flag to enable console logging
        log_to_file: Flag to enable file logging
        max_log_bytes: The maximum size in bytes of log file
        backup_log_count: The number of backup log files to retain
        colorize: Flag to enable ANSI colorized log output

    Returns:
        default_logger instance

    """

    if isinstance(name, Sentinel):
        name = Config.DEFAULT_LOGGER_NAME

    if Config.LOGGER is not None and Config.LOGGER.name == name:
        Config.LOGGER.debug(f"Existing logger found in global Config class. Returning {Config.LOGGER!r}")
        return Config.LOGGER

    queued_msg = [f"{get_function_name()} called by {get_called_by()}"]

    tmp_logger = logging.getLogger(name)
    tmp_logger.setLevel(logging.getLevelName(log_level))

    # Console handler
    if log_to_console:
        queued_msg.append(f"Configuring console logging handler ...")
        console_handler = logging.StreamHandler()
        if colorize:
            console_handler.setFormatter(LoggingFormatterColor())
        else:
            console_handler.setFormatter(LoggingFormatter())
        tmp_logger.addHandler(console_handler)

    log_path = None

    # File handler
    if log_to_file:
        queued_msg.append(f"Configuring file logging handler ...")
        logfile_name = name + ".log"
        root_log_path = os.path.join(os.getcwd(), "logs")
        Path(root_log_path).mkdir(parents=True, exist_ok=True)
        log_path = os.path.join(root_log_path, logfile_name)
        file_handler = RotatingFileHandler(
                filename=log_path, encoding="utf-8", maxBytes=max_log_bytes, backupCount=backup_log_count
                )
        if colorize:
            file_handler.setFormatter(LoggingFormatterColor())
        else:
            file_handler.setFormatter(LoggingFormatter())
        tmp_logger.addHandler(file_handler)

    tmp_logger.info("")
    tmp_logger.info(" --- [ Logging started for %s ] ---", name)
    tmp_logger.info(" Log file path: %s", log_path)
    tmp_logger.info(" Log file size: %s, max count: %s", max_log_bytes, backup_log_count)
    tmp_logger.debug(f"New default_logger name: {name!r} - Instance: {tmp_logger} (ID: {hex(id(tmp_logger))})")

    for handler in tmp_logger.handlers:
        tmp_logger.debug(f"Handler: {handler!r}")

    if len(queued_msg) > 0:
        for msg in queued_msg:
            tmp_logger.debug(f"Queued message: {msg}")

    Config.LOGGER = tmp_logger

    return tmp_logger


def _remove_null_handlers(logger: logging.Logger) -> None:
    for handler in logger.handlers:
        if isinstance(handler, logging.NullHandler):
            logger.removeHandler(handler)


def get_logger(
        name: str = Config.DEFAULT_LOGGER_NAME,
        default_logger: bool = Config.DEFAULT_LOGGER_ENABLED,
        **kwargs,
        ) -> logging.Logger:
    """Get a logging.Logger instance

        Args:
            name: Name of the default_logger instance to create or retrieve
            default_logger: Flag to enable default logger

        Keyword Args
            log_level: Log level of messages to capture. [Default: "INFO"]
            log_to_console: Enable logging to STDERR (console). [Default: True]
            log_to_file: Enabling logging to file(s). [Default: True]
            max_log_bytes: Maximum size of log file before rotating. [Default: 25,000,000]
            backup_log_count: Number of log files to keep. [Default: 3]
            colorize: Enable ANSI colorized log messages [Default: False]

        Returns:
            logging.Logger instance
    """
    queued_msgs = [
            f"Received default_logger request from: {get_called_by()}, logger name: {name}",
            f"Default logger: {default_logger}",
            ]

    if default_logger or Config.DEFAULT_LOGGER_ENABLED:
        Config.DEFAULT_LOGGER_ENABLED = True
        queued_msgs.append(f"Creating new default_logger with {name=} {default_logger=}")
        new_logger = _get_new_logger(name, **kwargs)
        _remove_null_handlers(new_logger)
        for msg in queued_msgs:
            new_logger.debug(msg)
        return new_logger
    else:
        # If the default default_logger is disabled, log messages to NULL handler
        # This allows library users to implement their own loggers, if desired
        base_logger = logging.getLogger(Config.DEFAULT_LOGGER_NAME)
        base_logger.addHandler(logging.NullHandler())
        queued_msgs.append(f"Return base NULL default_logger instance.")
        return base_logger


def set_debug(debug: bool):
    """Set the global DEBUG flag"""
    orig_debug = getattr(Config, "DEBUG", False)
    get_logger().debug(f"{get_function_name()}: Setting _DEBUG to {debug}. Previous setting: {orig_debug}")
    setattr(Config, 'DEBUG', debug)


__all__ = [
        GIVEN,  # Sentinel
        OPTIONAL,  # Sentinel
        MISSING,  # Sentinel
        NotGiven,  # Sentinel
        REQUIRED,  # Sentinel
        MutualExclusiveRequired,  # Sentinel
        MutualRequiredNotSet,  # Sentinel
        NotSet,  # Sentinel
        SET,  # Sentinel
        EMPTY,  # Sentinel
        DataItems,  # Class for get_game_data() 'items' arguments
        Constants,  # Class with general application shared constants/methods
        Config,  # Global configuration container class
        get_logger,  # Function to create/return library logger
        param_alias,  # Decorator to replace function/method argument aliases with actual parameter name
        get_function_name,
        get_called_by,
        ]
