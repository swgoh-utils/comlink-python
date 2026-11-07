# coding=utf-8
"""
Asynchronous Python 3 interface for swgoh-comlink.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

import httpx

from . import retry as _retry
from ._base import (
    DEFAULT_TIMEOUT,
    GAME_DATA_TIMEOUT,
    SwgohComlinkBase,
    _bounded_error_response,
    _CachedVersions,
    _declared_length,
    _lookup_name,
    _PreparedRequest,
    param_alias,
)
from .exceptions import (
    SwgohComlinkException,
    SwgohComlinkHTTPError,
    SwgohComlinkValueError,
)
from .helpers import Constants, DataItems

__all__ = ["SwgohComlinkAsync"]

logger = logging.getLogger(__name__)


class SwgohComlinkAsync(SwgohComlinkBase):
    """Asynchronous interface for the swgoh-comlink service.

    Instances of this class are used to query the Star Wars Galaxy of Heroes
    game servers for exposed endpoints via the swgoh-comlink proxy library
    running on the same host.

    Args:
        url (str): The URL where swgoh-comlink is running. Defaults to 'http://localhost:3000'
        access_key (str): The HMAC public key. Default to None which indicates HMAC is not used.
        secret_key (str): The HMAC private key. Default to None which indicates HMAC is not used.
        stats_url (str): The url of the swgoh-stats service (if used), such as 'http://localhost:3223'
        host (str): IP address or DNS name of server where the swgoh-comlink service is running
        port (int): TCP port number where the swgoh-comlink service is running. With 'host' it defaults to 3000;
            without 'host' it replaces the port in 'url'. [Default: None]
        stats_port (int): TCP port number of where the comlink-stats service is running. With 'host' it defaults
            to 3223; without 'host' it replaces the port in 'stats_url'. [Default: None]
        verify_ssl (bool): Whether to verify TLS certificates. [Default: True]
        version_cache_ttl (float): Seconds to cache the game/localization versions fetched from
            /metadata. 0 disables caching; ``math.inf`` caches for the client lifetime. [Default: 3600]
        retry (RetryPolicy | None): Keyword-only. Retry rate refusals and HTTP 503 responses, and optionally
            space calls to the same endpoint, as described by a
            :class:`~swgoh_comlink.retry.RetryPolicy`. [Default: None, one attempt per call and no waiting]
        max_response_bytes (int | None): Keyword-only. Largest response body, in decoded bytes, accepted from any
            endpoint except /data. A larger response raises ``SwgohComlinkValueError``; an HTTP error body is cut
            to this size. [Default: None, no limit]
        max_game_data_bytes (int | None): Keyword-only. The same limit for /data (``get_game_data``), whose
            responses are far larger than any other endpoint's. [Default: None, no limit]
        limits (httpx.Limits | None): Keyword-only. Connection pool limits for both underlying httpx clients,
            such as ``httpx.Limits(keepalive_expiry=30)``. Timeouts are not affected.
            [Default: None, the httpx defaults: 100 connections, 20 kept alive, idle ones closed after 5 s]

    Notes:
        If the 'host' parameter is provided, the 'url' and 'stats_url' parameters are ignored.

    Examples:
        Basic usage::

            async with SwgohComlinkAsync() as comlink:
                player = await comlink.get_player(allycode=123456789)
    """

    __comlink_type__ = "SwgohComlinkAsync"
    _log = logger

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._version_lock = asyncio.Lock()
        self._enums_lock = asyncio.Lock()
        self.client = httpx.AsyncClient(
            base_url=self.url_base,
            headers={"Content-Type": "application/json"},
            verify=self.verify_ssl,
            timeout=DEFAULT_TIMEOUT,
            **self._pool_limits,
        )
        self.stats_client = httpx.AsyncClient(
            base_url=self.stats_url_base,
            headers={"Content-Type": "application/json"},
            verify=self.verify_ssl,
            timeout=DEFAULT_TIMEOUT,
            **self._pool_limits,
        )

    async def __aenter__(self) -> SwgohComlinkAsync:
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying async HTTP client connections."""
        await self.client.aclose()
        await self.stats_client.aclose()

    async def _request(
        self,
        method: str = "POST",
        endpoint: str = "",
        payload: dict[str, Any] | list[Any] | None = None,
        stats: bool = False,
        timeout: float | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Send an async HTTP request to the comlink service: the single gateway for all HTTP communication.

        Each attempt waits for admission (pacing and rate holds), is sent, and on an HTTP error asks the
        shared retry core in ``_base`` whether to try again, so both clients retry identically.

        Raises:
            SwgohComlinkHTTPError: When the service answers with an HTTP error status, after any retries
                allowed by the client's retry policy. Subclasses identify rate refusals, HTTP 503 and 4xx.
            SwgohComlinkException: On any network or decoding error.
        """
        attempt, extra = 1, 0.0
        while True:
            await self._admit(endpoint, stats, extra)
            try:
                return await self._send(method, endpoint, payload, stats, timeout)
            except SwgohComlinkHTTPError as exc:
                extra = self._retry_wait(exc, attempt, endpoint, stats)
                if extra is None:
                    raise
                attempt += 1

    async def _admit(self, endpoint: str, stats: bool, extra: float) -> None:
        """Sleep until *endpoint* admits the next attempt.

        Any exception raised while sleeping (a ``KeyboardInterrupt`` or, in the async client, a cancelled task)
        gives the reserved slot back before it propagates, so an interrupted caller never leaves a gap that
        later callers wait out.
        """
        admission = self._admission(endpoint, stats, extra)
        while (wait := admission.next_wait()) is not None:
            try:
                await _retry._async_sleep(wait)
            except BaseException:
                admission.abandon()
                raise

    async def _send(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | list[Any] | None,
        stats: bool,
        timeout: float | None,
    ) -> dict[str, Any] | list[Any]:
        """Make one attempt at a request. Headers, including the HMAC signature, are rebuilt per attempt."""
        request = self._prepare_request(method, endpoint, payload, stats, timeout)
        client = self.stats_client if request.stats else self.client
        try:
            if request.limit is None:
                response = await client.request(request.method, request.url, **request.kwargs)
                content = response.content
            else:
                response, content = await self._receive_limited(client, request, endpoint, request.limit)
        except httpx.RequestError as e:
            raise SwgohComlinkException(e) from e
        return self._interpret_response(response, content)

    async def _receive_limited(
        self, client: httpx.AsyncClient, request: _PreparedRequest, endpoint: str, limit: int
    ) -> tuple[httpx.Response, bytes]:
        """Stream one response, reading at most *limit* decoded bytes of its body; return it and the body.

        A success larger than *limit* raises ``SwgohComlinkValueError``, before any of the body is read when
        ``Content-Length`` already exceeds it. An error response comes back as a copy whose body is cut to
        *limit* bytes.
        """
        async with client.stream(request.method, request.url, **request.kwargs) as r:
            if r.is_success and (declared := _declared_length(r.headers)) is not None and declared > limit:
                raise self._too_large(endpoint, request.limit_name, limit, declared)
            chunks: list[bytes] = []
            size = 0
            async for chunk in r.aiter_bytes():
                chunks.append(chunk)
                size += len(chunk)
                if size > limit:
                    if r.is_success:
                        raise self._too_large(endpoint, request.limit_name, limit)
                    break
            body = b"".join(chunks)
            if not r.is_success:
                error = _bounded_error_response(r, body[:limit])
                return error, error.content
            return r, body

    async def _post(
        self,
        endpoint: str = "",
        payload: dict[str, Any] | list[Any] | None = None,
        stats: bool = False,
        timeout: float | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Send an async POST request to the comlink service.

        Convenience wrapper around :meth:`_request`.
        """
        return await self._request(method="POST", endpoint=endpoint, payload=payload, stats=stats, timeout=timeout)

    async def _get_versions(self, refresh: bool = False) -> _CachedVersions:
        """Return the current game/localization versions, served from the instance cache.

        Args:
            refresh: When True, bypass the cache and fetch fresh values from /metadata.
        """
        if not refresh:
            cached = self._cached_versions()
            if cached is not None:
                return cached
        async with self._version_lock:
            # Double-check inside the lock so concurrent cold-cache callers
            # coalesce into a single /metadata request.
            if not refresh:
                cached = self._cached_versions()
                if cached is not None:
                    return cached
            metadata = await self.get_game_metadata()
            return self._store_versions(*self._versions_from_metadata(metadata))

    async def _get_game_version(self) -> str:
        return (await self._get_versions()).require_game()

    # ── Public API methods ───────────────────────────────────────────────

    async def get_unit_stats(
        self, request_payload: dict[str, Any] | list[Any], flags: list[str] | None = None, language: str | None = None
    ) -> list[Any] | dict[str, Any]:
        """
        Calculate unit stats using the swgoh-stats service interface to swgoh-comlink.

        Args:
            request_payload: Dictionary or list of dictionaries containing units for which to calculate stats.
            flags: List of strings specifying which flags to include in the request URI.
            language: String indicating the desired localized language. Default "eng_us".

        Returns:
            Input object with the calculated stats for the specified units included.
        """
        endpoint_string = self._build_unit_stats_endpoint(flags, language)
        if isinstance(request_payload, dict):
            request_payload = [request_payload]
        return await self._post(endpoint=endpoint_string, payload=request_payload, stats=True)

    async def get_enums(self, refresh: bool = False) -> dict[str, Any]:
        """
        Get an object containing the game data enums.

        Unlike most endpoints, ``/enums`` uses a GET request.

        The response is cached on the instance as ``enums``, with the game data version it was fetched
        under as ``enums_version``. Later calls return the cached response while the game data version is
        unchanged and fetch it again once it changes. The version is read through the instance version
        cache (see ``version_cache_ttl``), so a check usually makes no request. When the version cannot be
        determined, the enums are fetched and returned without being cached.

        Args:
            refresh: When True, fetch the game data version and the enums again even if they are cached.

        Returns:
            A dictionary containing the game data enums. A cached response is the same object as ``enums``:
            copy it before changing it.
        """
        async with self._enums_lock:
            try:
                version = (await self._get_versions(refresh=refresh)).require_game()
            except SwgohComlinkException:
                return cast(dict[str, Any], await self._request(method="GET", endpoint="enums"))
            if not refresh and self.enums is not None and self.enums_version == version:
                return self.enums
            enums = cast(dict[str, Any], await self._request(method="GET", endpoint="enums"))
            self.enums, self.enums_version = enums, version
            return enums

    # alias for non PEP usage of direct endpoint calls
    getEnums = get_enums

    async def get_events(self, enums: bool = False) -> dict[str, list[Any]]:
        """
        Get an object containing the events game data.

        Args:
            enums: Boolean flag to indicate whether enum value should be converted in response. [Default is False]

        Returns:
            A single element dictionary containing a list of the events game data.
        """
        payload = {"payload": {}, "enums": enums}
        return cast(dict[str, list[Any]], await self._post(endpoint="getEvents", payload=payload))

    # alias for non PEP usage of direct endpoint calls
    getEvents = get_events

    async def get_game_data(
        self,
        version: str = "",
        include_pve_units: bool = True,
        request_segment: int = 0,
        enums: bool = False,
        items: str | DataItems | int | None = None,
        device_platform: str = "Android",
    ) -> dict[str, Any]:
        """
        Get game data.

        Args:
            version: string (found in metadata key value 'latestGamedataVersion')
            include_pve_units: boolean [Defaults to True]
            request_segment: integer >=0 [Defaults to 0]
            enums: boolean [Defaults to False]
            items: string [Defaults to None] bitwise value indicating the collections to retrieve from game.
                NOTE: this parameter is mutually exclusive with request_segment.
            device_platform: string [Defaults to "Android"]

        Returns:
            A dictionary containing the game data.
        """
        if version == "":
            game_version = await self._get_game_version()
        else:
            game_version = version

        payload = self._build_game_data_payload(
            game_version=game_version,
            include_pve_units=include_pve_units,
            request_segment=request_segment,
            enums=enums,
            items=items,
            device_platform=device_platform,
        )
        return cast(dict[str, Any], await self._post(endpoint="data", payload=payload, timeout=GAME_DATA_TIMEOUT))

    # alias for non PEP usage of direct endpoint calls
    getGameData = get_game_data

    async def get_localization(
        self, localization_id: str | None = None, locale: str | None = None, unzip: bool = False, enums: bool = False
    ) -> dict[str, Any]:
        """
        Get localization data from game.

        Args:
            localization_id: latestLocalizationBundleVersion found in game metadata.
            locale: string Specify only a specific locale to retrieve [for example "ENG_US"]
            unzip: boolean [Defaults to False]
            enums: boolean [Defaults to False]

        Returns:
            A dictionary containing the localization data.
        """
        if not localization_id:
            localization_id = (await self._get_versions()).require_language()

        if locale:
            localization_id = localization_id + ":" + locale.upper()

        payload = {"unzip": unzip, "enums": enums, "payload": {"id": localization_id}}
        return cast(dict[str, Any], await self._post(endpoint="localization", payload=payload))

    # aliases for non PEP usage of direct endpoint calls
    getLocalization = get_localization
    getLocalizationBundle = get_localization
    get_localization_bundle = get_localization

    async def get_game_metadata(
        self, client_specs: dict[str, Any] | None = None, enums: bool = False
    ) -> dict[str, Any]:
        """
        Get the game metadata. Game metadata contains the current game and localization versions.

        Args:
            client_specs: Optional dictionary containing client specifications.
            enums: Boolean signifying whether enums in response should be translated to text. [Default: False]

        Returns:
            A dictionary containing the game metadata.
        """
        if client_specs:
            payload: dict[str, Any] = {"payload": {"clientSpecs": client_specs}, "enums": enums}
        else:
            payload = {}
        metadata = cast(dict[str, Any], await self._post(endpoint="metadata", payload=payload))
        # Opportunistically refresh the version cache; enums=True responses are
        # skipped since their values may be translated.
        if not enums and isinstance(metadata, dict):
            game, language = self._versions_from_metadata(metadata)
            if game is not None and language is not None:
                self._store_versions(game, language)
        return metadata

    # alias for non PEP usage of direct endpoint calls
    getGameMetaData = get_game_metadata
    getMetaData = get_game_metadata
    get_metadata = get_game_metadata

    async def get_player(
        self, allycode: str | int | None = None, player_id: str | None = None, enums: bool = False
    ) -> dict[str, Any]:
        """
        Get player information from game. Either allycode or player_id must be provided.

        Args:
            allycode: integer or string representing player allycode
            player_id: string representing player game ID
            enums: boolean [Defaults to False]

        Returns:
            A dictionary containing the player information.
        """
        payload = self._get_player_payload(allycode=allycode, player_id=player_id, enums=enums)
        return cast(dict[str, Any], await self._post(endpoint="player", payload=payload))

    # alias for non PEP usage of direct endpoint calls
    getPlayer = get_player

    @param_alias(param="player_details_only", alias="playerDetailsOnly")
    async def get_player_arena(
        self,
        allycode: str | int | None = None,
        player_id: str | None = None,
        player_details_only: bool = False,
        enums: bool = False,
    ) -> dict[str, Any]:
        """
        Get player arena information from game. Either allycode or player_id must be provided.

        Args:
            allycode: integer or string representing player allycode
            player_id: string representing player game ID
            player_details_only: filter results to only player details [Defaults to False]
            enums: boolean [Defaults to False]

        Returns:
            A dictionary containing the player arena information.
        """
        payload = self._get_player_payload(allycode=allycode, player_id=player_id, enums=enums)
        payload["payload"]["playerDetailsOnly"] = player_details_only
        return cast(dict[str, Any], await self._post(endpoint="playerArena", payload=payload))

    # alias to allow for get_arena() calls as a shortcut for get_player_arena() and non PEP variations
    get_arena = get_player_arena
    get_player_arena_profile = get_player_arena
    getPlayerArena = get_player_arena
    getPlayerArenaProfile = get_player_arena

    @param_alias(param="include_recent_guild_activity_info", alias="includeRecent")
    async def get_guild(
        self, guild_id: str, include_recent_guild_activity_info: bool = False, enums: bool = False
    ) -> dict[str, Any]:
        """
        Get guild information for a specific Guild ID.

        Args:
            guild_id: String ID of guild to retrieve.
            include_recent_guild_activity_info: boolean [Default: False]
            enums: Should enums in response be translated to text. [Default: False]

        Returns:
            A dictionary containing the guild information.
        """
        if not guild_id:
            raise SwgohComlinkValueError("guild_id must not be empty.")
        payload = {
            "payload": {"guildId": guild_id, "includeRecentGuildActivityInfo": include_recent_guild_activity_info},
            "enums": enums,
        }
        guild: dict[str, Any] = cast(dict[str, Any], await self._post(endpoint="guild", payload=payload))
        if "guild" in guild.keys():
            guild = guild["guild"]
        return guild

    # alias for non PEP usage of direct endpoint calls
    getGuild = get_guild

    async def get_guilds_by_name(
        self, name: str, start_index: int = 0, count: int = 10, enums: bool = False
    ) -> dict[str, Any]:
        """
        Search for guild by name and return match.

        Args:
            name: string for guild name search
            start_index: integer for where in the result list to begin
            count: integer for max matches to return [Default: 10]
            enums: Whether to translate enums in response to text [Default: False]

        Returns:
            A dictionary containing the guild search results.
        """
        payload = {
            "payload": {"name": name, "filterType": 4, "startIndex": start_index, "count": count},
            "enums": enums,
        }
        return cast(dict[str, Any], await self._post(endpoint="getGuilds", payload=payload))

    # alias for non PEP usage of direct endpoint calls
    getGuildByName = get_guilds_by_name

    async def get_guilds_by_criteria(
        self, search_criteria: dict[str, Any], start_index: int = 0, count: int = 10, enums: bool = False
    ) -> dict[str, Any]:
        """
        Search for guild by guild criteria and return matches.

        Args:
            search_criteria: Dictionary of search criteria
            start_index: integer for where in the result list to begin
            count: integer for max matches to return
            enums: Whether to translate enum values to text [Default: False]

        Returns:
            A dictionary containing the guild search results.
        """
        payload = {
            "payload": {"searchCriteria": search_criteria, "filterType": 5, "startIndex": start_index, "count": count},
            "enums": enums,
        }
        return cast(dict[str, Any], await self._post(endpoint="getGuilds", payload=payload))

    # alias for non PEP usage of direct endpoint calls
    getGuildByCriteria = get_guilds_by_criteria

    async def get_leaderboard(
        self,
        leaderboard_type: int,
        *,
        league: int | str | None = None,
        division: int | str | None = None,
        event_instance_id: str | None = None,
        group_id: str | None = None,
        enums: bool = False,
    ) -> dict[str, Any]:
        """
        Retrieve Grand Arena Championship leaderboard information.

        Args:
            leaderboard_type: Type 4 for GAC brackets, Type 6 for global leaderboards.
            league: Enum value or string name for league.
            division: Enum value or string name for division.
            event_instance_id: Event+instance ID (for type 4).
            group_id: Group ID (for type 4).
            enums: Whether to translate enum values to text [Default: False]

        Returns:
            A dictionary containing the leaderboard data.
        """
        leagues = Constants.LEAGUES
        divisions = Constants.DIVISIONS
        if isinstance(league, str):
            league = _lookup_name("league", leagues, league)
        if isinstance(division, int) and len(str(division)) == 1:
            division = _lookup_name("division", divisions, str(division))
        if isinstance(division, str):
            division = _lookup_name("division", divisions, division)
        inner_payload: dict[str, Any] = {"leaderboardType": leaderboard_type}
        payload: dict[str, Any] = {"payload": inner_payload, "enums": enums}
        if leaderboard_type == 4:
            inner_payload["eventInstanceId"] = event_instance_id
            inner_payload["groupId"] = group_id
        elif leaderboard_type == 6:
            inner_payload["league"] = league
            inner_payload["division"] = division
        return cast(dict[str, Any], await self._post(endpoint="getLeaderboard", payload=payload))

    # alias for non PEP usage of direct endpoint calls
    getLeaderboard = get_leaderboard
    get_gac_leaderboard = get_leaderboard
    getGacLeaderboard = get_leaderboard

    async def get_guild_leaderboard(
        self, leaderboard_id: list[dict[str, Any]], count: int = 200, enums: bool = False
    ) -> dict[str, Any]:
        """
        Fetches the guild leaderboard data for given leaderboard ID.

        Parameters:
            leaderboard_id: A list containing one leaderboard ID dictionary.
            count: The number of leaderboard entries to retrieve. [Default: 200]
            enums: Whether or not to translate enum values. [Default: False]

        Returns:
            A dictionary containing the guild leaderboard data.
        """
        payload = dict(payload={"leaderboardId": leaderboard_id, "count": count}, enums=enums)
        return cast(dict[str, Any], await self._post(endpoint="getGuildLeaderboard", payload=payload))

    # alias for non PEP usage of direct endpoint calls
    getGuildLeaderboard = get_guild_leaderboard

    async def get_name_spaces(self, only_compatible: bool = False, enums: bool = False) -> dict[str, Any]:
        """Fetches namespaces based on the specified filter criteria."""
        payload = {"payload": {"onlyCompatible": only_compatible}, "enums": enums}
        return cast(dict[str, Any], await self._post(endpoint="getNameSpaces", payload=payload))

    async def get_segmented_content(
        self, content_name_space: str = "current", accept_language: str = "ENG_US", enums: bool = False
    ) -> dict[str, Any]:
        """Retrieves segmented content from a specified namespace."""
        payload = {
            "payload": {"contentNameSpace": content_name_space, "acceptLanguage": accept_language},
            "enums": enums,
        }
        return cast(dict[str, Any], await self._post(endpoint="getSegmentedContent", payload=payload))

    # ── Helper methods ───────────────────────────────────────────────────

    async def get_latest_game_data_version(self, refresh: bool = False) -> dict[str, Any]:
        """Get the latest game data and language bundle versions.

        Results are served from the instance version cache (see ``version_cache_ttl``).

        Args:
            refresh: When True, bypass the cache and fetch fresh values from /metadata.

        Returns:
            Dictionary with 'game' and 'language' version strings.
        """
        versions = await self._get_versions(refresh=refresh)
        return {"game": versions.require_game(), "language": versions.require_language()}

    # alias for shorthand call
    getVersion = get_latest_game_data_version
