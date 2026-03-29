from __future__ import annotations

import logging
from typing import Any

import httpx

from .calculator import StatCalc


class StatCalcAsync(StatCalc):
    """Async-capable SWGOH stat calculator.

    Inherits all computation methods from :class:`StatCalc`. The only
    difference is how game data is fetched during initialization: this
    class uses ``httpx.AsyncClient`` instead of blocking
    ``urllib.request``.

    Because ``__init__`` cannot be ``async``, use the :meth:`create`
    classmethod factory when game data needs to be fetched from GitHub:

    .. code-block:: python

        calc = await StatCalcAsync.create()

    If you already have game data loaded, pass it directly:

    .. code-block:: python

        calc = StatCalcAsync(game_data=my_data)

    Args:
        game_data: Game data payload. **Required** — use :meth:`create`
            for automatic async fetching.
    """

    _LOGGER = logging.getLogger(__name__)

    def __init__(self, game_data: dict[str, Any]) -> None:
        """Initialize with pre-loaded game data.

        Unlike the sync :class:`StatCalc`, this constructor does **not**
        auto-fetch from GitHub.  Use :meth:`create` for that.

        Args:
            game_data: Game data payload containing unit, gear, CR, GP,
                relic, and mod set tables.
        """
        super().__init__(game_data=game_data)

    @classmethod
    async def create(cls, game_data: dict[str, Any] | None = None) -> StatCalcAsync:
        """Factory method to create a :class:`StatCalcAsync` instance.

        If *game_data* is ``None``, the latest payload is fetched
        asynchronously from the swgoh-utils GitHub repository.

        Args:
            game_data: Optional pre-loaded game data payload.

        Returns:
            A fully initialized :class:`StatCalcAsync` instance.
        """
        if game_data is None:
            cls._LOGGER.info("No game data provided, loading from GitHub (async)")
            game_data = await cls._async_fetch_game_data_from_github()
        else:
            cls._LOGGER.debug("Using caller-provided game data")
        return cls(game_data=game_data)

    @classmethod
    async def _async_fetch_game_data_from_github(cls) -> dict[str, Any]:
        """Fetch game data from GitHub asynchronously using httpx."""
        try:
            cls._LOGGER.info("Fetching game data from %s", cls._DEFAULT_GAMEDATA_URL)
            async with httpx.AsyncClient() as client:
                response = await client.get(cls._DEFAULT_GAMEDATA_URL, timeout=30)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            cls._LOGGER.exception("Failed to fetch game data from GitHub")
            raise RuntimeError(f"Unable to retrieve game data from {cls._DEFAULT_GAMEDATA_URL}") from exc

        return cls._normalize_game_data_payload(payload)
