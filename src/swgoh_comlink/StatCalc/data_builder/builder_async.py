"""Asynchronous GameDataBuilderAsync."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ...helpers import DataItems
from ._builder_base import GameDataBuilderBase

if TYPE_CHECKING:
    from swgoh_comlink import SwgohComlinkAsync

logger = logging.getLogger(__name__)

# Collections needed to produce a full StatCalc game-data payload.
_REQUIRED_ITEMS: int = (
    DataItems.CATEGORY
    | DataItems.SKILL
    | DataItems.EQUIPMENT
    | DataItems.XP_TABLE
    | DataItems.STAT_PROGRESSION
    | DataItems.STAT_MOD_SET
    | DataItems.RELIC_TIER_DEFINITION
    | DataItems.UNITS
)


class GameDataBuilderAsync(GameDataBuilderBase):
    """Build StatCalc game data from a running Comlink service (async).

    Args:
        client: An active ``SwgohComlinkAsync`` instance used to fetch raw
            game data.

    Example::

        from swgoh_comlink import SwgohComlinkAsync, StatCalcAsync
        from swgoh_comlink.StatCalc.data_builder import GameDataBuilderAsync

        async with SwgohComlinkAsync() as comlink:
            game_data = await GameDataBuilderAsync(comlink).build()
            calc = StatCalcAsync(game_data=game_data)
    """

    def __init__(self, client: SwgohComlinkAsync) -> None:
        self._client = client

    async def build(self) -> dict[str, Any]:
        """Fetch game data from Comlink and transform it.

        Returns:
            Dict suitable for ``StatCalcAsync(game_data=...)`` or
            ``StatCalc.set_game_data()``.
        """
        logger.info("Fetching game data from Comlink (items=%d)", _REQUIRED_ITEMS)
        raw = await self._client.get_game_data(
            # Use int() to ensure a plain numeric string regardless of
            # Python version (IntFlag.__str__ changed in 3.11).
            items=str(int(_REQUIRED_ITEMS)),
            include_pve_units=False,
        )
        return self._build_game_data(raw)
