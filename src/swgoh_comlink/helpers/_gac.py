# coding=utf-8
"""GAC (Grand Arena Championships) helper functions."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from ..exceptions import SwgohComlinkValueError
from ._constants import Constants
from ._sentinels import MISSING
from ._utils import get_function_name

logger = logging.getLogger(__name__)

_DEFAULT_INITIAL_STEP = 1024
_DEFAULT_BATCH_SIZE = 50

Leagues: tuple[str, ...] = tuple(Constants.LEAGUES.keys())


# ── Boundary probing helpers ──────────────────────────────────────────


def _find_bracket_boundary(probe_fn: Callable[[int], bool], initial_step: int = _DEFAULT_INITIAL_STEP) -> int:
    """Find the last non-empty bracket index using exponential probing + binary search.

    Args:
        probe_fn: Callable that accepts a bracket index and returns True if non-empty.
        initial_step: Starting probe index for the exponential phase.

    Returns:
        Index of the last non-empty bracket, or -1 if bracket 0 is empty.

    """
    if not probe_fn(0):
        return -1

    # Exponential phase: find an upper bound where probe returns False
    lo = 0
    hi = initial_step
    while probe_fn(hi):
        lo = hi
        hi *= 2

    # Binary search phase: narrow [lo, hi) to find exact boundary
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if probe_fn(mid):
            lo = mid
        else:
            hi = mid

    return lo


async def _async_find_bracket_boundary(
    probe_fn: Callable[[int], Any], initial_step: int = _DEFAULT_INITIAL_STEP
) -> int:
    """Async version of :func:`_find_bracket_boundary`.

    Args:
        probe_fn: Async callable that accepts a bracket index and returns True if non-empty.
        initial_step: Starting probe index for the exponential phase.

    Returns:
        Index of the last non-empty bracket, or -1 if bracket 0 is empty.

    """
    if not await probe_fn(0):
        return -1

    lo = 0
    hi = initial_step
    while await probe_fn(hi):
        lo = hi
        hi *= 2

    while lo < hi - 1:
        mid = (lo + hi) // 2
        if await probe_fn(mid):
            lo = mid
        else:
            hi = mid

    return lo


# ── Pure conversion helpers ───────────────────────────────────────────


def convert_league_to_int(league: str) -> int | None:
    """Convert GAC leagues to integer

    Args:
        league (str): GAC league name

    Returns:
        GAC league identifier as used in game data

    """
    if not isinstance(league, str) or not league:
        err_msg = f"{get_function_name()}: The 'league' argument is required."
        raise SwgohComlinkValueError(err_msg)

    return Constants.LEAGUES.get(league.lower())


def convert_divisions_to_int(division: int | str) -> int | None:
    """Convert GAC divisions to integer

    Args:
        division: GAC division ID as seen in game

    Returns:
        GAC division identifier as used within game data

    """
    if not isinstance(division, (str, int)) or (isinstance(division, str) and not division):
        err_msg = f"{get_function_name()}: The 'division' argument is required."
        raise SwgohComlinkValueError(err_msg)

    key = str(division) if isinstance(division, int) else division
    return Constants.DIVISIONS.get(key)


# ── Event helpers ─────────────────────────────────────────────────────


def get_current_gac_event(comlink: Any) -> dict[str, Any]:
    """Return the event object for the current gac season

    Args:
        comlink: Instance of SwgohComlink

    Returns:
        Current GAC event object

    Raises:
        SwgohComlinkValueError: If no active GAC event is found

    """
    comlink_type = getattr(comlink, "__comlink_type__", MISSING)
    if comlink is MISSING or comlink_type != "SwgohComlink":
        err_str = f"{get_function_name()}: comlink instance must be provided."
        raise SwgohComlinkValueError(err_str)

    current_events = comlink.get_events()

    gac_events: list[dict[str, Any]] = [event for event in current_events.get("gameEvent", []) if event["type"] == 10]
    if not gac_events:
        raise SwgohComlinkValueError(f"{get_function_name()}: No active GAC event found.")
    return gac_events[0]


async def async_get_current_gac_event(comlink: Any) -> dict[str, Any]:
    """Return the event object for the current gac season (async version).

    Args:
        comlink: Instance of SwgohComlinkAsync

    Returns:
        Current GAC event object

    Raises:
        SwgohComlinkValueError: If no active GAC event is found

    """
    comlink_type = getattr(comlink, "__comlink_type__", MISSING)
    if comlink is MISSING or comlink_type != "SwgohComlinkAsync":
        err_str = f"{get_function_name()}: async comlink instance must be provided."
        raise SwgohComlinkValueError(err_str)

    current_events = await comlink.get_events()

    gac_events: list[dict[str, Any]] = [event for event in current_events.get("gameEvent", []) if event["type"] == 10]
    if not gac_events:
        raise SwgohComlinkValueError(f"{get_function_name()}: No active GAC event found.")
    return gac_events[0]


# ── Bracket scanning ─────────────────────────────────────────────────


def get_gac_brackets(comlink: Any, league: str, limit: int = 0) -> dict[int, Any] | None:
    """Scan currently running GAC brackets for the requested league.

    Uses exponential probing with binary search to find the last non-empty
    bracket before fetching all bracket data.

    Args:
        comlink: Instance of SwgohComlink
        league: League to scan
        limit: Maximum number of brackets to return. 0 means no limit.

    Returns:
        Dictionary mapping bracket index to player list, or None if no GAC event is running.

    """
    comlink_type = getattr(comlink, "__comlink_type__", MISSING)
    if comlink is MISSING or comlink_type != "SwgohComlink":
        err_msg = f"{get_function_name()}: Invalid comlink instance."
        raise SwgohComlinkValueError(err_msg)

    if not isinstance(league, str):
        err_msg = f"{get_function_name()}: 'league' type <str> argument is required."
        raise SwgohComlinkValueError(err_msg)

    current_gac_event = get_current_gac_event(comlink)
    if not current_gac_event:
        return None

    event_instance = f"{current_gac_event['id']}:{current_gac_event['instance'][0]['id']}"

    def _probe(index: int) -> bool:
        group_id = f"{event_instance}:{league}:{index}"
        result = comlink.get_gac_leaderboard(leaderboard_type=4, event_instance_id=event_instance, group_id=group_id)
        return len(result["player"]) > 0

    last_bracket = _find_bracket_boundary(_probe)
    if last_bracket < 0:
        return {}

    end = min(last_bracket, limit - 1) if limit > 0 else last_bracket

    brackets: dict[int, Any] = {}
    for i in range(end + 1):
        group_id = f"{event_instance}:{league}:{i}"
        result = comlink.get_gac_leaderboard(leaderboard_type=4, event_instance_id=event_instance, group_id=group_id)
        brackets[i] = result["player"]

    return brackets


async def async_get_gac_brackets(comlink: Any, league: str, limit: int = 0) -> dict[int, Any] | None:
    """Scan currently running GAC brackets for the requested league (async version).

    Uses exponential probing with binary search to find the last non-empty
    bracket, then fetches all bracket data in parallel batches using
    ``asyncio.gather``.

    Args:
        comlink: Instance of SwgohComlinkAsync
        league: League to scan
        limit: Maximum number of brackets to return. 0 means no limit.

    Returns:
        Dictionary mapping bracket index to player list, or None if no GAC event is running.

    """
    comlink_type = getattr(comlink, "__comlink_type__", MISSING)
    if comlink is MISSING or comlink_type != "SwgohComlinkAsync":
        err_msg = f"{get_function_name()}: Invalid comlink instance."
        raise SwgohComlinkValueError(err_msg)

    if not isinstance(league, str):
        err_msg = f"{get_function_name()}: 'league' type <str> argument is required."
        raise SwgohComlinkValueError(err_msg)

    current_gac_event = await async_get_current_gac_event(comlink)
    if not current_gac_event:
        return None

    event_instance = f"{current_gac_event['id']}:{current_gac_event['instance'][0]['id']}"

    async def _probe(index: int) -> bool:
        group_id = f"{event_instance}:{league}:{index}"
        result = await comlink.get_gac_leaderboard(
            leaderboard_type=4, event_instance_id=event_instance, group_id=group_id
        )
        return len(result["player"]) > 0

    last_bracket = await _async_find_bracket_boundary(_probe)
    if last_bracket < 0:
        return {}

    end = min(last_bracket, limit - 1) if limit > 0 else last_bracket

    async def _fetch(index: int) -> tuple[int, list[Any]]:
        group_id = f"{event_instance}:{league}:{index}"
        result = await comlink.get_gac_leaderboard(
            leaderboard_type=4, event_instance_id=event_instance, group_id=group_id
        )
        return index, result["player"]

    brackets: dict[int, Any] = {}
    for start in range(0, end + 1, _DEFAULT_BATCH_SIZE):
        batch_end = min(start + _DEFAULT_BATCH_SIZE, end + 1)
        results = await asyncio.gather(*[_fetch(i) for i in range(start, batch_end)])
        for index, players in results:
            brackets[index] = players

    return brackets


# ── Bracket search ────────────────────────────────────────────────────


def search_gac_brackets(gac_brackets: dict[int, Any], player_name: str) -> dict[str, Any]:
    """Search the provided gac brackets data for a specific player

    Args:
        gac_brackets (dict): GAC bracket data to search
        player_name (str): Player name to search for

    Returns:
        dict: GAC bracket and player information or empty if no match is found

    """
    match_data: dict[str, Any] = {}
    for bracket in gac_brackets:
        for player in gac_brackets[bracket]:
            if player_name.lower() == player["name"].lower():
                match_data = {"player": player, "bracket": bracket}
    return match_data
