# coding=utf-8
"""Omicron and skill-related helper functions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, NamedTuple, TypedDict

from ..exceptions import SwgohComlinkValueError
from ._game_data import get_playable_units
from ._localization import _localize
from ._stat_data import OMICRON_MODE
from ._utils import get_function_name
from ._wire import as_int, as_list, as_scalar, as_str, base_id, parse_enum

# OmicronMode members. omicronMode arrives as a number (enums=False) or a member name (enums=True), bare
# (TERRITORY_WAR_OMICRON) or type-prefixed (OMICRONMODE_TERRITORYWAROMICRON); parse_enum reads all three.
_OMICRON_MODES: dict[str, int] = {
    "OmicronMode_DEFAULT": 0,
    "ALL_OMICRON": 1,
    "PVE_OMICRON": 2,
    "PVP_OMICRON": 3,
    "GUILD_RAID_OMICRON": 4,
    "TERRITORY_STRIKE_OMICRON": 5,
    "TERRITORY_COVERT_OMICRON": 6,
    "TERRITORY_BATTLE_BOTH_OMICRON": 7,
    "TERRITORY_WAR_OMICRON": 8,
    "TERRITORY_TOURNAMENT_OMICRON": 9,
    "WAR_OMICRON": 10,
    "CONQUEST_OMICRON": 11,
    "GALACTIC_CHALLENGE_OMICRON": 12,
    "PVE_EVENT_OMICRON": 13,
    "TERRITORY_TOURNAMENT_3_OMICRON": 14,
    "TERRITORY_TOURNAMENT_5_OMICRON": 15,
    "GALACTIC_CHALLENGE_3_OMICRON": 16,
    "GALACTIC_CHALLENGE_5_OMICRON": 17,
}


class Unit(NamedTuple):
    """The unit that owns a skill, as returned by :func:`get_unit_from_skill`."""

    baseId: str | None
    nameKey: str | None


def get_tw_omicrons(skill_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def get_omicron_skills(skill_list: list[dict[str, Any]], omicron_type: int | list[int]) -> list[dict[str, Any]]:
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


def get_omicron_skill_tier(skill: dict[str, Any]) -> int | None:
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
    omicron_skill_list: list[dict[str, Any]],
    skill_id: str | None = None,
    skill_tier: int | None = None,
    *,
    roster_unit_skill: dict[str, Any] | None = None,
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
        # Tier 0 is a legitimate value for a freshly unlocked skill, so only a missing tier is an error.
        if not skill_id or skill_tier is None:
            raise SwgohComlinkValueError("Invalid 'roster_unit_skill' argument.")
    else:
        # Validate that skill_id and skill_tier were provided directly
        if not isinstance(skill_id, str):
            raise SwgohComlinkValueError(f"'skill_id' must be a string, not {type(skill_id)}")
        if not skill_id or skill_tier is None:
            raise SwgohComlinkValueError(
                "'skill_id' and 'skill_tier' are required when 'roster_unit_skill' is not provided."
            )

    omicron_skill = [omi_skill for omi_skill in omicron_skill_list if omi_skill["id"] == skill_id]

    if not omicron_skill:
        return False

    skill_omicron_tier = get_omicron_skill_tier(omicron_skill[0])

    if skill_omicron_tier is None:
        return False

    result: bool = skill_omicron_tier == skill_tier
    return result


def get_unit_from_skill(unit_list: list[dict[str, Any]], skill: str) -> Unit | None:
    """
    Extracts the base ID and name key of a unit from a list of units based on a specific skill.

    Parameters:
      unit_list (list[dict]): The list of units to search within.
      skill (str): The skill to search for in the 'skillReference' field of each unit.

    Returns:
      Unit | None: A ``Unit`` named tuple with the 'baseId' and 'nameKey' of the first unit
        that matches the specified skill, or None if no such unit is found.

    Raises:
      SwgohComlinkValueError: If 'unit_list' is not of type list.
      SwgohComlinkValueError: If 'skill' is not of type string.
    """
    if not isinstance(unit_list, list):
        raise SwgohComlinkValueError(f"'unit_list' must be a list, not {type(unit_list)}")

    if not isinstance(skill, str):
        raise SwgohComlinkValueError(f"'skill' must be a string, not {type(skill)}")

    def skill_exists(value: Any, dict_list: list[dict[str, Any]] | None) -> bool:
        if not dict_list:
            return False
        return any(value in d.values() for d in dict_list)

    return next(
        (
            Unit(unit.get("baseId"), unit.get("nameKey"))
            for unit in unit_list
            if skill_exists(skill, unit.get("skillReference"))
        ),
        None,
    )


# ── Guild omicron breakdown ─────────────────────────────────────────────


class OmicronMember(TypedDict):
    """One player's standing on a single omicron, as listed in :class:`OmicronSkillStats`."""

    player_id: str
    player_name: str
    tier: int | None
    """The tier the player has taken the skill to, or ``None`` when they own the unit but the skill is
    absent from their roster: a star-gated skill is left out until the unit reaches the rarity that
    unlocks it."""


class OmicronSkillStats(TypedDict):
    """Adoption of one omicron skill, as listed in :attr:`OmicronModeBreakdown.skills`.

    ``len(applied) + len(owned_not_applied) + not_owned_count`` always equals
    :attr:`OmicronBreakdown.total_members`.
    """

    skill_id: str
    """The game data ``skill`` id carrying the omicron tier."""
    skill_name_key: str | None
    """Localization key of the omicron's name, read from the ``ability`` the skill references. ``None``
    when no ``ability_list`` was given. The skill's own ``nameKey`` is a placeholder shared across
    unrelated skills (``DEFENSE_UP_NAME_KEY``) and is not used."""
    skill_name: str | None
    """Localized omicron name, when both ``ability_list`` and ``localization`` were given."""
    unit_base_id: str | None
    """The unit the skill belongs to, or ``None`` when no unit in ``unit_list`` references it."""
    unit_name_key: str | None
    unit_name: str | None
    """Localized unit name, when ``localization`` was given and holds the key."""
    omicron_tier: int
    """Index into the game data skill's ``tier`` list at which the omicron applies."""
    applied: list[OmicronMember]
    """Players who own the unit and have taken the skill to the omicron tier."""
    owned_not_applied: list[OmicronMember]
    """Players who own the unit but have not."""
    not_owned_count: int
    """Players who do not own the unit."""


class OmicronModeBreakdown(TypedDict):
    """Every omicron of one game mode, as listed in :attr:`OmicronBreakdown.modes`."""

    mode: int | str
    """The skills' ``omicronMode`` as a number (see ``OMICRON_MODE``), whether the game data was fetched
    with ``enums=True`` or not. A mode name the library does not know yet is kept as given."""
    mode_name: str
    """Label from ``mode_names``, or ``"Mode <mode>"`` when it has none."""
    skills: list[OmicronSkillStats]
    """Ordered by applied count, highest first, then by skill id."""


class OmicronBreakdown(TypedDict):
    """Omicron adoption across player profiles, as returned by :func:`get_omicron_breakdown`."""

    total_members: int
    """Number of player profiles the statistics cover."""
    modes: list[OmicronModeBreakdown]
    """Numbered modes in ascending order, then any mode kept as a name."""


def _omicron_mode(value: Any) -> int | str:
    """A skill's ``omicronMode`` as its number; a name missing from ``_OMICRON_MODES`` is kept as given."""
    raw = as_scalar(value)
    if raw is None:
        return 0  # proto3 leaves out a zero enum, so a missing mode is OmicronMode_DEFAULT.
    if isinstance(raw, int):
        return raw
    name = parse_enum(raw, _OMICRON_MODES, enum_name="OmicronMode")
    return _OMICRON_MODES[name] if name is not None else raw


def _omicron_tier_index(skill: dict[str, Any]) -> int | None:
    """The index of a game data skill's omicron tier, or ``None`` when it has none."""
    return next(
        (
            index
            for index, tier in enumerate(as_list(skill.get("tier")))
            if isinstance(tier, dict) and tier.get("isOmicronTier") is True
        ),
        None,
    )


def _owning_units(units: list[dict[str, Any]]) -> dict[str, tuple[str | None, str | None]]:
    """Map each skill id to the ``(baseId, nameKey)`` of the unit a player must own to have it.

    A skill is commonly referenced by several base ids: the playable unit, a non-obtainable ``PVE_``
    mirror the AI uses, and sometimes a raid or event variant. Only the playable unit can be in a
    roster, so resolving a skill to any other reports every player as not owning it. Playable units
    (:func:`get_playable_units`) are therefore read first; the rest only name skills no playable unit
    references. The first unit read wins, and the per-rarity rows of one unit agree.
    """
    owners: dict[str, tuple[str | None, str | None]] = {}
    for unit in (*get_playable_units(units), *units):
        identity = (as_str(unit.get("baseId")) or None, as_str(unit.get("nameKey")) or None)
        for reference in as_list(unit.get("skillReference")):
            skill_id = reference.get("skillId") if isinstance(reference, dict) else None
            if isinstance(skill_id, str):
                owners.setdefault(skill_id, identity)
    return owners


def _read_profile(profile: dict[str, Any]) -> tuple[set[str], dict[str, int]]:
    """A player profile's owned base ids and the tier of each skill in its roster."""
    owned: set[str] = set()
    tiers: dict[str, int] = {}
    for unit in as_list(profile.get("rosterUnit")):
        if not isinstance(unit, dict):
            continue
        if unit_id := base_id(unit.get("definitionId")):
            owned.add(unit_id)
        for skill in as_list(unit.get("skill")):
            if isinstance(skill, dict) and isinstance(skill_id := skill.get("id"), str):
                # A listed skill is unlocked; proto3 leaves out tier 0.
                tiers[skill_id] = as_int(skill.get("tier"))
    return owned, tiers


def get_omicron_breakdown(
    player_profiles: list[dict[str, Any]],
    skill_list: list[dict[str, Any]],
    unit_list: list[dict[str, Any]],
    *,
    ability_list: list[dict[str, Any]] | None = None,
    localization: dict[str, str] | None = None,
    mode_names: Mapping[int, str] | None = None,
) -> OmicronBreakdown:
    """Summarise omicron adoption across a set of player profiles, grouped by game mode.

    Every omicron skill in the game data becomes a row, whether or not anybody owns it, so the result
    also answers "which omicrons exist, by mode". Each row splits the players into those who have
    applied the omicron, those who own the unit but have not, and a count of those who do not own the
    unit.

    A skill is an omicron when one of its tiers is flagged ``isOmicronTier``. Its ``omicronMode`` only
    says where the omicron applies: skills without one carry mode 1 (``ALL_OMICRON``) by default.

    A player owns a unit when it is in their roster; whether the skill is listed there does not
    decide it, because a star-gated skill is left out until unlocked. Only when no unit in
    ``unit_list`` references a skill does a listed skill stand in for ownership.

    Args:
        player_profiles: Full player profiles, as returned by ``get_player()``. Guild member entries do
            not work: they carry no roster.
        skill_list: The game data ``skill`` collection.
        unit_list: The game data ``units`` collection, which names the unit owning each skill and so
            decides ownership. ``include_pve_units=False`` is enough.
        ability_list: Optional game data ``ability`` collection. It names each omicron, which matters
            because a unit often has several omicrons in one mode (Doctor Aphra has three in 5v5 Grand
            Arena) and the unit name alone does not tell them apart.
        localization: Optional localization dictionary, e.g. from :func:`get_localization_dictionary`,
            used for the unit and omicron names.
        mode_names: Optional labels for the mode numbers. [Default: ``OMICRON_MODE``, which does not
            name every mode; an unnamed mode is labelled ``"Mode <mode>"``]

    Returns:
        An :class:`OmicronBreakdown`. Players within a row are ordered by name, then by player id.

    Raises:
        SwgohComlinkValueError: If an argument has the wrong type, a profile has no ``playerId``, or two
            profiles share one.

    Examples:
        >>> game_data = comlink.get_game_data(
        ...     items=DataItems.SKILL | DataItems.UNITS | DataItems.ABILITY, include_pve_units=False
        ... )  # doctest: +SKIP
        >>> profiles = [comlink.get_player(player_id=m["playerId"]) for m in guild["member"]]  # doctest: +SKIP
        >>> breakdown = get_omicron_breakdown(
        ...     profiles, game_data["skill"], game_data["units"], ability_list=game_data["ability"]
        ... )  # doctest: +SKIP
    """
    for arg_name, arg in (("player_profiles", player_profiles), ("skill_list", skill_list), ("unit_list", unit_list)):
        if not isinstance(arg, list):
            raise SwgohComlinkValueError(f"{get_function_name()}: '{arg_name}' must be a list, not {type(arg)}")
    if ability_list is not None and not isinstance(ability_list, list):
        raise SwgohComlinkValueError(f"{get_function_name()}: 'ability_list' must be a list, not {type(ability_list)}")
    if localization is not None and not isinstance(localization, dict):
        raise SwgohComlinkValueError(
            f"{get_function_name()}: 'localization' must be a dictionary, not {type(localization)}"
        )
    if mode_names is not None and not isinstance(mode_names, Mapping):
        raise SwgohComlinkValueError(f"{get_function_name()}: 'mode_names' must be a mapping, not {type(mode_names)}")

    members: list[tuple[str, str, set[str], dict[str, int]]] = []
    seen: set[str] = set()
    for profile in player_profiles:
        if not isinstance(profile, dict):
            raise SwgohComlinkValueError(
                f"{get_function_name()}: every player profile must be a dictionary, not {type(profile)}"
            )
        player_id = as_str(profile.get("playerId"))
        if not player_id:
            raise SwgohComlinkValueError(f"{get_function_name()}: every player profile must carry a 'playerId'.")
        if player_id in seen:
            raise SwgohComlinkValueError(
                f"{get_function_name()}: duplicate 'playerId' {player_id!r} in 'player_profiles'."
            )
        seen.add(player_id)
        members.append((player_id, as_str(profile.get("name")), *_read_profile(profile)))
    members.sort(key=lambda member: (member[1], member[0]))

    labels = OMICRON_MODE if mode_names is None else mode_names
    owners = _owning_units([unit for unit in unit_list if isinstance(unit, dict)])
    ability_names = {
        ability["id"]: ability["nameKey"]
        for ability in ability_list or []
        if isinstance(ability, dict) and isinstance(ability.get("id"), str) and isinstance(ability.get("nameKey"), str)
    }

    by_mode: dict[int | str, list[OmicronSkillStats]] = {}
    for skill in skill_list:
        if not isinstance(skill, dict) or not isinstance(skill_id := skill.get("id"), str):
            continue
        if (omicron_tier := _omicron_tier_index(skill)) is None:
            continue
        unit_id, unit_name_key = owners.get(skill_id, (None, None))
        skill_name_key = ability_names.get(as_str(skill.get("abilityReference")))

        applied: list[OmicronMember] = []
        owned_not_applied: list[OmicronMember] = []
        for player_id, player_name, owned, tiers in members:
            if not (unit_id in owned if unit_id is not None else skill_id in tiers):
                continue
            tier = tiers.get(skill_id)
            member: OmicronMember = {"player_id": player_id, "player_name": player_name, "tier": tier}
            (applied if tier is not None and tier >= omicron_tier else owned_not_applied).append(member)

        by_mode.setdefault(_omicron_mode(skill.get("omicronMode")), []).append(
            {
                "skill_id": skill_id,
                "skill_name_key": skill_name_key,
                "skill_name": _localize(localization, skill_name_key, "") or None,
                "unit_base_id": unit_id,
                "unit_name_key": unit_name_key,
                "unit_name": _localize(localization, unit_name_key, "") or None,
                "omicron_tier": omicron_tier,
                "applied": applied,
                "owned_not_applied": owned_not_applied,
                "not_owned_count": len(members) - len(applied) - len(owned_not_applied),
            }
        )

    def mode_order(mode: int | str) -> tuple[bool, int, str]:
        return (True, 0, mode) if isinstance(mode, str) else (False, mode, "")

    return {
        "total_members": len(members),
        "modes": [
            {
                "mode": mode,
                "mode_name": (labels.get(mode) if isinstance(mode, int) else None) or f"Mode {mode}",
                "skills": sorted(stats, key=lambda s: (-len(s["applied"]), s["skill_id"])),
            }
            for mode, stats in sorted(by_mode.items(), key=lambda item: mode_order(item[0]))
        ],
    }
