# coding=utf-8
"""
Helper utilities for the swgoh_comlink package and related modules
"""
from __future__ import annotations, print_function, absolute_import

import os
import time
from functools import wraps
from typing import Callable, TYPE_CHECKING, Any

from swgoh_comlink.const import Constants

if TYPE_CHECKING:
    import swgoh_comlink

logger = Constants.get_logger()

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


def sanitize_allycode(allycode: str or int) -> str:
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
    if isinstance(allycode, int):
        allycode = str(allycode)
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


def construct_unit_stats_query_string(flags: list[str], language: str) -> str:
    """Constructs query string from provided flags and language to be used with the get_unit_stats() function

    Args:
        flags: List of strings indicating the flags to enable for the unit_stats function call
        language: Language of the localization to use for returned data

    Returns:
        The query string portion of a URL

    """
    flag_string = f'flags={",".join(flags)}' if flags else None
    language_string = f"language={language}" if language else None
    constructed_string = "&".join(filter(None, [flag_string, language_string]))
    return f"?{constructed_string}" if constructed_string else None


def convert_league_to_int(league: int or str) -> int:
    """Convert GAC leagues to integer

    Args:
        league (str|int): GAC league name

    Returns:
        GAC league identifier as used in game data

    """
    if isinstance(league, str):
        return Constants.LEAGUES[league.lower()]
    return league


def convert_divisions_to_int(division: int or str) -> int:
    """Convert GAC divisions to integer

    Args:
        division: GAC division ID as seen in game

    Returns:
        GAC division identifier as used within game data

    """
    if isinstance(division, str):
        return Constants.DIVISIONS[division.lower()]
    if isinstance(division, int) and len(str(division)) == 1:
        return Constants.DIVISIONS[str(division)]
    return division


def create_localized_unit_name_dictionary(locale: str or list) -> dict:
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
        player_id: str = None,
        allycode: str or int = None,
) -> list[dict]:
    """Return list of guild member player allycodes based upon provided player ID or allycode

    Args:
        comlink: Instance of SwgohComlink
        player_id: Player's ID
        allycode: Player's allycode

    Returns:
        list of guild members objects

    """
    if player_id is None and allycode is None:
        raise RuntimeError("player_id or allycode must be provided.")
    if player_id is not None:
        player = comlink.get_player(player_id=player_id)
    else:
        player = comlink.get_player(allycode=sanitize_allycode(allycode))
    guild = comlink.get_guild(guild_id=player["guildId"])
    return guild["member"]


def get_current_gac_event(comlink: swgoh_comlink.SwgohComlink) -> dict or None:
    """Return the event object for the current gac season

    Args:
        comlink: Instance of SwgohComlink

    Returns:
        Current GAC event object or none if no event is running

    """
    current_events = comlink.get_events()
    for event in current_events["gameEvent"]:
        if event["type"] == 10:
            return event


def get_gac_brackets(comlink: swgoh_comlink.SwgohComlink, league: str) -> dict or None:
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
        return
    bracket = 0
    # Use brackets to store the results for each bracket for processing once all brackets have been scanned
    brackets = {}
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
        dict: GAC bracket and player information or None if no match is found

    """
    match_data = None
    for bracket in gac_brackets:
        for player in gac_brackets[bracket]:
            if player_name.lower() == player["name"].lower():
                match_data = {"player": player, "bracket": bracket}
    return match_data


def load_master_map(
        master_map_path: str = Constants.DATA_PATH, language: str = "eng_us"
) -> dict or None:
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
        datacron_list (list): List of datacron templates

    Returns:
        Filtered list of only active datacron sets

    """
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

    """
    tw_omicrons = []
    for skill in skill_list:
        if skill["omicronMode"] == 8:
            tw_omicrons.append(skill)
    return tw_omicrons
