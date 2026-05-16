# coding=utf-8
"""Guild-related helper functions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..exceptions import SwgohComlinkValueError
from ._utils import get_function_name, sanitize_allycode

if TYPE_CHECKING:
    from swgoh_comlink import SwgohComlink, SwgohComlinkAsync  # noqa: F401


def get_guild_members(
    comlink: Any,
    player_id: str | None = None,
    allycode: str | int | None = None,
) -> list[Any]:
    """Return list of guild member player allycodes based upon provided player ID or allycode

    Args:
        comlink: Instance of SwgohComlink
        player_id: Player's ID
        allycode: Player's allycode

    Returns:
        list of guild members objects

    Note:
        A player_id or allycode argument is required

    """
    comlink_type = getattr(comlink, "__comlink_type__", None)
    if comlink_type != "SwgohComlink":
        err_msg = f"{get_function_name()}: The 'comlink' argument is required and must be an instance of SwgohComlink."
        raise SwgohComlinkValueError(err_msg)

    if player_id is not None and allycode is not None:
        err_msg = f"{get_function_name()}: Either 'player_id' or 'allycode' are allowed arguments, not both."
        raise SwgohComlinkValueError(err_msg)

    if player_id is None and allycode is None:
        err_msg = f"{get_function_name()}: One of either 'player_id' or 'allycode' is required."
        raise SwgohComlinkValueError(err_msg)

    # v3: helpers stay v2-compatible by opting into raw=True (dict shape).
    # When this helper is migrated to attribute access, drop the kwargs.
    if isinstance(player_id, str):
        player = comlink.get_player(player_id=player_id, raw=True)
    else:
        player = comlink.get_player(allycode=sanitize_allycode(allycode), raw=True)
    guild = comlink.get_guild(guild_id=player["guildId"], raw=True)
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
        A player_id or allycode argument is required

    """
    comlink_type = getattr(comlink, "__comlink_type__", None)
    if comlink_type != "SwgohComlinkAsync":
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

    # v3: helpers stay v2-compatible by opting into raw=True (dict shape).
    if isinstance(player_id, str):
        player = await comlink.get_player(player_id=player_id, raw=True)
    else:
        player = await comlink.get_player(allycode=sanitize_allycode(allycode), raw=True)
    guild = await comlink.get_guild(guild_id=player["guildId"], raw=True)
    return guild["member"] or []
