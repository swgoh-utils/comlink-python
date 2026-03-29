# coding=utf-8
"""General utility functions: validation, sanitization, conversion."""

from __future__ import annotations

import inspect
import logging
import os
from pathlib import Path
from typing import Any

from ..exceptions import SwgohComlinkTypeError, SwgohComlinkValueError
from ._constants import Constants

logger = logging.getLogger(__name__)


def get_function_name() -> str:
    """Return the name of the calling function"""
    return f"{inspect.stack()[1].function}()"


def get_enum_key_by_value(enum_dict: dict[str, Any], category: Any, enum_value: Any, default_return: Any = None) -> Any:
    """
    Return the key from enum_dict for the given enum_value.
    """
    enum_values: dict[str, Any] | None = enum_dict.get(category)
    if enum_values:
        enum_value_match: list[Any] | None = [key for key, value in enum_values.items() if value == enum_value]
        return enum_value_match[0] if enum_value_match else default_return
    else:
        return default_return


def validate_file_path(path: str | Path | os.PathLike[str]) -> bool:
    """Test whether provided path exists or not

    Args:
        path: path of file to validate

    Returns:
        True if exists, False otherwise.

    """
    if not path:
        err_msg = f"{get_function_name()}: 'path' argument is required."
        raise SwgohComlinkValueError(err_msg)
    return os.path.exists(path) and os.path.isfile(path)


def sanitize_allycode(allycode: str | int | None = None) -> str:
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
    if allycode is None:
        logger.warning(f"{get_function_name()}: Invalid ally code: {allycode}")
        return ""

    # Handle string input validation
    if isinstance(allycode, str):
        allycode = allycode.replace("-", "")
        if not allycode.isdigit() or len(allycode) != 9:
            err_msg = f"{get_function_name()}: Invalid ally code: {allycode}"
            raise SwgohComlinkValueError(err_msg)
        return allycode

    if isinstance(allycode, int):
        allycode = str(allycode)
        if len(allycode) != 9:
            err_msg = f"{get_function_name()}: Invalid ally code: {allycode}"
            raise SwgohComlinkValueError(err_msg)
        return allycode

    err_msg = f"{get_function_name()}: Invalid ally code: {allycode}"
    raise SwgohComlinkValueError(err_msg)


def human_time(unix_time: int | float) -> str:
    """Convert unix time to human-readable string

    Args:
        unix_time (int|float): standard unix time in seconds or milliseconds

    Returns:
        str: human-readable time string

    Raises:
        SwgohComlinkValueError: If the provided unix time is not of the expected type

    Notes:
        If the provided unix time is invalid or an error occurs, the default time string returned
        is 1970-01-01 00:00:00

    """
    # Try to handle a numeric timestamp value that was passed in as a string
    if isinstance(unix_time, str):
        try:
            unix_time = int(unix_time)
        except (ValueError, TypeError) as e:
            err_msg = f"Unable to convert unix time from {type(unix_time)} to type <int>"
            raise SwgohComlinkValueError(err_msg) from e
    if not isinstance(unix_time, (int, float)):
        raise SwgohComlinkValueError("The 'unix_time' argument is required.")
    from datetime import datetime, timezone

    if isinstance(unix_time, float):
        unix_time = int(unix_time)

    if len(str(unix_time)) >= 13:  # milliseconds
        unix_time /= 1000
    return datetime.fromtimestamp(unix_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def convert_relic_tier(relic_tier: str | int) -> str | None:
    """Convert character relic tier to offset string in-game value.

    Conversion is done based on a zero based table indicating both the relic tier status and achieved level.

    Args:
        relic_tier (str | int): The relic tier from character game data to convert to in-game equivalent.

    Returns:
        String representing the relic status and tier

    Raises:
        SwgohComlinkValueError: If the provided 'relic_tier' is not of the expected type.
        TypeError: If the provided 'relic_tier' cannot be converted to a string using the Python
                    built-in str() method.

    Examples:
        Relic tier is '0' indicates the character has not yet achieved a level where access to relics have been
            unlocked.
        Relic tier of '1', indicates that the character has achieved the required level to access relics,
            but has not yet upgraded to the first level.
    """
    if not isinstance(relic_tier, (str, int)):
        err_msg = f"{get_function_name()}: 'relic_tier' argument is required for conversion."
        raise SwgohComlinkValueError(err_msg)
    relic_value = None
    if isinstance(relic_tier, int):
        try:
            relic_tier = str(relic_tier)
        except TypeError:
            err_msg = f"{get_function_name()}: Unable to convert 'relic_tier' argument to string."
            raise SwgohComlinkTypeError(err_msg)

    if relic_tier in Constants.RELIC_TIERS:
        relic_value = Constants.RELIC_TIERS[relic_tier]
    return relic_value
