# coding=utf-8
"""Game configuration helper functions."""

from __future__ import annotations

from typing import Any, overload

from ..exceptions import SwgohComlinkValueError
from ._utils import get_function_name


def _config_rows(metadata: dict[str, Any] | list[dict[str, Any]], function_name: str) -> list[dict[str, Any]]:
    rows = metadata.get("config") if isinstance(metadata, dict) else metadata
    if not isinstance(rows, list):
        raise SwgohComlinkValueError(
            f"{function_name}: 'metadata' must be a get_game_metadata() response or its 'config' list, "
            f"not {type(metadata)}"
        )
    return [row for row in rows if isinstance(row, dict)]


def _config_value(rows: list[dict[str, Any]], key: str) -> Any:
    """The first value listed for ``key``, or ``None``."""
    return next((row["value"] for row in rows if row.get("key") == key and "value" in row), None)


@overload
def get_game_config(metadata: dict[str, Any] | list[dict[str, Any]], key: None = None) -> dict[str, str]: ...


@overload
def get_game_config(metadata: dict[str, Any] | list[dict[str, Any]], key: str) -> str | None: ...


def get_game_config(
    metadata: dict[str, Any] | list[dict[str, Any]], key: str | None = None
) -> dict[str, str] | str | None:
    """Read the game's own configuration values from the game metadata.

    ``get_game_metadata()`` returns several hundred ``config`` rows of game tuning, each
    ``{"key": ..., "value": ...}``, with every value a string, including the numeric ones. Useful keys
    include ``max-conquest-currency``, ``max-datacron-currency``, ``stat-mod-max-storage``,
    ``conquest-stamina-recovery-duration-in-seconds`` and the ``squad-preset-*`` limits. Use
    :func:`get_game_config_int` to read one as an integer.

    Args:
        metadata: The response from ``SwgohComlink.get_game_metadata()``, or its ``config`` list.
        key: A single configuration key to return. [Default: all of them]

    Returns:
        With no ``key``, a dictionary of every configuration key to its string value. With a ``key``, its
        value, or ``None`` when the game metadata does not carry it. A key listed more than once keeps
        its first value.

    Raises:
        SwgohComlinkValueError: If ``metadata`` is not a ``get_game_metadata()`` response or its
            ``config`` list.

    Examples:
        >>> metadata = comlink.get_game_metadata()  # doctest: +SKIP
        >>> get_game_config(metadata, "max-conquest-currency")  # doctest: +SKIP
        '3500'
        >>> get_game_config(metadata)["stat-mod-max-level"]  # doctest: +SKIP
        '15'
    """
    rows = _config_rows(metadata, get_function_name())
    if key is not None:
        value = _config_value(rows, key)
        return None if value is None else str(value)
    config: dict[str, str] = {}
    for row in rows:
        if isinstance(row.get("key"), str) and "value" in row:
            config.setdefault(row["key"], str(row["value"]))
    return config


def get_game_config_int(
    metadata: dict[str, Any] | list[dict[str, Any]], key: str, default: int | None = None
) -> int | None:
    """Read one numeric configuration value from the game metadata as an integer.

    Configuration values are strings, and some keys hold text (``"true"``, ``"SPEED"``) rather than a
    number. A missing key or a value that is not an integer returns ``default``, so a caller can tell
    "not known" apart from a real value of zero.

    Args:
        metadata: The response from ``SwgohComlink.get_game_metadata()``, or its ``config`` list.
        key: The configuration key, e.g. ``"stat-mod-max-storage"``.
        default: The value to return when the key is missing or not an integer. [Default: None]

    Returns:
        The configuration value as an integer, or ``default``.

    Raises:
        SwgohComlinkValueError: If ``metadata`` is not a ``get_game_metadata()`` response or its
            ``config`` list.

    Examples:
        >>> get_game_config_int(comlink.get_game_metadata(), "stat-mod-max-storage")  # doctest: +SKIP
        500
    """
    value = _config_value(_config_rows(metadata, get_function_name()), key)
    try:
        return int(str(value).strip()) if value is not None else default
    except ValueError:
        return default
