"""
Helper utilities for the comlink-python package and related modules
"""
from __future__ import annotations, print_function

import logging
import os
import time
from datetime import datetime, timezone
from functools import wraps
from logging.handlers import RotatingFileHandler
from typing import Callable, LiteralString

from swgoh_comlink import const

# Store created logging instances in a hash table for quick retrieval on repeat calls
logging_instances = {}


class LoggingFormatter(logging.Formatter):
    """Custom logging formatter class with colored output"""

    # Colors
    black = "\x1b[30m"
    white = "\x1b[37m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    gray = "\x1b[38m"
    # Styles
    reset = "\x1b[0m"
    bold = "\x1b[1m"

    # ANSI color reference https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797

    COLORS = {
        logging.DEBUG: gray + bold,
        logging.INFO: blue + bold,
        logging.WARNING: yellow + bold,
        logging.ERROR: red,
        logging.CRITICAL: '\x1b[1;31;43m'  # Bold (1) Red (31) with Yellow (43) background
    }

    def format(self, record):
        """Method to dynamically color log messages for console output based on message severity"""
        log_color = self.COLORS[record.levelno]
        time_color = '\x1b[1;30;47m'
        format_str = ("(black){asctime}(reset) | (lvl_color){levelname:8}(reset) | " +
                      "(green){name:<25} | {threadName} | " +
                      "(green){module:<14}(reset) | (green){funcName:>20}:{lineno:^4}(reset) | {message}")
        """        
        log_message_format = ('{asctime} | [{levelname:^9}] | {name:25} | pid:{process} | {threadName} | ' +
                              '{filename:<15} | {module:<14} : {funcName:>20}()_{lineno:_^4}_ | {message}')
        """
        format_str = format_str.replace("(black)", time_color)
        format_str = format_str.replace("(reset)", self.reset)
        format_str = format_str.replace("(lvl_color)", log_color)
        format_str = format_str.replace("(green)", self.green + self.bold)
        formatter = logging.Formatter(format_str, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


##################
# Decorators
##################
def func_timer(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()
        logging.getLogger(const.DEFAULT_LOGGER_NAME).debug(f'func:{f.__name__} took: {te - ts:.6f} sec')
        return result

    return wrap


def func_debug_logger(f):
    @wraps(f)
    def wrap(*args, **kw):
        logging.getLogger(const.DEFAULT_LOGGER_NAME).debug("  [ function %s ] called with args: %s and kwargs: %s",
                                                           f.__name__, args, kw)
        result = f(*args, **kw)
        return result

    return wrap


def param_alias(param: str, alias: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Callable:
            if alias in kwargs:
                kwargs[param] = kwargs.pop(alias)
            return func(*args, **kwargs)

        return wrapper

    return decorator


# Helper functions
def validate_path(path: str) -> bool:
    """Test whether provided path exists or not

    :param str path: path of file to validate

    :return bool: True if exists, False otherwise.

    """
    return os.path.exists(path) and os.path.isfile(path)


def sanitize_allycode(allycode: str | int) -> str:
    """
    Sanitize a player allycode to ensure it does not:
        - contain dashes
        - is the proper length
        - contains only digits

    :param (str|int) allycode: Player allycode to sanitize

    :return str: Player allycode in the proper format

    """
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
    payload = {
        "payload": {},
        "enums": enums
    }
    if allycode is not None:
        allycode = sanitize_allycode(allycode)
        payload['payload']['allyCode'] = f'{allycode}'
    else:
        payload['payload']['playerId'] = f'{player_id}'
    if enums:
        payload["enums"] = True
    return payload


def get_logger(
        name: str = const.DEFAULT_LOGGER_NAME,
        /,
        *,
        log_level: str = 'INFO',
        log_to_console: bool = False,
        log_to_file: bool = True,
        logfile_name: str = None,
        log_message_format: LiteralString = None) -> logging.Logger:
    """
    Get logger instance

    :param str name: Name of the logger instance to create or retrieve
    :param str log_level: The message severity level to assign to the new logger instance
    :param bool log_to_console: Flag to enable console logging
    :param bool log_to_file: Flag to enable file logging
    :param str logfile_name: Log file name if logging to file enabled
    :param LiteralString log_message_format: Log message format to use

    :return logging.Logger:  logger instance

    """
    print(f"[DEBUG] Default logger name: {const.DEFAULT_LOGGER_NAME}")
    """Create a logging instance and return a logger"""
    if name != const.DEFAULT_LOGGER_NAME:
        print("logger name is None or DEFAULT")
        name = f"{const.DEFAULT_LOGGER_NAME}.{name}"
    else:
        name = const.DEFAULT_LOGGER_NAME
    print(f"[DEBUG] Logger name: {name}")
    if name in logging_instances:
        print(f"[DEBUG] Existing logger instance for {name} found. Using that.")
        logging_instances[name]['instance'].info("Existing logger instance for %s found. Using that.", name)
        return logging_instances[name]['instance']
    else:
        logger = logging.getLogger(name)
    logger.setLevel(logging.getLevelName(log_level))
    # logger.propagate = False

    if log_message_format is None:
        # log_message_format = "[{asctime}] [{levelname:<8}] {name}: {message}"
        # log_message_format = ("{asctime} | {levelname:8} | {name:<10} | {filename:<15} | " +
        #                       "{module:<12} | {funcName:>15}():{lineno:_^4} | {message}")
        log_message_format = ('{asctime} | [{levelname:^9}] | {name:25} | pid:{process} | {threadName} | ' +
                              '{filename:<15} | {module:<14} : {funcName:>20}()_{lineno:_^4}_ | {message}')

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(LoggingFormatter())
        logger.addHandler(console_handler)

    # File handler
    log_path = None
    if log_to_file:
        if logfile_name is None:
            logfile_name = const.DEFAULT_LOGGER_NAME + '.log'
        log_path = os.path.join(os.getcwd(), 'logs', logfile_name)
        file_handler = RotatingFileHandler(filename=log_path, encoding="utf-8")
        # file_handler_formatter = logging.Formatter(log_message_format, "%Y-%m-%d %H:%M:%S", style="{")
        file_handler_formatter = LoggingFormatter()
        file_handler.setFormatter(file_handler_formatter)
        logger.addHandler(file_handler)
    logger.info(" --- [ Logging started for %s ] ---", name)
    logging_instances[name] = {'file': log_path, 'instance': logger}
    print(f"[DEBUG] {logging_instances[name]=}")
    return logger


def get_log_file_path(logger_instance_name: str) -> str:
    """Retrieve the requested log file path and return it as a string

    :param str logger_instance_name: Name of the logger instance

    :return str: Path to the log file currently associated with the logger instance file handler

    """
    return logging_instances[logger_instance_name]['file'] if logger_instance_name in logging_instances else None


def human_time(unix_time: int or float) -> str:
    """Convert unix time to human-readable string

    :param (int|float) unix_time: standard unix time in seconds or milliseconds

    :return str: human-readable time string

    """
    if isinstance(unix_time, float):
        unix_time = int(unix_time)
    if isinstance(unix_time, str):
        try:
            unix_time = int(unix_time)
        except Exception as exc:
            logging.getLogger(const.DEFAULT_LOGGER_NAME).exception(f"Exception caught: [{exc}]")
            raise
    return datetime.fromtimestamp(unix_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%s')


def construct_unit_stats_query_string(flags: list[str], language: str) -> str:
    """
    Constructs query string from provided flags and language to be used with the get_unit_stats() function

    :param list[str] flags: List of strings indicating the flags to enable for the unit_stats function call
    :param str language: Language of the localization to use for returned data

    :return str: The query string portion of a URL

    """
    flag_string = f'flags={",".join(flags)}' if flags else None
    language_string = f'language={language}' if language else None
    constructed_string = '&'.join(filter(None, [flag_string, language_string]))
    return f'?{constructed_string}' if constructed_string else None


def update_hmac_obj(hmac_obj, values: list):
    for value in values:
        hmac_obj.update(value.encode())


def convert_league_to_int(league: int | str) -> int:
    """Convert GAC leagues to integer

    :param (int|str) league: GAC league name

    :return int: GAC league identifier as used in game data

    """
    if isinstance(league, str):
        return const.LEAGUES[league.lower()]
    return league


def convert_divisions_to_int(division: int | str) -> int:
    """Convert GAC divisions to integer

    :param (int|str) division: GAC division ID as seen in game

    :return int: GAC division identifier as used within game data

    """
    if isinstance(division, str):
        return const.DIVISIONS[division.lower()]
    if isinstance(division, int) and len(str(division)) == 1:
        return const.DIVISIONS[str(division)]
    return division


def construct_url_base(protocol: str, host: str, port: int) -> str:
    """Construct a URL base string from protocol, host and port inputs

    :param str protocol: http or https protocol
    :param str host: host address
    :param int port: port number

    :return str: URL string

    """
    return f"{protocol}://{host}:{port}"


def create_localized_unit_name_dictionary(locale: str or list) -> dict:
    """
    Take a localization element from the SwgohComlink.get_localization() result dictionary and
    extract the UNIT_NAME entries for building a conversion dictionary for translating BASEID values to in game
    descriptive names

    :param (str|list[bytes]) locale: The string element or List[bytes] from the SwgohComlink.get_localization()
                                        result key value

    :return dict[str,str]: A dictionary with the UNIT_NAME BASEID as keys and the UNIT_NAME description as values

    """
    unit_name_map = {}
    lines = []
    if isinstance(locale, str):
        lines = locale.split('\n')
    elif isinstance(locale, list):
        lines = locale
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode()
        line = line.rstrip('\n')
        if line.startswith('#') or '|' not in line:
            continue
        if line.startswith('UNIT_'):
            name_key, desc = line.split('|')
            if name_key.endswith('_NAME'):
                unit_name_map[name_key] = desc
    return unit_name_map


def get_guild_members(comlink, /, *, player_id: str = None, allycode: str or int = None) -> list:
    """Return list of guild member player allycodes based upon provided player ID or allycode

    :param SwgohComlink comlink: Instance of SwgohComlink
    :param str player_id: Player's ID
    :param (str|int) allycode: Player's allycode

    :return list: list of guild members

    """
    if player_id is None and allycode is None:
        raise RuntimeError(f'player_id or allycode must be provided.')
    if player_id is not None:
        player = comlink.get_player(player_id=player_id)
    else:
        player = comlink.get_player(allycode=sanitize_allycode(allycode))
    guild = comlink.get_guild(guild_id=player['guildId'])
    return guild['member']


def get_gac_brackets(comlink, /, *, league: str) -> dict or None:
    """Scan currently running GAC brackets for the requested league and return them as a dictionary"""
    current_events = comlink.get_events()
    current_event_instance = None
    for event in current_events['gameEvent']:
        if event['type'] == 10:
            current_event_instance = f"{event['id']}:{event['instance'][0]['id']}"
    if not current_event_instance:
        # No current GAC season running
        logging.warning("There is no GAC season currently active in game events.")
        return None
    bracket = 0
    # Use brackets to store the results for each bracket for processing once all brackets have been scanned
    brackets = {}
    number_of_players_in_bracket = 8
    while number_of_players_in_bracket > 0:
        group_id = f"{current_event_instance}:{league}:{bracket}"
        group_of_8_players = comlink.get_gac_leaderboard(leaderboard_type=4,
                                                         event_instance_id=current_event_instance,
                                                         group_id=group_id)
        brackets[bracket] = brackets.get(bracket, group_of_8_players['player'])
        bracket += 1
        number_of_players_in_bracket = len(group_of_8_players['player'])
    return brackets


def search_gac_brackets(gac_brackets: dict, player_name: str) -> dict:
    """
    Search the provided gac brackets data for a specific player and return the player and bracket information
    as a dictionary
    """
    match_data = {}
    for bracket in gac_brackets:
        for player in gac_brackets[bracket]:
            if player_name.lower() == player['name'].lower():
                match_data['player'] = player
                match_data['bracket'] = bracket
    return match_data


def load_master_map(master_map_path: str = const.DATA_PATH, language: str = "eng_us") -> dict or None:
    """Read master localization key/string mapping file into dictionary and return"""
    full_path = os.path.join(master_map_path, 'master', f"{language}_master.json")
    try:
        import json
        with open(full_path) as fn:
            return json.load(fn)
    except FileNotFoundError as e_str:
        logging.error(f"Unable to open {full_path}: {e_str}")
        return None


if __name__ == "__main__":
    exit(0)
