# coding=utf-8
"""Unit ability and named battle effect helper functions."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, TypedDict

from ..exceptions import SwgohComlinkValueError
from ._localization import _localize, parse_swgoh_string
from ._utils import get_function_name

# Skill id prefix -> ability kind. Matched case-insensitively: the game data has both
# 'contractskill_' and 'Contractskill_assajdarkdisciple'. The skill's own 'skillType' field is not
# this; it separates unit skills from crew skills.
_SKILL_KINDS = {
    "basicskill": "basic",
    "specialskill": "special",
    "uniqueskill": "unique",
    "leaderskill": "leader",
    "hardwareskill": "hardware",
    "contractskill": "contract",
}
# skill.tier[0] upgrades the ability from level 1 (its base text) to level 2.
_FIRST_TIER_LEVEL = 2

# A named effect's localization value opens with its name in colour markup, then a colon. The game
# writes it with the colon inside the closing tags ('[c][ffff33]Potency Up:[-][/c] ...') or after them
# ('[c][F0FF23]Overcharge[-][/c]: ...'), and sometimes with a space before it ('Provoked: [-][/c]').
# Anchoring on this shape is what separates 'Potency Up' from '+15% Accuracy' and from mission text.
_EFFECT_NAME = re.compile(r"^(?:\[c\])?\[[0-9a-fA-F]{6}\](?P<name>[^\[\]:]{1,40}?)(?::\s*\[-\]|(?:\[-\]|\[/c\])+\s*:)")
_VERSION_SUFFIX = re.compile(r"_V(?P<version>\d+)$")
# Demoralized has no BattleEffect_ key carrying the markup, only its stack tiers ..._DEBUFF_TIER0..7.
_TIER_EFFECT_KEY = re.compile(r"^.+_(?:DE)?BUFF_TIER(?P<tier>\d+)$")
# Core effects keyed outside the BattleEffect_ convention: FEAR_DEBUFF_DESC, ARMORSHRED_DEBUFF_V2, ...
_GENERIC_EFFECT_KEY = re.compile(r"_(?:DE)?BUFF(?:_DESC)?(?:_V(?P<version>\d+))?$")
# Per-unit effects with no BUFF marker at all: VIP (<unit>_VIP_ALLY) and Insight (MOFFGIDEON_INSIGHT).
_UNIT_EFFECT_KEY = re.compile(r"(?:_VIP_ALLY|_INSIGHT(?:_V(?P<version>\d+))?)$")


class AbilityTier(TypedDict):
    """One upgrade tier of a unit ability, as returned in :attr:`UnitAbility.tiers`."""

    level: int
    """The skill level this tier upgrades to. Level 1 is the base ability, so tiers start at 2."""
    description: str
    """The ability's full description at this level."""
    upgrade: str
    """What this tier adds, e.g. ``"+5% Damage"`` or the omicron's effect text."""
    is_zeta: bool
    is_omicron: bool


class UnitAbility(TypedDict):
    """A single unit ability as returned by :func:`get_unit_abilities`."""

    base_id: str
    """The unit the ability belongs to."""
    unit_name: str
    """Localized unit name, falling back to its ``nameKey``."""
    crew_base_id: str | None
    """For a ship's crew ability, the crew member it comes from; otherwise ``None``."""
    skill_id: str
    ability_id: str
    kind: str
    """``"basic"``, ``"special"``, ``"unique"``, ``"leader"``, ``"hardware"`` or ``"contract"``."""
    name: str
    description: str
    """The ability's level 1 description."""
    max_level: int
    zeta_level: int | None
    omicron_level: int | None
    omicron_mode: int | str | None
    """The skill's ``omicronMode`` (see ``OMICRON_MODE``), or ``None`` when it has no omicron tier."""
    tiers: list[AbilityTier]


class NamedEffect(TypedDict):
    """A named buff or debuff as returned by :func:`get_named_effects`."""

    name: str
    description: str
    key: str
    """The localization key the definition was read from."""


def _as_filter(value: Any, arg_name: str, item_types: tuple[type, ...]) -> set[Any] | None:
    """Normalize a scalar-or-list filter argument into a set, or ``None`` when not filtering."""
    if value is None:
        return None
    values = [value] if isinstance(value, item_types) else value
    if not isinstance(values, list) or not all(isinstance(v, item_types) for v in values):
        raise SwgohComlinkValueError(
            f"{get_function_name()}: '{arg_name}' must be a {' or '.join(t.__name__ for t in item_types)} "
            f"or a list of them, not {type(value)}"
        )
    return set(values)


def _build_ability(
    unit: dict[str, Any],
    unit_name: str,
    crew_base_id: str | None,
    skill: dict[str, Any],
    ability: dict[str, Any],
    text: Callable[[str | None], str],
) -> UnitAbility:
    """Join one skill with its ability record into a :class:`UnitAbility`."""
    skill_tiers = skill.get("tier") or []
    ability_tiers = ability.get("tier") or []
    base_description = text(ability.get("descKey"))

    tiers: list[AbilityTier] = []
    description = base_description
    for index, skill_tier in enumerate(skill_tiers):
        ability_tier = ability_tiers[index] if index < len(ability_tiers) else {}
        # A few abilities list fewer text tiers than their skill has upgrades; their text is unchanged.
        if ability_tier.get("descKey"):
            description = text(ability_tier["descKey"])
        tiers.append(
            {
                "level": index + _FIRST_TIER_LEVEL,
                "description": description,
                "upgrade": text(ability_tier.get("upgradeDescKey")),
                "is_zeta": bool(skill_tier.get("isZetaTier")),
                "is_omicron": bool(skill_tier.get("isOmicronTier")),
            }
        )

    zeta_level = next((t["level"] for t in tiers if t["is_zeta"]), None)
    omicron_level = next((t["level"] for t in tiers if t["is_omicron"]), None)
    prefix = skill["id"].split("_", 1)[0].lower()
    return {
        "base_id": unit.get("baseId", ""),
        "unit_name": unit_name,
        "crew_base_id": crew_base_id,
        "skill_id": skill["id"],
        "ability_id": ability.get("id", ""),
        "kind": _SKILL_KINDS.get(prefix, prefix.removesuffix("skill")),
        "name": text(ability.get("nameKey")),
        "description": base_description,
        "max_level": len(tiers) + 1,
        "zeta_level": zeta_level,
        "omicron_level": omicron_level,
        # Skills without an omicron tier report mode 1 (ALL), the unset default, not a real mode.
        "omicron_mode": skill.get("omicronMode") if omicron_level is not None else None,
        "tiers": tiers,
    }


def get_unit_abilities(
    units: list[dict[str, Any]],
    skills: list[dict[str, Any]],
    abilities: list[dict[str, Any]],
    localization: dict[str, str] | None = None,
    *,
    base_id: str | list[str] | None = None,
    omicron_mode: int | str | list[int | str] | None = None,
) -> list[UnitAbility]:
    """List units' abilities with their name, kind, per-level text and zeta/omicron tiers.

    Joins ``units`` -> ``skillReference`` -> ``skill`` -> ``abilityReference`` -> ``ability``. Text is
    read through the keys each ``ability`` record names, never derived from the ability id: after a
    rework the game moves the ability to new ``_V<n>`` keys and keeps the old lines, so a derived key
    returns the pre-rework text. For the same reason the name comes from ``ability.nameKey``;
    ``skill.nameKey`` is usually a placeholder such as ``DEFENSE_UP_NAME_KEY``.

    ``skill.tier[i]`` and ``ability.tier[i]`` describe the same upgrade, so whether a level is a zeta or
    an omicron is read from the same index as its text.

    A ship's crew abilities (``units.crew[].skillReference``) are included, with ``crew_base_id`` set.

    Args:
        units: The game data ``units`` collection. Each ``baseId`` is listed once, from its first row,
            so the raw per-rarity collection works; pass :func:`get_playable_units` output to leave out
            NPC and event units.
        skills: The game data ``skill`` collection.
        abilities: The game data ``ability`` collection.
        localization: Optional localization dictionary, e.g. from :func:`get_localization_dictionary`.
            When omitted, names and descriptions are returned as their localization keys.
        base_id: Restrict to one unit or a list of units (case-insensitive). [Default: all]
        omicron_mode: Restrict to abilities with an omicron in this mode or modes, e.g. ``8`` for
            Territory War (see ``OMICRON_MODE``). Compared with the raw ``omicronMode`` value, so pass
            enum names when the game data was fetched with ``enums=True``. [Default: all abilities]

    Returns:
        A list of :class:`UnitAbility` dictionaries, in ``units`` order and then each unit's
        ``skillReference`` order, followed by its crew abilities.

    Raises:
        SwgohComlinkValueError: If a collection is not a list, ``localization`` is not a dictionary, or a
            filter has the wrong type.

    Examples:
        >>> game_data = comlink.get_game_data(items=DataItems.UNITS | DataItems.SKILL | DataItems.ABILITY)  # doctest: +SKIP
        >>> loc = get_localization_dictionary(comlink)  # doctest: +SKIP
        >>> tw_omicrons = get_unit_abilities(
        ...     get_playable_units(game_data["units"]), game_data["skill"], game_data["ability"], loc,
        ...     omicron_mode=8,
        ... )  # doctest: +SKIP
    """
    for arg_name, arg in (("units", units), ("skills", skills), ("abilities", abilities)):
        if not isinstance(arg, list):
            raise SwgohComlinkValueError(f"{get_function_name()}: '{arg_name}' must be a list, not {type(arg)}")
    if localization is not None and not isinstance(localization, dict):
        raise SwgohComlinkValueError(
            f"{get_function_name()}: 'localization' must be a dictionary, not {type(localization)}"
        )
    base_ids = _as_filter(base_id, "base_id", (str,))
    if base_ids is not None:
        base_ids = {b.upper() for b in base_ids}
    modes = _as_filter(omicron_mode, "omicron_mode", (int, str))

    skill_map = {skill["id"]: skill for skill in skills}
    ability_map = {ability["id"]: ability for ability in abilities}

    # Many tiers share a description key, and parsing markup is the expensive step.
    cache: dict[str, str] = {}

    def text(key: str | None) -> str:
        if not key:
            return ""
        if key not in cache:
            cache[key] = _localize(localization, key, key)
        return cache[key]

    seen: set[str] = set()
    result: list[UnitAbility] = []
    for unit in units:
        unit_id = unit.get("baseId", "")
        if unit_id in seen or (base_ids is not None and unit_id.upper() not in base_ids):
            continue
        seen.add(unit_id)
        unit_name = _localize(localization, unit.get("nameKey"), unit.get("nameKey") or unit_id)
        references = [(ref, None) for ref in unit.get("skillReference") or []] + [
            (ref, crew.get("unitId")) for crew in unit.get("crew") or [] for ref in crew.get("skillReference") or []
        ]
        for reference, crew_base_id in references:
            skill = skill_map.get(reference.get("skillId", ""))
            if skill is None or (ability := ability_map.get(skill.get("abilityReference", ""))) is None:
                continue
            if modes is not None and (
                skill.get("omicronMode") not in modes
                or not any(tier.get("isOmicronTier") for tier in skill.get("tier") or [])
            ):
                continue
            result.append(_build_ability(unit, unit_name, crew_base_id, skill, ability, text))
    return result


def _effect_key_rank(key: str) -> tuple[int, int] | None:
    """How authoritative a localization key is as a named effect's definition, or ``None`` if it is not one.

    Higher wins when a name is defined under several keys: ``BattleEffect_*`` first (any case; Concussion
    Mine is ``Battleeffect_ConcussionMine``), then stack-tier keys with tier 0 preferred, then the generic
    ``_(DE)BUFF`` and per-unit families. Within a family the highest ``_V<n>`` wins, because a reworked
    effect keeps its original wording under the unversioned key.
    """
    if key.lower().startswith("battleeffect_"):
        version = _VERSION_SUFFIX.search(key)
        return (2, int(version["version"]) if version else 0)
    if (match := _TIER_EFFECT_KEY.match(key)) is not None:
        return (1, -int(match["tier"]))
    if (match := _GENERIC_EFFECT_KEY.search(key) or _UNIT_EFFECT_KEY.search(key)) is not None:
        return (0, int(match["version"] or 0))
    return None


def get_named_effects(localization: dict[str, str]) -> dict[str, NamedEffect]:
    """Map every named buff and debuff (Potency Up, Fear, Overcharge, ...) to its description.

    A named effect is a localization value that opens with the effect's name in the game's colour markup
    followed by a colon, e.g. ``[c][ffff33]Potency Up:[-][/c] Increased chance to apply detrimental
    effects``. Stat lines such as ``+15% Accuracy`` are excluded. Most effects are keyed
    ``BattleEffect_*``, but several core ones are not: Fear and Armor Shred are keyed
    ``<NAME>_(DE)BUFF[_DESC][_V<n>]``, Demoralized only under its stack tiers
    (``DEMORALIZED_DEBUFF_TIER0``...), and VIP and Insight under unit-specific keys. All of these are read.
    When a name is defined more than once, the ``BattleEffect_`` key and then the highest ``_V<n>`` wins.

    The key conventions are language-independent, so any language's dictionary works; names are then in
    that language.

    Args:
        localization: A localization dictionary, e.g. from :func:`get_localization_dictionary`.

    Returns:
        A dictionary of effect name to :class:`NamedEffect`, sorted by name.

    Raises:
        SwgohComlinkValueError: If ``localization`` is not a dictionary.

    Examples:
        >>> effects = get_named_effects(get_localization_dictionary(comlink))  # doctest: +SKIP
        >>> effects["Potency Up"]["description"]  # doctest: +SKIP
        'Increased chance to apply detrimental effects'
    """
    if not isinstance(localization, dict):
        raise SwgohComlinkValueError(
            f"{get_function_name()}: 'localization' must be a dictionary, not {type(localization)}"
        )

    best: dict[str, tuple[tuple[int, int], str, str]] = {}
    for key, value in localization.items():
        if not isinstance(value, str) or (rank := _effect_key_rank(key)) is None:
            continue
        if (match := _EFFECT_NAME.match(value)) is None:
            continue
        name = match["name"].strip()
        if not name or name.startswith(("+", "-")) or "%" in name:
            continue
        if name not in best or best[name][0] < rank:
            best[name] = (rank, key, value)

    return {
        name: {
            "name": name,
            "description": parse_swgoh_string(value).split(":", 1)[-1].strip(),
            "key": key,
        }
        for name, (_, key, value) in sorted(best.items())
    }
