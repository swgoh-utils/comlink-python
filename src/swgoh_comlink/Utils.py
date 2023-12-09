"""
Helper utilities for the swgoh-python-async package and related modules
"""
from __future__ import annotations, print_function

import functools
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Callable

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync

logger_name = 'swgoh_comlink'

LEAGUES: dict[str, int] = {
    'kyber': 100,
    'aurodium': 80,
    'chromium': 60,
    'bronzium': 40,
    'carbonite': 20
}

DIVISIONS: dict[str, int] = {
    '1': 25,
    '2': 20,
    '3': 15,
    '4': 10,
    '5': 5
}


def sanitize_allycode(allycode: str | int) -> str:
    if isinstance(allycode, int):
        allycode = str(allycode)
    allycode = allycode.replace('-', '')
    if not allycode.isdigit() or len(allycode) != 9:
        raise ValueError(f"Invalid ally code: {allycode}")
    return allycode


def get_player_payload(allycode: str | int = None, player_id: str = None, enums: bool = False) -> dict:
    if allycode is None and player_id is None:
        raise ValueError("Either allycode or player_id must be provided.")
    if allycode is not None and player_id is not None:
        raise ValueError("Only one of allycode or player_id can be provided.")
    if allycode is not None:
        allycode = sanitize_allycode(allycode)
        payload = {"allycodes": [allycode]}
    else:
        payload = {"playerIds": [player_id]}
    if enums:
        payload["enums"] = 1
    return payload


def param_alias(param: str, alias: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if param in kwargs:
                kwargs[alias] = kwargs.pop(param)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_logger(name: str = None, logging_level: str = 'INFO', terminal: bool = False) -> logging.Logger:
    """Create logger instance for writing messages to log files.

    :param name: Name of the log file to create. [Default: swgoh-comlink-async.log]
    :type name: str
    :param logging_level: Level of messages to log. [Default: INFO]
    :type logging_level: str
    :param terminal: Flag to determine if messages should be logged to terminal and to log file. [Default: False]
    :type terminal: bool
    :return: Logger instance
    :rtype: Logger
    """
    if name is None:
        name = logger_name
    logger = logging.getLogger(name)
    logger.setLevel(logging.getLevelName(logging_level.upper()))
    # Create message formatting to include module and function naming for easier debugging
    formatter = logging.Formatter('{asctime} [ {levelname:^9}] {module:25} : {funcName:20}({lineno}) - {message}',
                                  style='{')
    log_base = os.path.join(os.getcwd(), 'logs')
    try:
        os.mkdir(log_base)
    except FileExistsError:
        pass
    log_base_name = os.path.join(log_base, f'{logger_name}.log')
    # Create a log file handler to write logs to disk
    log_file_handler = RotatingFileHandler(
        log_base_name,
        maxBytes=25000000,
        backupCount=5
    )
    log_file_handler.setFormatter(formatter)
    logger.addHandler(log_file_handler)
    # Create a second handler for output to terminal
    if terminal is True:
        log_console_handler = logging.StreamHandler()
        log_console_handler.setFormatter(formatter)
        logger.addHandler(log_console_handler)
    logger.info(f"Logger created with level set to {logging_level.upper()!r}.")
    return logger


def human_time(time: int or float) -> str:
    """Convert unix time to human readable string"""
    if isinstance(time, float):
        time = int(time)
    if isinstance(time, str):
        try:
            time = int(time)
        except Exception as exc:
            logging.getLogger(logger_name).exception(f"Exception caught: [{exc}]")
            raise
    return datetime.fromtimestamp(time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%s')


def construct_unit_stats_query_string(flags: list, language: str) -> str:
    """
    Constructs query string from provided flags and language to be used with the get_unit_stats function
    """
    flag_string = f'flags={",".join(flags)}' if flags else None
    language_string = f'language={language}' if language else None
    constructed_string = '&'.join(filter(None, [flag_string, language_string]))
    return f'?{constructed_string}' if constructed_string else None


def update_hmac_obj(hmac_obj, values: list):
    for value in values:
        hmac_obj.update(value.encode())


def convert_league_to_int(league: int | str) -> int:
    if isinstance(league, str):
        return LEAGUES[league.lower()]
    return league


def convert_divisions_to_int(division: int | str) -> int:
    if isinstance(division, str):
        return DIVISIONS[division.lower()]
    if isinstance(division, int) and len(str(division)) == 1:
        return DIVISIONS[str(division)]
    return division


def construct_url_base(protocol: str, host: str, port: int) -> str:
    return f"{protocol}://{host}:{port}"


def get_guild_members(comlink: SwgohComlink or SwgohComlinkAsync, **kwargs) -> list:
    """Return list of guild member player allycodes based upon provided player ID or allycode"""
    guild_members = []
    if 'player_id' or 'allycode' not in kwargs:
        raise f'player_id or allycode must be provided.'
    # TODO: check if player_id or allycode provided
    if isinstance(comlink, SwgohComlink):
        # player = comlink.get_player_arena(allycode=)
        # guild = comlink
        pass
    return guild_members
