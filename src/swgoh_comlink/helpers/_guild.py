# coding=utf-8
"""Guild-related helper functions."""

from __future__ import annotations

from collections.abc import Coroutine
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal, TypedDict, overload

from ..exceptions import SwgohComlinkValueError
from ._utils import _as_int, _client_kind, get_function_name, sanitize_allycode

if TYPE_CHECKING:
    from swgoh_comlink import SwgohComlink, SwgohComlinkAsync

# memberLevel (GuildMemberLevel), looked up as text: an integer (enums=False) or its enum name (enums=True)
_MEMBER_ROLES: dict[str, tuple[int, str]] = {
    "1": (1, "Pending"),
    "2": (2, "Member"),
    "3": (3, "Officer"),
    "4": (4, "Leader"),
    "GUILD_PENDING": (1, "Pending"),
    "GUILD_MEMBER": (2, "Member"),
    "GUILD_OFFICER": (3, "Officer"),
    "GUILD_LEADER": (4, "Leader"),
}


class TerritoryBattleResult(TypedDict):
    """A completed Territory Battle, as returned in :attr:`GuildActivity.best_territory_battle`."""

    definition_id: str
    """The battle's ``definitionId``, e.g. ``"t05D"`` for Rise of the Empire."""
    total_stars: int


class TerritoryWarResult(TypedDict):
    """A completed Territory War, as returned in :attr:`GuildActivity.territory_wars`."""

    territory_war_id: str
    score: int
    opponent_score: int
    result: Literal["win", "loss", "tie"]
    """``"win"`` when ``score`` is higher than ``opponent_score``."""
    opponent_name: str | None
    """The opponent guild's name, when the payload carries its profile."""


class RaidResult(TypedDict):
    """A guild's most recent raid, as returned in :attr:`GuildActivity.last_raid`."""

    raid_id: str
    """The raid's ``raidId``, e.g. ``"order66"`` or ``"kraytdragon"``."""
    guild_score: int
    """The guild's ``guildRewardScore``: the sum of every member's score."""
    member_scores: dict[str, int]
    """Player id to that member's ``memberProgress`` (score) in this raid."""


class GuildMemberActivity(TypedDict):
    """One guild member, as returned in :attr:`GuildActivity.members`."""

    player_id: str
    name: str
    member_level: int | None
    """``memberLevel`` as a number: 1 pending, 2 member, 3 officer, 4 leader. ``None`` when unknown."""
    role: str | None
    """``"Pending"``, ``"Member"``, ``"Officer"`` or ``"Leader"``, or ``None`` when unknown."""
    galactic_power: int
    joined: datetime | None
    """When the member joined the guild (``guildJoinTime``), as a timezone-aware UTC datetime."""
    last_activity: datetime | None
    """The member's ``lastActivityTime``, as a timezone-aware UTC datetime."""
    raid_score: int | None
    """The member's score in :attr:`GuildActivity.last_raid`, or ``None`` when they are not in it."""


class GuildActivity(TypedDict):
    """A guild's recent activity as returned by :func:`get_guild_activity`."""

    guild_id: str
    name: str
    member_count: int
    member_max: int
    galactic_power: int
    best_territory_battle: TerritoryBattleResult | None
    """The recent Territory Battle with the most stars, or ``None`` when there is none."""
    territory_wars: list[TerritoryWarResult]
    """Recent Territory Wars, in payload order."""
    territory_war_wins: int
    territory_war_losses: int
    last_raid: RaidResult | None
    members: list[GuildMemberActivity]


@overload
def get_guild_members(
    comlink: SwgohComlink, player_id: str | None = None, allycode: str | int | None = None
) -> list[Any]: ...
@overload
def get_guild_members(
    comlink: SwgohComlinkAsync, player_id: str | None = None, allycode: str | int | None = None
) -> Coroutine[Any, Any, list[Any]]: ...
def get_guild_members(
    comlink: Any,
    player_id: str | None = None,
    allycode: str | int | None = None,
) -> list[Any] | Coroutine[Any, Any, list[Any]]:
    """Return list of guild member player allycodes based upon provided player ID or allycode

    Args:
        comlink: Instance of SwgohComlink. An instance of SwgohComlinkAsync is also accepted, in which case
            the result of :func:`async_get_guild_members` is returned for the caller to await.
        player_id: Player's ID
        allycode: Player's allycode

    Returns:
        list of guild members objects, or an awaitable of it when ``comlink`` is a SwgohComlinkAsync

    Note:
        A player_id or allycode argument is required. The guild is requested with
        ``include_recent_guild_activity_info=True``: without it, current game versions return every
        member with an empty name, zero galactic power and no last activity time.

    """
    kind = _client_kind(comlink)
    if kind == "async":
        return async_get_guild_members(comlink, player_id=player_id, allycode=allycode)
    if kind != "sync":
        err_msg = f"{get_function_name()}: The 'comlink' argument is required and must be an instance of SwgohComlink."
        raise SwgohComlinkValueError(err_msg)

    if player_id is not None and allycode is not None:
        err_msg = f"{get_function_name()}: Either 'player_id' or 'allycode' are allowed arguments, not both."
        raise SwgohComlinkValueError(err_msg)

    if player_id is None and allycode is None:
        err_msg = f"{get_function_name()}: One of either 'player_id' or 'allycode' is required."
        raise SwgohComlinkValueError(err_msg)

    if isinstance(player_id, str):
        player = comlink.get_player(player_id=player_id)
    else:
        player = comlink.get_player(allycode=sanitize_allycode(allycode))
    guild = comlink.get_guild(guild_id=player["guildId"], include_recent_guild_activity_info=True)
    return guild["member"] or []


async def async_get_guild_members(
    comlink: Any,
    player_id: str | None = None,
    allycode: str | int | None = None,
) -> list[Any]:
    """Return list of guild member player allycodes based upon provided player ID or allycode (async version).

    Args:
        comlink: Instance of SwgohComlinkAsync
        player_id: Player's ID
        allycode: Player's allycode

    Returns:
        list of guild members objects

    Note:
        A player_id or allycode argument is required. The guild is requested with
        ``include_recent_guild_activity_info=True``: without it, current game versions return every
        member with an empty name, zero galactic power and no last activity time.

    """
    if _client_kind(comlink) != "async":
        err_msg = (
            f"{get_function_name()}: The 'comlink' argument is required and must be an instance of SwgohComlinkAsync."
        )
        raise SwgohComlinkValueError(err_msg)

    if player_id is not None and allycode is not None:
        err_msg = f"{get_function_name()}: Either 'player_id' or 'allycode' are allowed arguments, not both."
        raise SwgohComlinkValueError(err_msg)

    if player_id is None and allycode is None:
        err_msg = f"{get_function_name()}: One of either 'player_id' or 'allycode' is required."
        raise SwgohComlinkValueError(err_msg)

    if isinstance(player_id, str):
        player = await comlink.get_player(player_id=player_id)
    else:
        player = await comlink.get_player(allycode=sanitize_allycode(allycode))
    guild = await comlink.get_guild(guild_id=player["guildId"], include_recent_guild_activity_info=True)
    return guild["member"] or []


def _epoch(value: Any, scale: int) -> datetime | None:
    """An epoch time in seconds (``scale=1``) or milliseconds (``scale=1000``); 0 or missing is ``None``."""
    number = _as_int(value)
    return datetime.fromtimestamp(number / scale, tz=timezone.utc) if number > 0 else None


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def get_guild_activity(guild: dict[str, Any]) -> GuildActivity:
    """Summarize a guild's recent Territory Battles, Territory Wars and raid, and its members.

    The recent results are only present when the guild was requested with
    ``include_recent_guild_activity_info=True``; without it they are empty, and current game versions
    also return every member with an empty name, zero galactic power and no last activity time.

    The payload's numbers are read whether they arrive as integers or as strings. Member join times
    (``guildJoinTime``) are epoch **seconds**, while ``lastActivityTime`` is epoch milliseconds; both are
    returned as datetimes, and a missing or zero value as ``None``. ``memberLevel`` is read as a number
    or as its ``GuildMemberLevel`` enum name (``enums=True``).

    Args:
        guild: The response from ``SwgohComlink.get_guild(..., include_recent_guild_activity_info=True)``.
            A response still wrapped as ``{"guild": {...}}`` is accepted.

    Returns:
        A :class:`GuildActivity` dictionary. ``best_territory_battle`` is the recent battle with the most
        stars (the payload carries no all-time best); a Territory War is a win when ``score`` beats
        ``opponentScore``, and a tie counts as neither; ``last_raid`` is the first ``recentRaidResult``.
        Members are in payload order.

    Raises:
        SwgohComlinkValueError: If ``guild`` is not a dictionary.

    Examples:
        >>> guild = comlink.get_guild(guild_id, include_recent_guild_activity_info=True)  # doctest: +SKIP
        >>> activity = get_guild_activity(guild)  # doctest: +SKIP
        >>> activity["territory_war_wins"], activity["territory_war_losses"]  # doctest: +SKIP
        (6, 2)
    """
    if not isinstance(guild, dict):
        raise SwgohComlinkValueError(f"{get_function_name()}: 'guild' must be a dictionary, not {type(guild)}")
    if isinstance(guild.get("guild"), dict):
        guild = guild["guild"]
    profile: dict[str, Any] = raw if isinstance(raw := guild.get("profile"), dict) else {}
    members = _dicts(guild.get("member"))

    battles: list[TerritoryBattleResult] = [
        {"definition_id": entry.get("definitionId", ""), "total_stars": _as_int(entry.get("totalStars"))}
        for entry in _dicts(guild.get("recentTerritoryBattleResult"))
    ]

    wars: list[TerritoryWarResult] = []
    for entry in _dicts(guild.get("recentTerritoryWarResult")):
        score, opponent_score = _as_int(entry.get("score")), _as_int(entry.get("opponentScore"))
        opponent = entry.get("opponentGuildProfile")
        wars.append(
            {
                "territory_war_id": entry.get("territoryWarId", ""),
                "score": score,
                "opponent_score": opponent_score,
                "result": "win" if score > opponent_score else "loss" if score < opponent_score else "tie",
                "opponent_name": opponent.get("name") if isinstance(opponent, dict) else None,
            }
        )

    last_raid: RaidResult | None = None
    if raids := _dicts(guild.get("recentRaidResult")):
        last_raid = {
            "raid_id": raids[0].get("raidId", ""),
            "guild_score": _as_int(raids[0].get("guildRewardScore")),
            "member_scores": {
                member["playerId"]: _as_int(member.get("memberProgress"))
                for member in _dicts(raids[0].get("raidMember"))
                if member.get("playerId")
            },
        }
    raid_scores = last_raid["member_scores"] if last_raid is not None else {}

    member_activity: list[GuildMemberActivity] = []
    for member in members:
        level, role = _MEMBER_ROLES.get(str(member.get("memberLevel")), (None, None))
        player_id = member.get("playerId", "")
        member_activity.append(
            {
                "player_id": player_id,
                "name": member.get("playerName", ""),
                "member_level": level,
                "role": role,
                "galactic_power": _as_int(member.get("galacticPower")),
                "joined": _epoch(member.get("guildJoinTime"), 1),
                "last_activity": _epoch(member.get("lastActivityTime"), 1000),
                "raid_score": raid_scores.get(player_id),
            }
        )

    return {
        "guild_id": profile.get("id", ""),
        "name": profile.get("name", ""),
        # memberCount is the game's own figure; fall back to the roster when it is missing
        "member_count": _as_int(profile.get("memberCount")) or len(members),
        "member_max": _as_int(profile.get("memberMax")),
        "galactic_power": _as_int(profile.get("guildGalacticPower")),
        "best_territory_battle": max(battles, key=lambda battle: battle["total_stars"]) if battles else None,
        "territory_wars": wars,
        "territory_war_wins": sum(war["result"] == "win" for war in wars),
        "territory_war_losses": sum(war["result"] == "loss" for war in wars),
        "last_raid": last_raid,
        "members": member_activity,
    }
