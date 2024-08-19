# coding=utf-8
"""
Class definition for 'StatValues' object. The StatValues object is intended to be used
with the stat calculation interfaces for indicating the unit attributes to use during
calculations.
"""
from __future__ import absolute_import

from typing import Any

from swgoh_comlink.constants import get_logger, _get_function_name

logger = get_logger()


class StatValues(object):
    """
    Container class to house unit attributes for stat calculations.

    Args:
        attributes (dict): character attribute values in the format from the game data['unit'] collection

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
    char: dict | None = None
    ship: dict | None = None
    crew: dict | None = None

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

    unit_type: str | None = None

    def _check_unit_type(self, unit_type: str, func_name: str = None):
        if unit_type not in self._ALLOWED_UNIT_TYPES:
            err_msg = f"{func_name}: unit type {unit_type} not allowed."
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

    def __init__(self, attributes: dict | None = None):
        """StatValues instance constructor"""
        if attributes:
            if not isinstance(attributes, dict):
                err_msg = f"{_get_function_name()}: 'attributes' argument must be a dictionary."
                logger.error(err_msg)
                raise AttributeError(err_msg)
            else:
                for unit_type in attributes.keys():
                    self._check_unit_type(unit_type, _get_function_name())
                    temp_attrs = {}
                    for attr in attributes[unit_type].keys():
                        self._check_attribute(unit_type, attr, attributes[unit_type][attr], _get_function_name())
                        temp_attrs.setdefault(attr, {})
                        temp_attrs[attr] = attributes[unit_type][attr]
                    logger.debug(f"{_get_function_name()}: setting {unit_type} attributes to {temp_attrs}")
                    setattr(self.__class__, unit_type, temp_attrs)

    def set_attribute(self, unit_type: str, attributes: dict):
        """
        Set StatValues instance attributes.

        Args:
            unit_type (str): One of 'char', 'ship', or 'crew'
            attributes (dict): Dictionary of attribute values for the corresponding 'unit_type'

        Returns:
            None

        Raises:
            AttributeError if arguments do not contain the expected attributes.

        """
        if not unit_type:
            err_msg = f"{_get_function_name()}: 'unit_type' argument cannot be empty."
            logger.error(err_msg)
            raise AttributeError(err_msg)

        self._check_unit_type(unit_type, _get_function_name())

        if attributes:
            if not isinstance(attributes, dict):
                err_msg = f"{_get_function_name()}: 'attributes' argument must be a dictionary."
                logger.error(err_msg)
                raise AttributeError(err_msg)
            else:
                for attr in attributes.keys():
                    self._check_attribute(unit_type, attr, attributes[attr], _get_function_name())
                logger.debug(f"{_get_function_name()}: setting {unit_type} attributes to {attributes}")
                setattr(self.__class__, unit_type, attributes)
        else:
            err_msg = f"{_get_function_name()}: 'attributes' argument cannot be empty."
            logger.error(err_msg)
            raise AttributeError(err_msg)

    def get_attribute(self, unit_type: str) -> dict | None:
        """
        Returns StatValues instance attributes for the corresponding 'unit_type'.

        Args:
            unit_type (str): One of 'char', 'ship', or 'crew':

        Returns:
            Dictionary containing StatValues instance attributes for the corresponding 'unit_type'

        Raises:
            AttributeError if arguments do not contain the expected attributes.

        """
        if not unit_type:
            err_msg = f"{_get_function_name()}: 'unit_type' argument cannot be empty."
            logger.error(err_msg)
            raise AttributeError(err_msg)

        if unit_type not in self._ALLOWED_UNIT_TYPES:
            err_msg = f"{_get_function_name()}: unit type {unit_type} not allowed."
            logger.error(err_msg)
            raise AttributeError(err_msg)

        return getattr(self.__class__, unit_type, None)
