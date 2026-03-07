# coding=utf-8
"""Omicron and skill-related helper functions."""

from __future__ import annotations

from collections import namedtuple
from typing import NamedTuple

from ..exceptions import SwgohComlinkValueError


def get_tw_omicrons(skill_list: list) -> list:
    """Return a list of territory war omicrons

    Args:
        skill_list (list): List of character abilities/skills

    Returns:
        List of territory war omicron abilities

    Raises:
        SwgohComlinkValueError: If skill_list is not a list

    """
    if not isinstance(skill_list, list):
        raise SwgohComlinkValueError(f"'skill_list' must be a list, not {type(skill_list)}")

    return get_omicron_skills(skill_list, 8)


def get_omicron_skills(skill_list: list, omicron_type: int | list[int]) -> list:
    """
    Filters and retrieves omicron skills from a given skill list based on the specified omicron type.

    Args:
        skill_list (list): A list of dictionaries representing skills. The 'skill' collection in game data.
        omicron_type (int | list): The omicron mode type to filter the skills by.
            The 'OmicronMode' in the game data enums.

    Returns:
        list: A list of dictionaries representing skills that match the specified omicron type.

    Raises:
        SwgohComlinkValueError: If either of the arguments is not of the expected type.
    """

    if not isinstance(skill_list, list):
        raise SwgohComlinkValueError(f"'skill_list' must be a list, not {type(skill_list)}")

    if not isinstance(omicron_type, (int, list)):
        raise SwgohComlinkValueError(f"'omicron_type' must be an integer or list of integers, not {type(omicron_type)}")

    omicron_type_list = [omicron_type] if isinstance(omicron_type, int) else omicron_type

    return [skill for skill in skill_list if skill["omicronMode"] in omicron_type_list]


def get_omicron_skill_tier(skill: dict) -> int | None:
    """
    Return the omicron tier index for the given skill.

    Parameters:
        skill (dict): A dictionary representing the skill, containing
                      a 'tier' key which holds a list of tier dictionaries.

    Returns:
        int: The index of the Omicron skill tier within the 'tier' list or None if not found.

    Raises:
        SwgohComlinkValueError: If the input 'skill' is not a dictionary.
        SwgohComlinkValueError: If the required 'tier' key is not present in the 'skill' dictionary.
    """
    if not isinstance(skill, dict):
        raise SwgohComlinkValueError(f"'skill' must be a dictionary, not {type(skill)}")

    if "tier" not in skill:
        raise SwgohComlinkValueError("'skill' must contain 'tier' key")

    skill_tier = [idx for idx, tier in enumerate(skill["tier"]) if tier["isOmicronTier"] is True]

    return skill_tier[0] if skill_tier else None


def is_omicron_skill(
    omicron_skill_list: list[dict],
    skill_id: str | None = None,
    skill_tier: int | None = None,
    *,
    roster_unit_skill: dict | None = None,
) -> bool:
    """
    Check if a given skill is an Omicron skill based on its ID and tier.

    Args:
        omicron_skill_list (list[dict]): List of skills from game data that have omicron tiers.
        skill_id (str): ID of the skill to check.
        skill_tier (int): Tier index of the skill to check.
        roster_unit_skill (Optional[dict]): Optional dictionary containing the skill data for the roster unit.

    Returns:
        bool: True if the skill is an Omicron skill, False otherwise.

    Raises:
        SwgohComlinkValueError: If either of the arguments is not of the expected type.
    """
    if not isinstance(omicron_skill_list, list):
        raise SwgohComlinkValueError(f"'omicron_skill_list' must be a list, not {type(omicron_skill_list)}")

    # When roster_unit_skill is provided, extract skill_id and skill_tier from it
    if roster_unit_skill is not None:
        skill_id = roster_unit_skill.get("id")
        skill_tier = roster_unit_skill.get("tier")
        if not skill_id or not skill_tier:
            raise SwgohComlinkValueError("Invalid 'roster_unit_skill' argument.")
    else:
        # Validate that skill_id and skill_tier were provided directly
        if not isinstance(skill_id, str):
            raise SwgohComlinkValueError(f"'skill_id' must be a string, not {type(skill_id)}")
        if not skill_id or not skill_tier:
            raise SwgohComlinkValueError(
                "'skill_id' and 'skill_tier' are required when 'roster_unit_skill' is not provided."
            )

    omicron_skill = [omi_skill for omi_skill in omicron_skill_list if omi_skill["id"] == skill_id]

    if not omicron_skill:
        return False

    skill_omicron_tier = get_omicron_skill_tier(omicron_skill[0])

    if skill_omicron_tier is None:
        return False

    return skill_omicron_tier == skill_tier


def get_unit_from_skill(unit_list: list[dict], skill: str) -> NamedTuple | None:
    """
    Extracts the base ID and name key of a unit from a list of units based on a specific skill.

    Parameters:
      unit_list (list[dict]): The list of units to search within.
      skill (str): The skill to search for in the 'skillReference' field of each unit.

    Returns:
      NamedTuple | None: Returns a namedtuple containing the 'baseId' and 'nameKey' of the first
        unit that matches the specified skill, or None if no such unit is found.

    Raises:
      SwgohComlinkValueError: If 'unit_list' is not of type list.
      SwgohComlinkValueError: If 'skill' is not of type string.
    """
    if not isinstance(unit_list, list):
        raise SwgohComlinkValueError(f"'unit_list' must be a list, not {type(unit_list)}")

    if not isinstance(skill, str):
        raise SwgohComlinkValueError(f"'skill' must be a string, not {type(skill)}")

    def skill_exists(value, dict_list: list[dict]) -> bool:
        if not dict_list:
            return False
        return any(value in d.values() for d in dict_list)

    Unit = namedtuple("Unit", "baseId nameKey")
    base_ids: list[NamedTuple] = [
        Unit(unit.get("baseId"), unit.get("nameKey"))
        for unit in unit_list
        if skill_exists(skill, unit.get("skillReference"))
    ]
    if base_ids:
        return base_ids[0]
    else:
        return None
