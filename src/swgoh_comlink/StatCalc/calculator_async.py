from __future__ import annotations

import logging
from typing import Any

import httpx

from ..exceptions import SwgohComlinkValueError
from .calculator import _GAMEDATA_TIMEOUT, StatCalc, _check_fetch_options, _GameDataDownload


class StatCalcAsync(StatCalc):
    """Async-capable SWGOH stat calculator.

    Inherits all computation methods from :class:`StatCalc`. The only
    difference is how game data is fetched during initialization: this
    class uses ``httpx.AsyncClient`` instead of the blocking
    ``httpx.Client``. Both apply the same size cap and SHA-256 check.

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
