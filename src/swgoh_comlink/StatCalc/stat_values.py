# coding=utf-8
"""
Class definition for 'StatValues' object. The StatValues object is intended to be used
with the stat calculation interfaces for indicating the unit attributes to use during
calculations.
"""
from __future__ import absolute_import, annotations

from abc import ABC, abstractmethod

from sentinels import Sentinel

from swgoh_comlink.constants import get_logger, Constants, OPTIONAL
from swgoh_comlink.exceptions import StatValueError, StatTypeError

logger = get_logger()


# Validation classes
class Validator(ABC):
    def __set_name__(self, owner, name):
        self.private_name = '_' + name

    def __get__(self, obj, objtype=None):
        return getattr(obj, self.private_name)

    def __set__(self, obj, value):
        self.validate(value)
        setattr(obj, self.private_name, value)

    def __delete__(self, obj):
        raise NotImplementedError(f"Removal of {obj!r} is not permitted.")

    @abstractmethod
    def validate(self, value):
        pass


class ValueType(Validator):

    def __init__(self, *types):
        self.types = set(types)

    def validate(self, value_type):
        if value_type not in self.types:
            raise StatValueError(f"Expected {value_type} to be one of {self.types!r}")


class ValueAttr(Validator):

    def __init__(self, *stat_attrs):
        self.stat_attrs = stat_attrs

    def validate(self, stat_attr):
        if stat_attr not in self.stat_attrs:
            raise StatValueError(f"Expected {stat_attr} to be one of {self.stat_attrs!r}")


class ValueOptions(Validator):

    def __init__(self, options):
        self.options = set(options)

    def validate(self, attr_value):
        if isinstance(attr_value, list):
            for v in attr_value:
                self.validate(v)
        elif attr_value not in self.options:
            raise StatValueError(f'Expected {attr_value!r} to be one of {self.options!r}')


# Public classes
class StatValues:
    """Container class to house unit attributes for stat calculations."""

    __module__ = Constants.MODULE_NAME

    ALLOWED_ATTRS: set = {
        "unit_type",
        "rarity",
        "level",
        "gear",
        "equipment",
        "skills",
        "relic",
        "mod_rarity",
        "mod_level",
        "mod_tier",
        "purchase_ability_id",
    }

    unit_type = ValueType('char', 'ship', 'crew')

    rarity = ValueOptions(tuple(range(1, 8)))
    level = ValueOptions(tuple(range(1, 91)))
    gear = ValueOptions(tuple(range(1, 14)))
    equipment = ValueOptions(tuple(["all", None] + list(range(0, 6))))
    relic = ValueOptions(tuple(["locked", "unlocked"] + list(range(1, Constants.MAX_VALUES['RELIC_TIER'] + 1))))
    skills = ValueOptions(tuple(["max", "max_no_zeta", "max_no_omicron"] + list(range(1, 10))))
    mod_rarity = ValueOptions(tuple(range(1, 7)))
    mod_level = ValueOptions(tuple(range(1, 16)))
    mod_tier = ValueOptions(tuple(range(1, 7)))
    purchase_ability_id = []

    def __init__(self,
                 /,
                 *,
                 unit_type: str = "char",
                 rarity: int = Constants.MAX_VALUES['UNIT_RARITY'],
                 level: int = Constants.MAX_VALUES['UNIT_LEVEL'],
                 gear: int = Constants.MAX_VALUES['GEAR_TIER'],
                 equipment: str | int | list | None = "all",
                 skills: str | int = "max",
                 relic: int | str = Constants.MAX_VALUES['RELIC_TIER'],
                 mod_rarity: int = Constants.MAX_VALUES['MOD_RARITY'],
                 mod_level: int = Constants.MAX_VALUES['MOD_LEVEL'],
                 mod_tier: int = Constants.MAX_VALUES['MOD_TIER'],
                 purchase_ability_id: list[str] | None = None,
                 ):
        """StatValues instance constructor

        Keyword Args:
                 unit_type: Type of unit the stat values apply to. Possible values are: "char", "ship", "crew".
                            [Default: "char"]
                 rarity: Unit rarity tier (1-7) [Default: 7]
                 level: Unit level (1-90) [Default: 85]
                 gear: Unit gear (equipment) tier (1-13) [Default: 13]
                 equipment: Unit equipment pieces to model.
                            Possible values are:
                                "all": Include all possible gear pieces [Default]
                                None: Do not include any gear pieces.
                                (int|list): List of integers indicating which gear slots to include.
                                             Slots are numbered as:
                                                    0    3
                                                    1    4
                                                    2    5
                                            For example: [1,2,4]
                                            For unit_type "crew", a single integer (1-6) can be used to indicate how
                                            many gear pieces to include without specifying the slot assignment.
                 skills: Unit skill level to model.
                            Possible values are:
                                "max": Include all possible skills
                                "max_no_zeta": Include all skills at the highest possible level below the zeta threshold
                                "max_no_omicron": Include all skills at the highest possible level below the omicron
                                                    threshold
                                (int): Include all skills at the level (1-9) indicated by the integer provided
                 relic: Relic tier to use for calculations.
                            Possible values are:
                                "locked": Unit is gear level 13 but has NOT unlocked the relic tier
                                "unlocked": Unit is gear level 13 and has unlocked the relic tier
                                (int): Single integer (1-9) indicating the relic tier. [Default: 9]
                 mod_rarity: Unit mod pips/dots to model. Integer (1-6) [Default: 6]
                 mod_level: Unit mod level to model. Integer (1-15) [Default: 15]
                 mod_tier: Unit mod tier to model. Integer (1-6) [Default: 6]
                 purchase_ability_id: Galactic Legend Ultimate Ability ID string. Not Implemented
        """
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
            self.purchase_ability_id = purchase_ability_id if purchase_ability_id else []

    def __setattr__(self, key, value):
        if key.lstrip('_') not in self.ALLOWED_ATTRS:
            raise StatValueError(f"{key} not in allowed attributes list: {self.ALLOWED_ATTRS!r}")
        object.__setattr__(self, key, value)

    def __repr__(self):
        return f"{self.__class__.__name__}(**{self.to_dict()})"

    def __str__(self):
        rtn_str = ''
        for attr in self.__dict__.keys():
            rtn_str += f"{attr.lstrip('_')}: {self.__dict__[attr]}\n"
        return rtn_str

    def to_dict(self):
        """Return instance attributes as dict"""
        rtn_dict = {}
        if getattr(self, 'unit_type') == 'ship':
            attrs = ['unit_type', 'rarity', 'level']
        else:
            attrs = self.ALLOWED_ATTRS

        for attr in attrs:
            rtn_dict[attr] = getattr(self, attr)
        return rtn_dict


class StatOptions:
    """
    Data object containing flags to control various aspects of unit stat calculation and results formatting.
    """

    __module__ = Constants.MODULE_NAME

    __slots__ = [
        "WITHOUT_MOD_CALC",
        "PERCENT_VALS",
        "CALC_GP",
        "ONLY_GP",
        "USE_MAX",
        "SCALED",
        "UNSCALED",
        "GAME_STYLE",
        "STAT_IDS",
        "ENUMS",
        "NO_SPACE",
        "LANGUAGE",
    ]

    def __init__(self, flags: list | dict | None | Sentinel = OPTIONAL, **kwargs):
        """
        StatCalc Options constructor. Controls the behavior of stat calculation and results formatting.
        All flags default to False. Default constructor sets all allowed attributes to False. List argument sets
        attributes matching allowed attributes to True. Dictionary argument set allowed attributes to specified
        value. Keyword arguments set the corresponding attributes to the indicated vale.

        Keyword Args:
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
        for attr in self.__slots__:
            if attr == 'LANGUAGE':
                setattr(self, attr, 'eng_us')
            else:
                setattr(self, attr, False)

        if flags is not OPTIONAL:
            if isinstance(flags, list):
                self.from_list(flags)
            elif isinstance(flags, dict):
                self.from_dict(flags)
            else:
                raise StatValueError("StatOptions(): Unknown constructor type provided.")
        else:
            for k, v in kwargs.items():
                if k.upper() == 'LANGUAGE':
                    if v.lower() not in Constants.LANGUAGES:
                        raise StatValueError(f"StatOptions() 'LANGUAGE' attribute must be one of "
                                             f"{Constants.LANGUAGES!r}, not {v.lower()!r}")
                    else:
                        setattr(self, k.upper(), v.lower())
                elif not isinstance(v, bool):
                    raise StatValueError(f"StatOptions() flag values must be type bool, not {type(v)!r}")
                else:
                    setattr(self, k.upper(), v)

    def __setattr__(self, attr_name, value):
        if attr_name.upper() == 'LANGUAGE':
            if value.lower() not in Constants.LANGUAGES:
                raise StatValueError(f"StatOptions() 'LANGUAGE' attribute must be one of "
                                     f"{Constants.LANGUAGES!r}, not {value.lower()!r}")
            else:
                object.__setattr__(self, 'LANGUAGE', value.lower())
        else:
            if not isinstance(value, bool):
                raise StatTypeError(f"Expected {value} to be of type bool, not {type(value)!r}.")
            else:
                object.__setattr__(self, attr_name.upper(), value)

    def __delattr__(self, attr_name):
        logger.warning(f"Attempted removal of {attr_name!r} from {self.__class__.__name__} instance.")

    def __repr__(self):
        return f"{self.__class__.__name__}({self.to_dict()})"

    def __str__(self):
        rtn_str = '\nInstance of StatOptions class.\n\n'
        for attr in self.__slots__:
            rtn_str += f"{attr}: {getattr(self, attr)}\n"
        return rtn_str

    def from_list(self, options_list: list[str]):
        """Create instance from list"""
        if not isinstance(options_list, list):
            raise StatTypeError(f"Expected {options_list} to be of type list[str], not {type(options_list)!r}.")
        else:
            for option in options_list:
                if 'LANGUAGE' in option.upper():
                    _, lang_code = option.split('=')
                    if lang_code.lower() not in Constants.LANGUAGES:
                        raise StatValueError(f"StatOptions() 'LANGUAGE' attribute must be one of "
                                             f"{Constants.LANGUAGES!r}, not {lang_code.lower()!r}")
                    else:
                        setattr(self, 'LANGUAGE', lang_code.lower())
                else:
                    setattr(self, option.upper(), True)

    def from_dict(self, options_dict: dict[str, bool | str]):
        """Create instance from dict"""
        if not isinstance(options_dict, dict):
            raise StatTypeError(f"Expected {options_dict} to be of type dict, not {type(options_dict)!r}.")
        else:
            for option, value in options_dict.items():
                if option.upper() == 'LANGUAGE':
                    if value.lower() not in Constants.LANGUAGES:
                        raise StatValueError(f"StatOptions() 'LANGUAGE' attribute must be one of "
                                             f"{Constants.LANGUAGES!r}, not {value.lower()!r}")
                    else:
                        setattr(self, 'LANGUAGE', value.lower())
                else:
                    if not isinstance(value, bool):
                        raise StatTypeError(f"Expected {value} to be of type bool, not {type(value)!r}.")
                    setattr(self, option.upper(), value)

    def to_list(self):
        """Return instance attributes as list"""
        rtn_list = []
        for attr in self.__slots__:
            if attr == 'LANGUAGE':
                rtn_list.append(f"LANGUAGE={getattr(self, attr)}")
            elif getattr(self, attr):
                rtn_list.append(attr)
        return rtn_list

    def to_dict(self):
        """Return instance attributes as dict"""
        rtn_dict = {}
        for attr in self.__slots__:
            rtn_dict[attr] = getattr(self, attr)
        return rtn_dict


__all__ = [
    StatValues,
    StatOptions,
    StatValueError,
    StatTypeError,
]
