# coding=utf-8
"""
Asynchronous Python 3 interface for swgoh-comlink.
"""

from __future__ import annotations

from json import loads
from typing import Any

import httpx

from ._base import (
    DEFAULT_TIMEOUT,
    GAME_DATA_TIMEOUT,
    SwgohComlinkBase,
    param_alias,
)
from .exceptions import SwgohComlinkException
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        connection_limits = httpx.Limits(keepalive_expiry=None)
        self.client = httpx.AsyncClient(
            base_url=self.url_base,
            headers={"Content-Type": "application/json"},
            verify=self.verify_ssl,
            timeout=DEFAULT_TIMEOUT,
            limits=connection_limits,
        )
        self.stats_client = httpx.AsyncClient(
            base_url=self.stats_url_base,
            headers={"Content-Type": "application/json"},
            verify=self.verify_ssl,
            timeout=DEFAULT_TIMEOUT,
            limits=connection_limits,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()
        return False

    async def aclose(self) -> None:
        """Close the underlying async HTTP client connections."""
        await self.client.aclose()
        await self.stats_client.aclose()

    async def _request(
        self,
        method: str = "POST",
        endpoint: str = "",
        payload: dict | list | None = None,
        stats: bool = False,
        timeout: float | None = None,
    ) -> dict | list:
        """Send an async HTTP request to the comlink service.

        This is the single gateway for all HTTP communication.

        Args:
            method: HTTP method (``"GET"`` or ``"POST"``).
            endpoint: API endpoint path.
            payload: JSON body for the request (ignored for GET requests).
            stats: If True, use the stats service client.
            timeout: Per-request timeout override.

        Returns:
            Decoded JSON response (dict or list).

        Raises:
            SwgohComlinkException: On any network or decoding error.
        """
        req_headers = self._construct_request_headers(method, endpoint, payload)
        client = self.stats_client if stats else self.client

        request_kwargs: dict[str, Any] = {"headers": req_headers}
        if timeout is not None:
            request_kwargs["timeout"] = timeout
        if method.upper() != "GET":
            request_kwargs["json"] = payload

        try:
            r = await client.request(method.upper(), f"/{endpoint}", **request_kwargs)
            return loads(r.content.decode("utf-8"))
        except httpx.RequestError as e:
            raise SwgohComlinkException(e) from e

    async def _post(
        self,
        endpoint: str = "",
        payload: dict | list | None = None,
        stats: bool = False,
        timeout: float | None = None,
    ) -> dict | list:
        """Send an async POST request to the comlink service.

        Convenience wrapper around :meth:`_request`.
        """
        return await self._request(method="POST", endpoint=endpoint, payload=payload, stats=stats, timeout=timeout)

    async def _get_game_version(self) -> str:
        md = await self.get_game_metadata()
        return md["latestGamedataVersion"]

    # ── Public API methods ───────────────────────────────────────────────

    async def get_unit_stats(
        self, request_payload: dict | list, flags: list[str] | None = None, language: str | None = None
    ) -> list | dict:
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

    async def get_enums(self) -> dict:
        """
        Get an object containing the game data enums.

        Unlike most endpoints, ``/enums`` uses a GET request.

        Returns:
            A dictionary containing the game data enums.
        """
        return await self._request(method="GET", endpoint="enums")

    # alias for non PEP usage of direct endpoint calls
    getEnums = get_enums

    async def get_events(self, enums: bool = False) -> dict[str, list]:
        """
        Get an object containing the events game data.

        Args:
            enums: Boolean flag to indicate whether enum value should be converted in response. [Default is False]

        Returns:
            A single element dictionary containing a list of the events game data.
        """
        payload = {"payload": {}, "enums": enums}
        return await self._post(endpoint="getEvents", payload=payload)

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
    ) -> dict:
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
        return await self._post(endpoint="data", payload=payload, timeout=GAME_DATA_TIMEOUT)

    # alias for non PEP usage of direct endpoint calls
    getGameData = get_game_data

    async def get_localization(
        self, localization_id: str | None = None, locale: str | None = None, unzip: bool = False, enums: bool = False
    ) -> dict:
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
            localization_id = localization_id + ":" + locale.upper()

        payload = {"unzip": unzip, "enums": enums, "payload": {"id": localization_id}}
        return await self._post(endpoint="localization", payload=payload)

    # aliases for non PEP usage of direct endpoint calls
    getLocalization = get_localization
    getLocalizationBundle = get_localization
    get_localization_bundle = get_localization

    async def get_game_metadata(self, client_specs: dict | None = None, enums: bool = False) -> dict:
        """
        Get the game metadata. Game metadata contains the current game and localization versions.

        Args:
            client_specs: Optional dictionary containing client specifications.
            enums: Boolean signifying whether enums in response should be translated to text. [Default: False]

        Returns:
            A dictionary containing the game metadata.
        """
        if client_specs:
            payload = {"payload": {"client_specs": client_specs}, "enums": enums}
        else:
            payload = {}
        return await self._post(endpoint="metadata", payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGameMetaData = get_game_metadata
    getMetaData = get_game_metadata
    get_metadata = get_game_metadata

    async def get_player(self, allycode: str | int | None = None, player_id: str | None = None, enums: bool = False) -> dict:
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
        return await self._post(endpoint="player", payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getPlayer = get_player

    @param_alias(param="player_details_only", alias="playerDetailsOnly")
    async def get_player_arena(
        self, allycode: str | int | None = None, player_id: str | None = None, player_details_only: bool = False, enums: bool = False
    ) -> dict:
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
        return await self._post(endpoint="playerArena", payload=payload)

    # alias to allow for get_arena() calls as a shortcut for get_player_arena() and non PEP variations
    get_arena = get_player_arena
    get_player_arena_profile = get_player_arena
    getPlayerArena = get_player_arena
    getPlayerArenaProfile = get_player_arena

    @param_alias(param="include_recent_guild_activity_info", alias="includeRecent")
    async def get_guild(self, guild_id: str, include_recent_guild_activity_info: bool = False, enums: bool = False) -> dict:
        """
        Get guild information for a specific Guild ID.

        Args:
            guild_id: String ID of guild to retrieve.
            include_recent_guild_activity_info: boolean [Default: False]
            enums: Should enums in response be translated to text. [Default: False]

        Returns:
            A dictionary containing the guild information.
        """
        payload = {
            "payload": {"guildId": guild_id, "includeRecentGuildActivityInfo": include_recent_guild_activity_info},
            "enums": enums,
        }
        guild = await self._post(endpoint="guild", payload=payload)
        if "guild" in guild.keys():
            guild = guild["guild"]
        return guild

    # alias for non PEP usage of direct endpoint calls
    getGuild = get_guild

    async def get_guilds_by_name(self, name: str, start_index: int = 0, count: int = 10, enums: bool = False) -> dict:
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
        return await self._post(endpoint="getGuilds", payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGuildByName = get_guilds_by_name

    async def get_guilds_by_criteria(
        self, search_criteria: dict, start_index: int = 0, count: int = 10, enums: bool = False
    ) -> dict:
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
        return await self._post(endpoint="getGuilds", payload=payload)

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
    ) -> dict:
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
        return await self._post(endpoint="getLeaderboard", payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getLeaderboard = get_leaderboard
    get_gac_leaderboard = get_leaderboard
    getGacLeaderboard = get_leaderboard

    async def get_guild_leaderboard(self, leaderboard_id: list, count: int = 200, enums: bool = False) -> dict:
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
        return await self._post(endpoint="getGuildLeaderboard", payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGuildLeaderboard = get_guild_leaderboard

    async def get_name_spaces(self, only_compatible: bool = False, enums: bool = False) -> dict:
        """Fetches namespaces based on the specified filter criteria."""
        payload = {"payload": {"onlyCompatible": only_compatible}, "enums": enums}
        return await self._post(endpoint="getNameSpaces", payload=payload)

    async def get_segmented_content(
        self, content_name_space: str = "current", accept_language: str = "ENG_US", enums: bool = False
    ) -> dict:
        """Retrieves segmented content from a specified namespace."""
        payload = {
            "payload": {"contentNameSpace": content_name_space, "acceptLanguage": accept_language},
            "enums": enums,
        }
        return await self._post(endpoint="getSegmentedContent", payload=payload)

    # ── Helper methods ───────────────────────────────────────────────────

    async def get_latest_game_data_version(self) -> dict:
        """Get the latest game data and language bundle versions.

        Returns:
            Dictionary with 'game' and 'language' version strings.
        """
        current_metadata = await self.get_metadata()
        return {
            "game": current_metadata["latestGamedataVersion"],
            "language": current_metadata["latestLocalizationBundleVersion"],
        }

    # alias for shorthand call
    getVersion = get_latest_game_data_version
