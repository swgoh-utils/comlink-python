# coding=utf-8
"""
Helper utilities for the swgoh_comlink package and related modules
"""
from __future__ import annotations

import inspect
import os
import time
from functools import wraps
from pathlib import Path
from typing import Callable, TYPE_CHECKING, Any

from _const import *

if TYPE_CHECKING:
    import swgoh_comlink

logger = get_logger()

__all__ = [
    "construct_unit_stats_query_string",
    "convert_divisions_to_int",
    "convert_league_to_int",
    "create_localized_unit_name_dictionary",
    "func_debug_logger",
    "func_timer",
    "get_current_datacron_sets",
    "get_current_gac_event",
    "get_gac_brackets",
    "get_guild_members",
    "get_tw_omicrons",
    "human_time",
    "load_master_map",
    "param_alias",
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


def param_alias(param: str, alias: str) -> Callable:
    """Decorator for aliasing function parameters"""

    def decorator(func: Callable) -> Callable:
        """Decorating function"""

        @wraps(func)
        def wrapper(*args, **kwargs) -> Callable:
            """Wrapper function"""
            if alias in kwargs:
                kwargs[param] = kwargs.pop(alias)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def validate_file_path(path: str) -> bool:
    """Test whether provided path exists or not

    Args:
        path: path of file to validate

    Returns:
        True if exists, False otherwise.

    """
    return os.path.exists(path) and os.path.isfile(path)


def sanitize_allycode(allycode: str | int) -> str:
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
    if not allycode:
        return str()
    if isinstance(allycode, int):
        allycode = str(allycode)
    if '-' in allycode:
        allycode = allycode.replace("-", "")
    if not allycode.isdigit() or len(allycode) != 9:
        raise ValueError(f"Invalid ally code: {allycode}")
    return allycode


def human_time(unix_time: Any) -> str:
    """Convert unix time to human-readable string

    Args:
        unix_time (int|float): standard unix time in seconds or milliseconds

    Returns:
        str: human-readable time string

    Notes:
        If the provided unix time is invalid or an error occurs, the default time string returned
        is 1970-01-01 00:00:00

    """
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
    return datetime.fromtimestamp(unix_time, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def construct_unit_stats_query_string(flags: list[str], language: str = "eng_us") -> str | None:
    """Constructs query string from provided flags and language to be used with the get_unit_stats() function

    Args:
        flags: List of strings indicating the flags to enable for the unit_stats function call
        language: Language of the localization to use for returned data

    Returns:
        The query string portion of a URL

    """
    allowed_flags: set = set(sorted(["gameStyle", "calcGP", "onlyGP", "withoutModCalc", "percentVals", "useMax",
                                     "scaled", "unscaled", "statIDs", "enums", "noSpace"]))
    language_string = f"language={language}" if language else None
    if flags:
        if not isinstance(flags, list):
            raise ValueError(f"{_get_function_name()}, Invalid flags '{flags}', must be type list of strings.")
        tmp_flags: set = set(sorted(list(dict.fromkeys(flags))))
        flag_string = f'flags={",".join(sorted(tmp_flags.intersection(allowed_flags)))}' if flags else str()
        constructed_string = "&".join(filter(None, [flag_string, language_string]))
        return f"?{constructed_string}"


def convert_league_to_int(league: str) -> int | None:
    """Convert GAC leagues to integer

    Args:
        league (str): GAC league name

    Returns:
        GAC league identifier as used in game data

    """
    if isinstance(league, str) and league.lower() in LEAGUES:
        return LEAGUES[league.lower()]


def convert_divisions_to_int(division: int | str) -> int | None:
    """Convert GAC divisions to integer

    Args:
        division: GAC division ID as seen in game

    Returns:
        GAC division identifier as used within game data

    """
    if isinstance(division, str):
        if division in DIVISIONS:
            return DIVISIONS[division]
    if isinstance(division, int) and len(str(division)) == 1:
        if str(division) in DIVISIONS:
            return DIVISIONS[str(division)]


def create_localized_unit_name_dictionary(locale: str | list) -> dict:
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
        raise ValueError(f"{_get_function_name()}, locale must be a list of strings or string containing newlines")

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


def get_guild_members(
        comlink: swgoh_comlink.SwgohComlink,
        *,
        player_id: str | None = None,
        allycode: str | int | None = None,
) -> list[dict]:
    """Return list of guild member player allycodes based upon provided player ID or allycode

    Args:
        comlink: Instance of SwgohComlink
        player_id: Player's ID
        allycode: Player's allycode

    Returns:
        list of guild members objects

    """
    if not player_id and not allycode:
        raise RuntimeError("player_id or allycode must be provided.")
    if not allycode:
        player = comlink.get_player(player_id=player_id)
    else:
        player = comlink.get_player(allycode=sanitize_allycode(allycode))
    guild = comlink.get_guild(guild_id=player["guildId"])
    return guild["member"]


def get_current_gac_event(comlink: swgoh_comlink.SwgohComlink) -> dict:
    """Return the event object for the current gac season

    Args:
        comlink: Instance of SwgohComlink

    Returns:
        Current GAC event object or empty if no event is running

    """
    current_gac_event: dict = {}
    current_events: dict[str, list] = comlink.get_events()
    for event in current_events["gameEvent"]:
        if event["type"] == 10:
            current_gac_event = event
            break
    return current_gac_event


def get_gac_brackets(comlink: swgoh_comlink.SwgohComlink, league: str) -> dict | None:
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
        raise ValueError(f"{_get_function_name()}, 'datacron_list' must be a list, not {type(datacron_list)}")

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
        raise ValueError(f"{_get_function_name()}, 'skill_list' must be a list, not {type(skill_list)}")
    tw_omicrons = []
    for skill in skill_list:
        if skill["omicronMode"] == 8:
            tw_omicrons.append(skill)
    return tw_omicrons
