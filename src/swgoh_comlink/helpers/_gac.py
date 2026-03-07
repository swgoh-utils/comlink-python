# coding=utf-8
"""GAC (Grand Arena Championships) helper functions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..exceptions import SwgohComlinkValueError
from ._constants import Constants
from ._sentinels import MISSING, OPTIONAL, REQUIRED, NotSet
from ._utils import get_function_name

if TYPE_CHECKING:
    from swgoh_comlink import SwgohComlink, SwgohComlinkAsync  # noqa: F401

logger = logging.getLogger(__name__)


def convert_league_to_int(league: str | Any = REQUIRED) -> int | None:
    """Convert GAC leagues to integer

    Args:
        league (str): GAC league name

    Returns:
        GAC league identifier as used in game data

    """
    if league is MISSING or not league:
        err_msg = f"{get_function_name()}: The 'league' argument is required."
        raise SwgohComlinkValueError(err_msg)

    if isinstance(league, str) and league.lower() in Constants.LEAGUES:
        return Constants.LEAGUES[league.lower()]
    else:
        return None


def convert_divisions_to_int(division: int | str | Any = REQUIRED) -> int | None:
    """Convert GAC divisions to integer

    Args:
        division: GAC division ID as seen in game

    Returns:
        GAC division identifier as used within game data

    """
    if division is MISSING or not division:
        err_msg = f"{get_function_name()}: The 'division' argument is required."
        raise SwgohComlinkValueError(err_msg)

    if isinstance(division, str):
        if division in Constants.DIVISIONS:
            return Constants.DIVISIONS[division]
    if isinstance(division, int) and len(str(division)) == 1:
        if str(division) in Constants.DIVISIONS:
            return Constants.DIVISIONS[str(division)]
    return None


def get_current_gac_event(comlink: Any = REQUIRED) -> dict:
    """Return the event object for the current gac season

    Args:
        comlink: Instance of SwgohComlink

    Returns:
        Current GAC event object or empty if no event is running

    """
    if hasattr(comlink, "__comlink_type__"):
        comlink_type = comlink.__comlink_type__
    else:
        comlink_type = MISSING

    if comlink is MISSING or comlink_type is MISSING:
        err_str = f"{get_function_name()}: comlink instance must be provided."
        raise SwgohComlinkValueError(err_str)

    current_events = comlink.get_events()

    gac_events = [event for event in current_events["gameEvent"] if event["type"] == 10]
    if not gac_events:
        raise SwgohComlinkValueError(f"{get_function_name()}: No active GAC event found.")
    return gac_events[0]


def get_gac_brackets(
    comlink: Any = REQUIRED, league: str | Any = REQUIRED, limit: int | Any = OPTIONAL
) -> dict | None:
    """Scan currently running GAC brackets for the requested league and return them as a dictionary

    Args:
        comlink: Instance of SwgohComlink
        league: League to scan
        limit: Number of brackets to return

    Returns:
        Dictionary containing each GAC bracket as a key

    """
    if hasattr(comlink, "__comlink_type__"):
        comlink_type = comlink.__comlink_type__
    else:
        comlink_type = MISSING
    if comlink is MISSING or comlink_type != "SwgohComlink":
        err_msg = f"{get_function_name()}: Invalid comlink instance."
        raise SwgohComlinkValueError(err_msg)

    if league is MISSING or not isinstance(league, str):
        err_msg = f"{get_function_name()}: 'league' type <str> argument is required."
        raise SwgohComlinkValueError(err_msg)

    bracket_iteration_limit: int | None = None if limit is NotSet else int(limit)

    current_gac_event = get_current_gac_event(comlink)

    if current_gac_event:
        current_event_instance = f"{current_gac_event['id']}:{current_gac_event['instance'][0]['id']}"
    else:
        # No current GAC season running
        return None
    bracket = 0
    # Use brackets to store the results for each bracket for processing once all brackets have been scanned
    brackets: dict = {}
    number_of_players_in_bracket = 8
    while number_of_players_in_bracket > 0 and bracket_iteration_limit != bracket:
        group_id = f"{current_event_instance}:{league}:{bracket}"
        group_of_8_players = comlink.get_gac_leaderboard(
            leaderboard_type=4,
            event_instance_id=current_event_instance,
            group_id=group_id,
        )
        brackets[bracket] = brackets.get(bracket, group_of_8_players["player"])
        bracket += 1
        number_of_players_in_bracket = len(group_of_8_players["player"])
    return brackets


async def async_get_current_gac_event(comlink: Any = REQUIRED) -> dict:
    """Return the event object for the current gac season (async version).

    Args:
        comlink: Instance of SwgohComlinkAsync

    Returns:
        Current GAC event object or empty if no event is running

    """
    if hasattr(comlink, "__comlink_type__"):
        comlink_type = comlink.__comlink_type__
    else:
        comlink_type = MISSING

    if comlink is MISSING or comlink_type is MISSING:
        err_str = f"{get_function_name()}: comlink instance must be provided."
        raise SwgohComlinkValueError(err_str)

    current_events = await comlink.get_events()

    gac_events = [event for event in current_events["gameEvent"] if event["type"] == 10]
    if not gac_events:
        raise SwgohComlinkValueError(f"{get_function_name()}: No active GAC event found.")
    return gac_events[0]


async def async_get_gac_brackets(
    comlink: Any = REQUIRED, league: str | Any = REQUIRED, limit: int | Any = OPTIONAL
) -> dict | None:
    """Scan currently running GAC brackets for the requested league and return them as a dictionary (async version).

    Args:
        comlink: Instance of SwgohComlinkAsync
        league: League to scan
        limit: Number of brackets to return

    Returns:
        Dictionary containing each GAC bracket as a key

    """
    if hasattr(comlink, "__comlink_type__"):
        comlink_type = comlink.__comlink_type__
    else:
        comlink_type = MISSING
    if comlink is MISSING or comlink_type != "SwgohComlinkAsync":
        err_msg = f"{get_function_name()}: Invalid comlink instance."
        raise SwgohComlinkValueError(err_msg)

    if league is MISSING or not isinstance(league, str):
        err_msg = f"{get_function_name()}: 'league' type <str> argument is required."
        raise SwgohComlinkValueError(err_msg)

    bracket_iteration_limit: int | None = None if limit is NotSet else int(limit)

    current_gac_event = await async_get_current_gac_event(comlink)

    if current_gac_event:
        current_event_instance = f"{current_gac_event['id']}:{current_gac_event['instance'][0]['id']}"
    else:
        # No current GAC season running
        return None
    bracket = 0
    # Use brackets to store the results for each bracket for processing once all brackets have been scanned
    brackets: dict = {}
    number_of_players_in_bracket = 8
    while number_of_players_in_bracket > 0 and bracket_iteration_limit != bracket:
        group_id = f"{current_event_instance}:{league}:{bracket}"
        group_of_8_players = await comlink.get_gac_leaderboard(
            leaderboard_type=4,
            event_instance_id=current_event_instance,
            group_id=group_id,
        )
        brackets[bracket] = brackets.get(bracket, group_of_8_players["player"])
        bracket += 1
        number_of_players_in_bracket = len(group_of_8_players["player"])
    return brackets


def search_gac_brackets(gac_brackets: dict, player_name: str) -> dict:
    """Search the provided gac brackets data for a specific player

    Args:
        gac_brackets (dict): GAC bracket data to search
        player_name (str): Player name to search for

    Returns:
        dict: GAC bracket and player information or empty if no match is found

    """
    match_data: dict = {}
    for bracket in gac_brackets:
        for player in gac_brackets[bracket]:
            if player_name.lower() == player["name"].lower():
                match_data = {"player": player, "bracket": bracket}
    return match_data
