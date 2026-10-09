# coding=utf-8
"""Conquest helper functions."""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from math import ceil, floor
from typing import Any, TypedDict

from ..exceptions import SwgohComlinkValueError
from ._localization import _localize
from ._utils import _as_int, get_function_name

# Roman numeral in a feat challenge id -> difficulty name (I = Easy, II = Normal, III = Hard)
_FEAT_TIERS = {"I": "Easy", "II": "Normal", "III": "Hard"}
_FEAT_TIER_ORDER = {name: i for i, name in enumerate(_FEAT_TIERS.values())}
_FEAT_KINDS = {"EVENT": "Global", "SECTOR": "Sector", "MINIBOSS": "Mini-Boss", "BOSS": "Boss"}
_FEAT_KIND_ORDER = {label: i for i, label in enumerate(_FEAT_KINDS.values())}
# ItemType reward values, as integers (enums=False) or names (enums=True)
_CONQUEST_POINT = {22, "CONQUEST_POINT"}
_ARTIFACT = {23, "ARTIFACT"}


class ConquestFeat(TypedDict):
    """A single Conquest feat as returned by :func:`get_conquest_feats`."""

    difficulty: str
    """``"Easy"``, ``"Normal"`` or ``"Hard"``."""
    scope: str
    """``"Global"`` for event-wide feats, otherwise the sector title (e.g. ``"Sector 1"``)."""
    sector_id: str | None
    """Sector id (``"S0"`` .. ``"S4"``), or ``None`` for global feats."""
    kind: str
    """``"Global"``, ``"Sector"``, ``"Mini-Boss"`` or ``"Boss"``."""
    name: str
    description: str
    keycards: int
    reward_artifact_id: str | None
    reward_artifact: str | None
    """Localized artifact name, falling back to its id when no name can be resolved."""
    challenge_id: str


def calc_current_stamina(unit: dict[str, Any], pass_plus: bool = False) -> int:
    """
    Calculates the current stamina of a game unit based on the elapsed time since the last refresh.
    The calculation considers a unit's last recorded stamina value, the time that has passed since it
    was last refreshed, and the optional influence of Conquest Pass+ (which accelerates stamina recovery by 33%).

    Parameters:
    unit (dict[str, Any]): A dictionary containing the unit's data, including "remainingStamina" and "lastRefreshTime".
    pass_plus (bool): A flag indicating whether the Conquest Pass+ is active. Defaults to False.

    Returns:
    int: The calculated current stamina value, capped at a maximum of 100.

    Raises:
    SwgohComlinkValueError: If 'unit' is not a dictionary.
    SwgohComlinkValueError: If the unit dictionary does not contain valid "remainingStamina" or "lastRefreshTime" fields.
    """

    if not isinstance(unit, dict):
        raise SwgohComlinkValueError(f"'unit' must be a dict, not {type(unit)}")

    acceleration_factor = 1.33 if pass_plus else 1.0
    raw_stamina = unit.get("remainingStamina")
    raw_refresh = unit.get("lastRefreshTime")

    if raw_stamina is None or raw_refresh is None:
        raise SwgohComlinkValueError("Invalid unit data. Unable to determine current stamina and/or last refresh time.")

    remaining_stamina: int = int(raw_stamina)
    last_refresh_time: int = int(raw_refresh)

    time_diff_minutes = floor((floor(time.time()) - last_refresh_time) / 60)

    # Stamina regenerates 1% every 30 minutes
    # Conquest Pass+ holders increase stamina regeneration by 33%

    return min(floor(time_diff_minutes / 30 * acceleration_factor) + remaining_stamina, 100)


def calc_stamina_full_time(unit: dict[str, Any], pass_plus: bool = False, *, now: datetime | None = None) -> datetime:
    """Calculate when a unit's Conquest stamina reaches 100.

    Uses the same model as :func:`calc_current_stamina`: stamina regenerates 1 point every 30 minutes
    (33% faster with Conquest Pass+) from ``remainingStamina`` at ``lastRefreshTime``, an epoch time in
    seconds. For a unit with a ``lastRefreshTime`` that is not in the future, :func:`calc_current_stamina`
    returns 100 from the returned moment on.

    A missing ``lastRefreshTime`` (an older payload) or one ahead of ``now`` (a clock running ahead) is
    not treated as elapsed regeneration in either direction: the unit is counted as last refreshed at
    ``now``.

    Args:
        unit: A ``unitStamina`` entry from a player's Conquest status, with ``remainingStamina`` and,
            usually, ``lastRefreshTime``.
        pass_plus: Whether Conquest Pass+ is active. [Default: False]
        now: The current time. A naive value is read as local time. Defaults to the current time.

    Returns:
        The moment stamina reaches 100, as a timezone-aware UTC datetime with whole seconds. For a unit
        that was already full this is in the past (or equal to ``now``); compare it with ``now`` to get
        the time remaining.

    Raises:
        SwgohComlinkValueError: If ``unit`` is not a dictionary or has no valid ``remainingStamina``.

    Examples:
        >>> from datetime import datetime, timezone
        >>> unit = {"remainingStamina": 90, "lastRefreshTime": "1790164800"}
        >>> calc_stamina_full_time(unit, now=datetime(2026, 9, 23, 13, tzinfo=timezone.utc))
        datetime.datetime(2026, 9, 23, 17, 0, tzinfo=datetime.timezone.utc)
    """
    if not isinstance(unit, dict):
        raise SwgohComlinkValueError(f"{get_function_name()}: 'unit' must be a dict, not {type(unit)}")
    remaining = _as_int(unit.get("remainingStamina"), -1)
    if remaining < 0:
        raise SwgohComlinkValueError(f"{get_function_name()}: 'unit' has no valid 'remainingStamina'.")

    now = datetime.now(timezone.utc) if now is None else now.astimezone(timezone.utc)
    # Whole seconds, as lastRefreshTime and calc_current_stamina count them
    now_seconds = floor(now.timestamp())
    last_refresh = _as_int(unit.get("lastRefreshTime"))
    if last_refresh <= 0 or last_refresh > now_seconds:
        last_refresh = now_seconds

    factor = 1.33 if pass_plus else 1.0
    missing = max(0, 100 - remaining)
    # The fewest whole minutes for which calc_current_stamina's floor(minutes / 30 * factor) covers the
    # missing points, nudged to absorb float rounding in the estimate.
    minutes = ceil(missing * 30 / factor)
    while floor(minutes / 30 * factor) < missing:
        minutes += 1
    while minutes > 0 and floor((minutes - 1) / 30 * factor) >= missing:
        minutes -= 1
    return datetime.fromtimestamp(last_refresh + minutes * 60, tz=timezone.utc)


def get_conquest_feats(
    conquest_definitions: list[dict[str, Any]],
    challenges: list[dict[str, Any]],
    localization: dict[str, str] | None = None,
    artifact_definitions: list[dict[str, Any]] | None = None,
    *,
    conquest_id: str | None = None,
    difficulty: str | None = None,
) -> list[ConquestFeat]:
    """List the feats for a Conquest event, covering both global and per-sector feats.

    Feats are not referenced from ``conquestDefinition``; they are linked to an event only by the
    ``challenge`` id convention ``<CONQUEST_ID>_[<KIND>_]<NAME>_<I|II|III>_DIFF[_S<n>]``, where KIND is
    ``EVENT`` (global feat, no sector suffix), ``SECTOR``, ``MINIBOSS`` or ``BOSS``, and the roman
    numeral is the difficulty (I = Easy, II = Normal, III = Hard). Many feats, mostly in older
    conquests, have no KIND token (``CONQUEST_VOL23_SILVO_VANE_III_DIFF_S0``); their kind is
    ``"Sector"`` when the id has a sector suffix and ``"Global"`` otherwise.

    Args:
        conquest_definitions: The game data ``conquestDefinition`` collection.
        challenges: The game data ``challenge`` collection.
        localization: Optional localization dictionary, e.g. from :func:`get_localization_dictionary`.
            When omitted, names and descriptions are returned as their localization keys.
        artifact_definitions: Optional game data ``artifactDefinition`` collection, used to resolve
            reward artifact names.
        conquest_id: Conquest id (e.g. ``"CONQUEST_VOL25"``, case-insensitive). Game data has no event
            calendar, so this defaults to the newest conquest: the last ``conquestDefinition`` entry.
        difficulty: Restrict to ``"easy"``, ``"normal"`` or ``"hard"`` (case-insensitive). [Default: all]

    Returns:
        A list of :class:`ConquestFeat` dictionaries ordered by difficulty, then global feats before
        sector feats, then sector, feat kind and name.

    Raises:
        SwgohComlinkValueError: If an argument is not a list, ``difficulty`` is not recognized, or
            ``conquest_id`` does not match any conquest definition.

    Examples:
        >>> game_data = comlink.get_game_data(items=DataItems.CHALLENGE | DataItems.CONQUEST)  # doctest: +SKIP
        >>> loc = get_localization_dictionary(comlink)  # doctest: +SKIP
        >>> feats = get_conquest_feats(
        ...     game_data["conquestDefinition"], game_data["challenge"], loc,
        ...     game_data["artifactDefinition"], difficulty="hard",
        ... )  # doctest: +SKIP
    """
    for arg_name, arg in (("conquest_definitions", conquest_definitions), ("challenges", challenges)):
        if not isinstance(arg, list):
            raise SwgohComlinkValueError(f"{get_function_name()}: '{arg_name}' must be a list, not {type(arg)}")
    if not conquest_definitions:
        raise SwgohComlinkValueError(f"{get_function_name()}: 'conquest_definitions' is empty.")

    difficulty_filter = None
    if difficulty is not None:
        difficulty_filter = difficulty.capitalize()
        if difficulty_filter not in _FEAT_TIER_ORDER:
            err_msg = (
                f"{get_function_name()}: unknown difficulty {difficulty!r}. Expected one of {list(_FEAT_TIER_ORDER)}."
            )
            raise SwgohComlinkValueError(err_msg)

    if conquest_id is None:
        conquest = conquest_definitions[-1]
    else:
        conquest = next((c for c in conquest_definitions if c["id"].upper() == conquest_id.upper()), None)
        if conquest is None:
            known = ", ".join(c["id"] for c in conquest_definitions)
            raise SwgohComlinkValueError(f"{get_function_name()}: unknown conquest {conquest_id!r}. Known: {known}")

    sector_titles = {
        sector["id"]: _localize(localization, sector.get("titleKey"), sector["id"].upper()).title()
        for conquest_difficulty in conquest.get("conquestDifficulty", [])
        for sector in conquest_difficulty.get("sector", [])
    }
    artifact_names = {
        artifact["id"]: _localize(localization, artifact.get("nameKey"), artifact["id"])
        for artifact in artifact_definitions or []
    }
    pattern = re.compile(
        rf"^{re.escape(conquest['id'])}_(?:(EVENT|SECTOR|MINIBOSS|BOSS)_)?.+?_(I{{1,3}})_DIFF(?:_(S\d+))?$",
        re.IGNORECASE,
    )

    feats: list[ConquestFeat] = []
    for challenge in challenges:
        if not (match := pattern.match(challenge.get("id", ""))):
            continue
        kind, tier, sector_id = match.groups()
        feat_difficulty = _FEAT_TIERS[tier.upper()]
        if difficulty_filter and feat_difficulty != difficulty_filter:
            continue
        rewards = challenge.get("reward") or []
        artifact_id = next((r["id"] for r in rewards if r.get("type") in _ARTIFACT), None)
        feats.append(
            {
                "difficulty": feat_difficulty,
                "scope": sector_titles.get(sector_id, sector_id) if sector_id else "Global",
                "sector_id": sector_id,
                "kind": _FEAT_KINDS[kind.upper()] if kind else "Sector" if sector_id else "Global",
                "name": _localize(localization, challenge.get("nameKey"), challenge.get("nameKey", "")),
                "description": _localize(localization, challenge.get("descKey"), challenge.get("descKey", "")),
                "keycards": sum(int(r.get("maxQuantity", 0)) for r in rewards if r.get("type") in _CONQUEST_POINT),
                "reward_artifact_id": artifact_id,
                "reward_artifact": artifact_names.get(artifact_id, artifact_id) if artifact_id else None,
                "challenge_id": challenge["id"],
            }
        )

    feats.sort(
        key=lambda f: (
            _FEAT_TIER_ORDER[f["difficulty"]],
            f["sector_id"] is not None,
            f["sector_id"] or "",
            _FEAT_KIND_ORDER[f["kind"]],
            f["name"],
        )
    )
    return feats
