# coding=utf-8
"""General utility functions: validation, sanitization, conversion."""

from __future__ import annotations

import inspect
import logging
import os
from pathlib import Path
from typing import Any, Literal

from ..exceptions import SwgohComlinkValueError
from ._constants import Constants

logger = logging.getLogger(__name__)

_CLIENT_KINDS: dict[str, Literal["sync", "async"]] = {"SwgohComlink": "sync", "SwgohComlinkAsync": "async"}


def get_function_name() -> str:
    """Return the name of the calling function"""
    return f"{inspect.stack()[1].function}()"


def _client_kind(comlink: Any) -> Literal["sync", "async"] | None:
    """Return whether *comlink* is a sync or an async client, or ``None`` when it is neither.

    ``__comlink_type__`` is read from the instance and then from each class in its MRO, so a subclass
    that sets a ``__comlink_type__`` of its own is still recognised as the client it extends.
    """
    candidates = [getattr(comlink, "__comlink_type__", None)]
    candidates += [vars(cls).get("__comlink_type__") for cls in type(comlink).__mro__]
    return next((_CLIENT_KINDS[name] for name in candidates if name in _CLIENT_KINDS), None)


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


_RELIC_TIER_NAMES = {"RELICTIER_DEFAULT": 0, "RELIC_LOCKED": 1, "RELIC_UNLOCKED": 2}


def convert_relic_tier(relic_tier: str | int) -> str | None:
    """Convert a unit's wire relic tier to the relic level shown in game.

    The game's RelicTier enum starts two below the relic level: ``RELIC_LOCKED`` is 1, ``RELIC_UNLOCKED``
    (relic 0) is 2 and ``RELIC_TIER_01`` is 3, so a roster unit's ``relic.currentTier`` of 9 is relic 7.

    Args:
        relic_tier (str | int): A roster unit's ``relic.currentTier``, as an integer, a numeric string, or
            the enum name returned with ``enums=True`` (e.g. ``"RELIC_TIER_07"``).

    Returns:
        ``"LOCKED"``, ``"UNLOCKED"`` (relic 0), the relic level as a string (``"1"`` to ``"10"``), or
        ``None`` for an unrecognized value.

    Raises:
        SwgohComlinkValueError: If the provided 'relic_tier' is not a string or integer.

    Examples:
        >>> convert_relic_tier(1)
        'LOCKED'
        >>> convert_relic_tier(2)
        'UNLOCKED'
        >>> convert_relic_tier(9)
        '7'
        >>> convert_relic_tier("RELIC_TIER_07")
        '7'
    """
    if not isinstance(relic_tier, (str, int)) or isinstance(relic_tier, bool):
        err_msg = f"{get_function_name()}: 'relic_tier' argument is required for conversion."
        raise SwgohComlinkValueError(err_msg)

    key = str(relic_tier)
    if isinstance(relic_tier, str) and not key.isdigit():
        name = key.upper()
        level = name.removeprefix("RELIC_TIER_")
        if name in _RELIC_TIER_NAMES:
            key = str(_RELIC_TIER_NAMES[name])
        elif level != name and level.isdigit():
            key = str(int(level) + Constants.RELIC_OFFSET)
    return Constants.RELIC_TIERS.get(key)


def _as_int(value: Any, default: int = 0) -> int:
    """Read a payload number, which arrives as an int or, for int64 fields, as a numeric string.

    Anything else (``None``, a bool, an enum name, junk) reads as ``default``.
    """
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default
