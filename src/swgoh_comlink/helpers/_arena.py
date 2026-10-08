# coding=utf-8
"""Arena-related helper functions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
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


def get_arena_payout(offset: int, fleet: bool = False, *, now: datetime | None = None) -> datetime:
    """
    Calculate the next arena payout time.

    A player's payout is a fixed time each day: 18:00 UTC (squad) or 19:00 UTC (fleet), moved back by
    the player's ``localTimeZoneOffsetMinutes``.

    Args:
        offset (int): The player's ``localTimeZoneOffsetMinutes`` from ``get_player()``.
        fleet (bool): Indicates if the payout is for fleet arena (True) or squad arena
            (False). Defaults to False.
        now (datetime | None): The time to count from. A naive value is read as local time.
            Defaults to the current time.

    Returns:
        datetime: The next payout after ``now``, as a timezone-aware UTC datetime.
    """
    now = datetime.now(timezone.utc) if now is None else now.astimezone(timezone.utc)
    hour = 19 if fleet else 18
    payout = now.replace(hour=hour, minute=0, second=0, microsecond=0) - timedelta(minutes=offset)
    # The offset can move the payout onto another UTC day, so step back as well as forward.
    while payout - timedelta(days=1) > now:
        payout -= timedelta(days=1)
    while payout <= now:
        payout += timedelta(days=1)
    return payout
