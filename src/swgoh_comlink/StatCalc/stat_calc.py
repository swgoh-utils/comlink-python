# coding=utf-8
"""
Python library module for calculating character and ship statistic values for the Star Wars: Galaxy of Heroes mobile
game from EA/CG.
"""
import base64
import functools
import io
import json
import logging
import os
import zipfile
from copy import deepcopy, copy
from dataclasses import dataclass
from math import floor as math_floor
from typing import Any
from typing import Callable

import swgoh_comlink
from swgoh_comlink.constants import Constants, get_logger, set_debug
from swgoh_comlink.data_builder import DataBuilder, DataBuilderException
from swgoh_comlink.utils import _get_function_name, validate_file_path, create_localized_unit_name_dictionary

logger = get_logger()


def _format_stats(stats: dict, level: int = 85, options: dict = None) -> dict:
    logger.info("*** Formatting stats *** ")
    if not stats:
        logger.debug("No stats object provided. Returning empty.")
        return {}

    logger.debug(f"{_get_function_name()}: Stats: {stats} {level=} {options=}")

    scale = 1
    if options["scaled"]:
        scale = 1e-4
    elif options["unscaled"]:
        scale = 1e-8

    logger.debug(f"{_get_function_name()}: Scaling stats ... {scale=}")

    if stats['mods']:
        logger.debug(f"{_get_function_name()}: Rounding mod values ... ")
        for stat_id, value in stats['mods'].items():
            stats['mods'][stat_id] = round(value, 6)
            logger.debug(f"{_get_function_name()}: {stat_id} old value: {value}, "
                         + f"new value: {stats['mods'][stat_id]}")

    if scale != 1:
        logger.debug(f"{_get_function_name()}: Scaling stats ... {scale=}")
        for stat_type in ('base', 'gear', 'crew', 'growthModifiers', 'mods'):
            if stat_type in stats:
                for stat_id in stats[stat_type].keys():
                    original_value = stats[stat_type][stat_id]
                    stats[stat_type][stat_id] *= scale
                    logger.debug(f"{_get_function_name()}: {stat_id} old value: {original_value}, "
                                 + f"new value: {stats[stat_type][stat_id]}")
            else:
                logger.debug(f"{_get_function_name()}: {stat_type} not found in {list(stats.keys())}")

    if options.get('percentVals') or options.get('gameStyle'):  # 'gameStyle' flag inherently includes 'percentVals'
        def convert_percent(stat_id_str: str, convert_func: Callable):
            logger.debug(f"{_get_function_name()}: {stat_id_str=}, {convert_func=}")
            flat = stats['base'].get(stat_id_str, 0)
            percent = convert_func(flat)
            stats['base'][stat_id_str] = percent
            last = percent
            logger.debug(f"{_get_function_name()}: {flat=}, {percent=}, {last=}")
            if stats.get('crew'):  # is Ship
                if stats['crew'].get(stat_id_str):
                    flat += stats['crew'][stat_id_str]
                    stats['crew'][stat_id_str] = convert_func(flat) - last
            else:  # is Char
                if stats.get('gear') and stats['gear'].get(stat_id_str):
                    flat += stats['gear'][stat_id_str]
                    percent = convert_func(flat)
                    stats['gear'][stat_id_str] = percent - last
                    last = percent
                if stats.get('mods') and stats['mods'].get(stat_id_str):
                    flat += stats['mods'][stat_id_str]
                    stats['mods'][stat_id_str] = convert_func(flat) - last

        # convert Crit
        convert_percent('14', lambda val: _convert_flat_crit_to_percent(val, scale * 1e8))  # Ph. Crit Rating -> Chance
        convert_percent('15', lambda val: _convert_flat_crit_to_percent(val, scale * 1e8))  # Sp. Crit Rating -> Chance
        # convert Def
        convert_percent('8', lambda val: _convert_flat_def_to_percent(val, level, scale * 1e8,
                                                                      bool(stats.get('crew'))))  # Armor
        convert_percent('9', lambda val: _convert_flat_def_to_percent(val, level, scale * 1e8,
                                                                      bool(stats.get('crew'))))  # Resistance
        # convert Acc
        convert_percent('37', lambda val: _convert_flat_acc_to_percent(val, scale * 1e8))  # Physical Accuracy
        convert_percent('38', lambda val: _convert_flat_acc_to_percent(val, scale * 1e8))  # Special Accuracy
        # convert Evasion
        convert_percent('12', lambda val: _convert_flat_acc_to_percent(val, scale * 1e8))  # Dodge
        convert_percent('13', lambda val: _convert_flat_acc_to_percent(val, scale * 1e8))  # Deflection
        # convert Crit Avoidance
        convert_percent('39',
                        lambda val: _convert_flat_crit_avoid_to_percent(val, scale * 1e8))  # Physical Crit Avoidance
        convert_percent('40',
                        lambda val: _convert_flat_crit_avoid_to_percent(val, scale * 1e8))  # Special Crit Avoidance

    if options.get("gameStyle"):
        gs_stats = {"final": {}}
        stat_list = list(stats["base"].keys())
        logger.debug(f"{_get_function_name()}: {stat_list=}")

        def add_stats(stat_id_str: str):
            logger.debug(f"{_get_function_name()}: {stat_id_str=} ({type(stat_id_str)})...")
            if not isinstance(stat_id_str, str):
                logger.debug(f"{_get_function_name()}: converting 'stat_id' from {type(stat_id_str)} to 'str' ...")
                stat_id_str = str(stat_id_str)
            if stat_id_str not in stat_list:
                logger.debug(f"{_get_function_name()}: {stat_id_str} not in stat_list. Adding it ...")
                stat_list.append(stat_id_str)

        if "gear" in stats:  # Character
            logger.debug(f"{_get_function_name()}: Processing 'gear' ...")
            for stat_id in stats['gear']:
                add_stats(stat_id)  # add stats from gear to list
            if 'mods' in stats:
                logger.debug(f"{_get_function_name()}: Processing 'mods' ...")
                for stat_id in stats['mods']:
                    add_stats(stat_id)  # add stats from mods to list
                gs_stats['mods'] = stats['mods']  # keep mod stats untouched

            for stat_id in stat_list:
                flat_stat_id = stat_id
                logger.debug(f"{_get_function_name()}: {flat_stat_id=} ({type(flat_stat_id)})... ...")
                match math_floor(int(stat_id)):
                    # stats with both Percent Stats get added to the ID for their flat stat
                    # (which was converted to % above)
                    case 21 | 22:  # Ph. Crit Chance | Sp. Crit Chance
                        # 21-14 = 7 = 22-15 ==> subtracting 7 from statID gets the correct flat stat
                        flat_stat_id = str(int(stat_id) - 7)
                    case 35 | 36:  # Ph. Crit Avoid | Sp. Crit Avoid
                        # 39-35 = 4 = 40-36 ==> adding 4 to statID gets the correct flat stat
                        flat_stat_id = str(math_floor(int(stat_id)) + 4)
                    case _:
                        pass

                gs_stats['final'].setdefault(flat_stat_id, 0)  # ensure stat already exists
                gs_stats['final'][str(flat_stat_id)] += (stats['base'].get(stat_id, 0) +
                                                         stats['gear'].get(stat_id, 0) +
                                                         (stats['mods'].get(stat_id, 0) if 'mods' in stats else 0))
        else:  # Ship
            for stat in stats['crew']:
                add_stats(stat)  # add stats from crew to list
                gs_stats['crew'] = stats['crew']  # keep crew stats untouched

            for statID in stat_list:
                gs_stats['final'][statID] = (stats['base'].get(statID, 0) +
                                             stats['crew'].get(statID, 0))
        stats = gs_stats
        logger.debug(f"Stats: {stats}")
    return stats


def _scale_stat_value(stat_id: int or str, value: float) -> float:
    """Convert stat value from displayed value to "unscaled" value used in calculations"""
    logger.debug(f"{_get_function_name()}: *** Scaling statId: {stat_id} value: {value} ***")
    if isinstance(stat_id, str):
        stat_id = int(stat_id)
    if stat_id in [1, 5, 28, 41, 42]:
        logger.debug(f"{_get_function_name()}:    New value: {value * 1e8} (times 1e8)")
        return value * 1e8
    else:
        logger.debug(f"{_get_function_name()}:    New value: {value * 1e6} (times 1e6)")
        return value * 1e6


def _floor(value: float, digits: int = 0) -> float:
    precision = float(("1e" + str(digits)))
    floor_value = math_floor(value / precision) * precision
    logger.debug(f"{_get_function_name()}: {value=}, {floor_value=}")
    return floor_value


def _convert_flat_def_to_percent(
        value: float,
        level: int = 85,
        scale: float = 1.0,
        is_ship: bool = False) -> float:
    logger.debug(f"{_get_function_name()}: *** Converting flat defense value to percent ({value=}, "
                 + f"{level=}, {scale=}, {is_ship=}) *** ")
    val = value / scale
    level_effect = 300 + level * 5 if is_ship else level * 7.5
    percent_value = (val / (level_effect + val)) * scale
    logger.debug(f"{_get_function_name()}: {val=}, {level_effect=}, {percent_value=}")
    return percent_value


def _convert_flat_crit_to_percent(value: float, scale: float = 1.0) -> float:
    logger.debug(f"{_get_function_name()}: *** Converting flat Critical Chance to percent ({value=}, {scale=}) *** ")
    val = value / scale
    percent_val = (val / 2400 + 0.1) * scale
    logger.debug(f"{_get_function_name()}: {val=}, {percent_val=}")
    return percent_val


def _convert_flat_acc_to_percent(value: float, scale: float = 1.0) -> float:
    logger.debug(f"{_get_function_name()}: *** Converting flat Accuracy to percent ({value=}, {scale=}) *** ")
    val = value / scale
    percent_val = (val / 1200) * scale
    logger.debug(f"{_get_function_name()}: {val=}, {percent_val=}")
    return percent_val


def _convert_flat_crit_avoid_to_percent(value: float, scale: float = 1.0) -> float:
    logger.debug(f"{_get_function_name()}: *** Converting flat Critical Avoidance to percent ({value=}, {scale=}) *** ")
    val = value / scale
    percent_val = (val / 2400) * scale
    logger.debug(f"{_get_function_name()}: {val=}, {percent_val=}")
    return percent_val


def _verify_def_id(unit: dict) -> dict:
    logger.debug(f"*** Verifying 'defId' exists ***")
    if 'defId' not in unit:
        if 'definitionId' in unit:
            unit['defId'] = unit.get("definitionId").split(":")[0]
        elif 'baseId' in unit:
            unit['defId'] = unit.get("baseId")
        else:
            logger.warning(f"{_get_function_name()}: Unable to set a 'defId' value for {unit['id']}")
    logger.debug(f"{_get_function_name()}: {unit['defId']=}")
    return unit


class StatCalcException(Exception):
    pass


class StatCalcRuntimeError(RuntimeError):
    pass


@dataclass
class StatCalc:
    """
    Container class to house collection of stat calculation methods. Not intended to be instantiated.
    """

    _INITIALIZED = False

    _DEFAULT_MOD_TIER = os.getenv("DEFAULT_MOD_TIER", 5)
    _DEFAULT_MOD_LEVEL = os.getenv("DEFAULT_MOD_LEVEL", 15)
    _DEFAULT_MOD_PIPS = os.getenv("DEFAULT_MOD_PIPS", 6)

    _GAME_DATA = None
    _UNIT_DATA = {}
    _GEAR_DATA = {}
    _MOD_SET_DATA = {}
    _CR_TABLES = {}
    _GP_TABLES = {}
    _RELIC_DATA = {}

    _UNIT_NAME_MAP = {}
    _STAT_NAME_MAP = {}

    _LANGUAGE = "eng_us"
    _OPTIONS = {}
    _USE_VALUES = None

    _ALLOWED_OPTIONS = [
        "withoutModCalc",
        "percentVals",
        "calcGP",
        "onlyGP",
        "useMax",
        "scaled",
        "unscaled",
        "gameStyle",
        "statIDs",
        "enums",
        "noSpace",
        "language",
    ]

    _MAX_VALUES = {
        "char": {
            "rarity": 7,
            "currentLevel": int(os.getenv("MAX_LEVEL", 85)),
            "currentTier": int(os.getenv("MAX_GEAR_LEVEL", 13)),
            "equipped": "all",
            "relic": 11,
        },
        "ship": {
            "rarity": 7,
            "currentLevel": int(os.getenv("MAX_LEVEL", 85)),
            "skills": "max",
        },
        "crew": {
            "rarity": 7,
            "currentLevel": int(os.getenv("MAX_LEVEL", 85)),
            "currentTier": int(os.getenv("MAX_GEAR_LEVEL", 13)),
            "equipped": "all",
            "skills": "max",
            "modRarity": int(os.getenv("MAX_MOD_PIPS", 6)),
            "modLevel": 15,
            "relic": 11,
        },
    }

    _COMLINK: swgoh_comlink.SwgohComlink = None

    @classmethod
    def is_initialized(cls) -> bool:
        return cls._INITIALIZED

    @classmethod
    def set_attribute(cls, attr_name: str, attr_value: any) -> None:
        """Set class attribute

        Args:
            attr_name (str): Name of attribute to set
            attr_value (any): The value to assign to the attribute

        Returns:
            None
        """
        if not cls.is_initialized:
            raise StatCalcException(
                "StatCalc is not initialized. Please perform the initialization first."
            )
        setattr(cls, attr_name, attr_value)

    @classmethod
    def set_log_level(cls, log_level: str):
        """Set the logging level for message output. Default is 'INFO'

        Args:
            log_level (str): Logging level

        Raises:
            StatCalcException: If the logging level is not valid

        """
        if not cls.is_initialized:
            raise StatCalcException(
                "StatCalc is not initialized. Please perform the initialization first."
            )
        log_levels = logging.getLevelNamesMapping()
        if log_level in log_levels:
            logger.setLevel(log_levels[log_level])
        else:
            raise StatCalcRuntimeError(
                f"Invalid log level {log_level}. Available options are {list(log_levels.keys())}"
            )

    @classmethod
    def reset_options(cls):
        for option in cls._ALLOWED_OPTIONS:
            default_value = False
            if option == 'language':
                default_value = "eng_us"
            cls._OPTIONS.setdefault(option, default_value)

    @classmethod
    def _load_unit_name_map(cls) -> bool:
        """Create unit_name_map dictionary"""
        latest_game_version = cls._COMLINK.get_latest_game_data_version()
        loc_bundle = cls._COMLINK.get_localization_bundle(
            id=latest_game_version["language"]
        )
        loc_bundle_decoded = base64.b64decode(loc_bundle["localizationBundle"])
        logger.info(f"{_get_function_name()}: Decompressing data stream...")
        zip_obj = zipfile.ZipFile(io.BytesIO(loc_bundle_decoded))
        lang_file_name = f"Loc_{cls._LANGUAGE.upper()}.txt"
        with zip_obj.open(lang_file_name) as lang_file:
            contents = lang_file.readlines()
        cls._UNIT_NAME_MAP = create_localized_unit_name_dictionary(contents)
        return True if len(cls._UNIT_NAME_MAP) > 0 else False

    @classmethod
    def _load_stat_name_map(cls) -> bool:
        """Create statId to name dictionary object from localized JSON file"""
        data_path = DataBuilder.get_language_file_path()
        try:
            language_file = os.path.join(data_path, cls._LANGUAGE + ".json")
        except Exception as e_str:
            logger.error(
                f"{_get_function_name()}: An error occurred while attempting to load the stat names map. [{e_str}]"
            )
            return False
        if not validate_file_path(language_file):
            logger.error(
                f"{_get_function_name()}: Error while validating language file data path ({language_file})"
            )
            return False
        try:
            with open(language_file) as fn:
                cls._STAT_NAME_MAP = json.load(fn)
        except OSError as os_error:
            logger.exception(f"{_get_function_name()}: Error while loading {language_file}. [{os_error}]")
            return False
        else:
            return True

    @classmethod
    def _rename_stats(cls, stats: dict, options: dict) -> dict:
        logger.info(f"{_get_function_name()}: Renaming stats ... ")
        if options.get('language'):
            lang = options.get('language', "eng_us").lower()
            # Create a new localized stat name mapping rather than use the global default
            # so that different languages can be supported for each call
            stat_id_name_map = DataBuilder.get_localized_stat_names(language=lang)
            rn_stats = {}
            for stat_type in stats:
                rn_stats[stat_type] = {}
                for stat_id, value in stats[stat_type].items():
                    stat_name = stat_id_name_map.get(stat_id, stat_id)
                    if options.get('no_space'):
                        stat_name = stat_name.replace(' ', '')  # remove spaces
                        stat_name = stat_name[0].lower() + stat_name[1:]  # ensure first letter is lower case
                    logger.debug(f"{_get_function_name()}: Renaming {stat_id} to {stat_name} ... ")
                    rn_stats[stat_type][stat_name] = value
            stats = deepcopy(rn_stats)
        logger.info(f"{_get_function_name()}: Done renaming stats")
        return stats

    @classmethod
    def _calculate_base_stats(cls, stats: dict, level: int, base_id: str) -> dict:
        """Calculate bonus primary stats from growth modifiers"""
        logger.info(f"{_get_function_name()}: Calculating base stats")
        logger.debug(f"{stats=}")
        if 'base' not in stats:
            stats['base'] = {}
        for i in ("2", "3", "4"):
            logger.info(f"{_get_function_name()}: Processing base stats for {i} ...")
            logger.info(f"{_get_function_name()}: {stats['base'][i]=} before")
            logger.info(f"{_get_function_name()}: Adding math_floor({stats['growthModifiers'][i]} * "
                        + f"{level} * 1e8) / 1e8")
            stats["base"][i] += math_floor(stats["growthModifiers"][i] * level * 1e8) / 1e8
            logger.info(f"{_get_function_name()}: {stats['base'][i]=} after")
        if stats["base"].get("61"):
            logger.info(f"{_get_function_name()}: Calculating effect of mastery on secondary stats ...")
            mastery_modifier_key = cls._UNIT_DATA[base_id].get("masteryModifierID")
            try:
                mms = cls._CR_TABLES[mastery_modifier_key]
                for stat_id, modifier in mms.items():
                    stats['base'][stat_id] = stats['base'].get(stat_id, 0) + stats['base']["61"] * modifier
            except KeyError as e_str:
                logger.error(
                    f"{_get_function_name()}: Unable to find mastery modifier key [{mastery_modifier_key}] in crTable."
                )
                logger.error(e_str)
                logger.error(f"crTable keys: {sorted(list(cls._CR_TABLES.keys()))}")

        logger.info(f"{_get_function_name()}: Calculating effect of primary stat on secondary stats ...")
        logger.debug(f"{_get_function_name()}: {stats['base']=}")
        # Calculate effects of primary stats on secondary stats
        stats['base']['1'] = stats['base'].get('1', 0) + stats['base']['2'] * 18  # Health += STR * 18
        stats['base']['6'] = math_floor((stats['base'].get('6', 0) + stats['base'][
            str(cls._UNIT_DATA[base_id]['primaryStat'])] * 1.4) * 1e8) / 1e8  # Ph. Damage += MainStat * 1.4
        stats['base']['7'] = math_floor(
            (stats['base'].get('7', 0) + stats['base']['4'] * 2.4) * 1e8) / 1e8  # Sp. Damage += TAC * 2.4
        stats['base']['8'] = math_floor(
            (stats['base'].get('8', 0) + stats['base']['2'] * 0.14 +
             stats['base']['3'] * 0.07) * 1e8) / 1e8  # Armor += STR*0.14 + AGI*0.07
        stats['base']['9'] = math_floor(
            (stats['base'].get('9', 0) + stats['base']['4'] * 0.1) * 1e8) / 1e8  # Resistance += TAC * 0.1
        stats['base']['14'] = math_floor(
            (stats['base'].get('14', 0) + stats['base']['3'] * 0.4) * 1e8) / 1e8  # Ph. Crit += AGI * 0.4

        logger.info(f"{_get_function_name()}: Ensuring core stats are present and at minimum ...")
        # add hard-coded minimums or potentially missing stats
        stats["base"]["12"] = stats["base"].get("12", 0) + (24 * 1e8)
        stats["base"]["13"] = stats["base"].get("13", 0) + (24 * 1e8)
        stats["base"]["15"] = stats["base"].get("15", 0)
        stats["base"]["16"] = stats["base"].get("16", 0) + (150 * 1e6)
        stats["base"]["18"] = stats["base"].get("18", 0) + (15 * 1e8)
        logger.debug(f"{_get_function_name()}: Base stat calculated: {stats['base']=}")
        return stats

    @classmethod
    def _calculate_mod_stats(cls, base_stats: dict, char: dict = None) -> dict or None:
        logger.info("{_get_function_name()}: Calculating mod stats ... ")
        logger.info(f"{_get_function_name()}: {base_stats=}")
        if not char.get('mods') and not char.get('equippedStatMod'):
            logger.warning(f"{_get_function_name()}: Mod list is missing or empty. Returning.")
            return char

        set_bonuses = {}
        raw_mod_stats = {}

        if char.get('equippedStatMod'):
            for mod in char['equippedStatMod']:
                # The mod['definitionId'] value is a 3 character string. Each character in the string is a numeral
                #   representing mod set type (health, speed, potency, etc.), rarity (pips)  and position (slot)
                #   The first numeric character is the mod set ID
                #   The second numeric character is the mod rarity (number of pips/dots [1-6])
                #   The third numeric character is the mod position/slot [1-6]
                mod_set_id = int(mod['definitionId'][0])
                mod_set_name = Constants.MOD_SET_IDS[str(mod_set_id)]
                set_bonus = set_bonuses.get(mod_set_id)
                logger.debug(f"{_get_function_name()}: Mod set id: {mod_set_id} ({mod_set_name}), {set_bonus=}")
                if set_bonus:
                    # set bonus already found, increment
                    logger.debug(f"{_get_function_name()}: {mod_set_id} ({mod_set_name}) "
                                 + f"already present in set_bonuses list. Incrementing counter.")
                    set_bonus['count'] += 1
                    if mod['level'] == 15:
                        set_bonus['maxLevel'] += 1
                    logger.debug(f"{_get_function_name()}: {set_bonus['count']=}, "
                                 + f"{set_bonus['maxLevel']=}, {mod['level']=}")
                else:
                    # new set bonus, create object
                    logger.debug(f"{_get_function_name()}: Creating new entry for {mod_set_id} "
                                 + f"({mod_set_name}) in set_bonuses list.")
                    set_bonuses[mod_set_id] = {'count': 1, 'maxLevel': 1 if mod['level'] == 15 else 0}

                # add Primary/Secondary stats to data
                stat = mod['primaryStat']['stat']
                i = 0
                logger.debug(f"{_get_function_name()}: counter = {i}, {stat=}")
                while True:
                    unscaled_stat = float(stat['unscaledDecimalValue']) + raw_mod_stats.get(stat['unitStatId'], 0)
                    raw_mod_stats[stat['unitStatId']] = unscaled_stat
                    logger.debug(f"{_get_function_name()}: raw_mod_stats[{stat['unitStatId']}] = {unscaled_stat}")
                    if i >= len(mod['secondaryStat']):
                        break
                    stat = mod['secondaryStat'][i]['stat']
                    i += 1
                    logger.debug(f"{_get_function_name()}: counter = {i}, {stat=}")
        else:
            # return empty dictionary if no mods
            logger.debug(f"{_get_function_name()}: Failed to find 'definitionId' in {char['defId']}. "
                         + f"Returning empty dictionary.")
            return {}

        # add stats given by set bonuses
        logger.debug(f"{_get_function_name()}: Adding mod set bonuses ...")
        for set_id, set_bonus in set_bonuses.items():
            set_def = cls._MOD_SET_DATA[str(set_id)]
            count = set_bonus['count']
            max_count = set_bonus['maxLevel']
            multiplier = math_floor(count / set_def['count']) + math_floor(max_count / set_def['count'])

            logger.debug(f"{_get_function_name()}: {count=}, {max_count=}, {multiplier=}")
            raw_mod_stat = raw_mod_stats.get(set_def['id'], 0) + (set_def['value'] * multiplier)

            logger.debug(f"{_get_function_name()}: raw_mod_stats[{set_def['id']}] = {raw_mod_stat}")
            raw_mod_stats[set_def['id']] = raw_mod_stat

        # calculate actual stat bonuses from mods
        logger.debug(f"{_get_function_name()}: Calculating stat bonuses from mods ...")
        mod_stats = {}
        for stat_id, value in raw_mod_stats.items():
            stat_id = int(stat_id)
            if stat_id == 41:  # Offense
                mod_stats['6'] = mod_stats.get('6', 0) + value  # Ph. Damage
                mod_stats['7'] = mod_stats.get('7', 0) + value  # Sp. Damage
                logger.debug(f"{_get_function_name()}: {stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), "
                             + f"{mod_stats['6']=}, {mod_stats['7']=}")
            elif stat_id == 42:  # Defense
                mod_stats['8'] = mod_stats.get('8', 0) + value  # Armor
                mod_stats['9'] = mod_stats.get('9', 0) + value  # Resistance
                logger.debug(f"{_get_function_name()}: {stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), "
                             + f"{mod_stats['8']=}, {mod_stats['9']=}")
            elif stat_id == 48:  # Offense %
                mod_stats['6'] = math_floor(
                    (mod_stats.get('6', 0) + (base_stats['6'] * 1e-8 * value)) * 1e8) / 1e8  # Ph. Damage
                mod_stats['7'] = math_floor(
                    (mod_stats.get('7', 0) + (base_stats['7'] * 1e-8 * value)) * 1e8) / 1e8  # Sp. Damage
                logger.debug(f"{_get_function_name()}: {stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), "
                             + f"{mod_stats['6']=}, {mod_stats['7']=}")
            elif stat_id == 49:  # Defense %
                mod_stats['8'] = math_floor(
                    (mod_stats.get('8', 0) + (base_stats['8'] * 1e-8 * value)) * 1e8) / 1e8  # Armor
                mod_stats['9'] = math_floor(
                    (mod_stats.get('9', 0) + (base_stats['9'] * 1e-8 * value)) * 1e8) / 1e8  # Resistance
                logger.debug(f"{_get_function_name()}: {stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), "
                             + f"{mod_stats['8']=}, {mod_stats['9']=}")
            elif stat_id == 53:  # Crit Chance
                mod_stats['21'] = mod_stats.get('21', 0) + value  # Ph. Crit Chance
                mod_stats['22'] = mod_stats.get('22', 0) + value  # Sp. Crit Chance
                logger.debug(f"{_get_function_name()}: {stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), "
                             + f"{mod_stats['21']=}, {mod_stats['22']=}")
            elif stat_id == 54:  # Crit Avoid
                mod_stats['35'] = mod_stats.get('35', 0) + value  # Ph. Crit Avoid
                mod_stats['36'] = mod_stats.get('36', 0) + value  # Ph. Crit Avoid
                logger.debug(f"{_get_function_name()}: {stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), "
                             + f"{mod_stats['35']=}, {mod_stats['36']=}")
            elif stat_id == 55:  # Health %
                mod_stats['1'] = math_floor(
                    (mod_stats.get('1', 0) + (base_stats['1'] * 1e-8 * value)) * 1e8) / 1e8  # Health
                logger.debug(f"{_get_function_name()}: {stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), "
                             + f"{mod_stats['1']=}")
            elif stat_id == 56:  # Protection %
                mod_stats['28'] = math_floor((mod_stats.get('28', 0) + (
                        base_stats.get('28', 0) * 1e-8 * value)) * 1e8) / 1e8  # Protection may not exist in base
                logger.debug(f"{_get_function_name()}: {stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), "
                             + f"{mod_stats['28']=}")
            elif stat_id == 57:  # Speed %
                mod_stats['5'] = math_floor(
                    (mod_stats.get('5', 0) + (base_stats['5'] * 1e-8 * value)) * 1e8) / 1e8  # Speed
                logger.debug(f"{_get_function_name()}: {stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), "
                             + f"{mod_stats['5']=}")
            else:
                # other stats add like flat values
                mod_stats[str(stat_id)] = mod_stats.get(str(stat_id), 0) + value
                logger.debug(f"{_get_function_name()}: {stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), "
                             + f"{mod_stats[str(stat_id)]=}")

        return mod_stats

    @classmethod
    def _get_crew_rating(cls, crew):
        def calculate_character_cr(crew_rating, char):
            crew_rating += cls._CR_TABLES['unitLevelCR'][char['level']] + cls._CR_TABLES['crewRarityCR'][char['rarity']]
            crew_rating += cls._CR_TABLES['gearLevelCR'][char['gear']]
            crew_rating += cls._CR_TABLES['gearPieceCR'][char['gear']] * len(char.get('equipped', []))

            crew_rating = functools.reduce(lambda cr, skill: cr + cls._get_skill_crew_rating(skill), char['skills'],
                                           crew_rating)

            if 'mods' in char:
                crew_rating = functools.reduce(
                    lambda cr, mod: cr + cls._CR_TABLES['modRarityLevelCR'][mod['pips']][mod['level']], char['mods'],
                    crew_rating)
            elif 'equippedStatMod' in char:
                crew_rating = functools.reduce(
                    lambda cr, mod: cr + cls._CR_TABLES['modRarityLevelCR'][int(mod['definitionId'][1])][mod['level']],
                    char['equippedStatMod'], crew_rating)

            if 'relic' in char and char['relic']['currentTier'] > 2:
                crew_rating += cls._CR_TABLES['relicTierCR'][char['relic']['currentTier']]
                crew_rating += char['level'] * cls._CR_TABLES['relicTierLevelFactor'][char['relic']['currentTier']]

            return crew_rating

        total_cr = functools.reduce(calculate_character_cr, crew, 0)
        return total_cr

    @classmethod
    def _get_skill_crew_rating(cls, skill):
        return cls._CR_TABLES['abilityLevelCR'][skill['tier']]

    @classmethod
    def _get_crewless_crew_rating(cls, ship):
        # temporarily uses hard-coded multipliers, as the true in-game formula remains a mystery.
        # but these values have experimentally been found accurate for the first 3 crewless ships:
        #     (Vulture Droid, Hyena Bomber, and BTL-B Y-wing)
        crew_rating = math_floor(
            cls._CR_TABLES['crewRarityCr'][ship['currentRarity']] +
            3.5 * cls._CR_TABLES['unitLevelCr'][ship['currentLevel']] +
            cls._get_crewless_skills_crew_rating(ship['skills'])
        )
        return crew_rating

    @classmethod
    def _get_crewless_skills_crew_rating(cls, skills):
        crew_rating = 0
        for skill in skills:
            const = 0.696 if skill['id'].startswith('hardware') else 2.46
            crew_rating += const * cls._CR_TABLES['abilityLevelCR'][str(skill['currentTier'])]
        return crew_rating

    @classmethod
    def _get_char_raw_stats(cls, char: dict) -> dict:
        """Generate raw stats for character"""
        # Construction stats dictionary using game data for character based on specifics of character data provided
        stats: dict = {
            "base": copy(cls._UNIT_DATA[char["defId"]]["gearLvl"][str(char["currentTier"])]["stats"]),
            "growthModifiers": deepcopy(
                cls._UNIT_DATA[char["defId"]]["growthModifiers"][str(char["currentRarity"])]
            ),
            "gear": {},
        }
        logger.info(f"{_get_function_name()}: raw stats: {stats=}")
        # Calculate stats from current gear
        if len(char["equipment"]) != 0:
            logger.info(f"{_get_function_name()}: Calculating stats for {char['defId']} equipment ")
            for equipment_piece in char["equipment"]:
                equipmentId = equipment_piece["equipmentId"]
                logger.info(f"{_get_function_name()}: Searching for {equipmentId} in game gearData ...")
                if equipmentId not in cls._GEAR_DATA:
                    logger.info(f"{_get_function_name()}: {equipmentId=} not found in game gearData ...")
                    continue
                equipment_stats = copy(cls._GEAR_DATA[equipmentId]["stats"])
                for equipment_stat_id in equipment_stats.keys():
                    if equipment_stat_id in ["2", "3", "4"]:
                        # Primary stat applies before mods
                        stats["base"][equipment_stat_id] += stats["base"][equipment_stat_id]
                    else:
                        # Secondary stat applies after mods
                        stats["gear"][equipment_stat_id] = (equipment_stats[equipment_stat_id] +
                                                            stats["gear"].get(equipment_stat_id, 0))
        else:
            logger.info(f"{_get_function_name()}: No equipment for {char['defId']}")

        if char.get("relic") and char["relic"]["currentTier"] > 2:
            current_relic_tier: int = char["relic"].get("currentTier")
            logger.info(f"{_get_function_name()}: Calculating stats for {char['defId']} relic level: "
                        + f"{current_relic_tier - 2}")
            # Calculate stats from relics
            relic_tier_data = cls._RELIC_DATA[
                cls._UNIT_DATA[char["defId"]]["relic"][str(current_relic_tier)]
            ]
            for r_id in list(relic_tier_data["stats"].keys()):
                stats["base"][r_id] = relic_tier_data["stats"][r_id] + stats["base"].get(r_id, 0)
                logger.info(f"{stats['base'][r_id]=}")
            for g_id in list(relic_tier_data["gms"].keys()):
                stats["growthModifiers"][g_id] += relic_tier_data["gms"][g_id]
                logger.info(f"{_get_function_name()}: {stats['growthModifiers'][g_id]=}")
        else:
            logger.info(f"{_get_function_name()}: No relic information for {char['defId']}")
        logger.info(f"{_get_function_name()}: Stat results for {char['defId']}: {stats}")
        return stats

    @classmethod
    def _get_ship_raw_stats(cls, ship, crew):
        # ensure crew is the correct crew
        if len(crew) != len(cls._UNIT_DATA[ship['defId']]['crew']):
            # TODO: log error
            raise ValueError(f"Incorrect number of crew members for ship {ship['defId']}.")

        for char in crew:
            if char['defId'] not in cls._UNIT_DATA[ship['defId']]['crew']:
                # TODO: log error
                raise ValueError(f"Unit {char['defId']} is not in {ship['defId']}'s crew.")

        # if still here, crew is good -- go ahead and determine stats
        crew_rating = cls._get_crewless_crew_rating(ship) if len(crew) == 0 else cls._get_crew_rating(crew)

        stats = {
            'base': deepcopy(cls._UNIT_DATA[ship['defId']]['stats']),
            'crew': {},
            'growth_modifiers': deepcopy(cls._UNIT_DATA[ship['defId']]['growthModifiers'][ship['rarity']])
        }

        stat_multiplier = cls._CR_TABLES['shipRarityFactor'][ship['rarity']] * crew_rating

        for stat_id, stat_value in cls._UNIT_DATA[ship['defId']]['crewStats'].items():
            # stats 1-15 and 28 all have final integer values
            # other stats require decimals -- shrink to 8 digits of precision through 'unscaled'
            # values this calculator uses
            precision = 8 if int(stat_id) < 16 or int(stat_id) == 28 else 0
            stats['crew'][stat_id] = math_floor(stat_value * stat_multiplier * (10 ** precision)) / (10 ** precision)
        return stats

    @classmethod
    def calc_char_stats(
            cls,
            char: dict,
            options: list or dict = None,
            use_values: dict = None,
            set_global_options: bool = False,
    ) -> dict:
        """Calculate stats for a single character based upon arguments provided.

        Args:
            char (dict): Character object from player roster or game_data['unit']
            options (dict|list): Dictionary or list of options to enable
            use_values (dict): See example below
            set_global_options (bool): Flag indicating if the global attributes should be set
                                        using the 'options' attribute

        Returns:
            dict: character object dictionary with stats calculated

        Examples:
            use_values dictionary template:

            {
              "char": {                           # used when calculating character stats
                "rarity": int,                    # 1-7 (default 7)
                "currentLevel": int,              # 1-90 (default 85)
                "currentTier": int,               # 1-13 (default 13)
                "equipped": list or str,          # See Below
                "relic": int,                     # 1-9 (See Below)
                "skills":list,                    # 1-7 (default 6)
                "mods": [ { "level": <integer>,   # 1-5 (default 5)
                            "rarity": <integer>,  # 1-15 (default 15)
                            "tier": <integer>
                           }, ...
                        ]
              },
              "ship": {                              # used when calculating ship stats
                "rarity": int,                       # 1-7 (default 7)
                "currentLevel": int                  # 1-90 (default 85)
              },
              "crew": {                              # used for characters when calculating ship stats
                "rarity": int,                       # 1-7 (default 7)
                "currentLevel": int,                 # 1-90 (default 85)
                "currentTier": int,                  # 1-12 (default 12)
                "equipped": str or int or list,      # See Below
                "skills": str or int,                # See Below
                "modRarity": int,                    # 1-7 (default 6)
                "modLevel": int,                     # 1-15 (default 15)
                "modTier": int,                      # 1-5 (default 5)
                "relic": int                         # 1-9 (See Below)
              }
            }

            equipped: (defaults to "all")
                "all" defines all possible gear pieces are equipped.
                "none" defines no gear pieces are equipped.
                An Array can define which gear slots have gear equipped, i.e. [1,2,6] says the top two and the bottom
                right slots are filled.
                An integer 1-6 can define how many pieces are equipped, without specific slots (crew definition only).
            skills: (defaults to "max")
                "max" defines all skills are maxed.
                "maxNoZeta" defines all non-zeta skills are maxed, while Zeta abilities are still rank 7.
                An integer 1-8 defines all skills to be at that rank if possible, or as close to it if they max at a
                lower rank (such as contracts).
            relic: (defaults to 9)
                1 - Relic Locked (gear <13).
                2 - Relic Unlocked (but still level 0).
                3-9 - Relic Levels 1-7, respectively. 'Tier' value here is Relic Level + 2, as defined in game data.

        """

        if not cls.is_initialized:
            raise StatCalcException("StatCalc is not initialized. Please perform the initialization first.")

        char = _verify_def_id(char)

        logger.info(f"{_get_function_name()}: Calculating stats for {char['defId']}")

        if options is None:
            logger.debug(f"{_get_function_name()}: No options provided. Copying defaults ...")
            options = deepcopy(cls._OPTIONS)
        else:
            options = cls._process_options(options, set_global=set_global_options)

        cls._process_language(options.get('language', "eng_us"))
        char = cls._use_values_char(char, use_values)

        stats = {}
        if not options.get('onlyGP'):
            stats = cls._get_char_raw_stats(char)
            stats = cls._calculate_base_stats(stats, char["currentLevel"], char["defId"])
            if len(char["equippedStatMod"]) > 0 and not options["withoutModCalc"]:
                stats['mods'] = cls._calculate_mod_stats(stats.get("base"), char)
            stats = _format_stats(stats, int(char["currentLevel"]), options)
            char['stats'] = cls._rename_stats(stats, options)

        if options.get('calcGP') or options.get('onlyGP'):
            char['gp'] = cls._calc_char_gp(char)
            stats['gp'] = char['gp']

        return char

    @classmethod
    def calc_ship_stats(
            cls,
            ship: dict,
            crew: list,
            options: list or dict = None,
            use_values: dict = None,
            set_global_options: bool = False,
    ) -> dict:
        """

        Args:
            ship (dict): Ship object from player roster
            crew (list): List of ship crew members
            options (dict|list): Dictionary or list of options to enable
            use_values (dict): See example from calc_char_stats
            set_global_options (bool): Flag indicating if the global attributes should be set
                                        using the 'options' attribute

        Returns:
            dict: Ship object with stats calculated

        """

        if not cls.is_initialized:
            raise StatCalcException(
                "StatCalc is not initialized. Please perform the initialization first."
            )

        ship = _verify_def_id(ship)

        logger.info(f"{_get_function_name()}: Calculating stats for {ship['defId']}")

        cls._process_language(options.get('language', "eng_us"))

        if options is None:
            logger.debug(f"{_get_function_name()}: No options provided. Copying defaults ...")
            options = deepcopy(cls._OPTIONS)
        else:
            options = cls._process_options(options, set_global=set_global_options)

        try:
            ship, crew = cls._use_values_ships(ship, crew, use_values)

            stats = {}
            if not options.get('onlyGP'):
                stats = cls._get_ship_raw_stats(ship, crew)
                stats = cls._calculate_base_stats(stats, ship['currentLevel'], ship['defId'])
                stats = _format_stats(stats, ship['currentLevel'], options)
                ship['stats'] = cls._rename_stats(stats, options)

            if options.get('calcGP') or options.get('onlyGP'):
                ship['gp'] = cls._calc_ship_gp(ship, crew)
                stats['gp'] = ship['gp']

            return ship
        except Exception as e:
            # TODO: log error
            print(f"Error on ship '{ship['defId']}':\n{json.dumps(ship)}")
            print(str(e))
            raise

    @classmethod
    def _set_skills(cls, unit_id: str, val: str) -> list:
        logger.info(f"{_get_function_name()}: Setting skills for {unit_id}")
        logger.debug(f"{_get_function_name()}: {val=}")
        if val == "max":
            logger.debug(f"{_get_function_name()}: Setting skills for {unit_id} (max)")
            return [
                {"id": d["id"], "tier": d["maxTier"]}
                for d in cls._UNIT_DATA[unit_id]["skills"]
            ]
        elif val == "maxNoZeta":
            logger.debug(f"{_get_function_name()}: Setting skills for {unit_id} (maxNoZeta)")
            return [
                {"id": d["id"], "tier": d["maxTier"] - (1 if d["isZeta"] else 0)}
                for d in cls._UNIT_DATA[unit_id]["skills"]
            ]
        elif isinstance(val, int):
            _skills = [
                {"id": d["id"], "tier": min(val, d["maxTier"])}
                for d in cls._UNIT_DATA[unit_id]["skills"]
            ]
            logger.debug(f"{_get_function_name()}: Setting {len(_skills)} skills for {unit_id} ")
            return _skills
        else:
            return []

    @classmethod
    def _use_values_ships(cls, ship: dict, crew: list, use_values: dict = None) -> dict:
        if 'defId' not in ship:
            temp_ship = {
                'defId': ship['definitionId'].split(":")[0],
                'rarity': ship['currentRarity'],
                'level': ship['currentLevel'],
                'skills': [{'id': skill['id'], 'tier': skill.get('tier') + 2} for skill in ship['skill']]
            }
            ship.update(temp_ship)
            crew = [{
                'defId': c['definitionId'].split(":")[0],
                'rarity': c.get('currentRarity'),
                'level': c.get('currentLevel'),
                'gear': c.get('currentTier'),
                'equipped': c.get('equipment'),
                'equipped_stat_mod': c.get('equippedStatMod'),
                'relic': c['relic'].get('currentTier'),
                'skills': [{'id': skill.get('id'), 'tier': skill.get('tier') + 2} for skill in c['skill']],
                'gp': c.get('gp')
            } for c in crew]

        if not use_values:
            return {'ship': ship, 'crew': crew}

        ship = {
            'defId': ship['defId'],
            'rarity': use_values['ship'].get('rarity', ship['rarity']),
            'level': use_values['ship'].get('level', ship['level']),
            'skills': cls._set_skills(ship['defId'], use_values['ship'].get('skills', ship['skills']))
        }

        chars = []
        for char_id in cls._UNIT_DATA[ship['defId']]['crew']:
            char = next((cmem for cmem in crew if cmem['defId'] == char_id), None)
            char = {
                'defId': char_id,
                'rarity': use_values['crew'].get('rarity', char['rarity']),
                'level': use_values['crew'].get('level', char['level']),
                'gear': use_values['crew'].get('gear', char['gear']),
                'equipped': char['gear'],
                'skills': cls._set_skills(char_id, use_values['crew'].get('skills', char['skills'])),
                'mods': char.get('mods'),
                'relic': {'current_tier': use_values['crew']['relic']} if use_values['crew'].get('relic')
                else char.get('relic')
            }

            if use_values['crew'].get('equipped') == "all":
                char['equipped'] = [
                    {'equipmentId': gear_id} for gear_id in cls._UNIT_DATA[char_id]['gear_lvl'][char['gear']]['gear']
                    if int(gear_id) < 9990
                ]
            elif use_values['crew'].get('equipped') == "none":
                char['equipped'] = []
            elif isinstance(use_values['crew'].get('equipped'), list):
                char['equipped'] = [
                    cls._UNIT_DATA[char_id]['gear_lvl'][char['gear']]['gear'][int(slot) - 1]
                    for slot in use_values['crew']['equipped']
                ]
            elif use_values['crew'].get('equipped'):
                char['equipped'] = [{} for _ in range(use_values['crew']['equipped'])]

            if use_values['crew'].get('mod_rarity') or use_values['crew'].get('mod_level'):
                char['mods'] = [
                    {
                        'pips': use_values['crew'].get('mod_rarity', cls._DEFAULT_MOD_PIPS),
                        'level': use_values['crew'].get('mod_level', cls._DEFAULT_MOD_LEVEL),
                        'tier': use_values['crew'].get('mod_tier', cls._DEFAULT_MOD_TIER)
                    }
                    for _ in range(6)
                ]

            chars.append(char)

        return {'ship': ship, 'crew': chars}

    @classmethod
    def _use_values_char(cls, char: dict, use_values: dict = None) -> dict:
        """
        Method to parse character attribute values from the 'use_values' dictionary for purposes of
        generating character stats

        Args:
            char (dict): character attribute values in the format from the game data['unit'] collection
            use_values (dict): dictionary in the format of:
                ```python
                {
                  char: {
                    rarity: <int>,                        # 1-7 (default 7)
                    level: <int>,                         # 1-90 (default 85)
                    gear: <int>,                          # 1-12 (default 12)
                    equipment: <str|list|None>,           # [see below]
                    relic: <str|int>,                     # [see below]
                    skills: <str|list>,                   # [see below]
                    mod_rarity: <int>,                    # 1-7 [pips/dots] (default 6)
                    mod_level: <int>,                     # 1-15 (default 15)
                    mod_tier: <int>                       # 1-6 (default 6)
                  },
                  ship: {
                    rarity: <int>,                        # 1-7 (default 7)
                    level: <int>                          # 1-90 (default 85)
                  },
                  crew: {
                    rarity: <int>,                        # 1-7 (default 7)
                    level: <int>,                         # 1-90 (default 85)
                    gear: <int>,                          # 1-12 (default 12)
                    equipment: <str|int|list|None>,       # [see below]
                    skills: <str|int>,                    # [see below]
                    mod_rarity: <int>,                    # 1-7 [pips/dots] (default 6)
                    mod_level: <int>,                     # 1-15 (default 15)
                    mod_tier: <int>,                      # 1-5 (default 5)
                    relic: <str|int>                      # [see below]
                  }
                }
                ```

                **equipment** (default: "all"):
                    Possible values are:
                        "all": Include all possible gear pieces
                        None: Do not include any gear pieces. The dictionary key must exist with a None value assigned.
                        (list): List of integers indicating which gear slots to include, for example: [1,2,6]
                                For the "crew" element, a single integer can be used to indicate how many
                                gear pieces to include without specifying the slot assignment.

                **skills** (default: "max"):
                    Possible values are:
                        "max": Include all possible skills
                        "max_no_zeta": Include all skills at the highest possible level below the zeta threshold
                        "max_no_omicron": Include all skills at the highest possible level below the omicron threshold
                        (int): Include all skills at the level indicated by the integer provided

                **relic** (default: 9):
                    Possible values are:
                        "locked": Relic level has not been unlocked (gear level < 13)
                        "unlocked": Relic level unlocked but still level 0
                        (int): The actual relic level [1-9]

        Returns:
            dictionary of character attribute values

        """
        logger.info(f"{_get_function_name()}: Executing _use_values_char() ...")

        if not char.get('defId'):
            char = {
                'defId': char['definitionId'].split(":")[0],
                'rarity': char['currentRarity'],
                'level': char['currentLevel'],
                'gear': char['currentTier'],
                'equipped': char['equipment'],
                'equippedStatMod': char['equippedStatMod'],
                'relic': char['relic'],
                'skills': [{'id': skill['id'], 'tier': skill['tier'] + 2} for skill in char['skill']],
                'purchasedAbilityId': char['purchasedAbilityId']
            }

        # The use_values option has not been set so the char object does not need to be modified
        if not use_values:
            logger.info(f"{_get_function_name()}: No 'use_values' argument provided. Returning.")
            return char

        unit = {
            "defId": char["defId"],
            "rarity": use_values["char"].get("rarity", char["rarity"]),
            "level": use_values["char"].get("level", char["level"]),
            "gear": use_values["char"].get("gear", char["gear"]),
            "equipped": char["gear"],
            "mods": char["mods"],
            "equippedStatMod": char["equippedStatMod"],
            "relic": {"currentTier": use_values["char"]["relic"]} if use_values["char"].get("relic") else char["relic"],
            "skills": cls._set_skills(char["defId"], use_values["char"].get("skills", char.get("skills", []))),
            'purchasedAbilityId': use_values["char"].get('purchaseAbilityId', char['purchasedAbilityId'])
        }

        if use_values['char']['modRarity'] or use_values['char']['modLevel'] or use_values['char']['modTier']:
            unit['mods'] = []
            for _ in range(6):
                unit['mods'].append({
                    'pips': use_values['char']['modRarity'] or cls._DEFAULT_MOD_PIPS,
                    'level': use_values['char']['modLevel'] or cls._DEFAULT_MOD_LEVEL,
                    'tier': use_values['char']['modTier'] or cls._DEFAULT_MOD_TIER
                })

        if use_values['char']['equipment'] == "all":
            unit['equipment'] = []
            for gear_id in cls._UNIT_DATA[unit['defId']]['gearLvl'][unit['gear']]['gear']:
                if int(gear_id) < 9990:
                    unit['equipment'].append({'equipmentId': gear_id})
        elif use_values['char']['equipment'] == "none":
            unit['equipment'] = []
        elif isinstance(use_values['char']['equipped'], list):  # expecting array of gear slots
            # TODO: verify the below is correct
            unit['equipment'] = [cls._UNIT_DATA[unit['defId']]['gearLvl'][unit['gear']]['gear'][int(slot) - 1] for slot
                                 in use_values['char']['equipment']]

        return unit

    @classmethod
    def _calc_char_gp(cls, char: dict):
        logger.debug(f"{_get_function_name()}: *** Calculating character GP for {char['defId']} ***")

        gp = cls._GP_TABLES['unitLevelGP'][str(char['currentLevel'])]
        logger.debug(f"{_get_function_name()}: Char level: {str(char['currentLevel'])}, "
                     + f"GP added: {cls._GP_TABLES['unitLevelGP'][str(char['currentLevel'])]}")
        logger.debug(f"{_get_function_name()}: {gp=} after level adjustment "
                     + f"({cls._GP_TABLES['unitLevelGP'][str(char['currentLevel'])]})")

        gp += cls._GP_TABLES['unitRarityGP'][Constants.UNIT_RARITY[char['currentRarity']]]
        logger.debug(f"{_get_function_name()}: {gp=} after rarity adjustment")

        gp += cls._GP_TABLES['gearLevelGP'][str(char['currentTier'])]
        logger.debug(f"{_get_function_name()}: {gp=} after equipment level adjustment")

        # Game tables for current gear include the possibility of different GP per slot.
        # Currently, all values are identical across each gear level, so a simpler method is possible.
        # But that could change at any time.

        if len(char['equipment']) > 0:
            logger.debug(f"{_get_function_name()}: *** Equipment found (processing) ***")
            for piece in char['equipment']:
                gp += cls._GP_TABLES['gearPieceGP'][str(char['currentTier'])][str(piece['slot'])]
        else:
            logger.debug(f"{_get_function_name()}: *** No equipment found (skipping) ***")

        """
        gp += sum(cls._GP_TABLES['gearPieceGP'][str(char['currentTier'])][str(piece['slot'])]
                  for piece in char['equipment'])
        """

        logger.debug(f"{_get_function_name()}: {gp=} after equipment piece adjustment")

        gp += sum(cls._get_skill_gp(char['defId'], skill) for skill in char['skill'])
        logger.debug(f"{gp=} after skill adjustment")

        logger.debug(f"{_get_function_name()}: {gp=} after character skills adjustment")

        if char.get('purchasedAbilityId'):
            gp += len(char['purchasedAbilityId']) * cls._GP_TABLES['abilitySpecialGP']['ultimate']

        logger.debug(f"{_get_function_name()}: {gp=} after purchaseAbility adjustment")

        gp += sum(cls._GP_TABLES['modRarityLevelTierGP'][mod['definitionId'][1]][str(mod['level'])][str(mod['tier'])]
                  for mod in char['equippedStatMod'])

        logger.debug(f"{_get_function_name()}: {gp=} after mods adjustment")

        if char.get('relic') and char['relic']['currentTier'] > 2:
            relic_tier = str(char['relic']['currentTier'])
            gp += cls._GP_TABLES['relicTierGP'][relic_tier]
            gp += char['currentLevel'] * cls._GP_TABLES['relicTierLevelFactor'][relic_tier]
            logger.debug(f"{_get_function_name()}: {gp=} after relic adjustment")
        logger.debug(f"{_get_function_name()}: Final GP: {math_floor(gp * 1.5)}")

        return math_floor(gp * 1.5)

    @classmethod
    def _calc_ship_gp(cls, ship, crew=None):
        if crew is None:
            crew = []

        # ensure crew is the correct crew
        if len(crew) != len(cls._UNIT_DATA[ship['defId']]['crew']):
            # TODO: log error
            raise ValueError(f"Incorrect number of crew members for ship {ship['defId']}.")

        for char in crew:
            if char['defId'] not in cls._UNIT_DATA[ship['defId']]['crew']:
                # TODO: log error
                raise ValueError(f"Unit {char['defId']} is not in {ship['defId']}'s crew.")

        if len(crew) == 0:  # crewless calculations
            gps = cls._get_crewless_skills_gp(ship['defId'], ship['skills'])
            gps['level'] = cls._GP_TABLES['unit_level_gp'][ship['level']]
            gp = ((gps['level'] * 3.5 + gps['ability'] * 5.74 + gps['reinforcement'] * 1.61) *
                  cls._GP_TABLES['ship_rarity_factor'][ship['rarity']])
            gp += gps['level'] + gps['ability'] + gps['reinforcement']
        else:  # normal ship calculations
            gp = sum(c['gp'] for c in crew)
            gp *= cls._GP_TABLES['ship_rarity_factor'][ship['rarity']] * cls._GP_TABLES['crew_size_factor'][
                len(crew)]  # multiply crewPower factors before adding other GP sources
            gp += cls._GP_TABLES['unit_level_gp'][ship['level']]
            gp += sum(cls._get_skill_gp(ship['defId'], skill) for skill in ship['skills'])

        return math_floor(gp * 1.5)

    @classmethod
    def _get_crewless_skills_gp(cls, id, skills):
        a = 0
        r = 0
        for skill in skills:
            o_tag = next(
                (s['powerOverrideTags'][skill['tier']] for s in cls._UNIT_DATA[id]['skills'] if s['id'] == skill['id']),
                None)
            if o_tag and o_tag.startswith('reinforcement'):
                r += cls._GP_TABLES['abilitySpecialGP'][o_tag]
            else:
                a += cls._GP_TABLES['abilitySpecialGP'][o_tag] if o_tag else (
                    cls._GP_TABLES)['abilityLevelGP'][skill['tier']]

        return {'ability': a, 'reinforcement': r}

    @classmethod
    def _get_skill_gp(cls, def_id: str, skill: dict) -> float:
        logger.debug(f"{_get_function_name()}: *** Getting skill GP *** {def_id=}, {skill=}")
        for s in cls._UNIT_DATA[def_id]['skills']:
            if s['id'] == skill['id']:
                # Convert player unit skill tier to same index scale as base game data unit scale
                player_unit_skill_tier = str(int(skill['tier']) + 2)
                logger.debug(f"{_get_function_name()}: Original skill tier: {skill['tier']}, "
                             + f"Adjusted skill tier: {player_unit_skill_tier}")
                logger.debug(f"{_get_function_name()}: Found skill {skill['id']} "
                             + f"tier {player_unit_skill_tier} ... ")
                logger.debug(f"{_get_function_name()}: _GP_TABLES skill {s} ")
                if int(player_unit_skill_tier) > s['maxTier']:
                    temp_skill_tier = player_unit_skill_tier
                    player_unit_skill_tier = str(s['maxTier'])
                    logger.debug(f"{_get_function_name()}: Adjusting skill tier down to maximum.  "
                                 + f"Original: {temp_skill_tier}, new: {player_unit_skill_tier}.")
                power_override_tag = s['powerOverrideTags'].get(player_unit_skill_tier, None)
                # if 'powerOverrideTags' exists for the player unit skill, use that GP value
                if power_override_tag:  # 'zeta' or 'omicron' or 'upgrade'
                    logger.debug(f"{_get_function_name()}: {power_override_tag=}, returning "
                                 + f"{cls._GP_TABLES['abilitySpecialGP'][power_override_tag]}")
                    return cls._GP_TABLES['abilitySpecialGP'][power_override_tag]
                # if no 'powerOverrideTags' exists for the player unit skill, use the GP for skill tier
                else:
                    logger.debug(f"{_get_function_name()}: No 'powerOverrideTags' found. Using "
                                 + f"{cls._GP_TABLES['abilityLevelGP'].get(player_unit_skill_tier, '0.0')}")
                    return cls._GP_TABLES['abilityLevelGP'].get(player_unit_skill_tier, "0")

    @classmethod
    def _process_language(cls, language: str = None) -> None:
        """Update localized language selection for statIds"""
        logger.info(f"{_get_function_name()}: Processing language: {language}")
        languages: list = DataBuilder.get_languages()
        if language is not None and language in languages:
            cls._LANGUAGE = language
        else:
            logger.warning(f"{_get_function_name()}: Unknown language: {language}, "
                           + f"setting default language to {cls._LANGUAGE}")

    @classmethod
    def _process_options(cls, options: list or dict, set_global: bool = False) -> dict:
        """Update class instance properties based on flags provided"""
        logger.info(f"{_get_function_name()}: Processing options: type({type(options)})")
        new_options = cls._OPTIONS.copy()
        if isinstance(options, list):
            for option in options:
                if option in cls._ALLOWED_OPTIONS:
                    logger.info(f"{_get_function_name()}: Setting cls._OPTIONS['{option}'] to True.")
                    new_options[option] = True
                    if set_global:
                        cls._OPTIONS[option] = True
                else:
                    logger.warning(f"{_get_function_name()}: Unknown option: {option}")
        elif isinstance(options, dict):
            for option in list(options.keys()):
                if option in cls._ALLOWED_OPTIONS:
                    logger.info(f"{_get_function_name()}: Setting cls._OPTIONS[{option}] to {options[option]}.")
                    new_options[option] = options[option]
                    if set_global:
                        cls._OPTIONS[option] = options[option]
                else:
                    logger.warning(f"{_get_function_name()}: Unknown option: {option}")
        else:
            err_msg = (f"{_get_function_name()}: Invalid options argument: expected type list() or dict(), "
                       + f"got {type(options)}")
            logger.exception(err_msg)
            raise StatCalcRuntimeError(err_msg)
        logger.info(f"{_get_function_name()}: Returning {new_options=}")
        return new_options

    @classmethod
    def _process_use_values_settings(cls, use_values: dict) -> None:
        """Break options object into parts and validate settings"""
        if not use_values:
            logger.warning(f"{_get_function_name()}: No 'use_values' parameter. Returning ...")
            return
        if not isinstance(use_values, dict):
            raise StatCalcRuntimeError(
                (f"{_get_function_name()}: Invalid object type ({type(use_values)}) for "
                 + f"'options' attribute. Should be dict.")
            )
        for key in list(use_values.keys()):
            if key not in ["char", "ship", "crew"]:
                logger.debug(f"{_get_function_name()}: Deleting unexpected element: {key}")
                del use_values[key]
        cls._USE_VALUES = deepcopy(use_values)

    @classmethod
    def calc_player_stats(
            cls,
            players: list or dict,
            options: list or dict = None,
            use_values: dict = None,
    ) -> list or None:
        """
        Calculate roster stats for list of players

        Args:
            players (list or dict): List of player objects, including the rosterUnits
            options (list|dict): Dictionary or list of options to enable
            use_values (dict): A dictionary containing elements for 'char', 'ship', and 'crew' for overriding defaults

        Returns: List of players with stats included in each player unit roster
        """
        if not players:
            logger.error(f"{_get_function_name()}: No player rosters submitted to calc_player_stats(). Exiting...")
            return

        if isinstance(players, list):
            for player in players:
                logger.info(f"{_get_function_name()}: Processing player: {player['name']} ...")
                player['rosterUnit'] = cls.calc_roster_stats(player['rosterUnit'], options, use_values)
        else:
            # Single player roster
            logger.info(f"{_get_function_name()}: Processing player: {players['name']} ...")
            if 'rosterUnit' in players.keys():
                players['rosterUnit'] = cls.calc_roster_stats(players['rosterUnit'], options, use_values)
            else:
                logger.warning(f"{_get_function_name()}: No unit roster detected in submission. Exiting.")
                return
        return players

    @classmethod
    def calc_roster_stats(
            cls,
            units: list[dict],
            options: list or dict = None,
            use_values: dict = None,
    ) -> list:
        """
        Calculate units stats from SWGOH roster game data

        :param units: A list containing the value of the 'rosterUnit' key within the SwgohComlink.get_player() result
        :type units: list
        :param options: Dictionary or list of options to enable
        :type options: (dict|list)
        :param use_values: A dictionary containing elements for 'char', 'ship', and 'crew' for overriding defaults
        :type use_values: dict

        :return: The same object format provided in the units parameter with additional fields added containing the
                 results of the stat calculations
        :rtype: list
        """
        logger.info(f"{_get_function_name()}: *** Entering calc_roster_stats() ***")
        if not cls.is_initialized:
            raise StatCalcException(
                "StatCalc is not initialized. Please perform the initialization first."
            )

        cls._process_options(options)
        if use_values:
            cls._process_use_values_settings(use_values)

        language = options.get('language', "eng_us")
        cls._process_language(language)

        if isinstance(units, list):
            ships = []
            temp_units = []
            temp_ships = []
            for unit in units:
                unit = _verify_def_id(unit)
                defId = unit.get('defId')
                if not unit or not cls._UNIT_DATA[defId]:
                    logger.warning(f"{_get_function_name()}: Unable to find {defId} in game data.")
                    return []
                combat_type = cls._UNIT_DATA[defId]["combatType"]
                if combat_type == 2 or combat_type == "SHIP":
                    ships.append(unit)
                else:
                    temp_units.append(cls.calc_char_stats(unit, use_values=use_values, options=options))
            for ship in ships:
                ship = _verify_def_id(ship)
                defId = ship.get('defId')
                if not cls._UNIT_DATA[defId]:
                    logger.warning(f"{_get_function_name()}: Unable to find {defId} in game data.")
                    return []
                crw = cls._UNIT_DATA[defId].get("crew")
                temp_ships.append(cls.calc_ship_stats(ship, crw))
        else:
            raise StatCalcRuntimeError(
                f"{_get_function_name()}: Unsupported data type [{type(units)}] for 'unit' parameter"
            )
        return temp_units + temp_ships

    @classmethod
    def calc_stats(cls,
                   units: list[dict],
                   options: list or dict = None,
                   use_values: dict = None,
                   ) -> Any:
        """
        Entry point for submission of unit data for stat calculations. Decision is made here on how to
        proceed based on the type of data submitted.


        Returns: List

        """

    @classmethod
    def initialize(cls, cl: swgoh_comlink.SwgohComlink, language: str = "eng_us", **kwargs) -> bool:
        """Prepare StatCalc environment for first use. Providing keyword arguments can override default settings.

        Args: cl swgoh_comlink: Instance of SwgohComlink class for retrieving data from game servers
              language: String specifying the localization language to use for translations [Defaults to "eng_us"]
            
        Keyword Args:
            game_data dict: Defaults to None. Will autoload if not provided.
            default_mod_tier int: Defaults to 5. Should not need to be set unless the game changes mods and some point.
            default_mod_level int: Defaults to 15. Should not need to be set unless the game mod system changes.
            default_mod_pips int: Defaults to 6. Should not need to be set unless the game mod system changes.
            debug bool: flag to enable debug function logging. [Defaults to False]

        Returns: bool: True if initialization is successful, False otherwise
        """

        if language not in DataBuilder.get_languages():
            logger.warning(f"{_get_function_name()}: Provided language {language} is not supported. "
                           + f"Defaulting to 'eng_us'")
            setattr(cls, "language", "eng_us")
        else:
            logger.debug(f"{_get_function_name()}: Setting StatCalc.language to {language}")
            setattr(cls, "language", language)

        # Set allowed parameters and values for argument checking
        allowed_parameters = {
            "default_mod_tier": list(range(1, cls._DEFAULT_MOD_TIER + 1, 1)),
            "default_mod_level": list(range(1, cls._DEFAULT_MOD_LEVEL + 1, 1)),
            "default_mod_pips": list(range(1, cls._DEFAULT_MOD_PIPS + 1, 1)),
            "game_data": [None, dict],
            "language": DataBuilder.get_languages(),
            "debug": [False, True]
        }

        logger.info(f"{_get_function_name()}: Initializing StatCalc for first time use.")
        # Populate the _OPTIONS dictionary with default values
        cls.reset_options()

        cls._COMLINK = cl
        class_vars = vars(cls)
        logger.debug(f"{_get_function_name()}: Class vars: {class_vars.keys()}")
        for param, value in kwargs.items():
            if param in allowed_parameters.keys():
                if value in allowed_parameters[param]:
                    if param == 'debug':
                        set_debug(value)
                        continue
                    class_var = "_" + param.upper()
                    logger.debug(f"{_get_function_name()}: Setting class variable {class_var} to {value}")
                    # Remove .json file extension from file name arguments since it is added by the read/write methods
                    if value.endswith(".json"):
                        value = value.replace(".json", "")
                    logger.debug(f"{_get_function_name()}: Before: {class_var} = {class_vars[class_var]}")
                    setattr(cls, class_var, value)
                    new_vars = vars(cls)
                    logger.debug(f"{_get_function_name()}: After: {class_var} = {new_vars[class_var]}")
                else:
                    logger.error(
                        f"{_get_function_name()}: Invalid value ({value}) for argument ({param}). "
                        + f"Allowed values are [{allowed_parameters[param]}]."
                    )

        if not cls._GAME_DATA:
            logger.info("{_get_function_name()}: Loading game data from DataBuilder.")
            if not DataBuilder.is_initialized:
                if not DataBuilder.initialize():
                    logger.error(f"A{_get_function_name()}: n error occurred while initializing DataBuilder.")
                    return False
            try:
                cls._GAME_DATA = DataBuilder.get_game_data()
            except DataBuilderException as e_str:
                logger.exception(e_str)
                return False
        else:
            logger.info("{_get_function_name()}: Game stat information provided.")

        try:
            cls._UNIT_DATA = cls._GAME_DATA["unitData"]
            cls._GEAR_DATA = cls._GAME_DATA["gearData"]
            cls._MOD_SET_DATA = cls._GAME_DATA["modSetData"]
            cls._CR_TABLES = cls._GAME_DATA["crTables"]
            cls._GP_TABLES = cls._GAME_DATA["gpTables"]
            cls._RELIC_DATA = cls._GAME_DATA["relicData"]
        except KeyError as key_err_str:
            logger.error(f"{_get_function_name()}: Unable to initialize stat data structures. [{key_err_str}]")
            raise StatCalcRuntimeError(
                f"Unable to initialize stat data structures. [{key_err_str}]"
            )

        logger.info(f"{_get_function_name()}: Loading unit 'nameKey' mapping object from DataBuilder files...")
        try:
            cls._UNIT_NAME_MAP = DataBuilder.get_unit_names_mapping(cls._LANGUAGE)
        except FileNotFoundError:
            logger.error(f"{_get_function_name()}: Unit name mapping file not found. [{cls._LANGUAGE}]")
            logger.info(
                f"{_get_function_name()}: Creating unit 'nameKey' mapping object from game server data."
            )
            cls._load_unit_name_map()

        logger.info(
            f"{_get_function_name()}: Loading stat ID to localized name mapping for language: {cls._LANGUAGE} ..."
        )
        if not cls._load_stat_name_map():
            logger.error(f"{_get_function_name()}: Unable to load stat ID to name mapping. "
                         + f"Stats will be referenced by ID only.")
        else:
            logger.info(f"{_get_function_name()}: Stat ID to localized name mapping loading complete.")

        logger.debug("{_get_function_name()}: Setting StatCalc._INITIALIZED to True")
        setattr(cls, "_INITIALIZED", True)

        return True
