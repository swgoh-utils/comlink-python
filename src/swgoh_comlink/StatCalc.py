"""
Python library module for calculating character and ship statistic values for the Star Wars: Galaxy of Heroes mobile
game from EA/CG.
"""

import logging
import time
from functools import wraps

from swgoh_comlink import utils
from swgoh_comlink.DataBuilder import DataBuilder

logger = utils.get_logger()


def func_timer(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()
        logger.debug(f'func:{f.__name__} took: {te - ts:.6f} sec')
        return result

    return wrap


def fix_float(value, digits):
    # return Number(`${Math.round(`${value}e${digits}`)}e-${digits}`) || 0
    pass


def floor(value, digits=0):
    # return math.floor(value / ('1e'+digits)) * ('1e'+digits)
    pass


def convert_flat_def_to_percent(value, level=85, scale=1, is_ship=False):
    val = value / scale
    if is_ship is True:
        level_effect = 300 + level * 5
    else:
        level_effect = level * 7.5
    return (val / (level_effect + val)) * scale


def convert_flat_crit_to_percent(value, scale=1):
    val = value / scale
    return (val / 2400 + 0.1) * scale


def convert_flat_acc_to_percent(value, scale=1):
    val = value / scale
    return (val / 1200) * scale


def convert_flat_crit_avoid_to_percent(value, scale=1):
    val = value / scale
    return (val / 2400) * scale


class StatCalcException(Exception):
    pass


class StatCalcRuntimeError(RuntimeError):
    pass


class StatCalc:
    """
    Container class to house collection of stat calculation methods. Not intended to be instantiated.
    """

    _DEFAULT_MOD_TIER = 5
    _DEFAULT_MOD_LEVEL = 15
    _DEFAULT_MOD_PIPS = 6

    _GAME_DATA = None
    _UNIT_DATA = {}
    _GEAR_DATA = {}
    _MOD_SET_DATA = {}
    _CR_TABLES = {}
    _GP_TABLES = {}
    _RELIC_DATA = {}

    @classmethod
    def set_attribute(cls, attr_name: str, attr_value: any):
        """Set class attribute"""
        setattr(cls, attr_name, attr_value)

    @classmethod
    def set_log_level(cls, log_level):
        """Set the logging level for message output. Default is 'INFO'"""
        log_levels = logging.getLevelNamesMapping()
        if log_level in log_levels:
            logger.setLevel(log_levels[log_level])
        else:
            raise StatCalcRuntimeError(
                f"Invalid log level {log_level}. Available options are {list(log_levels.keys())}")

    @classmethod
    def calc_char_stats(cls, unit, options):
        pass

    @classmethod
    def calc_ship_stats(cls, ship, crw, options):
        pass

    @classmethod
    def set_skills(cls, unit_id, val):
        pass

    @classmethod
    def use_values_ships(cls, ship, crew, use_values):
        pass

    @classmethod
    def use_values_char(cls, char, use_values):
        pass

    @classmethod
    def get_crewless_skills_gp(cls, id, skills):
        a = 0
        r = 0
        for skill in skills:
            o_tag = cls._UNIT_DATA[id]['skills']

    @classmethod
    def calc_roster_stats(cls, units: any, options: dict = None):
        """Calculate units stats from SWGOH roster game data"""

        count = 0
        if isinstance(units, list):
            ships = []
            crew = {}
            for unit in units:
                if unit['defId']:
                    defID = unit['defId']
                else:
                    defID = unit['definitionId'].split(':')[0]
                if not unit or not cls._UNIT_DATA[defID]:
                    return
                if (
                        (isinstance(cls._UNIT_DATA[defID]['combatType'], int) and cls._UNIT_DATA[defID][
                            'combatType'] == 2) or
                        (isinstance(cls._UNIT_DATA[defID]['combatType'], str) and cls._UNIT_DATA[defID][
                            'combatType'] == 'SHIP')
                ):
                    ships.append(unit)
                else:
                    crew[defID] = unit
                    cls.calc_char_stats(unit, options)
            for ship in ships:
                if ship['defId']:
                    defID = ship['defId']
                else:
                    defID = ship['definitionId'].split(':')[0]
                if not ship or not cls._UNIT_DATA[defID]:
                    return
                # TODO: check the code below for proper functionality
                crw = [id for id in cls._UNIT_DATA[defID]['crew']['id'] if
                       crew['id'] == cls._UNIT_DATA[defID]['crew']['id']]
                cls.calc_ship_stats(ship, crw, options)
            count += len(units)
        else:
            ids = units.keys()
            for id in ids:
                for unit in units[id]:
                    if cls._UNIT_DATA[id]['combatType'] == 1:
                        temp_unit = {
                            'defId': id,
                            'rarity': unit['starLevel'],
                            'level': unit['level'],
                            'gear': unit['gearLevel'],
                            'equipped': [{'equipmentId': gearID} for gearID in unit['gear']],
                            'mods': unit['mods']
                        }
                        cls.calc_char_stats(temp_unit, options)
                        unit['stats'] = temp_unit['stats']
                        unit['gp'] = temp_unit['gp']
                        count += 1
        return count

    @classmethod
    @func_timer
    def initialize(cls, **kwargs) -> bool:
        """Prepare StatCalc environment for first use. Providing keyword arguments can override default settings.

        game_data: dict Defaults to None. Will autoload if not provided.
        default_mod_tier: int Defaults to 5. Should not need to be set unless the game changes mods and some point.
        default_mod_level: in Defaults to 15. Should not need to be set unless the game mod system changes.
        default_mod_pips: int Defaults to 6. Should not need to be set unless the game mod system changes.

        """
        allowed_parameters = [
            "default_mod_tier",
            "default_mod_level",
            "default_mod_pips",
            "game_data",
        ]
        logger.info("Initializing StatCalc for first time use.")
        class_vars = vars(cls)
        logger.debug(f"Class vars: {class_vars.keys()}")
        for param, value in kwargs.items():
            if param in allowed_parameters:
                class_var = '_' + param.upper()
                logger.debug(f"Setting class variable {class_var} to {value}")
                # Remove .json file extension from file name arguments since it is added by the read/write methods
                if value.endswith('.json'):
                    value = value.replace('.json', '')
                logger.debug(f"Before: {class_var} = {class_vars[class_var]}")
                setattr(cls, class_var, value)
                new_vars = vars(cls)
                logger.debug(f"After: {class_var} = {new_vars[class_var]}")

        if cls._GAME_DATA is None:
            logger.info("Loading game data from DataBuilder.")
            cls._GAME_DATA = DataBuilder.set_game_data()
        else:
            logger.info("Game stat information provided.")

        try:
            cls._UNIT_DATA = cls._GAME_DATA['unitData']
            cls._GEAR_DATA = cls._GAME_DATA['gearData']
            cls._MOD_SET_DATA = cls._GAME_DATA['modSetData']
            cls._CR_TABLES = cls._GAME_DATA['crTables']
            cls._GP_TABLES = cls._GAME_DATA['gpTables']
            cls._RELIC_DATA = cls._GAME_DATA['relicData']
        except KeyError as key_err_str:
            logger.error(f"Unable to initialize stat data structures. [{key_err_str}]")
            raise StatCalcRuntimeError(key_err_str)

        return True
