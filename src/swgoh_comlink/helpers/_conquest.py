# coding=utf-8
"""Conquest helper functions."""

from __future__ import annotations

import time
from typing import Any
from math import floor

from ..exceptions import SwgohComlinkValueError


def calc_current_stamina(unit: dict[str, Any], pass_plus: bool = False) -> int:
    """
    Calculates the current stamina of a game unit based on the elapsed time since the last refresh.
    The calculation considers a unit's last recorded stamina value, the time that has passed since it
    was last refreshed, and the optional influence of Conquest Pass+ (which accelerates stamina recovery by 33%).

    Parameters:
    unit (dict[str, Any]): A dictionary containing the unit's data, including "remainingStamina" and "lastRefreshTime".
    pass_plus (bool): A flag indicating whether the Conquest Pass+ is active. Defaults to False.

    Returns:
    int: The calculated current stamina value, capped at a maximum of 100.

    Raises:
    SwgohComlinkValueError: If 'unit' is not a dictionary.
    SwgohComlinkValueError: If the unit dictionary does not contain valid "remainingStamina" or "lastRefreshTime" fields.
    """

    if not isinstance(unit, dict):
        raise SwgohComlinkValueError(f"'unit' must be a dict, not {type(unit)}")

    acceleration_factor = 1.33 if pass_plus else 1.0
    remaining_stamina: int = unit.get("remainingStamina")
    last_refresh_time: int = int(unit.get("lastRefreshTime"))

    if remaining_stamina is None or last_refresh_time is None:
        raise SwgohComlinkValueError("Invalid unit data. Unable to determine current stamina and/or last refresh time.")

    time_diff_minutes = floor((floor(time.time()) - last_refresh_time) / 60)

    # Stamina regenerates 1% every 30 minutes
    # Conquest Pass+ holders increase stamina regeneration by 33%

    return min(floor(time_diff_minutes / 30 * acceleration_factor), 100)
