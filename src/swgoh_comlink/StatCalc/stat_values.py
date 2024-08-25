# coding=utf-8
"""
Class definition for 'StatValues' object. The StatValues object is intended to be used
with the stat calculation interfaces for indicating the unit attributes to use during
calculations.
"""
from __future__ import absolute_import, annotations

from abc import ABC, abstractmethod
from typing import Any

from swgoh_comlink.constants import get_logger

logger = get_logger()


class Validator(ABC):
    def __set_name__(self, owner, name):
        self.private_name = '_' + name

    def __get__(self, obj, objtype=None):
        return getattr(obj, self.private_name)

    def __set__(self, obj, value):
        self.validate(value)
        setattr(obj, self.private_name, value)

    @abstractmethod
    def validate(self, value):
        pass


class StatValidator(Validator):
    def __init__(self, *options):
        self.options = set(options)

    def validate(self, value):
        if value not in self.options:
            raise ValueError(f'Expected {value!r} to be one of {self.options!r}')


class StatValues(object):
    """
    Container class to house unit attributes for stat calculations.

    Args:
        unit_type:

            Dictionary structure must be as follows. Elements missing from the dictionary will be assigned
            their default value.

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
                relic: <str|int>                      # [see below]
                skills: <str|int>,                    # [see below]
                mod_rarity: <int>,                    # 1-7 [pips/dots] (default 6)
                mod_level: <int>,                     # 1-15 (default 15)
                mod_tier: <int>,                      # 1-5 (default 5)
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
        StatValue instance object

    """
    _ALLOWED_UNIT_TYPES: tuple = ('char', 'ship', 'crew')

    _ALLOWED_ATTRS: dict[str, tuple] = {
        "char": ('rarity', 'level', 'gear', 'equipment', 'skills', 'relic', 'mod_rarity', 'mod_level', 'mod_tier'),
        "ship": ('rarity', 'level'),
        "crew": ('rarity', 'level', 'gear', 'equipment', 'skills', 'relic', 'mod_rarity', 'mod_level', 'mod_tier')
    }

    _ATTR_LIMITS = {
        'rarity': {
            "type": (int,),
            "values": tuple(range(1, 8))
        },
        'level': {
            "type": (int,),
            "values": tuple(range(1, 91))
        },
        "gear": {
            "type": (int,),
            "values": tuple(range(1, 13))
        },
        "equipment": {
            "type": (str, int, list, None),
            "values": tuple(["all", None] + list(range(1, 7)))
        },
        "relic": {
            "type": (int, str),
            "values": tuple(["locked", "unlocked"] + list(range(1, 11)))
        },
        "skills": {
            "type": (str, int),
            "values": tuple(["max", "max_no_zeta", "max_no_omicron"] + list(range(1, 10)))
        },
        "mod_rarity": {
            "type": (int,),
            "values": tuple(range(1, 7))
        },
        "mod_level": {
            "type": (int,),
            "values": tuple(range(1, 16))
        },
        "mod_tier": {
            "type": (int,),
            "values": tuple(range(1, 6))
        }
    }

    def _check_unit_type(self, u_type: str):
        if u_type not in self._ALLOWED_UNIT_TYPES:
            err_msg = f"unit type {u_type} not allowed."
            logger.error(err_msg)
            raise AttributeError(err_msg)

    def _check_attribute(self, unit_type: str, attr_name: str, attr_value: Any, func_name: str = None):
        if attr_name not in self._ALLOWED_ATTRS[unit_type]:
            err_msg = f"{func_name}: attribute type {type(attr_name)} not allowed for {unit_type:r}."
            logger.error(err_msg)
            raise AttributeError(err_msg)

        if type(attr_value) not in self._ATTR_LIMITS[attr_name]['type']:
            err_msg = f"{func_name}: attribute type {type(attr_name)} not allowed for {unit_type:r}."
            logger.error(err_msg)
            raise AttributeError(err_msg)

        if attr_value not in self._ATTR_LIMITS[attr_name]['values']:
            err_msg = f"{func_name}: attribute value {attr_value} not allowed for {attr_name}."
            logger.error(err_msg)
            raise AttributeError(err_msg)

    def __init__(self,
                 unit_type: str = "char",
                 /,
                 *,
                 rarity: int = 7,
                 level: int = 85,
                 gear: int = 13,
                 equipment: str | int | list = "all",
                 skills: str | int = "max",
                 relic: int | str = 9,
                 mod_rarity: int = 6,
                 mod_level: int = 15,
                 mod_tier: int = 5,
                 purchase_ability_id: int = None,
                 ):
        """StatValues instance constructor"""
        self.unit_type = unit_type
        self.rarity = rarity
        self.level = level
        if self.unit_type != 'ship':
            self.gear = gear
            self.equipment = equipment
            self.skills = skills
            self.relic = relic
            self.mod_rarity = mod_rarity
            self.mod_level = mod_level
            self.mod_tier = mod_tier
            self.purchase_ability_id = purchase_ability_id

    def __str__(self):
        rtn_str = ''
        for attr in self.__dict__.keys():
            rtn_str += f"{attr}: {self.__dict__[attr]}\n"
        return rtn_str

    def from_dict(self, attributes: dict):
        """Create new StatValues instance from dictionary."""
        if attributes:
            if not isinstance(attributes, dict):
                err_msg = f"'attributes' argument must be a dictionary."
                logger.error(err_msg)
                raise AttributeError(err_msg)
            else:
                for unit_type in attributes.keys():
                    self._check_unit_type(unit_type)
                    temp_attrs = {}
                    for attr in attributes[unit_type].keys():
                        self._check_attribute(unit_type, attr, attributes[unit_type][attr])
                        temp_attrs.setdefault(attr, {})
                        temp_attrs[attr] = attributes[unit_type][attr]
                    logger.debug(f"setting {unit_type} attributes to {temp_attrs}")
                    setattr(self.__class__, unit_type, temp_attrs)

    def set_attribute(self, unit_type: str, attributes: dict):
        if not unit_type:
            err_msg = f"'unit_type' argument cannot be empty."
            logger.error(err_msg)
            raise AttributeError(err_msg)

        self._check_unit_type(unit_type)

        if attributes:
            if not isinstance(attributes, dict):
                err_msg = f"'attributes' argument must be a dictionary."
                logger.error(err_msg)
                raise AttributeError(err_msg)
            else:
                for attr in attributes.keys():
                    self._check_attribute(unit_type, attr, attributes[attr])
                logger.debug(f"setting {unit_type} attributes to {attributes}")
                setattr(self.__class__, unit_type, attributes)
        else:
            err_msg = f"'attributes' argument cannot be empty."
            logger.error(err_msg)
            raise AttributeError(err_msg)

    def get_attribute(self, unit_type: str) -> dict | None:
        if not unit_type:
            err_msg = f"'unit_type' argument cannot be empty."
            logger.error(err_msg)
            raise AttributeError(err_msg)

        if unit_type not in self._ALLOWED_UNIT_TYPES:
            err_msg = f"unit type {unit_type} not allowed."
            logger.error(err_msg)
            raise AttributeError(err_msg)

        return getattr(self.__class__, unit_type, None)


class StatOptions:
    """
    Data object containing flags to control various aspects of unit stat calculation and results formatting.
    """

    def __init__(self,
                 /,
                 *,
                 without_mod_calc=False,
                 percent_vals=False,
                 calc_gp=False,
                 only_gp=False,
                 use_max=False,
                 scaled=False,
                 unscaled=False,
                 game_style=False,
                 stat_ids=False,
                 enums=False,
                 no_space=False,
                 language="eng_us",
                 ):
        """
        StatCalc Options constructor. Controls the behavior of stat calculation and results formatting.
        All flags default to False.

        Args:
            without_mod_calc: Do not include mods in stat calculation.
            percent_vals: Converts Crit Chance and Armor/Resistance from their flat values (default) to the
                          percent values as displayed in-game
            calc_gp: Include total Galactic Power calculation.
            only_gp: Only calculate Galactic Power.
            use_max: Use maximum possible values for stat calculations.
            scaled: Returns all stats as their 'scaledValueDecimal' equivalents -- 10,000 times the common value.
                    Non-modded stats should all be integers at this scale.
            unscaled: Returns all stats as their 'unscaledDecimalValue' equivalents -- 100,000,000 times the common
                    value. All stats should be integers at this scale.
            game_style: Adjusts the stat objects to return 'final' stats (the total seen in-game)
                        instead of 'base' stats. Also applies same conversion as percentVals.
            stat_ids: Leaves the stat object indexed by the stat ID rather than localized string.
                      Ignores any specified 'language' option
            enums: Indexes the stat object by the non-localized enum string used as a key in the game's
                   localization files. Ignores any specified 'language' option
            no_space: In conjunction with the 'language' option below, this flag will convert the localization
                      string into standard camelCase with no spaces.
            language: String with the language code for the desired language. [Default: 'eng_us']

        """

        self.without_mod_calc = without_mod_calc
        self.percent_vals = percent_vals
        self.calc_gp = calc_gp
        self.only_gp = only_gp
        self.use_max = use_max
        self.scaled = scaled
        self.unscaled = unscaled
        self.game_style = game_style
        self.stat_ids = stat_ids
        self.enums = enums
        self.no_space = no_space
        self.language = language

    def __str__(self):
        rtn_str = ''
        for attr in self.__dict__.keys():
            rtn_str += f"{attr}: {self.__dict__[attr]}\n"
        return rtn_str

    def from_list(self, options_list: list[str]):
        """Create StatOptions instance with attributes from list

            Args:
                options_list: List of option names to set to True.

            Examples:
                ```python
                options_list = ['calc_gp', 'percent_vals', 'game_style', 'no_space', language='eng_us']
                ```

            Raises:
                AttributeError

        """
        if options_list:
            if not isinstance(options_list, list):
                err_msg = f"'options_list' argument must be a list."
                logger.error(err_msg)
                raise AttributeError(err_msg)
            else:
                for option in options_list:
                    if option in self.__dict__.keys():
                        if 'language' in option:
                            _, lang_code = option.split('=')
                            self.__dict__['language'] = lang_code
                        else:
                            self.__dict__[option] = True
                    else:
                        logger.warning(f"option {option!r} not recognized. skipping.")

    def from_dict(self, options_dict: dict[str, bool | str]):
        """Create StatOptions instance with attributes from dictionary

            Args:
                options_dict: Dictionary with option name as keys and boolean or string values.

            Examples:
                ```python
                options_dict = {'calc_gp': True, 'percent_vals': True, 'game_style': True, 'language': 'eng_us',}
                ```

            Raises:
                AttributeError

        """
        if options_dict:
            if not isinstance(options_dict, dict):
                err_msg = f"'options_dict' argument must be a dictionary."
                logger.error(err_msg)
                raise AttributeError(err_msg)
            else:
                for option in options_dict.keys():
                    if option in self.__dict__.keys():
                        self.__dict__[option] = options_dict[option]
                    else:
                        logger.warning(f"option {option!r} not recognized. skipping.")


__all__ = [
    StatValues,
    StatOptions,
]
