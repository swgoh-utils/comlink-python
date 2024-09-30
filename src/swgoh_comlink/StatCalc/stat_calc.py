# coding=utf-8
"""
Python library module for calculating character and ship statistic values for the Star Wars: Galaxy of Heroes mobile
game from EA/CG.
"""
from __future__ import annotations, absolute_import

import base64
import functools
import io
import logging
import os
import zipfile
from copy import deepcopy, copy
from functools import singledispatchmethod
from math import floor as math_floor
from typing import Callable

import orjson
from sentinels import Sentinel

import swgoh_comlink
from swgoh_comlink import SwgohComlink
from swgoh_comlink.StatCalc.stat_calc_helpers import raise_invalid_object_type_error
from swgoh_comlink.StatCalc.stat_values import StatValues, StatOptions, StatValueError
from swgoh_comlink.constants import (
    Constants,
    get_logger,
    set_debug,
    get_function_name,
    OPTIONAL,
    NotSet
)
from swgoh_comlink.data_builder import DataBuilder, DataBuilderException
from swgoh_comlink.exceptions import StatCalcRuntimeError, StatCalcException, StatCalcValueError
from swgoh_comlink.utils import validate_file_path, create_localized_unit_name_dictionary

logger = get_logger()


# TODO: fix usage of StatValues
def _format_stats(stats: dict, level: int = 85, options: StatOptions | Sentinel = OPTIONAL) -> dict:
    logger.info("*** Formatting stats *** ")
    if not stats:
        logger.debug("No stats object provided. Returning empty.")
        return {}

    logger.debug(f"Stats: {stats} {level=} {options=}")

    scale = 1
    if options.SCALED:
        scale = 1e-4
    elif not options.UNSCALED:
        scale = 1e-8

    if 'mods' in stats:
        logger.debug(f"Rounding mod values ... ")
        for stat_id, value in stats['mods'].items():
            stats['mods'][stat_id] = round(value, 6)
            logger.debug(f"{stat_id} old value: {value}, "
                         + f"new value: {stats['mods'][stat_id]}")

    if scale != 1:
        logger.debug(f"Scaling stats ... {scale=}")
        for stat_type in ('base', 'gear', 'crew', 'growthModifiers', 'mods'):
            if stat_type in stats:
                for stat_id in stats[stat_type].keys():
                    original_value = stats[stat_type][stat_id]
                    stats[stat_type][stat_id] *= scale
                    logger.debug(f"{stat_id} old value: {original_value}, "
                                 + f"new value: {stats[stat_type][stat_id]}")
            else:
                logger.debug(f"{stat_type} not found in {list(stats.keys())}")

    if options.PERCENT_VALS or options.GAME_STYLE:  # flags are basically included with each other
        def convert_percent(stat_id_str: str, convert_func: Callable):
            logger.debug(f"{stat_id_str=}, {convert_func=}")
            flat = stats['base'].get(stat_id_str, 0)
            percent = convert_func(flat)
            stats['base'][stat_id_str] = percent
            last = percent
            logger.debug(f"{flat=}, {percent=}, {last=}")
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
        convert_percent('14', lambda val: _convert_flat_stat_to_percent("cc", val,
                                                                        scale * 1e8))  # Ph. Crit Rating -> Chance
        convert_percent('15', lambda val: _convert_flat_stat_to_percent("cc", val,
                                                                        scale * 1e8))  # Sp. Crit Rating -> Chance
        # convert Def
        convert_percent('8', lambda val: _convert_flat_stat_to_percent("def", val, scale * 1e8, level,
                                                                       bool(stats.get('crew'))))  # Armor
        convert_percent('9', lambda val: _convert_flat_stat_to_percent("def", val, scale * 1e8, level,
                                                                       bool(stats.get('crew'))))  # Resistance
        # convert Acc
        convert_percent('37', lambda val: _convert_flat_stat_to_percent("acc", val,
                                                                        scale * 1e8))  # Physical Accuracy
        convert_percent('38', lambda val: _convert_flat_stat_to_percent("acc", val,
                                                                        scale * 1e8))  # Special Accuracy
        # convert Evasion
        convert_percent('12', lambda val: _convert_flat_stat_to_percent("acc", val,
                                                                        scale * 1e8))  # Dodge
        convert_percent('13', lambda val: _convert_flat_stat_to_percent("acc", val,
                                                                        scale * 1e8))  # Deflection
        # convert Crit Avoidance
        convert_percent('39',
                        lambda val: _convert_flat_stat_to_percent("cc", val, scale * 1e8))  # Physical Crit Avoid
        convert_percent('40',
                        lambda val: _convert_flat_stat_to_percent("cc", val, scale * 1e8))  # Special Crit Avoid

    if options.GAME_STYLE:
        gs_stats = {"final": {}}
        stat_list = list(stats["base"].keys())
        logger.debug(f"{stat_list=}")

        def add_stats(stat_id_str: str):
            logger.debug(f"{stat_id_str=} ({type(stat_id_str)})...")
            if not isinstance(stat_id_str, str):
                logger.debug(f"converting 'stat_id' from {type(stat_id_str)} to 'str' ...")
                stat_id_str = str(stat_id_str)
            if stat_id_str not in stat_list:
                logger.debug(f"{stat_id_str} not in stat_list. Adding it ...")
                stat_list.append(stat_id_str)

        if "gear" in stats:  # Character
            logger.debug(f"Processing 'gear' ...")
            for stat_id in stats['gear']:
                add_stats(stat_id)  # add stats from gear to list
            if 'mods' in stats:
                logger.debug(f"Processing 'mods' ...")
                for stat_id in stats['mods']:
                    add_stats(stat_id)  # add stats from mods to list
                gs_stats['mods'] = deepcopy(stats['mods'])  # keep mod stats untouched

            for stat_id in stat_list:
                flat_stat_id = stat_id
                logger.debug(f"{flat_stat_id=} ({type(flat_stat_id)})... ...")
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
        stats = deepcopy(gs_stats)
        logger.debug(f"Stats: {stats}")
    return stats


def _scale_stat_value(stat_id: int or str, value: float) -> float:
    """Convert stat value from displayed value to "unscaled" value used in calculations"""
    logger.debug(f"*** Scaling statId: {stat_id} value: {value} ***")
    if isinstance(stat_id, str):
        stat_id = int(stat_id)
    if stat_id in [1, 5, 28, 41, 42]:
        logger.debug(f"   New value: {value * 1e8} (times 1e8)")
        return value * 1e8
    else:
        logger.debug(f"   New value: {value * 1e6} (times 1e6)")
        return value * 1e6


def _floor(value: float, digits: int = 0) -> float:
    precision = float(("1e" + str(digits)))
    floor_value = math_floor(value / precision) * precision
    # logger.debug(f"{value=}, {floor_value=}")
    return floor_value


def _convert_flat_stat_to_percent(
        stat: str,
        value: float,
        scale: float = 1.0,
        level: int = 85,
        is_ship: bool = False) -> float:
    logger.debug(f"*** Converting flat value to percent ({stat=}, {value=}, "
                 + f"{level=}, {scale=}, {is_ship=}) *** ")
    val = value / scale
    match stat:
        case "def":
            level_effect = 300 + level * 5 if is_ship else level * 7.5
            percent_val = (val / (level_effect + val)) * scale
            logger.debug(f"{val=}, {level_effect=}, {percent_val=}")
        case "cc":
            percent_val = (val / 2400 + 0.1) * scale
        case "acc":
            percent_val = (val / 1200) * scale
        case "ca":
            percent_val = (val / 2400) * scale
        case _:
            err_msg = f"Unsupported stat {stat}."
            logger.error(err_msg)
            raise StatCalcRuntimeError(err_msg)
    logger.debug(f"{val=}, {percent_val=}")
    return percent_val


def _verify_def_id(unit: dict) -> dict:
    logger.debug(f"*** Verifying 'defId' exists ***")
    temp_def_id = _get_def_id(unit)
    logger.debug(f"{temp_def_id=}")
    return unit


def _get_def_id(unit: dict) -> str:
    logger.debug(f"Getting 'defId' ...")
    if 'defId' in unit:
        logger.debug(f"Existing 'defId' found: {unit.get('defId')}")
        return unit.get("defId")
    else:
        logger.debug(f"No 'defId' found. Generating one ...")
        if 'definitionId' in unit:
            unit['defId'] = unit.get("definitionId").split(":")[0]
            logger.debug(f"Unit contains 'definitionId'. Setting 'defId' to {unit.get('defId')} ...")
            return unit.get('defId')
        elif 'baseId' in unit:
            unit['defId'] = unit.get("baseId")
            logger.debug(f"Unit contains 'baseId'. Setting 'defId' to {unit.get('defId')} ...")
            return unit.get('defId')

        else:
            raise StatCalcRuntimeError(f"Unable to detect required value of 'defId' creation.")


class StatCalc:
    """
    Container class to house collection of stat calculation methods. Not intended to be instantiated.
    """

    _INITIALIZED = False

    _DEFAULT_MOD_TIER = os.getenv("DEFAULT_MOD_TIER", Constants.MAX_VALUES['MOD_TIER'])
    _DEFAULT_MOD_LEVEL = os.getenv("DEFAULT_MOD_LEVEL", Constants.MAX_VALUES['MOD_LEVEL'])
    _DEFAULT_MOD_PIPS = os.getenv("DEFAULT_MOD_PIPS", Constants.MAX_VALUES['MOD_RARITY'])

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

    _COMLINK: swgoh_comlink.SwgohComlink = None

    @classmethod
    def is_initialized(cls) -> bool:
        return cls._INITIALIZED

    @classmethod
    def set_attribute(cls, attr_name: str, attr_value: any) -> None:
        """Set class attribute

        Args
            attr_name: Name of attribute to set
            attr_value: The value to assign to the attribute

        Returns
            None

        """
        logger.debug(f"Setting class variable {attr_name} to {attr_value}")
        logger.debug(f"Before: {attr_name} = {cls.__dict__[attr_name]}")
        setattr(cls, attr_name, attr_value)
        logger.debug(f"After: {attr_name} = {cls.__dict__[attr_name]}")

    @classmethod
    def _update_class_attributes(cls, attr_items: dict) -> None:
        # Set allowed parameters and values for argument checking
        allowed_parameters = {
            "default_mod_tier": list(range(1, Constants.MAX_VALUES['MOD_TIER'] + 1, 1)),
            "default_mod_level": list(range(1, Constants.MAX_VALUES['MOD_LEVEL'] + 1, 1)),
            "default_mod_pips": list(range(1, Constants.MAX_VALUES['MOD_RARITY'] + 1, 1)),
            "game_data": [None, dict],
            "language": DataBuilder.get_languages(),
            "debug": [False, True]
        }

        for param, value in attr_items.items():
            if param in allowed_parameters.keys():
                if value in allowed_parameters[param]:
                    if param.lower() == 'debug':
                        set_debug(value)
                        continue
                    class_var = "_" + param.upper()
                    cls.set_attribute(class_var, value)
                else:
                    logger.error(
                        f"Invalid value ({value}) for argument ({param}). "
                        + f"Allowed values are [{allowed_parameters[param]}]."
                    )

    @classmethod
    def set_log_level(cls, log_level: str):
        """Set the logging level for message output. Default is 'INFO'

        Args
            log_level (str): Logging level

        Raises
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
    def _load_unit_name_map(cls,
                            /,
                            *,
                            locale: str | Sentinel = OPTIONAL,
                            ) -> bool:
        """Create unit_name_map dictionary"""
        if isinstance(locale, Sentinel):
            locale = cls._LANGUAGE

        latest_game_version = cls._COMLINK.get_latest_game_data_version()
        loc_bundle = cls._COMLINK.get_localization_bundle(
            id=latest_game_version["language"],
            locale=locale
        )
        loc_bundle_decoded = base64.b64decode(loc_bundle["localizationBundle"])
        logger.info(f"Decompressing data stream...")
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
                f"An error occurred while attempting to load the stat names map. [{e_str}]"
            )
            return False
        if not validate_file_path(language_file):
            logger.error(
                f"Error while validating language file data path ({language_file})"
            )
            return False
        try:
            with open(language_file) as fn:
                cls._STAT_NAME_MAP = orjson.loads(fn.read())
        except OSError as os_error:
            logger.exception(f"Error while loading {language_file}. [{os_error}]")
            return False
        else:
            return True

    @classmethod
    def _rename_stats(cls, stats: dict, options: StatOptions) -> dict:
        logger.info(f"Renaming stats ... ")

        if options.STAT_IDS:
            logger.debug(f"StatOptions 'stat_id' set to {options.STAT_IDS}. Skipping stat rename.")
            return stats

        lang = options.LANGUAGE
        # Create a new localized stat name mapping rather than use the global default
        # so that different languages can be supported for each call
        stat_id_name_map = DataBuilder.get_localized_stat_names(language=lang)
        rn_stats = {}
        for stat_type in stats:
            rn_stats[stat_type] = {}
            for stat_id, value in stats[stat_type].items():
                stat_name = stat_id_name_map.get(stat_id, stat_id)
                if options.NO_SPACE:
                    stat_name = stat_name.replace(' ', '')  # remove spaces
                    stat_name = stat_name[0].lower() + stat_name[1:]  # ensure first letter is lower case
                logger.debug(f"Renaming {stat_id} to {stat_name} ... ")
                rn_stats[stat_type][stat_name] = value
        stats = deepcopy(rn_stats)
        logger.info(f"Done renaming stats")
        return stats

    @classmethod
    def _calculate_base_stats(cls, stats: dict, level: int, base_id: str) -> dict:
        """Calculate bonus primary stats from growth modifiers"""
        logger.info(f"Calculating base stats")
        logger.debug(f"{stats=}")
        if 'base' not in stats:
            stats['base'] = {}
        for i in ("2", "3", "4"):
            logger.info(f"Processing base stats for {i} ...")
            logger.info(f"{stats['base'][i]=} before")
            logger.info(f"Adding math_floor({stats['growthModifiers'][i]} * "
                        + f"{level} * 1e8) / 1e8")
            stats["base"][i] += _floor(stats["growthModifiers"][i] * level, 8)
            logger.info(f"{stats['base'][i]=} after")
        if stats["base"].get("61"):
            logger.info(f"Calculating effect of mastery on secondary stats ...")
            mastery_modifier_key = cls._UNIT_DATA[base_id].get("masteryModifierID")
            try:
                mms = cls._CR_TABLES[mastery_modifier_key]
                for stat_id, modifier in mms.items():
                    stats['base'][stat_id] = stats['base'].get(stat_id, 0) + stats['base']["61"] * modifier
            except KeyError as e_str:
                logger.error(
                    f"Unable to find mastery modifier key [{mastery_modifier_key}] in crTable."
                )
                logger.error(e_str)
                logger.error(f"crTable keys: {sorted(list(cls._CR_TABLES.keys()))}")

        logger.info(f" *** Calculating effect of primary stat on secondary stats ... ***")
        logger.debug(f"{stats['base']=}")
        # Calculate effects of primary stats on secondary stats
        primary_stat_name = str(cls._UNIT_DATA[base_id]['primaryStat'])
        stats['base']['1'] = (stats['base'].get('1', 0) +
                              stats['base']['2'] * 18)  # Health += STR * 18
        stats['base']['6'] = _floor(stats['base'].get('6', 0) +
                                    stats['base'][primary_stat_name] * 1.4, 8)  # Ph. Damage += MainStat * 1.4
        stats['base']['7'] = _floor(stats['base'].get('7', 0) +
                                    stats['base']['4'] * 2.4, 8)  # Sp. Damage += TAC * 2.4
        stats['base']['8'] = _floor(stats['base'].get('8', 0) + stats['base']['2'] * 0.14 +
                                    stats['base']['3'] * 0.07, 8)  # Armor += STR*0.14 + AGI*0.07
        stats['base']['9'] = _floor(stats['base'].get('9', 0) +
                                    stats['base']['4'] * 0.1, 8)  # Resistance += TAC * 0.1
        stats['base']['14'] = _floor(stats['base'].get('14', 0) +
                                     stats['base']['3'] * 0.4, 8)  # Ph. Crit += AGI * 0.4

        logger.info(f"Ensuring core stats are present and at minimum ...")
        # add hard-coded minimums or potentially missing stats
        stats["base"]["12"] = stats["base"].get("12", 0) + (24 * 1e8)
        stats["base"]["13"] = stats["base"].get("13", 0) + (24 * 1e8)
        stats["base"]["15"] = stats["base"].get("15", 0)
        stats["base"]["16"] = stats["base"].get("16", 0) + (150 * 1e6)
        stats["base"]["18"] = stats["base"].get("18", 0) + (15 * 1e6)
        logger.debug(f"Base stat calculated: {stats['base']=}")
        return stats

    @classmethod
    def _calculate_mod_stats(cls, base_stats: dict, char: dict = None) -> dict or None:
        logger.info("Calculating mod stats ... ")
        logger.info(f"{base_stats=}")
        if not char.get('equippedStatMod'):
            logger.warning(f"Mod list is missing or empty. Returning.")
            return {}

        set_bonuses = {}
        raw_mod_stats = {}

        for mod in char['equippedStatMod']:
            # The mod['definitionId'] value is a 3 character string. Each character in the string is a numeral
            #   representing mod set type (health, speed, potency, etc.), rarity (pips)  and position (slot)
            #   The first numeric character is the mod set ID
            #   The second numeric character is the mod rarity (number of pips/dots [1-6])
            #   The third numeric character is the mod position/slot [1-6]
            mod_set_id = int(mod['definitionId'][0])
            mod_set_name = Constants.MOD_SET_IDS[str(mod_set_id)]
            set_bonus = set_bonuses.get(mod_set_id)
            logger.debug(f"Mod set id: {mod_set_id} ({mod_set_name}), {set_bonus=}")
            if set_bonus:
                # set bonus already found, increment
                logger.debug(f"{mod_set_id} ({mod_set_name}) "
                             + f"already present in set_bonuses list. Incrementing counter.")
                set_bonus['count'] += 1
                if mod['level'] == 15:
                    set_bonus['maxLevel'] += 1
                logger.debug(f"{set_bonus['count']=}, "
                             + f"{set_bonus['maxLevel']=}, {mod['level']=}")
            else:
                # new set bonus, create object
                logger.debug(f"Creating new entry for {mod_set_id} "
                             + f"({mod_set_name}) in set_bonuses list.")
                set_bonuses[mod_set_id] = {'count': 1, 'maxLevel': 1 if mod['level'] == 15 else 0}

            # add Primary/Secondary stats to data
            stat = mod['primaryStat']['stat']
            i = 0
            logger.debug(f"counter = {i}, {stat=}")
            while True:
                unscaled_stat = float(stat['unscaledDecimalValue']) + raw_mod_stats.get(stat['unitStatId'], 0)
                raw_mod_stats[stat['unitStatId']] = unscaled_stat
                logger.debug(f"raw_mod_stats[{stat['unitStatId']}] = {unscaled_stat}")
                if i >= len(mod['secondaryStat']):
                    break
                stat = mod['secondaryStat'][i]['stat']
                i += 1
                logger.debug(f"counter = {i}, {stat=}")

        # add stats given by set bonuses
        logger.debug(f" *** Adding mod set bonuses ... ***")
        for set_id, set_bonus in set_bonuses.items():
            set_def = cls._MOD_SET_DATA[str(set_id)]
            logger.debug(f"{set_id=}, {set_bonus=}, {set_def=}")

            count = set_bonus['count']
            max_count = set_bonus['maxLevel']
            logger.debug(f"{count=}, {max_count=}")
            multiplier = (count // set_def['count']) + (max_count // set_def['count'])
            logger.debug(f"(count // set_def['count']) + (max_count // set_def['count']) = {multiplier}")

            raw_mod_stat = raw_mod_stats.get(set_def['id'], 0) + (set_def['value'] * multiplier)

            logger.debug(f"raw_mod_stats[{set_def['id']}] = {raw_mod_stat}")
            raw_mod_stats[set_def['id']] = raw_mod_stat

        # calculate actual stat bonuses from mods
        logger.debug(f" *** Calculating stat bonuses from mods ... ***")
        mod_stats = {}
        for stat_id, value in raw_mod_stats.items():
            stat_id = int(stat_id)
            if stat_id == 41:  # Offense
                mod_stats['6'] = mod_stats.get('6', 0) + value  # Ph. Damage
                mod_stats['7'] = mod_stats.get('7', 0) + value  # Sp. Damage
                logger.debug(f"{stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), {value=}, "
                             + f"{mod_stats['6']=}, {mod_stats['7']=}")
            elif stat_id == 42:  # Defense
                mod_stats['8'] = mod_stats.get('8', 0) + value  # Armor
                mod_stats['9'] = mod_stats.get('9', 0) + value  # Resistance
                logger.debug(f"{stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), {value=}, "
                             + f"{mod_stats['8']=}, {mod_stats['9']=}")
            elif stat_id == 48:  # Offense %
                mod_stats['6'] = _floor(mod_stats.get('6', 0) + (base_stats['6'] * 1e-8 * value), 8)  # Ph. Damage
                mod_stats['7'] = _floor(mod_stats.get('7', 0) + (base_stats['7'] * 1e-8 * value), 8)  # Sp. Damage
                logger.debug(f"{stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), {value=}, "
                             + f"{mod_stats['6']=}, {mod_stats['7']=}")
            elif stat_id == 49:  # Defense %
                mod_stats['8'] = _floor(mod_stats.get('8', 0) + (base_stats['8'] * 1e-8 * value), 8)  # Armor
                mod_stats['9'] = _floor(mod_stats.get('9', 0) + (base_stats['9'] * 1e-8 * value), 8)  # Resistance
                logger.debug(f"{stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), {value=} "
                             + f"{mod_stats['8']=}, {mod_stats['9']=}")
            elif stat_id == 53:  # Crit Chance
                mod_stats['21'] = mod_stats.get('21', 0) + value  # Ph. Crit Chance
                mod_stats['22'] = mod_stats.get('22', 0) + value  # Sp. Crit Chance
                logger.debug(f"{stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), {value=}, "
                             + f"{mod_stats['21']=}, {mod_stats['22']=}")
            elif stat_id == 54:  # Crit Avoid
                mod_stats['35'] = mod_stats.get('35', 0) + value  # Ph. Crit Avoid
                mod_stats['36'] = mod_stats.get('36', 0) + value  # Ph. Crit Avoid
                logger.debug(f"{stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), {value=}, "
                             + f"{mod_stats['35']=}, {mod_stats['36']=}")
            elif stat_id == 55:  # Health %
                mod_stats['1'] = _floor(mod_stats.get('1', 0) + (base_stats['1'] * 1e-8 * value), 8)  # Health
                logger.debug(f"{stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), {value=}, "
                             + f"{mod_stats['1']=}")
            elif stat_id == 56:  # Protection %
                mod_stats['28'] = _floor(mod_stats.get('28', 0) + (base_stats.get('28', 0) * 1e-8 * value),
                                         8)  # Protection may not exist in base
                logger.debug(f"{stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), {value=}, "
                             + f"{mod_stats['28']=}")
            elif stat_id == 57:  # Speed %
                mod_stats['5'] = _floor(mod_stats.get('5', 0) + (base_stats['5'] * 1e-8 * value), 8)  # Speed
                logger.debug(f"{stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), {value=}, "
                             + f"{mod_stats['5']=}")
            else:
                # other stats add like flat values
                mod_stats[str(stat_id)] = mod_stats.get(str(stat_id), 0) + value
                logger.debug(f"{stat_id=} ({cls._STAT_NAME_MAP[str(stat_id)]}), {value=}, "
                             + f"{mod_stats[str(stat_id)]=}")
        logger.debug(f"{mod_stats=}")
        return mod_stats

    @classmethod
    def _get_crew_rating(cls, crew: list) -> float:
        logger.debug(f"Calculating crew rating ...")

        def calculate_character_cr(crew_rating: float, char: dict) -> float:
            logger.debug(f"{crew_rating=}")
            crew_rating += (cls._CR_TABLES['unitLevelCR'][str(char['currentLevel'])]
                            + cls._CR_TABLES['crewRarityCR'][Constants.UNIT_RARITY[char['currentRarity']]])
            logger.debug(f"{crew_rating=}")
            crew_rating += cls._CR_TABLES['gearLevelCR'][str(char['currentTier'])]

            if char['currentTier'] < Constants.MAX_VALUES['GEAR_TIER']:
                equipped_gear_piece_count = len(char.get('equipped', []))
                gear_tier = str(char['currentTier'])
                logger.debug(f"{char['defId']} is below max gear level. Adding gear piece crew rating for "
                             + f"{equipped_gear_piece_count} gear pieces at gear tier {gear_tier}.")
                crew_rating += cls._CR_TABLES['gearPieceCR'][gear_tier] * equipped_gear_piece_count

            crew_rating = functools.reduce(lambda cr, skill: cr + cls._get_skill_crew_rating(skill), char['skill'],
                                           crew_rating)
            logger.debug(f"{crew_rating=}")

            if 'mods' in char:
                crew_rating = functools.reduce(
                    lambda cr, mod: cr + cls._CR_TABLES['modRarityLevelCR'][mod['pips']][str(mod['level'])],
                    char['mods'], crew_rating)
                logger.debug(f"Adding mods ... {crew_rating=}")
            elif 'equippedStatMod' in char:
                crew_rating = functools.reduce(
                    lambda cr, mod: cr + cls._CR_TABLES['modRarityLevelCR'][mod['definitionId'][1]][str(mod['level'])],
                    char['equippedStatMod'], crew_rating)
                logger.debug(f"Adding mods ... {crew_rating=}")

            if 'relic' in char and char['relic']['currentTier'] > 2:
                relic_tier = str(char['relic']['currentTier'])
                crew_rating += cls._CR_TABLES['relicTierCR'][relic_tier]
                crew_rating += char['currentLevel'] * cls._CR_TABLES['relicTierLevelFactor'][relic_tier]
                logger.debug(f"Adding relics ... {crew_rating=}")

            logger.debug(f"{crew_rating=}")
            return crew_rating

        total_cr = functools.reduce(calculate_character_cr, crew, 0.0)
        logger.debug(f"{total_cr=}")
        return total_cr

    @classmethod
    def _get_skill_crew_rating(cls, skill: dict) -> float:
        return float(cls._CR_TABLES['abilityLevelCR'][str(skill['tier'] + 2)])

    @classmethod
    def _get_crewless_crew_rating(cls, ship: dict) -> float:
        # temporarily uses hard-coded multipliers, as the true in-game formula remains a mystery.
        # but these values have experimentally been found accurate for the first 3 crewless ships:
        #     (Vulture Droid, Hyena Bomber, and BTL-B Y-wing)
        return _floor(
            cls._CR_TABLES['crewRarityCR'][Constants.UNIT_RARITY[ship['currentRarity']]] +
            3.5 * cls._CR_TABLES['unitLevelCR'][str(ship['currentLevel'])] +
            cls._get_crewless_skills_crew_rating(ship['skill'])
        )

    @classmethod
    def _get_crewless_skills_crew_rating(cls, skills: list) -> float:
        crew_rating = 0.0
        for skill in skills:
            const = 0.696 if skill['id'].startswith('hardware') else 2.46
            crew_rating += const * cls._CR_TABLES['abilityLevelCR'][str(skill['tier'] + 2)]
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
        logger.info(f"raw stats: {stats=}")
        # Calculate stats from current gear
        if isinstance(char['equipment'], list) and len(char["equipment"]) != 0:
            logger.info(f"Calculating stats for {char['defId']} equipment ")
            for equipment_piece in char["equipment"]:
                equipment_id = equipment_piece["equipmentId"]
                logger.info(f"Searching for {equipment_id} in game gearData ...")
                if equipment_id not in cls._GEAR_DATA:
                    logger.info(f"{equipment_id=} not found in game gearData ...")
                    continue
                equipment_stats = copy(cls._GEAR_DATA[equipment_id]["stats"])
                for equipment_stat_id in equipment_stats.keys():
                    if equipment_stat_id in ["2", "3", "4"]:
                        # Primary stat applies before mods
                        stats["base"][equipment_stat_id] += stats["base"][equipment_stat_id]
                    else:
                        # Secondary stat applies after mods
                        stats["gear"][equipment_stat_id] = (equipment_stats[equipment_stat_id] +
                                                            stats["gear"].get(equipment_stat_id, 0))
        else:
            logger.info(f"No equipment for {char['defId']}")

        if char.get("relic") and char["relic"].get("currentTier", 0) > 2:
            current_relic_tier: int = char["relic"].get("currentTier")
            logger.info(f"Calculating stats for {char['defId']} relic level: "
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
                logger.info(f"{stats['growthModifiers'][g_id]=}")
        else:
            logger.info(f"No relic information for {char['defId']}")
        logger.info(f"Stat results for {char['defId']}: {stats}")
        return stats

    @classmethod
    def _get_ship_raw_stats(cls, ship: dict, crew: list[dict]) -> dict:
        logger.debug(f"Getting ship raw stats for {ship['defId']} [{len(crew)} crew members]")

        # ensure crew is the correct crew
        logger.debug(f"Verifying correct number of crew members ...")
        if len(crew) != len(cls._UNIT_DATA[ship['defId']]['crew']):
            err_msg = f"Incorrect number of crew members for ship {ship['defId']}."
            logger.error(err_msg)
            raise ValueError(err_msg)

        logger.debug(f"Verifying correct crew members provided for {ship['defId']} ...")
        for char in crew:
            def_id = _get_def_id(char)
            logger.debug(f"... Verifying crew member {def_id} ...")
            if def_id not in cls._UNIT_DATA[ship['defId']]['crew']:
                err_msg = f"Unit {char['defId']} is not in {ship['defId']}'s crew."
                logger.error(err_msg)
                raise ValueError(err_msg)

        logger.debug(f"Calculating crew rating ...")
        if len(crew) == 0:
            logger.debug(f"Getting crewless rating ...")
            crew_rating = cls._get_crewless_crew_rating(ship)
        else:
            logger.debug(f"Getting crew rating for {len(crew)} members ...")
            crew_rating = cls._get_crew_rating(crew)

        logger.debug(f"{crew_rating=}")
        rarity = str(ship['currentRarity'])

        stats: dict = {
            'base': deepcopy(cls._UNIT_DATA[ship['defId']]['stats']),
            'crew': {},
            'growthModifiers': deepcopy(cls._UNIT_DATA[ship['defId']]['growthModifiers'][rarity])
        }

        logger.debug(f"Initial {stats=}")
        stat_multiplier: float = cls._CR_TABLES['shipRarityFactor'][rarity] * crew_rating
        logger.debug(f"{crew_rating=}, {rarity=}, {stat_multiplier=}, {stats=}")

        for stat_id, stat_value in cls._UNIT_DATA[ship['defId']]['crewStats'].items():
            # stats 1-15 and 28 all have final integer values
            # other stats require decimals -- shrink to 8 digits of precision through 'unscaled'
            # values this calculator uses
            precision = 8 if int(stat_id) < 16 or int(stat_id) == 28 else 0
            stats['crew'].setdefault(stat_id, _floor(stat_value * stat_multiplier, precision))
        logger.debug(f"{stats=}")
        return stats

    @classmethod
    def _set_skills(cls, unit_id: str, val: str | int) -> list:
        logger.info(f"Setting skills for {unit_id}")
        logger.debug(f"{val=}")
        if val == "max":
            logger.debug(f"Setting skills for {unit_id} (max)")
            return [
                {"id": d["id"], "tier": d["maxTier"]}
                for d in cls._UNIT_DATA[unit_id]["skills"]
            ]
        elif val == "max_no_zeta":
            logger.debug(f"Setting skills for {unit_id} (max_no_zeta)")
            return [
                {"id": d["id"], "tier": d["maxTier"] - (1 if d["isZeta"] and not d['isOmicron'] else 0)}
                for d in cls._UNIT_DATA[unit_id]["skills"]
            ]
        elif val == "max_no_omicron":
            logger.debug(f"Setting skills for {unit_id} (max_no_omicron)")
            return [
                {"id": d["id"], "tier": d["maxTier"] - (1 if d["isOmicron"] else 0)}
                for d in cls._UNIT_DATA[unit_id]["skills"]
            ]
        elif isinstance(val, int):
            _skills = [
                {"id": d["id"], "tier": min(val, d["maxTier"])}
                for d in cls._UNIT_DATA[unit_id]["skills"]
            ]
            logger.debug(f"Setting {len(_skills)} skills for {unit_id} ")
            return _skills
        else:
            return []

    @classmethod
    def _use_values_ships(cls, ship: dict, crew: list, use_values: StatValues | Sentinel) -> dict:
        if not use_values:
            return {'ship': ship, 'crew': crew}

        ship = {
            'defId': ship['defId'],
            'rarity': use_values.rarity,
            'level': use_values.level,
            'skills': cls._set_skills(ship['defId'], use_values.skills)
        }

        chars = []
        for char_id in cls._UNIT_DATA[ship['defId']]['crew']:
            char = next((cmem for cmem in crew if cmem['defId'] == char_id), None)
            char = {
                'defId': char_id,
                'rarity': use_values.rarity,
                'level': use_values.level,
                'gear': use_values.gear,
                'equipped': char['gear'],
                'skills': cls._set_skills(char_id, use_values.skills),
                'mods': char.get('mods'),
                'relic': {'current_tier': use_values.relic if use_values else char.get('relic')}
            }

            if use_values.equipment == "all":
                char['equipped'] = [
                    {'equipmentId': gear_id} for gear_id in cls._UNIT_DATA[char_id]['gear_lvl'][char['gear']]['gear']
                    if int(gear_id) < 9990
                ]
            elif use_values.equipment == "none":
                char['equipped'] = []
            elif isinstance(use_values.equipment, list):
                char['equipped'] = [
                    cls._UNIT_DATA[char_id]['gear_lvl'][char['gear']]['gear'][int(slot) - 1]
                    for slot in use_values.equipment
                ]
            elif use_values.equipment:
                char['equipped'] = use_values.equipment

            if use_values.mod_rarity or use_values.mod_level:
                char['mods'] = [
                    {
                        'pips': use_values.mod_rarity if use_values.mod_rarity else cls._DEFAULT_MOD_PIPS,
                        'level': use_values.mod_level if use_values.mod_level else cls._DEFAULT_MOD_LEVEL,
                        'tier': use_values.mod_tier if use_values.mod_tier else cls._DEFAULT_MOD_TIER
                    }
                    for _ in range(6)
                ]
            chars.append(char)
        return {'ship': ship, 'crew': chars}

    @classmethod
    def _use_values_char(cls, char: dict, use_values: StatValues | Sentinel) -> dict:

        char['defId'] = _get_def_id(char)

        logger.info(f"Executing _use_values_char() for {char['defId']} ...")

        if not char.get('baseId'):  # Player roster unit
            logger.debug(f"Player roster unit detected ...")
            char['rarity'] = char.get('currentRarity')
            char['level'] = char.get('currentLevel')
            char['gear'] = char.get('currentTier')
            char['equipment'] = char.get('equipment')
            char['equippedStatMod'] = char.get('equippedStatMod')
            char['relic'] = char.get('relic')
            char['skills'] = [{'id': skill['id'], 'tier': skill['tier'] + 2} for skill in char['skill']]
            char['purchasedAbilityId'] = char.get('purchasedAbilityId')
        else:  # Game default unit, use max values
            logger.debug(f"Default game unit detected ...")
            char['rarity'] = char.get('rarity', Constants.MAX_VALUES['UNIT_RARITY'])
            char['level'] = char.get('maxLevelOverride', Constants.MAX_VALUES['UNIT_LEVEL'])
            char['gear'] = Constants.MAX_VALUES['GEAR_TIER']
            char['equipment'] = []
            char['equippedStatMod'] = []
            char['relic'] = {'currentTier': Constants.MAX_VALUES['RELIC_TIER']}
            char['skills'] = cls._set_skills(char["defId"], 'max')

        # The 'use_values' parameter has not been set so the 'char' object does not need to be modified
        if use_values is NotSet:
            logger.info(f"No 'use_values' argument provided. Returning default character object.")
            return char

        logger.debug(f"Processing StatValue settings ...")
        # 'use_values' StatValues instance provided. Override existing settings with values from 'use_values'
        char["rarity"] = use_values.rarity
        char["level"] = use_values.level
        char["gear"] = use_values.gear
        char["relic"] = {"currentTier": use_values.relic}
        char["skills"] = cls._set_skills(char["defId"], use_values.skills)
        char["purchasedAbilityId"] = use_values.purchase_ability_id

        # populate fake mods based on StatValues
        for _ in range(6):
            char['equippedStatMod'].append({
                'pips': use_values.rarity,
                'level': use_values.mod_level,
                'tier': use_values.mod_tier
            })

        # populate fake equipment based on StatValues
        _equipment_list: list = copy(cls._UNIT_DATA[char['defId']]['gearLvl'][str(char['gear'])]['gear'])
        if use_values.equipment == "all":
            char['equipment'] = []
            for gear_id in _equipment_list:
                if int(gear_id) < 9990:
                    char['equipment'].append({'equipmentId': gear_id})
        elif isinstance(use_values.equipment, list):  # expecting array of gear slots
            for idx in use_values.equipment:
                char['equipment'].append({'equipmentId': _equipment_list[idx]})
        else:
            char['equipment'] = []

        return char

    @classmethod
    def _calc_char_gp(cls, char: dict):
        logger.debug(f"*** Calculating character GP for {char['defId']} ***")

        gp = cls._GP_TABLES['unitLevelGP'][str(char['currentLevel'])]
        logger.debug(f"Char level: {str(char['currentLevel'])}, "
                     + f"GP added: {cls._GP_TABLES['unitLevelGP'][str(char['currentLevel'])]}")
        logger.debug(f"{gp=} after level adjustment "
                     + f"({cls._GP_TABLES['unitLevelGP'][str(char['currentLevel'])]})")

        gp += cls._GP_TABLES['unitRarityGP'][Constants.UNIT_RARITY[char['currentRarity']]]
        logger.debug(f"{gp=} after rarity adjustment")

        gp += cls._GP_TABLES['gearLevelGP'][str(char['currentTier'])]
        logger.debug(f"{gp=} after equipment level adjustment")

        # Game tables for current gear include the possibility of different GP per slot.
        # Currently, all values are identical across each gear level, so a simpler method is possible.
        # But that could change at any time.

        if len(char['equipment']) > 0:
            logger.debug(f"*** Equipment found (processing) ***")
            for piece in char['equipment']:
                gp += cls._GP_TABLES['gearPieceGP'][str(char['currentTier'])][str(piece['slot'])]
        else:
            logger.debug(f"*** No equipment found (skipping) ***")

        logger.debug(f"{gp=} after equipment piece adjustment")

        gp += sum(cls._get_skill_gp(char['defId'], skill) for skill in char['skill'])
        logger.debug(f"{gp=} after skill adjustment")

        logger.debug(f"{gp=} after character skills adjustment")

        if char.get('purchasedAbilityId'):
            gp += len(char['purchasedAbilityId']) * cls._GP_TABLES['abilitySpecialGP']['ultimate']

        logger.debug(f"{gp=} after purchaseAbility adjustment")

        gp += sum(cls._GP_TABLES['modRarityLevelTierGP'][mod['definitionId'][1]][str(mod['level'])][str(mod['tier'])]
                  for mod in char['equippedStatMod'])

        logger.debug(f"{gp=} after mods adjustment")

        if char.get('relic') and char['relic']['currentTier'] > 2:
            relic_tier = str(char['relic']['currentTier'])
            gp += cls._GP_TABLES['relicTierGP'][relic_tier]
            gp += char['currentLevel'] * cls._GP_TABLES['relicTierLevelFactor'][relic_tier]
            logger.debug(f"{gp=} after relic adjustment")
        logger.debug(f"Final GP: {math_floor(gp * 1.5)}")

        return math_floor(gp * 1.5)

    @classmethod
    def _calc_ship_gp(cls, ship, crew=None):
        if crew is None:
            crew = []

        # ensure crew is the correct crew
        if len(crew) != len(cls._UNIT_DATA[ship['defId']]['crew']):
            raise StatValueError(f"Incorrect number of crew members for ship {ship['defId']}.")

        for char in crew:
            if char['defId'] not in cls._UNIT_DATA[ship['defId']]['crew']:
                raise StatValueError(f"Unit {char['defId']} is not in {ship['defId']}'s crew.")

        if len(crew) == 0:  # crewless calculations
            gps = cls._get_crewless_skills_gp(ship['defId'], ship['skill'])
            gps['level'] = cls._GP_TABLES['unit_level_gp'][ship['level']]
            gp = ((gps['level'] * 3.5 + gps['ability'] * 5.74 + gps['reinforcement'] * 1.61) *
                  cls._GP_TABLES['ship_rarity_factor'][ship['rarity']])
            gp += gps['level'] + gps['ability'] + gps['reinforcement']
        else:  # normal ship calculations
            gp = sum(c['gp'] for c in crew)
            gp *= cls._GP_TABLES['ship_rarity_factor'][ship['rarity']] * cls._GP_TABLES['crew_size_factor'][
                len(crew)]  # multiply crewPower factors before adding other GP sources
            gp += cls._GP_TABLES['unit_level_gp'][ship['level']]
            gp += sum(cls._get_skill_gp(ship['defId'], skill) for skill in ship['skill'])

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
        logger.debug(f"*** Getting skill GP *** {def_id=}, {skill=}")
        for s in cls._UNIT_DATA[def_id]['skills']:
            if s['id'] == skill['id']:
                # Convert player unit skill tier to same index scale as base game data unit scale
                player_unit_skill_tier = str(int(skill['tier']) + 2)
                logger.debug(f"Original skill tier: {skill['tier']}, "
                             + f"Adjusted skill tier: {player_unit_skill_tier}")
                logger.debug(f"Found skill {skill['id']} "
                             + f"tier {player_unit_skill_tier} ... ")
                logger.debug(f"_GP_TABLES skill {s} ")
                if int(player_unit_skill_tier) > s['maxTier']:
                    temp_skill_tier = player_unit_skill_tier
                    player_unit_skill_tier = str(s['maxTier'])
                    logger.debug(f"Adjusting skill tier down to maximum.  "
                                 + f"Original: {temp_skill_tier}, new: {player_unit_skill_tier}.")
                power_override_tag = s['powerOverrideTags'].get(player_unit_skill_tier, None)
                # if 'powerOverrideTags' exists for the player unit skill, use that GP value
                if power_override_tag:  # 'zeta' or 'omicron' or 'upgrade'
                    logger.debug(f"{power_override_tag=}, returning "
                                 + f"{cls._GP_TABLES['abilitySpecialGP'][power_override_tag]}")
                    return cls._GP_TABLES['abilitySpecialGP'][power_override_tag]
                # if no 'powerOverrideTags' exists for the player unit skill, use the GP for skill tier
                else:
                    logger.debug(f"No 'powerOverrideTags' found. Using "
                                 + f"{cls._GP_TABLES['abilityLevelGP'].get(player_unit_skill_tier, '0.0')}")
                    return cls._GP_TABLES['abilityLevelGP'].get(player_unit_skill_tier, "0")

    @classmethod
    def calc_char_stats(
            cls,
            char: dict,
            options: StatOptions | Sentinel = OPTIONAL,
            use_values: StatValues | Sentinel = OPTIONAL,
    ) -> dict:
        """Calculate stats for a single character based upon arguments provided.

        Args
            char: Character object from player roster or 'unit' collection in game data
            options: Instance of swgoh_comlink.StatCalc.StatOptions
            use_values: Instance of swgoh_comlink.StatCalc.StatValues

        Returns
            dict: character object dictionary with stats calculated

        Raises
            ValueError if an unexpected argument type is passed
        """
        if not isinstance(char, dict):
            raise StatCalcValueError(f"'char' argument must be type(dict) not {type(dict)}")

        if not isinstance(options, Sentinel) and not isinstance(options, StatOptions):
            raise StatCalcValueError(f"The 'options' argument must be an instance of StatOptions.")

        if not isinstance(use_values, Sentinel) and not isinstance(use_values, StatValues):
            raise StatCalcValueError(f"The 'use_values' argument must be an instance of StatValues.")

        if not cls.is_initialized:
            raise StatCalcException("StatCalc is not initialized. Please perform the initialization first.")

        char = _verify_def_id(char)

        logger.info(f"Calculating stats for {char['defId']}")

        if options is NotSet:
            logger.debug(f"No options provided. Assigning defaults ...")
            options = StatOptions()

        char = cls._use_values_char(char, use_values)

        if not options.ONLY_GP:
            stats = cls._get_char_raw_stats(char)
            stats = cls._calculate_base_stats(stats, char["currentLevel"], char["defId"])
            if len(char["equippedStatMod"]) > 0 and not options.WITHOUT_MOD_CALC:
                stats['mods'] = cls._calculate_mod_stats(stats.get("base"), char)
            stats = _format_stats(stats, int(char["currentLevel"]), options)
            char['stats'] = cls._rename_stats(stats, options)

        if options.CALC_GP or options.ONLY_GP:
            char['gp'] = cls._calc_char_gp(char)
            char['stats']['gp'] = char['gp']

        return char

    @classmethod
    def calc_ship_stats(
            cls,
            ship: dict,
            crew: list[dict],
            options: StatOptions | Sentinel = OPTIONAL,
            use_values: StatValues | Sentinel = OPTIONAL,
    ) -> dict:
        """

        Args
            ship: Ship object from player roster
            crew: List of ship crew members objects from player roster
            options: StatOptions object instance
            use_values: StatValues object instance

        Returns
            dict: Ship object with stats calculated

        """

        if not cls.is_initialized:
            raise StatCalcException("StatCalc is not initialized. Please perform the initialization first.")

        ship = _verify_def_id(ship)

        logger.info(f"Calculating stats for {ship['defId']}")

        if options is NotSet:
            logger.debug(f"No options provided. Using defaults ...")
            options = StatOptions()

        if isinstance(use_values, StatValues):
            ship, crew = cls._use_values_ships(ship, crew, use_values)
        else:
            logger.debug(f"No StatValues provided. Skipping ...")

        if not options.ONLY_GP:
            stats = cls._get_ship_raw_stats(ship, crew)
            stats = cls._calculate_base_stats(stats, ship['currentLevel'], ship['defId'])
            stats = _format_stats(stats, ship['currentLevel'], options)
            ship['stats'] = cls._rename_stats(stats, options)

        if options.CALC_GP or options.ONLY_GP:
            ship['gp'] = cls._calc_ship_gp(ship, crew)
            ship['stats']['gp'] = ship['gp']

        return ship

    # noinspection PyNestedDecorators
    @singledispatchmethod
    @classmethod
    def calc_player_stats(cls, players):
        """
        Calculate roster stats for list of players

        Args
            players: List of player objects, including the rosterUnits

        Keyword Args
            options: StatOptions instance
            use_values: StatValues instance

        Returns
            List of players with stats included in each player unit roster

        Raises
            ValueError on invalid 'players' argument
            StatCalcRuntimeError on
        """
        raise_invalid_object_type_error(players, {'list', 'dict'})

    # noinspection PyNestedDecorators
    @calc_player_stats.register
    @classmethod
    def _(cls,
          players: list,
          *,
          options: StatOptions | Sentinel = OPTIONAL,
          use_values: StatValues | Sentinel = OPTIONAL,
          ) -> list:

        for player in players:
            logger.info(f"Processing player: {player.get('name', 'UNKNOWN')} ...")
            if isinstance(player, dict):
                if 'rosterUnit' in player.keys():
                    player['rosterUnit'] = cls.calc_roster_stats(
                        player['rosterUnit'],
                        options=options,
                        use_values=use_values
                    )
                else:
                    err_msg = f"The 'rosterUnit' element is missing from player {player.get('name', 'UNKNOWN')}"
                    logger.error(err_msg)
            else:
                raise StatValueError(f"Items in 'players' argument list must be type(dict) not {type(player)}")
        return players

    # noinspection PyNestedDecorators
    @calc_player_stats.register
    @classmethod
    def _(cls,
          player: dict,
          *,
          options: StatOptions | Sentinel = OPTIONAL,
          use_values: StatValues | Sentinel = OPTIONAL,
          ) -> dict:

        logger.info(f"Processing player: {player.get('name', 'UNKNOWN')} ...")
        if 'rosterUnit' in player.keys():
            player['rosterUnit'] = cls.calc_roster_stats(
                player['rosterUnit'],
                options=options,
                use_values=use_values
            )
        else:
            raise StatCalcRuntimeError("'rosterUnit' element is missing from player.")
        return player

    @classmethod
    def calc_roster_stats(
            cls,
            units: list[dict],
            *,
            options: StatOptions | Sentinel = OPTIONAL,
            use_values: StatValues | Sentinel = OPTIONAL,
    ) -> list:
        """Calculate units stats from SWGOH roster game data

            Args
                units: A list containing the value of the 'rosterUnit' key within the SwgohComlink.get_player() result

            Keyword Args
                options: A StatOptions instance
                use_values: A StatValues instance

            Returns
                Input list with additional elements added containing the results of the stat calculations

            Raises
                StatCalcException if StatCalc is not yet initialized.
        """
        logger.info(f"*** Entering {get_function_name()} ***")
        if not cls.is_initialized:
            raise StatCalcException("StatCalc is not initialized. Please perform the initialization first.")

        if isinstance(units, list):
            ships = []
            crew_members = {}
            temp_units = []
            temp_ships = []
            for unit in units:
                def_id = _get_def_id(unit)
                if not unit or not cls._UNIT_DATA[def_id]:
                    logger.warning(f"Unable to find {def_id} in game 'UNIT_DATA'.")
                    continue
                combat_type = cls._UNIT_DATA[def_id]["combatType"]
                if combat_type == 2 or combat_type == "SHIP":
                    ships.append(unit)
                else:
                    # Populate dictionary with unit data keyed by unit defId.
                    # Needed for lookup of ship crew members below
                    crew_members[def_id] = unit
                    temp_units.append(cls.calc_char_stats(unit, use_values=use_values, options=options))
            for ship in ships:
                def_id = _get_def_id(ship)
                if not ship or not cls._UNIT_DATA[def_id]:
                    logger.warning(f"Unable to find {def_id} in game data.")
                    continue
                # Get list of crew members for ship (or empty list for crewless)
                crew_list = [crew_members[def_id] for def_id in cls._UNIT_DATA[def_id].get("crew")]
                temp_ships.append(cls.calc_ship_stats(ship, crew_list))
        else:
            raise StatCalcRuntimeError(f"Unsupported data type [{type(units)}] for 'unit' parameter")
        return temp_units + temp_ships

    @classmethod
    def initialize(cls,
                   cl: SwgohComlink,
                   language: str = "eng_us",
                   **kwargs
                   ) -> bool:
        """Prepare StatCalc environment for first use. Providing keyword arguments can override default settings.

        Args
            cl: Instance of SwgohComlink class for retrieving data from game servers
            language: String specifying the localization language to use for translations [Defaults to "eng_us"]
            
        Keyword Args
            game_data: Game data dictionary from DataBuilder. Will autoload if not provided.
            default_mod_tier: Defaults to 5. Should not need to be set unless the game changes mods and some point.
            default_mod_level: Defaults to 15. Should not need to be set unless the game mod system changes.
            default_mod_pips: Defaults to 6. Should not need to be set unless the game mod system changes.
            debug: flag to enable debug function logging. [Defaults to False]

        Returns
            True if initialization is successful, False otherwise
        """
        logger.info(f"Initializing StatCalc for first time use.")

        if not isinstance(cl, SwgohComlink):
            raise StatValueError("'cl' argument must be a SwgohComlink instance.")
        else:
            cls.set_attribute(attr_name='_COMLINK', attr_value=cl)

        if language not in DataBuilder.get_languages():
            logger.warning(f"Provided language {language} is not supported. "
                           + f"Defaulting to 'eng_us'")
        else:
            cls.set_attribute(attr_name='_LANGUAGE', attr_value=language)

        cls._update_class_attributes(attr_items=kwargs)

        if not cls._GAME_DATA:
            logger.info("Loading game data from DataBuilder.")
            if not DataBuilder.is_initialized():
                logger.debug(f"DataBuilder not initialized. Initializing...")
                if not DataBuilder.initialize():
                    raise StatCalcRuntimeError(f"An error occurred while initializing DataBuilder.")
            try:
                cls._GAME_DATA = DataBuilder.get_game_data()
            except DataBuilderException as e_str:
                logger.exception(e_str)
                return False
        else:
            logger.info("Game stat information provided.")

        try:
            logger.debug(f"Initializing individual game data category tables ...")
            cls._UNIT_DATA = cls._GAME_DATA["unitData"]
            cls._GEAR_DATA = cls._GAME_DATA["gearData"]
            cls._MOD_SET_DATA = cls._GAME_DATA["modSetData"]
            cls._CR_TABLES = cls._GAME_DATA["crTables"]
            cls._GP_TABLES = cls._GAME_DATA["gpTables"]
            cls._RELIC_DATA = cls._GAME_DATA["relicData"]
        except KeyError as key_err_str:
            raise StatCalcRuntimeError(f"Unable to initialize stat data structures. [{key_err_str}]")

        logger.info(f"Loading unit 'nameKey' mapping object from DataBuilder files...")
        try:
            cls._UNIT_NAME_MAP = DataBuilder.get_unit_names_mapping(cls._LANGUAGE)
        except FileNotFoundError:
            logger.error(f"Unit name mapping file not found for language {cls._LANGUAGE!r}")
            logger.info(f"Creating unit 'nameKey' mapping object from game server data.")
            if not cls._load_unit_name_map(locale=cls._LANGUAGE):
                raise StatCalcRuntimeError(f"Creation of unit 'nameKey' mapping object failed.")

        logger.info(
            f"Loading stat ID to localized name mapping for language: {cls._LANGUAGE} ..."
        )
        if not cls._load_stat_name_map():
            logger.error(f"Unable to load stat ID to name mapping. "
                         + f"Stats will be referenced by ID only.")
        else:
            logger.info(f"Stat ID to localized name mapping loading complete.")

        logger.debug("Setting StatCalc._INITIALIZED to True")
        cls.set_attribute(attr_name="_INITIALIZED", attr_value=True)
        return True


__all__ = [
    StatCalc,
    StatCalcException,
    StatCalcRuntimeError,
    StatValueError,
]
