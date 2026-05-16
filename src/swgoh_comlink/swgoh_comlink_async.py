# coding=utf-8
"""
Asynchronous Python 3 interface for swgoh-comlink.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import httpx

from ._base import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    GAME_DATA_TIMEOUT,
    SwgohComlinkBase,
    param_alias,
    resolve_profile,
)
from ._models import (
    LEADERBOARD_DECODER,
    METADATA_DECODER,
    PLAYER_DECODER,
    UNTYPED_DECODER,
    Guild,
    LeaderboardResponse,
    Metadata,
    Player,
    decode_guild,
)
from ._retry import RetryableStatusError, retrying_async
from .exceptions import SwgohComlinkException, SwgohComlinkValueError
from .helpers import Constants

__all__ = ["SwgohComlinkAsync"]


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
        port (int): TCP port number where the swgoh-comlink service is running [Default: 3000]
        stats_port (int): TCP port number of where the comlink-stats service is running [Default: 3223]
        verify_ssl (bool): Whether to verify TLS certificates. [Default: True]

    Notes:
        If the 'host' and 'port' parameters are provided, the 'url' and 'stats_url' parameters are ignored.

    Examples:
        Basic usage::

            async with SwgohComlinkAsync() as comlink:
                player = await comlink.get_player(allycode=123456789)
    """

    __comlink_type__ = "SwgohComlinkAsync"

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient | None = None,
        profile: str = "default",
        max_retries: int = DEFAULT_MAX_RETRIES,
        **kwargs: Any,
    ) -> None:
        """Construct an async client.

        Args:
            http_client: Inject your own :class:`httpx.AsyncClient`. When
                provided, the SDK *does not* auto-close it on
                :meth:`aclose` — you own its lifecycle. When omitted, the
                SDK constructs one per the ``profile`` preset.
            profile: Connection pool preset — ``"default"`` / ``"bot"`` /
                ``"bulk"``. Ignored when ``http_client`` is supplied.
            max_retries: Additional attempts after the first failure for
                transient errors. ``0`` disables retries. Default 3.
            **kwargs: Passed through to :class:`SwgohComlinkBase`.
        """
        super().__init__(**kwargs)
        self.max_retries = max_retries

        if http_client is not None:
            self.client = http_client
            self._owns_client = False
        else:
            self.client = httpx.AsyncClient(
                base_url=self.url_base,
                headers={"Content-Type": "application/json"},
                verify=self.verify_ssl,
                timeout=DEFAULT_TIMEOUT,
                limits=resolve_profile(profile),
            )
            self._owns_client = True
        self.stats_client = httpx.AsyncClient(
            base_url=self.stats_url_base,
            headers={"Content-Type": "application/json"},
            verify=self.verify_ssl,
            timeout=DEFAULT_TIMEOUT,
            limits=resolve_profile(profile),
        )

    async def __aenter__(self) -> SwgohComlinkAsync:
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying async HTTP client connections we own.

        An injected ``http_client`` is NOT closed — the caller owns its
        lifecycle. The internal ``stats_client`` is always closed.
        """
        if getattr(self, "_owns_client", True):
            await self.client.aclose()
        await self.stats_client.aclose()

    async def _request(
        self,
        method: str = "POST",
        endpoint: str = "",
        payload: dict[str, Any] | list[Any] | None = None,
        stats: bool = False,
        timeout: float | None = None,
        *,
        decoder: Callable[[bytes], Any] | None = None,
    ) -> Any:
        """Send an async HTTP request to the comlink service.

        Mirror of :meth:`SwgohComlink._request` — same retry semantics,
        same building blocks (``_build_request_kwargs`` / ``_decode`` /
        ``_classify_response`` / ``_map_error`` from the base) — async send,
        ``asyncio.sleep`` between retries, and the same ``decoder=``
        protocol for typed Struct dispatch.
        """
        method_u = method.upper()
        full_path, request_kwargs = self._build_request_kwargs(method_u, endpoint, payload, timeout)
        client = self.stats_client if stats else self.client

        async def attempt() -> httpx.Response:
            r = await client.request(method_u, full_path, **request_kwargs)
            self._classify_response(r)
            return r

        try:
            response = await retrying_async(
                attempt,
                attempts=self.max_retries + 1,
                on=httpx.RequestError,
            )
        except (httpx.RequestError, RetryableStatusError) as e:
            raise self._map_error(e) from e
        except SwgohComlinkException:
            raise

        decode = decoder if decoder is not None else UNTYPED_DECODER.decode
        try:
            return decode(response.content)
        except Exception as e:  # noqa: BLE001 — msgspec.DecodeError, ValidationError, etc.
            raise SwgohComlinkException(f"failed to decode response body: {e}") from e

    async def _post(
        self,
        endpoint: str = "",
        payload: dict[str, Any] | list[Any] | None = None,
        stats: bool = False,
        timeout: float | None = None,
        *,
        decoder: Callable[[bytes], Any] | None = None,
    ) -> Any:
        """Send an async POST request to the comlink service.

        Convenience wrapper around :meth:`_request`. Forwards ``decoder=``
        so typed-endpoint methods can opt into a specific Struct decoder.
        """
        return await self._request(
            method="POST",
            endpoint=endpoint,
            payload=payload,
            stats=stats,
            timeout=timeout,
            decoder=decoder,
        )

    async def _get_game_version(self) -> str:
        # v3: get_game_metadata returns a Metadata Struct by default (raw=False).
        md = cast(Metadata, await self.get_game_metadata())
        return str(md.latest_gamedata_version)

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
        return cast(
            "list[Any] | dict[str, Any]",
            await self._post(endpoint=endpoint_string, payload=request_payload, stats=True),
        )

    async def get_enums(self) -> dict[str, Any]:
        """
        Get an object containing the game data enums.

        Unlike most endpoints, ``/enums`` uses a GET request.

        Returns:
            A dictionary containing the game data enums.
        """
        return cast(dict[str, Any], await self._request(method="GET", endpoint="enums"))

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
        items: str | None = None,
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
            current_game_version = await self.get_latest_game_data_version()
            localization_id = current_game_version["language"]

        if locale:
            assert localization_id is not None
            localization_id = localization_id + ":" + locale.upper()

        payload = {"unzip": unzip, "enums": enums, "payload": {"id": localization_id}}
        return cast(dict[str, Any], await self._post(endpoint="localization", payload=payload))

    # aliases for non PEP usage of direct endpoint calls
    getLocalization = get_localization
    getLocalizationBundle = get_localization
    get_localization_bundle = get_localization

    async def get_game_metadata(
        self,
        client_specs: dict[str, Any] | None = None,
        enums: bool = False,
        *,
        raw: bool = False,
    ) -> Metadata | dict[str, Any]:
        """
        Get the game metadata. Game metadata contains the current game and localization versions.

        Args:
            client_specs: Optional dictionary containing client specifications.
            enums: Boolean signifying whether enums in response should be translated to text. [Default: False]
            raw: When True, return raw ``dict`` (v2 shape). Default returns :class:`Metadata`.
        """
        if client_specs:
            payload: dict[str, Any] = {"payload": {"client_specs": client_specs}, "enums": enums}
        else:
            payload = {}
        if raw:
            return cast(dict[str, Any], await self._post(endpoint="metadata", payload=payload))
        return cast(Metadata, await self._post(endpoint="metadata", payload=payload, decoder=METADATA_DECODER.decode))

    # alias for non PEP usage of direct endpoint calls
    getGameMetaData = get_game_metadata
    getMetaData = get_game_metadata
    get_metadata = get_game_metadata

    async def get_player(
        self,
        allycode: str | int | None = None,
        player_id: str | None = None,
        enums: bool = False,
        *,
        raw: bool = False,
    ) -> Player | dict[str, Any]:
        """
        Get player information from game. Either allycode or player_id must be provided.

        Args:
            allycode: integer or string representing player allycode
            player_id: string representing player game ID
            enums: boolean [Defaults to False]
            raw: When True, return raw ``dict`` (v2 shape). Default returns :class:`Player`.
        """
        payload = self._get_player_payload(allycode=allycode, player_id=player_id, enums=enums)
        if raw:
            return cast(dict[str, Any], await self._post(endpoint="player", payload=payload))
        return cast(Player, await self._post(endpoint="player", payload=payload, decoder=PLAYER_DECODER.decode))

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
        self,
        guild_id: str,
        include_recent_guild_activity_info: bool = False,
        enums: bool = False,
        *,
        raw: bool = False,
    ) -> Guild | dict[str, Any]:
        """
        Get guild information for a specific Guild ID.

        Args:
            guild_id: String ID of guild to retrieve.
            include_recent_guild_activity_info: boolean [Default: False]
            enums: Should enums in response be translated to text. [Default: False]
            raw: When True, return raw ``dict`` (v2 shape, still unwrapped).
                Default returns :class:`Guild`.
        """
        if not guild_id:
            raise SwgohComlinkValueError("guild_id must not be empty.")
        payload = {
            "payload": {"guildId": guild_id, "includeRecentGuildActivityInfo": include_recent_guild_activity_info},
            "enums": enums,
        }
        if raw:
            guild: dict[str, Any] = cast(dict[str, Any], await self._post(endpoint="guild", payload=payload))
            if "guild" in guild.keys():
                guild = guild["guild"]
            return guild
        return cast(Guild, await self._post(endpoint="guild", payload=payload, decoder=decode_guild))

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
        raw: bool = False,
    ) -> LeaderboardResponse | dict[str, Any]:
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
            league = leagues[league.lower()]
        if isinstance(division, int) and len(str(division)) == 1:
            division = divisions[str(division).lower()]
        if isinstance(division, str):
            division = divisions[division.lower()]
        payload: dict[str, Any] = {
            "payload": {
                "leaderboardType": leaderboard_type,
            },
            "enums": enums,
        }
        if leaderboard_type == 4:
            payload["payload"]["eventInstanceId"] = event_instance_id
            payload["payload"]["groupId"] = group_id
        elif leaderboard_type == 6:
            payload["payload"]["league"] = league
            payload["payload"]["division"] = division
        if raw:
            return cast(dict[str, Any], await self._post(endpoint="getLeaderboard", payload=payload))
        return cast(
            LeaderboardResponse,
            await self._post(endpoint="getLeaderboard", payload=payload, decoder=LEADERBOARD_DECODER.decode),
        )

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

    async def get_latest_game_data_version(self) -> dict[str, Any]:
        """Get the latest game data and language bundle versions.

        Returns:
            Dictionary with 'game' and 'language' version strings.
        """
        # v3: get_game_metadata returns a Metadata Struct by default (raw=False).
        current_metadata = cast(Metadata, await self.get_game_metadata())
        return {
            "game": current_metadata.latest_gamedata_version,
            "language": current_metadata.latest_localization_bundle_version,
        }

    # alias for shorthand call
    getVersion = get_latest_game_data_version
