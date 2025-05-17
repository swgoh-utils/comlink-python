# coding=utf-8
"""
Helper utilities for the swgoh_comlink package and related modules
"""

from __future__ import annotations, absolute_import

import asyncio
import inspect
import os
import time
from functools import wraps
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING

from sentinels import Sentinel

from swgoh_comlink.constants import (
    get_logger,
    GIVEN,  # Sentinel
    OPTIONAL,  # Sentinel
    MISSING,  # Sentinel
    REQUIRED,  # Sentinel
    MutualExclusiveRequired,  # Sentinel
    NotSet,  # Sentinel
    Constants,
    Config,
    )
from swgoh_comlink.exceptions import ComlinkValueError

if TYPE_CHECKING:
    from swgoh_comlink import SwgohComlink, SwgohComlinkAsync  # noqa: ignore

default_logger = get_logger()
default_logger.debug("Utils logging is set to %s..." % default_logger.name)

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
        "_get_function_name",
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
    return f"{inspect.stack()[1].function}()"


def func_timer(f):
    """Decorator to record total execution time of a function to the configured logger using level DEBUG"""

    @wraps(f)
    def wrap(*args, **kw):
        """Wrapper function"""
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()
        default_logger.debug(f"  [ function {f.__name__} ] took: {(te - ts):.5f} seconds")
        return result

    return wrap


def func_debug_logger(f):
    """Decorator for applying DEBUG logging to a function"""

    @wraps(f)
    def wrap(*args, **kw):
        """Wrapper function"""
        default_logger.debug(
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
    if path is MISSING or not path:
        err_msg = f"{_get_function_name()}: 'path' argument is required."
        default_logger.error(err_msg)
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
        default_logger.warning("%s: no allycode input provided. Returning empty string." % _get_function_name())
        return str()
    if isinstance(allycode, int):
        allycode = str(allycode)
    if "-" in str(allycode):
        allycode = allycode.replace("-", "")
    if not allycode.isdigit() or len(allycode) != 9:
        err_msg = f"{_get_function_name()}: Invalid ally code: {allycode}"
        default_logger.error(err_msg)
        raise ValueError(err_msg)
    default_logger.debug("{}: {} allycode sanitized to: {}".format(_get_function_name(), _orig_ac, allycode))
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
    if unix_time is MISSING or not str(unix_time):
        err_msg = f"{_get_function_name()}: The 'unix_time' argument is required."
        default_logger.error(err_msg)
        raise ValueError(err_msg)
    from datetime import datetime, timezone
    if isinstance(unix_time, float):
        unix_time = int(unix_time)
    if isinstance(unix_time, str):
        try:
            unix_time = int(unix_time)
        except ValueError:
            err_msg = f"{_get_function_name()}: Unable to convert unix time from {type(unix_time)} to type <int>"
            default_logger.exception(err_msg)
            raise ValueError(err_msg)
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
    if league is MISSING or not league:
        err_msg = f"{_get_function_name()}: The 'league' argument is required."
        default_logger.error(err_msg)
        raise ValueError(err_msg)

    if isinstance(league, str) and league.lower() in Constants.LEAGUES:
        return Constants.LEAGUES[league.lower()]
    else:
        return None


def convert_divisions_to_int(division: int | str | Sentinel = REQUIRED) -> int | None:
    """Convert GAC divisions to integer

    Args:
        division: GAC division ID as seen in game

    Returns:
        GAC division identifier as used within game data

    """
    if division is MISSING or not division:
        err_msg = f"{_get_function_name()}: The 'division' argument is required."
        default_logger.error(err_msg)
        raise ValueError(err_msg)

    if isinstance(division, str):
        if division in Constants.DIVISIONS:
            return Constants.DIVISIONS[division]
    if isinstance(division, int) and len(str(division)) == 1:
        if str(division) in Constants.DIVISIONS:
            return Constants.DIVISIONS[str(division)]
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
        default_logger.error(err_msg)
        raise ValueError(err_msg)
    relic_value = None
    if isinstance(relic_tier, int):
        relic_tier = str(relic_tier)
    if relic_tier in Constants.RELIC_TIERS:
        relic_value = Constants.RELIC_TIERS[relic_tier]
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
        raise ComlinkValueError(f"'locale' must be a list of strings or string containing newlines.")

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


@func_debug_logger
async def get_async_player(
        comlink: SwgohComlinkAsync | Sentinel = REQUIRED,
        *,
        player_id: str | Sentinel = MutualExclusiveRequired,
        allycode: str | int | Sentinel = MutualExclusiveRequired
        ) -> dict:
    log_msg = f"Beginning async player call with arguments: {comlink=}, {player_id=}, {allycode=}"
    default_logger.debug('[DEFAULT_LOGGER]  ' + log_msg)

    if hasattr(comlink, '__comlink_type__'):
        comlink_type = comlink.__comlink_type__
    else:
        comlink_type = MISSING
    if comlink is MISSING or comlink_type != 'SwgohComlinkAsync':
        err_msg = (f"{_get_function_name()}: The 'comlink' argument is required and must be an "
                   f"instance of SwgohComlinkAsync.")
        default_logger.error(err_msg)
        raise ValueError(err_msg)

    default_logger.warning(f"player_id is not MutualExclusiveRequired: {player_id is not MutualExclusiveRequired}")
    default_logger.warning(f"allycode is not MutualExclusiveRequired: {allycode is not MutualExclusiveRequired}")
    if isinstance(player_id, str) and (isinstance(allycode, str) or isinstance(allycode, int)):
        err_msg = f"{_get_function_name()}: Either 'player_id' or 'allycode' are allowed arguments, not both."
        default_logger.error(err_msg)
        raise ValueError(err_msg)

    default_logger.warning(f"player_id is MutualExclusiveRequired: {player_id is MutualExclusiveRequired}")
    default_logger.warning(f"allycode is MutualExclusiveRequired: {allycode is MutualExclusiveRequired}")
    if player_id is MutualExclusiveRequired and allycode is MutualExclusiveRequired:
        err_msg = f"{_get_function_name()}: One of either 'player_id' or 'allycode' is required."
        default_logger.error(err_msg)
        raise ValueError(err_msg)

    if allycode is not MutualExclusiveRequired:
        if isinstance(allycode, int):
            allycode = str(allycode)
        if not isinstance(allycode, str):
            err_msg = f"{_get_function_name()}: 'allycode' must be a string or integer value."
            default_logger.error(err_msg)
            raise ValueError(err_msg)

    player = {}

    if player_id is not MutualExclusiveRequired and isinstance(player_id, str):
        try:
            default_logger.debug(f"Calling Comlink to get player by ID: {player_id}")
            player = await comlink.get_player(player_id=player_id)
        except RuntimeError as async_exc:
            async_exc = str(async_exc).replace("\n", "-")
            default_logger.warning(f"{_get_function_name()}: {async_exc}")
        return player
    elif allycode is not MutualExclusiveRequired and isinstance(allycode, str):
        try:
            default_logger.debug(f"Calling Comlink to get player by allycode {allycode}")
            player = await comlink.get_player(allycode=allycode)
        except RuntimeError as async_exc:
            async_exc = str(async_exc).replace("\n", "-")
            default_logger.warning(f"{_get_function_name()}: {async_exc}")
        return player
    else:
        default_logger.error(f"{_get_function_name()}: Unexpected condition encountered. Returning <None>")
        default_logger.debug(f"{_get_function_name()}: {player_id=}, {allycode=}")
        return {}


async def get_async_guild(
        comlink: SwgohComlinkAsync | Sentinel = REQUIRED,
        guild_id: str | Sentinel = REQUIRED,
        ) -> dict:
    """Return the SwgohComlinkAsync.get_guild() dictionary object

    Args:
        comlink ():
        guild_id ():

    Returns:

    """
    default_logger.debug(f"Calling SwgohComlinkAsync.get_guild(). {guild_id=}")
    return await comlink.get_guild(guild_id=guild_id)


def get_guild_members(
        comlink: SwgohComlink | SwgohComlinkAsync | Sentinel = REQUIRED,
        player_id: str | Sentinel = MutualExclusiveRequired,
        allycode: str | int | Sentinel = MutualExclusiveRequired,
        ) -> list:
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
    if hasattr(comlink, '__comlink_type__'):
        comlink_type = comlink.__comlink_type__
    else:
        comlink_type = MISSING
    if comlink is MISSING or (comlink_type != 'SwgohComlinkAsync' and comlink_type != 'SwgohComlink'):
        err_msg = (f"{_get_function_name()}: The 'comlink' argument is required and must be an "
                   f"instance of SwgohComlinkAsync.")
        default_logger.error(err_msg)
        raise ValueError(err_msg)

    if player_id is not MutualExclusiveRequired and allycode is not MutualExclusiveRequired:
        err_msg = f"{_get_function_name()}: Either 'player_id' or 'allycode' are allowed arguments, not both."
        default_logger.error(err_msg)
        raise ValueError(err_msg)

    if player_id is MutualExclusiveRequired and allycode is MutualExclusiveRequired:
        err_msg = f"{_get_function_name()}: One of either 'player_id' or 'allycode' is required."
        default_logger.error(err_msg)
        raise ValueError(err_msg)

    guild: dict = {"member": []}
    player = {}
    if comlink_type == 'SwgohComlink':  # noqa: type
        if isinstance(player_id, str):
            player = comlink.get_player(player_id=player_id)
        else:
            player = comlink.get_player(allycode=sanitize_allycode(allycode))
        guild = comlink.get_guild(guild_id=player["guildId"])
    elif comlink_type == 'SwgohComlinkAsync':  # noqa: type
        try:
            loop = asyncio.get_running_loop()
            default_logger.info(f"Current event loop found: {loop}")
        except RuntimeError as async_exc:
            async_exc = str(async_exc).replace("\n", "-")
            default_logger.warning(f"{_get_function_name()}: {async_exc}")
            default_logger.info(f"Creating new event loop")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            default_logger.info(f"Event loop: {loop}")
        if isinstance(player_id, str):
            try:
                default_logger.debug(f"Getting async player by id: {player_id}")
                player = asyncio.run(get_async_player(comlink=comlink, player_id=player_id), debug=True)
            except RuntimeError as async_exc:
                async_exc = str(async_exc).replace("\n", "-")
                default_logger.warning(f"{_get_function_name()}: {async_exc}")
        else:
            try:
                default_logger.debug(f"Getting async player by allycode: {allycode}")
                player = asyncio.run(get_async_player(comlink=comlink, allycode=allycode), debug=True)
            except RuntimeError as async_exc:
                async_exc = str(async_exc).replace("\n", "-")
                default_logger.warning(f"{_get_function_name()}: {async_exc}")
        default_logger.debug(f"player object response is type: {type(player)}")

        try:
            default_logger.debug(f"Getting guild members for: {player['guildId']}")
            guild = asyncio.run(comlink.get_guild(guild_id=player["guildId"]), debug=True)
        except RuntimeError as async_exc:
            async_exc = str(async_exc).replace("\n", "-")
            default_logger.warning(f"{_get_function_name()}: {async_exc}")
    return guild["member"] or []


async def get_async_events(comlink: SwgohComlinkAsync | Sentinel = REQUIRED) -> dict:
    if isinstance(comlink, Sentinel) or (
            hasattr(comlink, '__comlink_type__') and comlink.__comlink_type__ != 'SwgohComlinkAsync'):
        err_msg = f"{_get_function_name()}: async comlink instance must be provided."
        default_logger.error(err_msg)
        raise ValueError(err_msg)
    elif hasattr(comlink, '__comlink_type__') and comlink.__comlink_type__ == 'SwgohComlinkAsync':
        return await comlink.get_events()
    else:
        err_msg = f"{_get_function_name()}: invalid comlink instance {type(comlink)} provided."
        default_logger.error(err_msg)
        raise ValueError(err_msg)


def get_current_gac_event(
        comlink: SwgohComlink | SwgohComlinkAsync | Sentinel = REQUIRED
        ) -> dict:
    """Return the event object for the current gac season

    Args:
        comlink: Instance of SwgohComlink

    Returns:
        Current GAC event object or empty if no event is running

    """
    if hasattr(comlink, '__comlink_type__'):
        comlink_type = comlink.__comlink_type__
    else:
        comlink_type = MISSING
    default_logger.debug("{}: Getting current gac event. comlink={}".format(_get_function_name(), comlink))
    log_msg = f"{_get_function_name()}: 'comlink' instance type: {comlink_type}"
    default_logger.debug(log_msg)

    if comlink is MISSING or comlink_type is MISSING:
        err_str = f"{_get_function_name()}: comlink instance must be provided."
        default_logger.error(err_str)
        raise ValueError(err_str)

    current_gac_event: dict = {}
    if comlink_type == 'SwgohComlink':  # type: ignore
        current_events = comlink.get_events()
    elif comlink_type == 'SwgohComlinkAsync':
        current_events = asyncio.run(get_async_events(comlink))
    else:
        return current_gac_event

    for event in current_events["gameEvent"]:
        if event["type"] == 10:
            current_gac_event = event
            break
    return current_gac_event


def get_gac_brackets(
        comlink: SwgohComlink | Sentinel = REQUIRED,
        league: str | Sentinel = REQUIRED,
        limit: int | Sentinel = OPTIONAL
        ) -> dict | None:
    """Scan currently running GAC brackets for the requested league and return them as a dictionary

    Args:
        comlink: Instance of SwgohComlink
        league: League to scan
        limit: Number of brackets to return

    Returns:
        Dictionary containing each GAC bracket as a key

    """
    if hasattr(comlink, '__comlink_type__'):
        comlink_type = comlink.__comlink_type__
    else:
        comlink_type = MISSING
    if comlink is MISSING or comlink_type != 'SwgohComlink':
        err_msg = f"{_get_function_name()}: Invalid comlink instance."
        default_logger.error(err_msg)
        raise ValueError(err_msg)

    if league is MISSING or not isinstance(league, str):
        err_msg = f"{_get_function_name()}: 'league' type <str> argument is required."
        default_logger.error(err_msg)
        raise ValueError(err_msg)

    bracket_iteration_limit: int | None = None if limit is NotSet else int(limit)
    default_logger.debug(f"{_get_function_name()}: Bracket iteration limit is {bracket_iteration_limit}")

    current_gac_event = get_current_gac_event(comlink)

    if current_gac_event:
        current_event_instance = (
                f"{current_gac_event['id']}:{current_gac_event['instance'][0]['id']}"
        )
        default_logger.debug(f"{_get_function_name()}: Current GAC event instance is {current_event_instance}")
    else:
        # No current GAC season running
        default_logger.warning("There is no GAC season currently active in game events.")
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
    default_logger.debug(f"{_get_function_name()}: Returning {len(brackets)} GAC brackets.")
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
        master_map_path: str | Path = Config.DATA_PATH, language: str = "eng_us"
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
        default_logger.error(f"Unable to open {full_path}: {e_str}")
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
        raise ComlinkValueError(
                f"'skill_list' must be a list, not {type(skill_list)}"
                )
    tw_omicrons = []
    for skill in skill_list:
        if skill["omicronMode"] == 8:
            tw_omicrons.append(skill)
    return tw_omicrons


def get_raid_leaderboard_ids(campaign_data: list) -> list[str]:
    """
    Extracts and returns the raid leaderboard IDs from the provided campaign data.

    This function processes the `campaign_data` to find and extract the IDs of
    raids associated with the guild campaigns. The IDs are formatted as a string
    specifying the type and structure of the raid. The function specifically works
    with the "GUILD" campaign type and retrieves IDs from the "NORMAL_DIFF"
    difficulty group.

    Args:
        campaign_data (list): A list of campaign data structures, where each
            structure represents campaign information. The input data is
            expected to have nested dictionaries and lists with specific keys
            such as 'id', 'campaignMap', 'campaignNodeDifficultyGroup', and
            'campaignNode'.

    Returns:
        list: A list containing formatted raid leaderboard IDs extracted from the
        guild campaign data. Each ID is constructed as a string containing the
        relevant identifiers for the campaign and its raids.

    Raises:
        KeyError: If any of the required keys (e.g., 'id', 'campaignMap',
            etc.) are missing in the input data.
        TypeError: If `campaign_data` is not structured as expected, such as if
            it is not a list or contains improperly formatted elements.
    """
    raid_ids = []
    guild_campaigns = next((item for item in campaign_data if item.get('id') == 'GUILD'), None)
    for raid in guild_campaigns['campaignMap'][0]['campaignNodeDifficultyGroup'][0]['campaignNode']:
        for mission in raid['campaignNodeMission']:
            elements = [
                    guild_campaigns['id'],
                    guild_campaigns['campaignMap'][0]['id'],
                    "NORMAL_DIFF",
                    raid['id'],
                    mission['id']
                    ]
            raid_ids.append(":".join(elements))
    return raid_ids


def get_playable_units(units_collection: list[dict]) -> list[dict]:
    """Return a list of playable units from game data 'units' collection"""
    if not isinstance(units_collection, list):
        raise ComlinkValueError(f"'units_collection' must be a list, not {type(units_collection)}")

    return [unit for unit in units_collection
            if unit['rarity'] == 7
            and unit['obtainable'] is True
            and unit['obtainableTime'] == '0']
