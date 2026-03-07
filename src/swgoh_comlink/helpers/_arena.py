# coding=utf-8
"""Arena-related helper functions."""

from __future__ import annotations

from datetime import datetime, timedelta
from math import floor


def get_max_rank_jump(current_rank: int) -> int:
    """
    Calculates the maximum rank jump a player can achieve based on their current rank.
    The calculation is determined by applying different logic according to ranges of
    the current rank.

    Args:
        current_rank (int): The player's current rank.

    Returns:
        int: The maximum rank jump the player can achieve.
    """
    if current_rank < 6:
        return 1
    elif current_rank < 55:
        return current_rank - (3 + max(floor((current_rank - 1) / 6), 1))
    else:
        return int(round(current_rank * 0.85 - 1))


def get_arena_payout(offset: int, fleet: bool = False) -> datetime:
    """
    Calculate the next arena payout time.

    This function computes the next payout time based on the given offset, considering
    whether the requested payout is for fleet or squad arena. It adjusts for time zone
    offsets and ensures that the computed payout time is always in the future relative
    to the current time.

    Args:
        offset (int): Time offset in minutes to adjust the payout time.
        fleet (bool): Indicates if the payout is for fleet arena (True) or regular arena
            (False). Defaults to False.

    Returns:
        datetime: The computed next payout time as a datetime object.
    """
    payout = datetime.now()
    utc_offset = payout.astimezone().utcoffset()
    local_offset = -(utc_offset.total_seconds() / 60) if utc_offset is not None else 0.0
    if fleet:
        payout = payout.replace(hour=19, minute=0, second=0, microsecond=0)
    else:
        payout = payout.replace(hour=18, minute=0, second=0, microsecond=0)
    payout = payout - timedelta(minutes=(offset + local_offset))
    if payout < datetime.now():
        payout = payout + timedelta(days=1)
    return payout
