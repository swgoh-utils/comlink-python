from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from ..exceptions import SwgohComlinkValueError
from .calculator import _GAMEDATA_TIMEOUT, StatCalc, _check_fetch_options, _GameDataDownload


class StatCalcAsync(StatCalc):
    """Async-capable SWGOH stat calculator.

    Game data is fetched with ``httpx.AsyncClient`` instead of the blocking
    ``httpx.Client``. Both apply the same size cap and SHA-256 check.

    Stat calculation is CPU-bound: a full roster takes tens of milliseconds.
    Use the ``acalc_*`` methods (:meth:`acalc_char_stats`,
    :meth:`acalc_ship_stats`, :meth:`acalc_roster_stats`,
    :meth:`acalc_player_stats`) from async code; they run the matching
    ``calc_*`` method in a worker thread via :func:`asyncio.to_thread`, so the
    event loop keeps running. The inherited synchronous ``calc_*`` methods
    still work but block the loop while they run.

    The game data tables are only read during calculation, so concurrent
    ``acalc_*`` calls on one instance are safe. Do not call
    :meth:`set_game_data` while a calculation is running. Each call updates its
    input in place from the worker thread: do not read or change that input
    until the call returns. Cancelling the awaiting task does not stop the
    thread, which still finishes updating the input.

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
    async def create(
        cls,
        game_data: dict[str, Any] | None = None,
        *,
        game_data_url: str | None = None,
        expected_sha256: str | None = None,
    ) -> StatCalcAsync:
        """Factory method to create a :class:`StatCalcAsync` instance.

        If *game_data* is ``None``, the latest payload is fetched
        asynchronously from the swgoh-utils GitHub repository.

        Args:
            game_data: Optional pre-loaded game data payload.
            game_data_url: URL to fetch the game data from when *game_data* is
                omitted. Defaults to the latest ``main`` of swgoh-utils/gamedata.
            expected_sha256: Hex SHA-256 digest the fetched body must match.

        Returns:
            A fully initialized :class:`StatCalcAsync` instance.

        Raises:
            SwgohComlinkValueError: *expected_sha256* is malformed, a fetch option
                is combined with *game_data*, the fetched body is larger than
                64 MiB, or its digest does not match *expected_sha256*.
            RuntimeError: The game data could not be fetched or parsed.
        """
        expected_sha256 = _check_fetch_options(game_data, game_data_url, expected_sha256)
        if game_data is None:
            cls._LOGGER.info("No game data provided, loading from GitHub (async)")
            game_data = await cls._async_fetch_game_data_from_github(game_data_url, expected_sha256)
        else:
            cls._LOGGER.debug("Using caller-provided game data")
        return cls(game_data=game_data)

    async def acalc_char_stats(self, unit: dict[str, Any], datacron: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run :meth:`calc_char_stats` in a worker thread.

        Args:
            unit: Character object in either normalized (`defId`) or raw game
                format (`definitionId`).
            datacron: Optional datacron object to apply, as in :meth:`calc_char_stats`.

        Returns:
            The input unit with `stats` and `gp` keys added.
        """
        return await asyncio.to_thread(self.calc_char_stats, unit, datacron)

    async def acalc_ship_stats(self, unit: dict[str, Any], crew_member: list[dict[str, Any]]) -> dict[str, Any]:
        """Run :meth:`calc_ship_stats` in a worker thread.

        Args:
            unit: Ship object in either normalized (`defId`) or raw game format.
            crew_member: Crew member list for the ship.

        Returns:
            The input unit with `stats` and `gp` keys added.
        """
        return await asyncio.to_thread(self.calc_ship_stats, unit, crew_member)

    async def acalc_roster_stats(self, units: Any, datacron: dict[str, Any] | None = None) -> Any:
        """Run :meth:`calc_roster_stats` in a worker thread.

        Args:
            units: Either a list of units or a legacy dict keyed by unit id.
            datacron: Optional datacron object to apply to every character, as
                in :meth:`calc_roster_stats`.

        Returns:
            Input object with `stats` and `gp` fields added for each unit.
        """
        return await asyncio.to_thread(self.calc_roster_stats, units, datacron)

    async def acalc_player_stats(
        self, players: dict[str, Any] | list[dict[str, Any]], datacron_id: str | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Run :meth:`calc_player_stats` in a worker thread.

        Args:
            players: One player object, or a list of player objects, each with a `rosterUnit` element.
            datacron_id: Optional id of a datacron in each player's own
                `datacron` collection, as in :meth:`calc_player_stats`.

        Returns:
            The input object with `stats` and `gp` fields added for each player's roster.

        Raises:
            RuntimeError: If a dict player is missing a 'rosterUnit' key.
            TypeError: If the input object is not a list or dict.
            KeyError: If `datacron_id` is given and a player has no `datacron`
                collection or does not own that datacron.
        """
        return await asyncio.to_thread(self.calc_player_stats, players, datacron_id)

    @classmethod
    async def _async_fetch_game_data_from_github(
        cls, url: str | None = None, expected_sha256: str | None = None
    ) -> dict[str, Any]:
        """Fetch game data from GitHub asynchronously using httpx."""
        url = cls._DEFAULT_GAMEDATA_URL if url is None else url
        download = _GameDataDownload(url, expected_sha256)
        try:
            cls._LOGGER.info("Fetching game data from %s", url)
            async with (
                httpx.AsyncClient(follow_redirects=True, timeout=_GAMEDATA_TIMEOUT) as client,
                client.stream("GET", url) as response,
            ):
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    download.feed(chunk)
            payload = download.parse()
        except SwgohComlinkValueError:
            raise
        except Exception as exc:
            cls._LOGGER.exception("Failed to fetch game data from %s", url)
            raise RuntimeError(f"Unable to retrieve game data from {url}") from exc

        return cls._normalize_game_data_payload(payload)
