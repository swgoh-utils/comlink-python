# coding=utf-8
"""
Helper utilities for the swgoh_comlink package and related modules
"""

from __future__ import annotations

import asyncio
import inspect
import os
import time
from functools import wraps
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING

from sentinels import Sentinel

from .constants import (
    get_logger,
    LEAGUES,
    DIVISIONS,
    RELIC_TIERS,
    DATA_PATH,
    GIVEN,
    REQUIRED,
    MutualExclusiveRequired,
)

if TYPE_CHECKING:
    from swgoh_comlink import SwgohComlink, SwgohComlinkAsync

logger = get_logger()

__all__ = [
    "convert_divisions_to_int",
    "convert_league_to_int",
    "convert_relic_tier",
    "create_localized_unit_name_dictionary",
    "func_debug_logger",
    "func_timer",
    "get_async_player",
    "get_async_events",
    "get_current_datacron_sets",
    "get_current_gac_event",
    "get_gac_brackets",
    "get_guild_members",
    "get_tw_omicrons",
    "human_time",
    "load_master_map",
    "sanitize_allycode",
    "search_gac_brackets",
    "validate_file_path",
]


def _get_function_name() -> str:
    """Return the name for the calling function"""
    return f"{inspect.stack()[1].function}()"


def func_timer(f):
    """Decorator for timing function calls"""

    @wraps(f)
    def wrap(*args, **kw):
        """Wrapper function"""
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()
        logger.debug(f"func:{f.__name__} took: {te - ts:.6f} sec")
        return result

    return wrap


def func_debug_logger(f):
    """Decorator for applying debug logging to a function"""

    @wraps(f)
    def wrap(*args, **kw):
        """Wrapper function"""
        logger.debug(
            "  [ function %s ] called with args: %s and kwargs: %s",
            f.__name__,
            args,
            kw,
        )
        result = f(*args, **kw)
        return result

    return wrap


def validate_file_path(path: str | Path | PathLike | Sentinel = REQUIRED) -> bool:
    """Test whether provided path exists or not

    Args:
        path: path of file to validate

    Returns:
        True if exists, False otherwise.

    """
    if path is not GIVEN and not path:
        err_msg = f"{_get_function_name()}: 'path' argument is required."
        logger.error(err_msg)
        raise ValueError(err_msg)
    return os.path.exists(path) and os.path.isfile(path)


def sanitize_allycode(allycode: str | int | Sentinel = REQUIRED) -> str:
    """Sanitize a player allycode

    Ensure that allycode does not:
        - contain dashes
        - is the proper length
        - contains only digits

    Args:
        allycode: Player allycode to sanitize

    Returns:
        Player allycode in the proper format

    """
    _orig_ac = allycode
    if not allycode and allycode is not GIVEN:
        logger.warning(f"{_get_function_name()}: no allycode input provided. Returning empty string.")
        return str()
    if isinstance(allycode, int):
        allycode = str(allycode)
    if "-" in str(allycode):
        allycode = allycode.replace("-", "")
    if not allycode.isdigit() or len(allycode) != 9:
        err_msg = f"{_get_function_name()}: Invalid ally code: {allycode}"
        logger.error(err_msg)
        raise ValueError(err_msg)
    logger.debug(f"{_get_function_name()}: {_orig_ac} allycode sanitized to: {allycode}")
    return allycode


def human_time(unix_time: int | float | Sentinel = REQUIRED) -> str:
    """Convert unix time to human-readable string

    Args:
        unix_time (int|float): standard unix time in seconds or milliseconds

    Returns:
        str: human-readable time string

    Notes:
        If the provided unix time is invalid or an error occurs, the default time string returned
        is 1970-01-01 00:00:00

    """
    print(f"unix_time: {unix_time}")
    if unix_time is not GIVEN and not str(unix_time):
        err_msg = f"{_get_function_name()}: The 'unix_time' argument is required."
        logger.error(err_msg)
        raise ValueError(err_msg)
    from datetime import datetime, timezone
    if isinstance(unix_time, float):
        unix_time = int(unix_time)
    if isinstance(unix_time, str):
        try:
            unix_time = int(unix_time)
        except Exception as exc:
            logger.exception(f"Exception caught: [{exc}]")
            return datetime.fromtimestamp(0, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
    if len(str(unix_time)) >= 13:
        unix_time /= 1000
    return datetime.fromtimestamp(unix_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def convert_league_to_int(league: str | Sentinel = REQUIRED) -> int | None:
    """Convert GAC leagues to integer

    Args:
        league (str): GAC league name

    Returns:
        GAC league identifier as used in game data

    """
    if league is not GIVEN and not league:
        err_msg = f"{_get_function_name()}: The 'league' argument is required."
        logger.error(err_msg)
        raise ValueError(err_msg)

    if isinstance(league, str) and league.lower() in LEAGUES:
        return LEAGUES[league.lower()]
    else:
        return None


def convert_divisions_to_int(division: int | str | Sentinel = REQUIRED) -> int | None:
    """Convert GAC divisions to integer

    Args:
        division: GAC division ID as seen in game

    Returns:
        GAC division identifier as used within game data

    """
    if division is not GIVEN and not division:
        err_msg = f"{_get_function_name()}: The 'division' argument is required."
        logger.error(err_msg)
        raise ValueError(err_msg)

    if isinstance(division, str):
        if division in DIVISIONS:
            return DIVISIONS[division]
    if isinstance(division, int) and len(str(division)) == 1:
        if str(division) in DIVISIONS:
            return DIVISIONS[str(division)]
    return None


def convert_relic_tier(relic_tier: str | int | Sentinel = REQUIRED) -> str | None:
    """Convert character relic tier to offset string in-game value.

    Conversion is done based on a zero based table indicating both the relic tier status and achieved level.

    Args:
        relic_tier (str | int): The relic tier from character game data to convert to in-game equivalent.

    Returns:
        String representing the relic status and tier

    Raises:
        TypeError: If the provided 'relic_tier' cannot be converted to a string using the Python
                    built-in str() method.

    Examples:
        Relic tier is '0' indicates the character has not yet achieved a level where access to relics have been
            unlocked.
        Relic tier of '1', indicates that the character has achieved the required level to access relics,
            but has not yet upgraded to the first level.
    """
    if not isinstance(relic_tier, str) and not isinstance(relic_tier, int):
        err_msg = f"{_get_function_name()}: 'relic_tier' argument is required for conversion."
        logger.error(err_msg)
        raise ValueError(err_msg)
    relic_value = None
    if isinstance(relic_tier, int):
        relic_tier = str(relic_tier)
    if relic_tier in RELIC_TIERS:
        relic_value = RELIC_TIERS[relic_tier]
    return relic_value


def create_localized_unit_name_dictionary(locale: str | list | Sentinel = REQUIRED) -> dict:
    """Create localized translation mapping for unit names

    Take a localization element from the SwgohComlink.get_localization() result dictionary and
    extract the UNIT_NAME entries for building a conversion dictionary to translate BASEID values to in game
    descriptive names

    Args:
        locale: The string element or List[bytes] from the SwgohComlink.get_localization()
                                        result key value

    Returns:
        A dictionary with the UNIT_NAME BASEID as keys and the UNIT_NAME description as values

    """
    if not isinstance(locale, list) and not isinstance(locale, str):
        err_msg = f"{_get_function_name()}: locale must be a list of strings or string containing newlines."
        logger.error(err_msg)
        raise ValueError(err_msg)

    unit_name_map = {}
    lines = []
    if isinstance(locale, str):
        lines = locale.split("\n")
    elif isinstance(locale, list):
        lines = locale
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode()
        line = line.rstrip("\n")
        if line.startswith("#") or "|" not in line:
            continue
        if line.startswith("UNIT_"):
            name_key, desc = line.split("|")
            if name_key.endswith("_NAME"):
                unit_name_map[name_key] = desc
    return unit_name_map


async def get_async_player(comlink: SwgohComlinkAsync,
                           *,
                           player_id: str | Sentinel = MutualExclusiveRequired,
                           allycode: str | Sentinel = MutualExclusiveRequired) -> dict | None:
    if not isinstance(comlink, SwgohComlinkAsync):
        err_msg = (f"{_get_function_name()}: The 'comlink' argument is required and must be an "
                   f"instance of SwgohComlinkAsync.")
        logger.error(err_msg)
        raise ValueError(err_msg)

    if player_id is not MutualExclusiveRequired and allycode is not MutualExclusiveRequired:
        err_msg = f"{_get_function_name()}: Either 'player_id' or 'allycode' are allowed arguments, not both."
        logger.error(err_msg)
        raise ValueError(err_msg)

    if player_id is MutualExclusiveRequired and allycode is MutualExclusiveRequired:
        err_msg = f"{_get_function_name()}: One of either 'player_id' or 'allycode' is required."
        logger.error(err_msg)
        raise ValueError(err_msg)

    if player_id is not MutualExclusiveRequired and isinstance(player_id, str):
        return await comlink.get_player(player_id=player_id)
    elif allycode is not MutualExclusiveRequired and isinstance(allycode, str):
        return await comlink.get_player(allycode=allycode)
    else:
        logger.error(f"{_get_function_name()}: Unexpected condition encountered. Returning <None>")
        logger.debug(f"{_get_function_name()}: {player_id=}, {allycode=}")
        return None


def get_guild_members(
        comlink: SwgohComlink | SwgohComlinkAsync | Sentinel = REQUIRED,
        player_id: str | Sentinel = MutualExclusiveRequired,
        allycode: str | int | Sentinel = MutualExclusiveRequired,
) -> list[dict] | None:
    """Return list of guild member player allycodes based upon provided player ID or allycode

    Args:
        comlink: Instance of SwgohComlink or SwgohComlinkAsync
        player_id: Player's ID
        allycode: Player's allycode

    Returns:
        list of guild members objects

    Note:
        A player_id or allycode argument is REQUIRED

    """
    if not isinstance(comlink, SwgohComlinkAsync) and not isinstance(comlink, SwgohComlink):
        err_msg = (f"{_get_function_name()}: The 'comlink' argument is required and must be an "
                   f"instance of SwgohComlinkAsync.")
        logger.error(err_msg)
        raise ValueError(err_msg)

    if player_id is not MutualExclusiveRequired and allycode is not MutualExclusiveRequired:
        err_msg = f"{_get_function_name()}: Either 'player_id' or 'allycode' are allowed arguments, not both."
        logger.error(err_msg)
        raise ValueError(err_msg)

    if player_id is MutualExclusiveRequired and allycode is MutualExclusiveRequired:
        err_msg = f"{_get_function_name()}: One of either 'player_id' or 'allycode' is required."
        logger.error(err_msg)
        raise ValueError(err_msg)

    if isinstance(comlink, SwgohComlink):  # noqa: type
        if isinstance(player_id, str):
            player = comlink.get_player(player_id=player_id)
        else:
            player = comlink.get_player(allycode=sanitize_allycode(allycode))
        guild = comlink.get_guild(guild_id=player["guildId"])
    elif isinstance(comlink, SwgohComlinkAsync):  # noqa: type
        if isinstance(player_id, str):
            player = asyncio.run(get_async_player(comlink=comlink, player_id=player_id))
        else:
            player = asyncio.run(get_async_player(comlink=comlink, allycode=allycode))
        guild = asyncio.run(comlink.get_guild(guild_id=player["guildId"]))
    else:
        logger.error(f"{_get_function_name()}: Invalid comlink instance.")
        raise ValueError(f"{_get_function_name()}: Invalid comlink instance")
    return guild["member"]


async def get_async_events(comlink: SwgohComlinkAsync | Sentinel = REQUIRED) -> dict:
    if isinstance(comlink, Sentinel) or isinstance(comlink, SwgohComlink):
        raise ValueError(f"{_get_function_name()}: async comlink instance must be provided.")
    return await comlink.get_events()


def get_current_gac_event(comlink: SwgohComlink | SwgohComlinkAsync | Sentinel = REQUIRED) -> dict:
    """Return the event object for the current gac season

    Args:
        comlink: Instance of SwgohComlink

    Returns:
        Current GAC event object or empty if no event is running

    """
    if isinstance(comlink, Sentinel):
        raise ValueError(f"{_get_function_name()}: comlink instance must be provided.")

    current_gac_event: dict = {}
    if isinstance(comlink, SwgohComlink):  # type: ignore
        current_events: dict[str, list] = comlink.get_events()
    elif isinstance(comlink, SwgohComlinkAsync):
        current_events: dict[str, list] = asyncio.run(get_async_events(comlink))
    else:
        raise ValueError(f"{_get_function_name()} Invalid comlink instance")
    for event in current_events["gameEvent"]:
        if event["type"] == 10:
            current_gac_event = event
            break
    return current_gac_event


def get_gac_brackets(comlink: SwgohComlink, league: str) -> dict | None:
    """Scan currently running GAC brackets for the requested league and return them as a dictionary

    Args:
        comlink: Instance of SwgohComlink
        league: League to scan

    Returns:
        Dictionary containing each GAC bracket as a key

    """
    current_gac_event = get_current_gac_event(comlink)
    if current_gac_event:
        current_event_instance = (
            f"{current_gac_event['id']}:{current_gac_event['instance'][0]['id']}"
        )
    else:
        # No current GAC season running
        logger.warning("There is no GAC season currently active in game events.")
        return None
    bracket = 0
    # Use brackets to store the results for each bracket for processing once all brackets have been scanned
    brackets: dict = {}
    number_of_players_in_bracket = 8
    while number_of_players_in_bracket > 0:
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


def load_master_map(
        master_map_path: str | Path = DATA_PATH, language: str = "eng_us"
) -> dict | None:
    """Read master localization key/string mapping file into dictionary and return

    Args:
        master_map_path (str): Base path to master data folder
        language (str): Localization language to read

    Returns:
        String mapping dictionary or None if the localization file is missing

    """
    full_path = os.path.join(master_map_path, "master", f"{language}_master.json")
    try:
        import json

        with open(full_path) as fn:
            return json.load(fn)
    except FileNotFoundError as e_str:
        logger.error(f"Unable to open {full_path}: {e_str}")
        return None


def get_current_datacron_sets(datacron_list: list) -> list:
    """Get the currently active datacron sets

    Args:
        datacron_list (list): List of 'datacronSet' from game data

    Returns:
        Filtered list of only active datacron sets

    Raises:
        ValueError: If datacron list is not a list

    """
    if not isinstance(datacron_list, list):
        raise ValueError(
            f"{_get_function_name()}, 'datacron_list' must be a list, not {type(datacron_list)}"
        )
    import math
    current_datacron_sets = []
    for datacron in datacron_list:
        if int(datacron["expirationTimeMs"]) > math.floor(time.time() * 1000):
            current_datacron_sets.append(datacron)
    return current_datacron_sets


def get_tw_omicrons(skill_list: list) -> list:
    """Return a list of territory war omicrons

    Args:
        skill_list (list): List of character abilities/skills

    Returns:
        List of territory war omicron abilities

    Raises:
        ValueError: If skill_list is not a list

    """
    if not isinstance(skill_list, list):
        raise ValueError(
            f"{_get_function_name()}, 'skill_list' must be a list, not {type(skill_list)}"
        )
    tw_omicrons = []
    for skill in skill_list:
        if skill["omicronMode"] == 8:
            tw_omicrons.append(skill)
    return tw_omicrons
