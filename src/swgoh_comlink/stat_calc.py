# coding=utf-8
"""
Python library module for calculating character and ship statistic values for the Star Wars: Galaxy of Heroes mobile
game from EA/CG.
"""
import base64
import copy
import io
import json
import logging
import math
import os
import zipfile
from dataclasses import dataclass
from typing import Callable

import swgoh_comlink
import swgoh_comlink.utils as utils
from swgoh_comlink.const import Constants
from swgoh_comlink.data_builder import DataBuilder, DataBuilderException

logger = Constants.get_logger()


@utils.func_debug_logger
def _format_stats(stats: dict = None, level: int = 85, options: dict = None) -> dict:
    logger.info("Formatting stats ... ")
    logger.debug(f"Stats: {stats} {level=} {options=}")
    if stats is None:
        logger.debug("No stats object provided. Returning empty.")
        return {}

    def _convert_percent(stat_id_idx: str, convert_func: Callable, **kwargs) -> None:
        """In place conversion of stats to percent values where appropriate"""
        logger.info(f"Converting to percent ... {stat_id_idx=}")
        flat = stats["base"][stat_id_idx]
        percent = convert_func(flat)
        stats["base"][stat_id_idx] = percent
        last = percent
        logger.info(f" ... {flat=} {percent=} {last=} ...")
        if "crew" in stats:
            if stat_id_idx in stats["crew"]:
                logger.info("  ... converting crew member stat ...")
                flat += stats["crew"][stat_id_idx]
                stats["crew"][stat_id_idx] = (convert_func(flat, **kwargs)) - last
        else:
            if "gear" in stats and stat_id_idx in stats["gear"]:
                logger.info("  ... converting gear values ...")
                flat += stats["gear"][stat_id_idx]
                percent = convert_func(flat)
                flat += stats["gear"][stat_id_idx]
                stats["gear"][stat_id_idx] = percent - last
                last = percent
            if "mods" in stats and stat_id_idx in stats["mods"]:
                logger.info("  ... converting mod values ...")
                flat += stats["mods"][stat_id_idx]
                stats["mods"][stat_id_idx] = (convert_func(flat, **kwargs)) - last

    scale = 1
    if options["scaled"]:
        scale = 1e-4
    elif options["unscaled"]:
        scale = 1e-8

    if scale != 1:
        elements = list(stats.keys())
        if "mods" in stats:
            elements.append("mods")
        for element in elements:
            for stat_id in stats[element]:
                stats[element][stat_id] *= scale

    if options["percentVals"] or options["gameStyle"]:
        is_ship: bool = True if "crew" in stats else False
        logger.info("Converting flat values to percentages")
        conversion_dispatcher = {
            "8": {
                "func": _convert_flat_def_to_percent,
                "args": {"scale": scale * 1e8, "level": level, "is_ship": is_ship},
            },
            "9": {
                "func": _convert_flat_def_to_percent,
                "args": {"scale": scale * 1e8, "level": level, "is_ship": is_ship},
            },
            "12": {
                "func": _convert_flat_acc_to_percent,
                "args": {"scale": scale * 1e8},
            },
            "13": {
                "func": _convert_flat_acc_to_percent,
                "args": {"scale": scale * 1e8},
            },
            "14": {
                "func": _convert_flat_crit_to_percent,
                "args": {"scale": scale * 1e8},
            },
            "15": {
                "func": _convert_flat_crit_to_percent,
                "args": {"scale": scale * 1e8},
            },
            "37": {
                "func": _convert_flat_acc_to_percent,
                "args": {"scale": scale * 1e8},
            },
            "38": {
                "func": _convert_flat_acc_to_percent,
                "args": {"scale": scale * 1e8},
            },
            "39": {
                "func": _convert_flat_crit_avoid_to_percent,
                "args": {"scale": scale * 1e8},
            },
            "40": {
                "func": _convert_flat_crit_avoid_to_percent,
                "args": {"scale": scale * 1e8},
            },
        }

        for stat_category in list(stats.keys()):
            for stat_idx in stats[stat_category]:
                if stat_idx in conversion_dispatcher:
                    stats[stat_category][stat_idx] = conversion_dispatcher[stat_idx][
                        "func"
                    ](**conversion_dispatcher[stat_idx]["args"])
        # Convert Crit
        # _convert_percent("14", _convert_flat_crit_to_percent, scale=scale * 1e8)  # Ph.Crit Rating -> Chance
        # _convert_percent("15", _convert_flat_crit_to_percent, scale=scale * 1e8)  # Sp.Crit Rating -> Chance
        # convert Def
        # _convert_percent("8", _convert_flat_def_to_percent, level=level, scale=scale * 1e8, is_ship=is_ship)  # Armor
        # _convert_percent("9", _convert_flat_def_to_percent, level=level, scale=scale * 1e8, is_ship=is_ship)  # Resistance
        # convert Acc
        # _convert_percent("37", _convert_flat_acc_to_percent, scale=scale * 1e8)  # Physical Accuracy
        # _convert_percent("38", _convert_flat_acc_to_percent, scale=scale * 1e8)  # Special Accuracy
        # convert Evasion
        # _convert_percent("12", _convert_flat_acc_to_percent, scale=scale * 1e8)  # Dodge
        # _convert_percent("13", _convert_flat_acc_to_percent, scale=scale * 1e8)  # Deflection
        # convert Crit Avoidance
        # _convert_percent("39", _convert_flat_crit_avoid_to_percent, scale=scale * 1e8)  # Physical Crit Avoidance
        # _convert_percent("40", _convert_flat_crit_avoid_to_percent, scale=scale * 1e8)  # Special Crit Avoidance

    if options["gameStyle"] is True:
        gs_stats = {"final": {}}
        stat_list = list(stats["base"].keys())
        if "gear" in stats:  # Character
            for gear_key in list(stats["gear"].keys()):
                if gear_key not in stat_list:
                    stat_list.append(gear_key)
            if "mods" in stats:
                for mod_key in list(stats["mods"].keys()):
                    if mod_key not in stat_list:
                        stat_list.append(mod_key)
                gs_stats["mods"] = {}
                gs_stats["mods"].update(stats["mods"])
            for id in stat_list:
                flat_stat_id = id
                if id == "22" or id == "21":
                    flat_stat_id = int(id) - 7
                elif id == "35" or id == "36":
                    flat_stat_id = int(id) + 4
                if str(flat_stat_id) not in gs_stats["final"]:
                    gs_stats["final"][str(flat_stat_id)] = 0.0
                mod_val: float = 0
                if "mods" in stats:
                    mod_val = stats["mods"].get(id, 0.0)
                gs_stats["final"][str(flat_stat_id)] += (
                        stats["base"].get(id, 0.0 + stats["gear"].get(id, 0.0)) + mod_val
                )
        else:  # Ship
            for crew_stat in list(stats["crews"].keys()):
                if crew_stat not in stat_list:
                    stat_list.append(str(crew_stat))
            gs_stats["crew"].update(stats["crew"])

            for stat_list_id in stat_list:
                gs_stats["final"][stat_list_id] = gs_stats.get(
                    stat_list_id, 0.0
                )  # Make sure 'stat_list_id' exists
                mod_val = 0
                if "mods" in stats:
                    mod_val = stats["mods"].get(stat_list_id, 0.0)
                gs_stats["final"][stat_list_id] += (
                                                           stats["base"].get(stat_list_id, 0.0)
                                                           + stats["crew"].get(stat_list_id, 0.0)
                                                   ) + mod_val
        stats = gs_stats
        logger.debug(f"Stats: {stats}")
    return stats


def _scale_stat_value(stat_id: int or str, value: float) -> float:
    """Convert stat value from displayed value to "unscaled" value used in calculations"""
    if isinstance(stat_id, str):
        stat_id = int(stat_id)
    if stat_id in [1, 5, 28, 41, 42]:
        return value * 1e8
    else:
        return value * 1e6


def _floor(value: float, digits: int = 0) -> float:
    precision = float(("1e" + str(digits)))
    return math_floor(value / precision) * precision


def _convert_flat_def_to_percent(
        value: float, /, *, level: int = 85, scale: float = 1.0, is_ship: bool = False
) -> float:
    val = value / scale
    level_effect = level * 7.5
    if is_ship:
        level_effect = 300 + level * 5
    return (val / (level_effect + val)) * scale


def _convert_flat_crit_to_percent(value: float, /, *, scale: float = 1.0) -> float:
    return ((value / scale / 2400) + 0.1) * scale


def _convert_flat_acc_to_percent(value: float, /, *, scale: float = 1.0) -> float:
    return (value / scale / 1200) * scale


def _convert_flat_crit_avoid_to_percent(
        value: float, /, *, scale: float = 1.0
) -> float:
    return (value / scale / 2400) * scale


class StatCalcException(Exception):
    """Generic StatsCalc exception"""

    pass


class StatCalcRuntimeError(RuntimeError):
    """Generic StatsCalc RuntimeError exception"""

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

    _ALLOWED_OPTIONS = frozenset(
        [
            "withoutModCalc",
            "percentVals",
            "useMax",
            "scaled",
            "unscaled",
            "gameStyle",
            "statIDs",
            "enums",
            "noSpace",
        ]
    )

    for option in _ALLOWED_OPTIONS:
        _OPTIONS[option] = False

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

    _COMLINK: swgoh_comlink.SwgohComlink = swgoh_comlink.SwgohComlink()

    @property
    def is_initialized(self) -> bool:
        """Return current state of StatCalc"""
        return self._INITIALIZED

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
    def _load_unit_name_map(cls) -> bool:
        """Create unit_name_map dictionary"""
        latest_game_version = cls._COMLINK.get_latest_game_data_version()
        loc_bundle = cls._COMLINK.get_localization_bundle(
            id=latest_game_version["language"]
        )
        loc_bundle_decoded = base64.b64decode(loc_bundle["localizationBundle"])
        logger.info("Decompressing data stream...")
        zip_obj = zipfile.ZipFile(io.BytesIO(loc_bundle_decoded))
        lang_file_name = f"Loc_{cls._LANGUAGE.upper()}.txt"
        with zip_obj.open(lang_file_name) as lang_file:
            contents = lang_file.readlines()
        cls._UNIT_NAME_MAP = utils.create_localized_unit_name_dictionary(contents)
        if len(cls._UNIT_NAME_MAP) > 0:
            return True
        else:
            return False

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
        if not utils.validate_path(language_file):
            logger.error(
                f"Error while validating language file data path ({language_file})"
            )
            return False
        try:
            with open(language_file) as fn:
                cls._STAT_NAME_MAP = json.load(fn)
        except OSError as os_error:
            logger.exception(f"Error while loading {language_file}. [{os_error}]")
            return False
        else:
            return True

    @classmethod
    @utils.func_debug_logger
    def _rename_stats(cls, stats: dict, options: dict) -> dict:
        logger.info(f"Renaming stats ... ")
        if options.get('language'):
            rn_stats = {}
            for stat_type in stats:
                rn_stats[stat_type] = {}
                for stat_id, value in stats[stat_type].items():
                    stat_name = options['language'].get(stat_id,
                                                        stat_id)  # leave as stat_id if no localization string is found
                    if options.get('no_space'):
                        stat_name = stat_name.replace(' ', '')  # remove spaces
                        stat_name = stat_name[0].lower() + stat_name[1:]  # ensure first letter is lower case
                    rn_stats[stat_type][stat_name] = value
            stats = rn_stats
        logger.info(f"Done renaming stats")
        return stats

    @classmethod
    @utils.func_debug_logger
    def _calculate_base_stats(cls, stats: dict, level: int, base_id: str) -> dict:
        """Calculate bonus primary stats from growth modifiers"""
        logger.info("Calculating base stats")
        logger.debug(f"{stats=}")
        for i in ["2", "3", "4"]:
            logger.info(f"{stats['base'][i]=} before")
            logger.info(f"Adding math.floor({stats['growthModifiers'][i]} * {level}, 8")
            stats["base"][i] += math.floor(stats["growthModifiers"][i] * level, 1e8) / 1e8
            logger.info(f"{stats['base'][i]=} after")
        if stats["base"].get("61"):
            mastery_modifier_key = cls._UNIT_DATA[base_id]["masteryModifierID"]
            try:
                mms = cls._CR_TABLES[mastery_modifier_key]
                for stat_id, modifer in mms.items():
                    stats['base'][stat_id] = stats['base'].get(stat_id, 0) + stats['base']["61"] * modifer
            except KeyError as e_str:
                logger.error(
                    f"Unable to find mastery modifier key [{mastery_modifier_key}] in crTable."
                )
                logger.error(e_str)
                logger.error(f"crTable keys: {sorted(list(cls._CR_TABLES.keys()))}")

        # Calculate effects of primary stats on secondary stats
        stats['base']['1'] = stats['base'].get('1', 0) + stats['base']['2'] * 18  # Health += STR * 18
        stats['base']['6'] = math.floor((stats['base'].get('6', 0) + stats['base'][
            unit_data[base_id]['primaryStat']] * 1.4) * 1e8) / 1e8  # Ph. Damage += MainStat * 1.4
        stats['base']['7'] = math.floor(
            (stats['base'].get('7', 0) + stats['base']['4'] * 2.4) * 1e8) / 1e8  # Sp. Damage += TAC * 2.4
        stats['base']['8'] = math.floor((stats['base'].get('8', 0) + stats['base']['2'] * 0.14 +
                                         stats['base']['3'] * 0.07) * 1e8) / 1e8  # Armor += STR*0.14 + AGI*0.07
        stats['base']['9'] = math.floor(
            (stats['base'].get('9', 0) + stats['base']['4'] * 0.1) * 1e8) / 1e8  # Resistance += TAC * 0.1
        stats['base']['14'] = math.floor(
            (stats['base'].get('14', 0) + stats['base']['3'] * 0.4) * 1e8) / 1e8  # Ph. Crit += AGI * 0.4

        # add hard-coded minimums or potentially missing stats
        stats["base"]["12"] = stats["base"].get("12", 0) + (24 * 1e8)
        stats["base"]["13"] = stats["base"].get("13", 0) + (24 * 1e8)
        stats["base"]["15"] = stats["base"].get("15", 0)
        stats["base"]["16"] = stats["base"].get("16", 0) + (150 * 1e6)
        stats["base"]["18"] = stats["base"].get("18", 0) + (15 * 1e8)
        logger.debug(f"Base stat calculated: {stats=}")
        return stats

    @classmethod
    @utils.func_debug_logger
    def _calculate_mod_stats(cls, base_stats: dict, char: dict = None) -> dict or None:
        logger.info("Calculating mod stats ... ")
        if not char.get('mods') and not char.get('equippedStatMod'):
            logger.warning("Mod list is missing or empty. Returning empty")
            return {}

        set_bonuses = {}
        raw_mod_stats = {}

        def scale_stat_value(stat_id, value):
            # convert stat value from displayed value to "unscaled" value used in calculations
            if stat_id in [1, 5, 28, 41, 42]:
                # Flat stats
                return value * 1e8
            else:
                # Percent stats
                return value * 1e6

        if char.get('mods'):
            for mod in char['mods']:
                if not mod.get('set'):
                    continue  # ignore if empty mod (/units format only)

                # add to set bonuses counters (same for both formats)
                if mod['set'] in set_bonuses:
                    # set bonus already found, increment
                    set_bonuses[mod['set']]['count'] += 1
                    if mod['level'] == 15:
                        set_bonuses[mod['set']]['maxLevel'] += 1
                else:
                    # new set bonus, create object
                    set_bonuses[mod['set']] = {'count': 1, 'maxLevel': 1 if mod['level'] == 15 else 0}

                # add Primary/Secondary stats to data
                if mod.get('stat'):
                    # using /units format
                    for stat in mod['stat']:
                        raw_mod_stats[stat[0]] = raw_mod_stats.get(stat[0], 0) + scale_stat_value(stat[0], stat[1])
                else:
                    # using /player.roster format
                    stat = mod['primaryStat']
                    i = 0
                    while True:
                        raw_mod_stats[stat['unitStat']] = raw_mod_stats.get(stat['unitStat'], 0) + scale_stat_value(
                            stat['unitStat'], stat['value'])
                        if i >= len(mod['secondaryStat']):
                            break
                        stat = mod['secondaryStat'][i]
                        i += 1

        elif char.get('equippedStatMod'):
            for mod in char['equippedStatMod']:
                set_id = int(mod['definitionId'][0])
                if set_id in set_bonuses:
                    # set bonus already found, increment
                    set_bonuses[set_id]['count'] += 1
                    if mod['level'] == 15:
                        set_bonuses[set_id]['maxLevel'] += 1
                else:
                    # new set bonus, create object
                    set_bonuses[set_id] = {'count': 1, 'maxLevel': 1 if mod['level'] == 15 else 0}

                # add Primary/Secondary stats to data
                stat = mod['primaryStat']['stat']
                i = 0
                while True:
                    raw_mod_stats[stat['unitStatId']] = float(stat['unscaledDecimalValue']) + raw_mod_stats.get(
                        stat['unitStatId'], 0)
                    if i >= len(mod['secondaryStat']):
                        break
                    stat = mod['secondaryStat'][i]['stat']
                    i += 1
        else:
            # return empty dictionary if no mods
            return {}

        # add stats given by set bonuses
        for set_id, set_bonus in set_bonuses.items():
            set_def = mod_set_data[set_id]
            count, max_count = set_bonus['count'], set_bonus['maxLevel']
            multiplier = (count // set_def['count']) + (max_count // set_def['count'])
            raw_mod_stats[set_def['id']] = raw_mod_stats.get(set_def['id'], 0) + (set_def['value'] * multiplier)

        # calculate actual stat bonuses from mods
        mod_stats = {}
        for stat_id, value in raw_mod_stats.items():
            stat_id = int(stat_id)
            if stat_id == 41:  # Offense
                mod_stats[6] = mod_stats.get(6, 0) + value  # Ph. Damage
                mod_stats[7] = mod_stats.get(7, 0) + value  # Sp. Damage
            elif stat_id == 42:  # Defense
                mod_stats[8] = mod_stats.get(8, 0) + value  # Armor
                mod_stats[9] = mod_stats.get(9, 0) + value  # Resistance
            elif stat_id == 48:  # Offense %
                mod_stats[6] = math.floor(mod_stats.get(6, 0) + (base_stats[6] * 1e-8 * value), 8)  # Ph. Damage
                mod_stats[7] = math.floor(mod_stats.get(7, 0) + (base_stats[7] * 1e-8 * value), 8)  # Sp. Damage
            elif stat_id == 49:  # Defense %
                mod_stats[8] = math.floor(mod_stats.get(8, 0) + (base_stats[8] * 1e-8 * value), 8)  # Armor
                mod_stats[9] = math.floor(mod_stats.get(9, 0) + (base_stats[9] * 1e-8 * value), 8)  # Resistance
            elif stat_id == 53:  # Crit Chance
                mod_stats[21] = mod_stats.get(21, 0) + value  # Ph. Crit Chance
                mod_stats[22] = mod_stats.get(22, 0) + value  # Sp. Crit Chance
            elif stat_id == 54:  # Crit Avoid
                mod_stats[35] = mod_stats.get(35, 0) + value  # Ph. Crit Avoid
                mod_stats[36] = mod_stats.get(36, 0) + value  # Ph. Crit Avoid
            elif stat_id == 55:  # Health %
                mod_stats[1] = math.floor(mod_stats.get(1, 0) + (base_stats[1] * 1e-8 * value), 8)  # Health
            elif stat_id == 56:  # Protection %
                mod_stats[28] = math.floor(mod_stats.get(28, 0) + (base_stats.get(28, 0) * 1e-8 * value),
                                           8)  # Protection may not exist in base
            elif stat_id == 57:  # Speed %
                mod_stats[5] = math.floor(mod_stats.get(5, 0) + (base_stats[5] * 1e-8 * value), 8)  # Speed
            else:
                # other stats add like flat values
                mod_stats[stat_id] = mod_stats.get(stat_id, 0) + value

        return mod_stats

    @classmethod
    def _get_crew_rating(crew):
        def calculate_character_cr(crew_rating, char):
            crew_rating += cr_tables['unitLevelCR'][char['level']] + cr_tables['crewRarityCR'][char['rarity']]
            crew_rating += cr_tables['gearLevelCR'][char['gear']]
            crew_rating += cr_tables['gearPieceCR'][char['gear']] * len(char.get('equipped', []))

            crew_rating = functools.reduce(lambda cr, skill: cr + get_skill_crew_rating(skill), char['skills'],
                                           crew_rating)

            if 'mods' in char:
                crew_rating = functools.reduce(
                    lambda cr, mod: cr + cr_tables['modRarityLevelCR'][mod['pips']][mod['level']], char['mods'],
                    crew_rating)
            elif 'equippedStatMod' in char:
                crew_rating = functools.reduce(
                    lambda cr, mod: cr + cr_tables['modRarityLevelCR'][int(mod['definitionId'][1])][mod['level']],
                    char['equippedStatMod'], crew_rating)

            if 'relic' in char and char['relic']['currentTier'] > 2:
                crew_rating += cr_tables['relicTierCR'][char['relic']['currentTier']]
                crew_rating += char['level'] * cr_tables['relicTierLevelFactor'][char['relic']['currentTier']]

            return crew_rating

        total_cr = functools.reduce(calculate_character_cr, crew, 0)
        return total_cr

    @classmethod
    def _get_skill_crew_rating(skill):
        return cr_tables['abilityLevelCR'][skill['tier']]

    @classmethod
    def _get_crewless_crew_rating(ship):
        # temporarily uses hard-coded multipliers, as the true in-game formula remains a mystery.
        # but these values have experimentally been found accurate for the first 3 crewless ships:
        #     (Vulture Droid, Hyena Bomber, and BTL-B Y-wing)
        cr = math.floor(
            cr_tables.crew_rarity_cr[ship.rarity] +
            3.5 * cr_tables.unit_level_cr[ship.level] +
            get_crewless_skills_crew_rating(ship.skills)
        )
        return cr

    @classmethod
    def _get_crewless_skills_crew_rating(skills):
        return sum(
            (0.696 if re.match(r'^hardware', skill['id']) else 2.46) * cr_tables.ability_level_cr[skill['tier']]
            for skill in skills
        )

    @classmethod
    @utils.func_debug_logger
    def _get_char_raw_stats(cls, char: dict) -> dict:
        """Generate raw stats for character"""
        # Construction stats dictionary using game data for character based on specifics of character data provided
        stats: dict = {
            "base": cls._UNIT_DATA[char["defId"]]["gearLvl"][str(char["currentTier"])][
                "stats"
            ].copy(),
            "growthModifiers": copy.deepcopy(
                cls._UNIT_DATA[char["defId"]]["growthModifiers"][
                    str(char["currentRarity"])
                ]
            ),
            "gear": {},
        }
        logger.info(f"stats: {stats=}")
        # Calculate stats from current gear
        if len(char["equipment"]) != 0:
            logger.info(f"Calculating stats for {char['defId']} equipment ")
            for equipment_piece in char["equipment"]:
                equipmentId = equipment_piece["equipmentId"]
                logger.info(f"Searching for {equipmentId} in game gearData ...")
                if equipmentId not in cls._GEAR_DATA:
                    logger.info(f"{equipmentId=} not found in game gearData ...")
                    continue
                equipment_stats = cls._GEAR_DATA[equipmentId]["stats"].copy()
                for equipment_stat_id in equipment_stats.keys():
                    if equipment_stat_id in ["2", "3", "4"]:
                        # Primary stat applies before mods
                        stats["base"][equipment_stat_id] += stats["base"][
                            equipment_stat_id
                        ]
                    else:
                        # Secondary stat applies after mods
                        stats["gear"][equipment_stat_id] = equipment_stats[
                                                               equipment_stat_id
                                                           ] + stats["gear"].get(equipment_stat_id, 0)
        else:
            logger.info(f"No equipment for {char['defId']}")

        if "relic" in char and char["relic"]["currentTier"] > 2:
            current_relic_tier: int = char["relic"]["currentTier"]
            logger.info(
                f"Calculating stats for {char['defId']} relic level: {current_relic_tier - 2} "
            )
            # Calculate stats from relics
            relic_tier_data = cls._RELIC_DATA[
                cls._UNIT_DATA[char["defId"]]["relic"][str(current_relic_tier)]
            ]
            for r_id in list(relic_tier_data["stats"].keys()):
                stats["base"][r_id] = relic_tier_data["stats"][r_id] + stats[
                    "base"
                ].get(r_id, 0)
                logger.info(f"{stats['base'][r_id]=}")
            for g_id in list(relic_tier_data["gms"].keys()):
                stats["growthModifiers"][g_id] += relic_tier_data["gms"][g_id]
                logger.info(f"{stats['growthModifiers'][g_id]=}")
        else:
            logger.info(f"No relic information for {char['defId']}")
        logger.info(f"Stat results for {char['defId']}: {stats}")
        return stats

    @classmethod
    def _get_ship_raw_stats(ship, crew):
        # ensure crew is the correct crew
        if len(crew) != len(unit_data[ship['defId']]['crew']):
            raise ValueError(f"Incorrect number of crew members for ship {ship['defId']}.")

        for char in crew:
            if char['defId'] not in unit_data[ship['defId']]['crew']:
                raise ValueError(f"Unit {char['defId']} is not in {ship['defId']}'s crew.")

        # if still here, crew is good -- go ahead and determine stats
        crew_rating = get_crewless_crew_rating(ship) if len(crew) == 0 else get_crew_rating(crew)

        stats = {
            'base': dict(unit_data[ship['defId']]['stats']),
            'crew': {},
            'growth_modifiers': dict(unit_data[ship['defId']]['growthModifiers'][ship['rarity']])
        }

        stat_multiplier = cr_tables['shipRarityFactor'][ship['rarity']] * crew_rating

        for stat_id, stat_value in unit_data[ship['defId']]['crewStats'].items():
            # stats 1-15 and 28 all have final integer values
            # other stats require decimals -- shrink to 8 digits of precision through 'unscaled' values this calculator uses
            precision = 8 if int(stat_id) < 16 or int(stat_id) == 28 else 0
            stats['crew'][stat_id] = math.floor(stat_value * stat_multiplier * (10 ** precision)) / (10 ** precision)

        return stats

    @classmethod
    @utils.func_debug_logger
    def calc_char_stats(
            cls,
            char: dict,
            /,
            *,
            options: list or dict = None,
            use_values: dict = None,
            language: str = "eng_us",
            set_global_options: bool = False,
    ) -> dict:
        """Calculate stats for a single character based upon arguments provided.

        Args:
            char (dict): Character object from player roster or game_data['unit']
            options (dict|list): Dictionary or list of options to enable
            use_values (dict): See example below
            language (str): Localization language stat key translations
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
            raise StatCalcException(
                "StatCalc is not initialized. Please perform the initialization first."
            )

        if "defId" not in char:
            if "definitionId" in char and ":" in char["definitionId"]:
                char["defId"] = char["definitionId"].split(":")[0]
            else:
                logger.error(f"Invalid character [{char}].")
                return {}

        logger.info(f"Calculating stats for {char['defId']}")

        cls._process_language(language)
        if options is not None:
            options = cls._process_options(options, set_global=set_global_options)
        else:
            options = cls._OPTIONS

        char = cls._use_values_char(char, use_values)

        stats = cls._get_char_raw_stats(char)
        stats = cls._calculate_base_stats(stats, char["currentLevel"], char["defId"])
        if options is not None:
            if len(char["equippedStatMod"]) > 0 and not options["withoutModCalc"]:
                stats = cls._calculate_mod_stats(stats["base"], char["equippedStatMod"])
        stats = _format_stats(stats, int(char["currentLevel"]), options)
        stats = cls._rename_stats(stats, options)
        return stats

    @classmethod
    def calc_ship_stats(
            cls,
            ship: dict,
            crew: list,
            /,
            *,
            options: list or dict = None,
            use_values: dict = None,
            language: str = None,
    ) -> dict:
        """

        Args:
            ship (dict): Ship object from player roster
            crew (list): List of ship crew members
            options (dict|list): Dictionary or list of options to enable
            use_values (dict): See example from calc_char_stats
            language (str): Localization language stat key translations

        Returns:
            dict: Ship object with stats calculated

        """
        if options is None:
            options = {}

        try:
            ship, crew = _use_values_ship(unit, crew_member, options.get('useValues'))

            stats = {}
            if not options.get('onlyGP'):
                stats = get_ship_raw_stats(ship, crew)
                stats = calculate_base_stats(stats, ship.level, ship.def_id)
                stats = format_stats(stats, ship.level, options)
                stats = rename_stats(stats, options)

                unit.stats = stats

            if options.get('calcGP') or options.get('onlyGP'):
                unit.gp = _calc_ship_gp(ship, crew)
                stats['gp'] = unit.gp

            return stats
        except Exception as e:
            print(f"Error on ship '{ship['defId']}':\n{json.dumps(ship)}")
            print(e)
            raise

    @classmethod
    @utils.func_debug_logger
    def _set_skills(cls, unit_id: str, val: str) -> list:
        logger.info(f"Setting skills for {unit_id}")
        if val == "max":
            return [
                {"id": d["id"], "tier": d["maxTier"]}
                for d in StatCalc._UNIT_DATA[unit_id]["skills"]
            ]
        elif val == "maxNoZeta":
            return [
                {"id": d["id"], "tier": d["maxTier"] - (1 if d["isZeta"] else 0)}
                for d in StatCalc._UNIT_DATA[unit_id]["skills"]
            ]
        elif isinstance(val, int):
            return [
                {"id": d["id"], "tier": min(val, d["maxTier"])}
                for d in StatCalc._UNIT_DATA[unit_id]["skills"]
            ]
        else:
            return val

    @classmethod
    def _use_values_ships(cls, ship: dict, crew: list, use_values: dict = None):
        if not hasattr(ship, 'defId'):
            ship = {
                'defId': ship.definition_id.split(":")[0],
                'rarity': ship.current_rarity,
                'level': ship.current_level,
                'skills': [{'id': skill.id, 'tier': skill.tier + 2} for skill in ship.skill]
            }
            crew = [{
                'defId': c.definition_id.split(":")[0],
                'rarity': c.current_rarity,
                'level': c.current_level,
                'gear': c.current_tier,
                'equipped': c.equipment,
                'equipped_stat_mod': c.equipped_stat_mod,
                'relic': c.relic,
                'skills': [{'id': skill.id, 'tier': skill.tier + 2} for skill in c.skill],
                'gp': c.gp
            } for c in crew]

        if not use_values:
            return {'ship': ship, 'crew': crew}

        ship = {
            'defId': ship['defId'],
            'rarity': use_values['ship'].get('rarity', ship['rarity']),
            'level': use_values['ship'].get('level', ship['level']),
            'skills': set_skills(ship['defId'], use_values['ship'].get('skills', ship['skills']))
        }

        chars = []
        for char_id in unit_data[ship['defId']]['crew']:
            char = next((cmem for cmem in crew if cmem['defId'] == char_id), None)
            char = {
                'defId': char_id,
                'rarity': use_values['crew'].get('rarity', char['rarity']),
                'level': use_values['crew'].get('level', char['level']),
                'gear': use_values['crew'].get('gear', char['gear']),
                'equipped': char['gear'],
                'skills': set_skills(char_id, use_values['crew'].get('skills', char['skills'])),
                'mods': char['mods'],
                'relic': {'current_tier': use_values['crew']['relic']} if use_values['crew'].get('relic') else char[
                    'relic']
            }

            if use_values['crew'].get('equipped') == "all":
                char['equipped'] = [
                    {'equipmentId': gear_id} for gear_id in unit_data[char_id]['gear_lvl'][char['gear']]['gear']
                    if int(gear_id) < 9990
                ]
            elif use_values['crew'].get('equipped') == "none":
                char['equipped'] = []
            elif isinstance(use_values['crew'].get('equipped'), list):
                char['equipped'] = [
                    unit_data[char_id]['gear_lvl'][char['gear']]['gear'][int(slot) - 1]
                    for slot in use_values['crew']['equipped']
                ]
            elif use_values['crew'].get('equipped'):
                char['equipped'] = [{} for _ in range(use_values['crew']['equipped'])]

            if use_values['crew'].get('mod_rarity') or use_values['crew'].get('mod_level'):
                char['mods'] = [
                    {
                        'pips': use_values['crew'].get('mod_rarity', DEFAULT_MOD_PIPS),
                        'level': use_values['crew'].get('mod_level', DEFAULT_MOD_LEVEL),
                        'tier': use_values['crew'].get('mod_tier', DEFAULT_MOD_TIER)
                    }
                    for _ in range(6)
                ]

            chars.append(char)

        return {'ship': ship, 'crew': chars}

    @classmethod
    @utils.func_debug_logger
    def _use_values_char(cls, char: dict, use_values: dict = None):
        logger.info(f"Executing _use_values_char() ...")

        # Handle newer Comlink style raw data input
        if "defId" not in char:
            char = {
                "defId": char["definitionId"].split(":")[0],
                "rarity": char["currentRarity"],
                "level": char["currentLevel"],
                "gear": char["currentTier"],
                "equipped": char["equipment"],
                "equippedStatMod": char["equippedStatMod"],
                "relic": char["relic"],
                "skills": char["skill"].copy(),
            }

        # The use_values option has not been set so the char object does not need to be modified
        if use_values is None:
            logger.info(f"No 'use_values' argument provided. Returning.")
            return char

        unit_skills = []
        skills = cls._UNIT_DATA[char["defId"]]["skills"]
        for skill in skills:
            unit_skills.append({"id": skill["id"], "tier": char["skills"]})

        # use_values values should take precedence so that they can be used to model how the stats for a
        # current character would change if upgraded according to the provided values.
        unit = {
            "defId": char["defId"],
            "rarity": (
                use_values["char"]["rarity"]
                if "rarity" in use_values["char"]
                else char["rarity"]
            ),
            "level": (
                use_values["char"]["level"]
                if "level" in use_values["char"]
                else char["level"]
            ),
            "gear": (
                use_values["char"]["gear"]
                if "gear" in use_values["char"]
                else char["gear"]
            ),
            "equipped": char["gear"],
            "mods": char["mods"],
            "equippedStatMod": char["equippedStatMod"],
            "relic": {
                "currentTier": (
                    use_values["char"]["relic"]
                    if "relic" in use_values["char"]
                    else char["relic"]
                )
            },
        }

        set_skills_arg = []
        if "skills" in use_values["char"]:
            set_skills_arg = use_values["char"]["skills"]
        elif "skills" in char:
            set_skills_arg = char["skills"]
        unit["skills"]: cls._set_skills(char["defId"], set_skills_arg)

        if any(
                [
                    mod_element in use_values
                    for mod_element in ["modRarity", "modLevel", "modTier"]
                ]
        ):
            unit["mods"] = []
            mod_vals = {}
            mod_defaults = {
                "modRarity": cls._DEFAULT_MOD_PIPS,
                "modLevel": cls._DEFAULT_MOD_LEVEL,
                "modTier": cls._DEFAULT_MOD_TIER,
            }
            for i in range(6):
                if use_values and "char" in use_values:
                    for mod_element in ["modRarity", "modLevel", "modTier"]:
                        if mod_element in use_values["char"]:
                            mod_vals[mod_element] = use_values["char"][mod_element]
                        else:
                            mod_vals[mod_element] = mod_defaults[mod_element]
                unit["mods"].append(
                    {
                        "pips": mod_vals["modRarity"],
                        "level": mod_vals["modLevel"],
                        "tier": mod_vals["modTier"],
                    }
                )

        if use_values["char"]["equipped"] == "all":
            unit["equipped"] = []
            for gear_id in cls._UNIT_DATA[unit["definitionId"]]["gearLvl"][
                unit["gear"]
            ]["gear"]:
                if int(gear_id) < 9990:
                    unit["equipped"].append({"equipmentId": gear_id})
        elif use_values["char"]["equipped"] == "none":
            unit["equipped"] = []
        elif isinstance(cls._USE_VALUES["char"]["equipped"], list):
            unit["equipped"] = []
            for gear_slot in use_values["char"]["equipped"]:
                equip_id = use_values[unit["definitionId"]]["gearLvl"][unit["gear"]][
                    "gear"
                ][str(gear_slot - 1)]
                unit["equipped"].append(
                    {"equipmentId": equip_id, "slot": int(gear_slot) - 1}
                )

        return unit

    @classmethod
    def _calc_char_gp(cls, char):
        gp = cls._GP_TABLES['unitLevelGP'][char['level']]
        gp += cls._GP_TABLES['unitRarityGP'][char['rarity']]
        gp += cls._GP_TABLES['gearLevelGP'][char['gear']]

        # Game tables for current gear include the possibility of different GP per slot.
        # Currently, all values are identical across each gear level, so a simpler method is possible.
        # But that could change at any time.
        gp = sum(gp_tables['gearPieceGP'][char['gear']][piece['slot']] for piece in char['equipped']) + gp

        gp = sum(get_skill_gp(char['defId'], skill) for skill in char['skills']) + gp

        if char.get('purchasedAbilityId'):
            gp += len(char['purchasedAbilityId']) * gp_tables['abilitySpecialGP']['ultimate']

        if 'mods' in char:
            gp = sum(gp_tables['modRarityLevelTierGP'][mod['pips']][mod['level']][mod['tier']] for mod in
                     char['mods']) + gp
        elif 'equipped_stat_mod' in char:
            gp = sum(
                gp_tables['modRarityLevelTierGP'][int(mod['definitionId'][1])][mod['level']][mod['tier']] for mod
                in char['equippedStatMod']) + gp

        if char.get('relic') and char['relic']['current_tier'] > 2:
            gp += gp_tables['relicTierGP'][char['relic']['currentTier']]
            gp += char['level'] * gp_tables['relicTierLevelFactor'][char['relic']['currentTier']]

        return math.floor(gp * 1.5)

    @classmethod
    def _calc_ship_gp(cls, ship, crew=None):
        if crew is None:
            crew = []

        # ensure crew is the correct crew
        if len(crew) != len(unit_data[ship['defId']]['crew']):
            raise ValueError(f"Incorrect number of crew members for ship {ship['defId']}.")

        for char in crew:
            if char['defId'] not in unit_data[ship['defId']]['crew']:
                raise ValueError(f"Unit {char['defId']} is not in {ship['defId']}'s crew.")

        if len(crew) == 0:  # crewless calculations
            gps = get_crewless_skills_gp(ship['defId'], ship['skills'])
            gps['level'] = gp_tables['unit_level_gp'][ship['level']]
            gp = (gps['level'] * 3.5 + gps['ability'] * 5.74 + gps['reinforcement'] * 1.61) * \
                 gp_tables['ship_rarity_factor'][ship['rarity']]
            gp += gps['level'] + gps['ability'] + gps['reinforcement']
        else:  # normal ship calculations
            gp = sum(c['gp'] for c in crew)
            gp *= gp_tables['ship_rarity_factor'][ship['rarity']] * gp_tables['crew_size_factor'][
                len(crew)]  # multiply crewPower factors before adding other GP sources
            gp += gp_tables['unit_level_gp'][ship['level']]
            gp = sum(get_skill_gp(ship['defId'], skill) for skill in ship['skills']) + gp

        return math.floor(gp * 1.5)

    @classmethod
    def _get_crewless_skills_gp(cls, id, skills):
        a = 0
        r = 0
        for skill in skills:
            o_tag = next(
                (s['powerOverrideTags'][skill['tier']] for s in unit_data[id]['skills'] if s['id'] == skill['id']),
                None)
            if o_tag and o_tag.startswith('reinforcement'):
                r += gp_tables['abilitySpecialGP'][o_tag]
            else:
                a += gp_tables['abilitySpecialGP'][o_tag] if o_tag else gp_tables['abilityLevelGP'][skill['tier']]

        return {'ability': a, 'reinforcement': r}

    @classmethod
    def _get_skill_gp(cls, id, skill):
        o_tag = next((s['powerOverrideTags'][skill['tier']] for s in unit_data[id]['skills'] if s['id'] == skill['id']),
                     None)
        if o_tag:
            return cls._GP_TABLES['abilitySpecialGP'][o_tag]
        else:
            return cls._GP_TABLES['abilityLevelGP'].get(skill['tier'], 0)

    @classmethod
    @utils.func_debug_logger
    def _process_language(cls, language: str = None) -> None:
        """Update localized language selection for statIds"""
        logger.info(f"Processing language: {language}")
        languages: list = DataBuilder.get_languages()
        if language is not None and language in languages:
            cls._LANGUAGE = language
        else:
            logger.warning(
                f"Unknown language: {language}, setting default language to {cls._LANGUAGE}"
            )

    @classmethod
    @utils.func_debug_logger
    def _process_options(cls, options: list or dict, set_global: bool = False) -> dict:
        """Update class instance properties based on flags provided"""
        logger.info(f"Processing options: type({type(options)})")
        new_options = cls._OPTIONS.copy()
        if isinstance(options, list):
            for option in options:
                if option in cls._ALLOWED_OPTIONS:
                    logger.info(f"Setting cls._OPTIONS['{option}'] to True.")
                    new_options[option] = True
                    if set_global:
                        cls._OPTIONS[option] = True
                else:
                    logger.warning(f"Unknown option: {option}")
        elif isinstance(options, dict):
            for option in list(options.keys()):
                if option in cls._ALLOWED_OPTIONS:
                    logger.info(f"Setting cls._OPTIONS[{option}] to {options[option]}.")
                    new_options[option] = options[option]
                    if set_global:
                        cls._OPTIONS[option] = options[option]
                else:
                    logger.warning(f"Unknown option: {option}")
        else:
            logger.exception(
                f"Invalid options argument: expected type list() or dict(), got {type(options)}"
            )
            raise StatCalcRuntimeError(
                f"Invalid 'options' value. Expected type list() or dict() but received {type(options)}"
            )
        logger.info(f"Returning {new_options=}")
        return new_options

    @classmethod
    @utils.func_debug_logger
    def _process_use_values_settings(cls, use_values: dict) -> None:
        """Break options object into parts and validate settings"""
        if not isinstance(use_values, dict):
            raise StatCalcRuntimeError(
                f"Invalid object type ({type(use_values)}) for 'options' attribute. Should be dict."
            )
        for key in list(use_values.keys()):
            if key not in ["char", "ship", "crew"]:
                del use_values[key]
        cls._USE_VALUES = copy.deepcopy(use_values)

    @classmethod
    @utils.func_debug_logger
    def calc_roster_stats(
            cls,
            units: list[dict],
            options: list[str] = None,
            use_values: dict = None,
            language: str = "eng_us",
    ) -> list:
        """
        Calculate units stats from SWGOH roster game data

        :param units: A list containing the value of the 'rosterUnit' key within the SwgohComlink.get_player() result
        :type units: list
        :param options: A list of strings indicating the optional flags affecting how data is return to enable
        :type options: list
        :param use_values: A dictionary containing elements for 'char', 'ship', and 'crew' for overriding defaults
        :type use_values: dict
        :param language: A string indicating which language to use for localization of statIds
        :type language: str

        :return: The same object format provided in the units parameter with additional fields added containing the
                 results of the stat calculations
        :rtype: list
        """

        if not cls.is_initialized:
            raise StatCalcException(
                "StatCalc is not initialized. Please perform the initialization first."
            )

        cls._process_options(options)
        cls._process_use_values_settings(use_values)
        if language is not None:
            cls._process_language(language)

        if isinstance(units, list):
            ships = []
            crew = {}
            for unit in units:
                defId = unit["definitionId"].split(":")[0]
                unit["defId"] = defId
                if not unit or not cls._UNIT_DATA[defId]:
                    logger.warning(f"Unable to find {defId} in game data.")
                    return []
                if (
                        isinstance(cls._UNIT_DATA[defId]["combatType"], int)
                        and cls._UNIT_DATA[defId]["combatType"] == 2
                ) or (
                        isinstance(cls._UNIT_DATA[defId]["combatType"], str)
                        and cls._UNIT_DATA[defId]["combatType"] == "SHIP"
                ):
                    ships.append(unit)
                else:
                    crew[defId] = unit
                    calculated_char_stats = cls.calc_char_stats(
                        unit, use_values=use_values, options=options, language=language
                    )
            for ship in ships:
                defId = ship["definitionId"].split(":")[0]
                if not ship or not cls._UNIT_DATA[defId]:
                    logger.warning(f"Unable to find {defId} in game data.")
                    return []
                # TODO: check the code below for proper functionality
                crw = [
                    id
                    for id in cls._UNIT_DATA[defId]["crew"]["id"]
                    if crew["id"] == cls._UNIT_DATA[defId]["crew"]["id"]
                ]
                calculated_ship_stats = cls.calc_ship_stats(ship, crw)
        else:
            raise StatCalcRuntimeError(
                f'[calc_roster_stats] Unsupported data type [{type(units)}] for "unit" parameter'
            )
        return []

    @classmethod
    def initialize(cls, **kwargs) -> bool:
        """Prepare StatCalc environment for first use. Providing keyword arguments can override default settings.

        Keyword Args:
            game_data dict: Defaults to None. Will autoload if not provided.
            default_mod_tier int: Defaults to 5. Should not need to be set unless the game changes mods and some point.
            default_mod_level int: Defaults to 15. Should not need to be set unless the game mod system changes.
            default_mod_pips int: Defaults to 6. Should not need to be set unless the game mod system changes.

        Returns:
            bool: True if initialization is successful, False otherwise

        """
        # Set allowed parameters and values for argument checking
        allowed_parameters = {
            "default_mod_tier": list(range(1, cls._DEFAULT_MOD_TIER + 1, 1)),
            "default_mod_level": list(range(1, cls._DEFAULT_MOD_LEVEL + 1, 1)),
            "default_mod_pips": list(range(1, cls._DEFAULT_MOD_PIPS + 1, 1)),
            "game_data": [None, dict],
            "language": DataBuilder.get_languages(),
        }

        logger.info("Initializing StatCalc for first time use.")
        class_vars = vars(cls)
        logger.debug(f"Class vars: {class_vars.keys()}")
        for param, value in kwargs.items():
            if param in allowed_parameters.keys():
                if value in allowed_parameters[param]:
                    class_var = "_" + param.upper()
                    logger.debug(f"Setting class variable {class_var} to {value}")
                    # Remove .json file extension from file name arguments since it is added by the read/write methods
                    if value.endswith(".json"):
                        value = value.replace(".json", "")
                    logger.debug(f"Before: {class_var} = {class_vars[class_var]}")
                    setattr(cls, class_var, value)
                    new_vars = vars(cls)
                    logger.debug(f"After: {class_var} = {new_vars[class_var]}")
                else:
                    logger.error(
                        f"Invalid value ({value}) for argument ({param}). "
                        + f"Allowed values are [{allowed_parameters[param]}]."
                    )

        if cls._GAME_DATA is None:
            logger.info("Loading game data from DataBuilder.")
            if not DataBuilder.is_initialized:
                if not DataBuilder.initialize():
                    logger.error(f"An error occurred while initializing DataBuilder.")
                    return False
            try:
                cls._GAME_DATA = DataBuilder.get_game_data()
            except DataBuilderException as e_str:
                logger.exception(e_str)
                return False
        else:
            logger.info("Game stat information provided.")

        try:
            cls._UNIT_DATA = cls._GAME_DATA["unitData"]
            cls._GEAR_DATA = cls._GAME_DATA["gearData"]
            cls._MOD_SET_DATA = cls._GAME_DATA["modSetData"]
            cls._CR_TABLES = cls._GAME_DATA["crTables"]
            cls._GP_TABLES = cls._GAME_DATA["gpTables"]
            cls._RELIC_DATA = cls._GAME_DATA["relicData"]
        except KeyError as key_err_str:
            logger.error(f"Unable to initialize stat data structures. [{key_err_str}]")
            raise StatCalcRuntimeError(
                f"Unable to initialize stat data structures. [{key_err_str}]"
            )

        logger.info(f"Loading unit 'nameKey' mapping object from DataBuilder files...")
        try:
            cls._UNIT_NAME_MAP = DataBuilder.get_unit_names_mapping(cls._LANGUAGE)
        except FileNotFoundError:
            logger.error(f"Unit name mapping file not found. [{cls._LANGUAGE}]")
            logger.info(
                f"Creating unit 'nameKey' mapping object from game server data."
            )
            cls._load_unit_name_map()

        logger.info(
            f"Loading stat ID to localized name mapping for language: {cls._LANGUAGE} ..."
        )
        if not cls._load_stat_name_map():
            logger.error(
                f"Unable to load stat ID to name mapping. Stats will be referenced by ID only."
            )
        else:
            logger.info(f"Stat ID to localized name mapping loading complete.")
        cls._INITIALIZED = True
        return True
