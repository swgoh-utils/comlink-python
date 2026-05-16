# coding=utf-8
"""Pure-function payload builders for every comlink endpoint.

Each endpoint method on :class:`SwgohComlink` / :class:`SwgohComlinkAsync`
delegates payload construction to one of these helpers. They're pure
(no client state needed) so they're shared between sync and async with
no duplication — the sync and async endpoint methods become tiny
wrappers around ``self._post(endpoint, payload(...), decoder=...)``.

Three pre-existing builders moved out of :class:`SwgohComlinkBase`
(where they lived as ``@staticmethod``s):

* :func:`player_payload` — was ``_get_player_payload``.
* :func:`game_data_payload` — was ``_build_game_data_payload``.
* :func:`unit_stats_endpoint` — was ``_build_unit_stats_endpoint``.

The old names remain on :class:`SwgohComlinkBase` as thin
back-compat aliases so any external caller that reached into the SDK
to call them keeps working. Mark for removal in v3.2.
"""

from __future__ import annotations

from typing import Any

from .exceptions import SwgohComlinkValueError
from .helpers import Constants

__all__ = [
    "game_data_payload",
    "game_metadata_payload",
    "guild_criteria_payload",
    "guild_leaderboard_payload",
    "guild_payload",
    "guild_search_payload",
    "leaderboard_payload",
    "localization_payload",
    "player_arena_payload",
    "player_payload",
    "resolve_leaderboard_league_division",
    "unit_stats_endpoint",
]


# ── /player ─────────────────────────────────────────────────────────────────


def player_payload(
    allycode: str | int | None = None,
    player_id: str | None = None,
    enums: bool = False,
) -> dict[str, Any]:
    """Build payload for ``get_player`` / ``get_player_arena``.

    Raises:
        SwgohComlinkValueError: If neither argument is provided, or the
            ally code isn't 9 digits.
    """
    if not allycode and not player_id:
        raise SwgohComlinkValueError("Either 'allycode' or 'player_id' must be provided.")
    payload: dict[str, Any] = {"payload": {}, "enums": enums}
    if player_id:
        payload["payload"]["playerId"] = str(player_id)
    else:
        code_str = str(allycode).replace("-", "")
        if not code_str.isdigit() or len(code_str) != 9:
            raise SwgohComlinkValueError("Allycode must be a 9-digit number.")
        payload["payload"]["allyCode"] = code_str
    return payload


def player_arena_payload(
    allycode: str | int | None = None,
    player_id: str | None = None,
    player_details_only: bool = False,
    enums: bool = False,
) -> dict[str, Any]:
    """Build payload for ``get_player_arena``."""
    payload = player_payload(allycode=allycode, player_id=player_id, enums=enums)
    payload["payload"]["playerDetailsOnly"] = player_details_only
    return payload


# ── /guild family ───────────────────────────────────────────────────────────


def guild_payload(
    guild_id: str,
    include_recent_guild_activity_info: bool = False,
    enums: bool = False,
) -> dict[str, Any]:
    """Build payload for ``get_guild``. Raises on empty ``guild_id``."""
    if not guild_id:
        raise SwgohComlinkValueError("guild_id must not be empty.")
    return {
        "payload": {
            "guildId": guild_id,
            "includeRecentGuildActivityInfo": include_recent_guild_activity_info,
        },
        "enums": enums,
    }


def guild_search_payload(
    name: str,
    start_index: int = 0,
    count: int = 10,
    enums: bool = False,
) -> dict[str, Any]:
    """Build payload for ``get_guilds_by_name`` (filterType=4)."""
    return {
        "payload": {"name": name, "filterType": 4, "startIndex": start_index, "count": count},
        "enums": enums,
    }


def guild_criteria_payload(
    search_criteria: dict[str, Any],
    start_index: int = 0,
    count: int = 10,
    enums: bool = False,
) -> dict[str, Any]:
    """Build payload for ``get_guilds_by_criteria`` (filterType=5)."""
    return {
        "payload": {
            "searchCriteria": search_criteria,
            "filterType": 5,
            "startIndex": start_index,
            "count": count,
        },
        "enums": enums,
    }


def guild_leaderboard_payload(
    leaderboard_id: list[dict[str, Any]],
    count: int = 200,
    enums: bool = False,
) -> dict[str, Any]:
    """Build payload for ``get_guild_leaderboard``."""
    return {"payload": {"leaderboardId": leaderboard_id, "count": count}, "enums": enums}


# ── /metadata ───────────────────────────────────────────────────────────────


def game_metadata_payload(
    client_specs: dict[str, Any] | None = None,
    enums: bool = False,
) -> dict[str, Any]:
    """Build payload for ``get_game_metadata``. Empty when ``client_specs`` is None."""
    if not client_specs:
        return {}
    return {"payload": {"client_specs": client_specs}, "enums": enums}


# ── /data ───────────────────────────────────────────────────────────────────


def game_data_payload(
    game_version: str,
    include_pve_units: bool = True,
    request_segment: int = 0,
    enums: bool = False,
    items: str | int | None = None,
    device_platform: str = "Android",
) -> dict[str, Any]:
    """Build payload for ``get_game_data``.

    Raises:
        SwgohComlinkValueError: If ``request_segment`` is out of range
            and ``items`` wasn't provided.
    """
    payload: dict[str, Any] = {
        "payload": {
            "version": f"{game_version}",
            "devicePlatform": device_platform,
            "includePveUnits": include_pve_units,
        },
        "enums": enums,
    }
    if items:
        if isinstance(items, int):
            payload["payload"]["items"] = str(items)
        elif items.lstrip("-").isdigit():
            payload["payload"]["items"] = items
        else:
            payload["payload"]["items"] = Constants.get(items) or "-1"
    else:
        if request_segment < 0 or request_segment > 4:
            raise SwgohComlinkValueError(
                "Invalid argument. <request_segment> should be an integer between 0 and 4, inclusive.",
            )
        payload["payload"]["requestSegment"] = request_segment
    return payload


# ── /localization ───────────────────────────────────────────────────────────


def localization_payload(
    localization_id: str,
    locale: str | None = None,
    unzip: bool = False,
    enums: bool = False,
) -> dict[str, Any]:
    """Build payload for ``get_localization``.

    ``localization_id`` must be resolved by the caller (the metadata-fetch
    fallback is sync/async-specific and stays in the endpoint method).
    """
    if locale:
        localization_id = f"{localization_id}:{locale.upper()}"
    return {"unzip": unzip, "payload": {"id": localization_id}, "enums": enums}


# ── /getLeaderboard ─────────────────────────────────────────────────────────


def resolve_leaderboard_league_division(
    league: int | str | None,
    division: int | str | None,
) -> tuple[int | None, int | None]:
    """Normalize the ``league`` and ``division`` args to their int IDs.

    Accepts string names (``"kyber"``), single-digit ints (``1`` → ``"1"`` →
    int ID), or already-normalized ints. Returns ``(league_id, division_id)``
    suitable for inclusion in a leaderboard payload.
    """
    leagues = Constants.LEAGUES
    divisions = Constants.DIVISIONS
    if isinstance(league, str):
        league = leagues[league.lower()]
    if isinstance(division, int) and len(str(division)) == 1:
        division = divisions[str(division).lower()]
    if isinstance(division, str):
        division = divisions[division.lower()]
    return league, division


def leaderboard_payload(
    leaderboard_type: int,
    league: int | str | None = None,
    division: int | str | None = None,
    event_instance_id: str | None = None,
    group_id: str | None = None,
    enums: bool = False,
) -> dict[str, Any]:
    """Build payload for ``get_leaderboard`` (types 4 and 6)."""
    league_id, division_id = resolve_leaderboard_league_division(league, division)
    payload: dict[str, Any] = {
        "payload": {"leaderboardType": leaderboard_type},
        "enums": enums,
    }
    if leaderboard_type == 4:
        payload["payload"]["eventInstanceId"] = event_instance_id
        payload["payload"]["groupId"] = group_id
    elif leaderboard_type == 6:
        payload["payload"]["league"] = league_id
        payload["payload"]["division"] = division_id
    return payload


# ── /getUnitStats endpoint string ──────────────────────────────────────────


def unit_stats_endpoint(
    flags: list[str] | None = None,
    language: str | None = None,
) -> str:
    """Build the ``/api`` endpoint string with optional query parameters.

    Raises:
        SwgohComlinkValueError: If *flags* contains values outside the
            allow-list.
    """
    _allowed_flags = {
        "gameStyle",
        "calcGP",
        "onlyGP",
        "withoutModCalc",
        "percentVals",
        "useMax",
        "scaled",
        "unscaled",
        "statIDs",
        "enums",
        "noSpace",
    }
    flag_str = None
    if flags:
        if isinstance(flags, list) and set(flags).issubset(_allowed_flags):
            flag_str = "flags=" + ",".join(flags)
        else:
            raise SwgohComlinkValueError(
                f'Invalid argument. <flags> should be a list of strings with one or more of "'
                f"{_allowed_flags} flag values.",
            )
    lang_str = f"language={language}" if language else None
    query_string = None
    if flag_str or lang_str:
        query_string = "?" + "&".join(filter(None, [flag_str, lang_str]))
    return "api" + query_string if query_string else "api"
