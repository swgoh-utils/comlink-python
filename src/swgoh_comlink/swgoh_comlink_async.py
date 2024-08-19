# -*- coding: utf-8 -*-
"""Python 3 interface library for swgoh-comlink (https://github.com/swgoh-utils/swgoh-comlink)

This module provides interface methods for the swgoh-comlink service. The swgoh-comlink service
runs either as a standalone executable or in a docker container on a locally controlled server or virtual
machine.

Additional information on the swgoh-comlink service can be also be found on the development team's discord server
located at https://discord.gg/8ATYnUA746

"""

from __future__ import annotations

from typing import Any

import httpx
from sentinels import Sentinel

from swgoh_comlink._base import SwgohComlinkBase
from swgoh_comlink.constants import (
    REQUIRED,
    OPTIONAL,
    MISSING,
    MutualExclusiveRequired,
    MutualRequiredNotSet,
    NotSet,
    param_alias,
    Constants,
)

__all__ = ["SwgohComlinkAsync"]


class SwgohComlinkAsync(SwgohComlinkBase):
    """
    Class definition for swgoh-comlink interface and supported methods.
    Instances of this class are used to query the Star Wars Galaxy of Heroes
    game servers for exposed endpoints via the swgoh-comlink proxy library
    running on the same host.

        Args:
            url (str): The URL where swgoh-comlink is running.
            stats_url (str): The url of the swgoh-stats service (if used), such as 'http://localhost:3223'
            access_key (str): The HMAC public key. Default to None which indicates HMAC is not used.
            secret_key (str): The HMAC private key. Default to None which indicates HMAC is not used.
            protocol (str): The protocol to use for connecting to comlink. Typically, http or https.
            host (str): IP address or DNS name of server where the swgoh-comlink service is running
            port (int): TCP port number between 1024 and 65535 where the swgoh-comlink service is running.
            stats_port (int): TCP port number between 1024 and 65535 where the comlink-stats service is running.
            logger (logging.Logger): A logger instance to use for logging messages if the default logger is
                                    insufficient.
            default_logger_enabled (bool): Flag to enable default logging. Should only be used if testing.

        Note:
            'url' and 'stat_url' are mutually exclusive of the protocol/host/port/stats_port parameters.
                Either of the options should be chosen but not both.

    """

    __module__ = None
    __comlink_type__ = 'SwgohComlinkAsync'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        connection_limit = httpx.Limits(keepalive_expiry=None)
        self.client = httpx.AsyncClient(base_url=self.url_base, verify=False, timeout=self._DEFAULT_CONNECTION_TIMEOUT,
                                        limits=connection_limit)
        self.stats_client = httpx.AsyncClient(base_url=self.stats_url_base, verify=False,
                                              timeout=self._DEFAULT_CONNECTION_TIMEOUT,
                                              limits=connection_limit)
        self.logger.debug(f"Logger for SwgohComlinkAsync is initialized to {self.logger.name}")

    async def _post(self,
                    endpoint: str,
                    payload: dict | list[dict],
                    stats: bool = False,
                    timeout: float | Sentinel = OPTIONAL
                    ) -> Any:
        req_headers = self._construct_request_headers(endpoint, payload)

        timeout = self._DEFAULT_CONNECTION_TIMEOUT if timeout is NotSet else timeout

        connection_limit = httpx.Limits(keepalive_expiry=None)
        self.client = httpx.AsyncClient(base_url=self.url_base, verify=False, timeout=self._DEFAULT_CONNECTION_TIMEOUT,
                                        limits=connection_limit)

        try:
            self.logger.debug(f"Sending POST, {endpoint=} {req_headers=}")
            if stats:
                resp = await self.stats_client.post(
                    f"/{endpoint}", json=payload, headers=req_headers, timeout=timeout
                )
            else:
                resp = await self.client.post(
                    f"/{endpoint}", json=payload, headers=req_headers, timeout=timeout
                )
            self.logger.debug(f"Returning JSON response")
            return resp.json()
        except httpx.RequestError as exc:
            exc_str = str(exc).replace("\n", "-")
            self.logger.exception(f"Exception occurred: {self._get_function_name()}: {exc_str}")
            raise exc
        except RuntimeError as exc:
            exc_str = str(exc).replace("\n", "-")
            self.logger.exception(f"Exception occurred: {self._get_function_name()}: {exc_str}")
            raise exc

    async def get_game_metadata(
            self, client_specs: dict[str, str] | Sentinel = OPTIONAL, enums: bool = False
    ) -> dict:
        """Get the game metadata. Game metadata contains the current game and localization versions.

        Args:
            client_specs:  Optional dictionary containing
            enums: Flag signifying whether enums in response should be translated to text. [Default: False]

        Returns:
            Current game client metadata

        Examples:
            ```python
            client_specs: {
                  "platform": "string",
                  "bundleId": "string",
                  "externalVersion": "string",
                  "internalVersion": "string",
                  "region": "string"
                }
            ```
        """
        return await self._post(
            endpoint="metadata", payload=self._make_client_specs(client_specs, enums), timeout=30.0
        )

    # alias for non PEP usage of direct endpoint calls
    getGameMetaData = get_game_metadata
    getMetaData = get_game_metadata
    get_metadata = get_game_metadata

    async def _get_game_version(self) -> str:
        """Get the current game version"""
        md = await self.get_game_metadata(client_specs={})
        return md["latestGamedataVersion"]

    async def get_enums(self) -> dict:
        """Get an object containing the game data enums

        Raises:
            httpx.RequestError: If the HTTP request encounters an error

        """
        try:
            resp = await self.client.get("/enums")
            return resp.json()
        except httpx.RequestError as exc:
            exc_str = str(exc).replace("\n", "-")
            self.logger.exception(f"Exception occurred: {self._get_function_name()}: {exc_str}")
            raise exc

    # alias for non PEP usage of direct endpoint calls
    getEnums = get_enums

    async def get_events(self, enums: bool = False) -> dict:
        """Get an object containing the events game data

        Args:
            enums: Boolean flag to indicate whether enum value should be converted in response.

        Returns:
            Dictionary containing a single 'gameEvents' which is a list of events as dicts

        Raises:
            requests.Exception: HTTP Request exception

        """
        payload = {"payload": {}, "enums": enums}
        return await self._post(endpoint="getEvents", payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getEvents = get_events

    async def get_game_data(
            self,
            version: str | Sentinel = OPTIONAL,
            include_pve_units: bool = True,
            request_segment: int = 0,
            enums: bool = False,
            items: str | None = None,
            device_platform: str = "Android",
    ) -> dict:
        """Get current game data from servers

        Args:
            version: Game data version (found in metadata key value 'latestGamedataVersion')
            include_pve_units: Flag to indicate whether PVE units should be included in results  [Defaults to True]
            request_segment: Identifier for whether to return all data (segment 0) or partial segments (values 1-4)
            enums: Flag to enable ENUM replace [Defaults to False]
            items: Bitwise value indicating the collection(s) to retrieve from game.
            device_platform: Type of device to emulate. [Unused at this time]


        Returns:
            Current game data

        Raises:
            ValueError: if 'version' is not provided or neither 'items' not 'request_segment' are set
        """

        if version is NotSet:
            game_version = await self._get_game_version()
        else:
            game_version = version

        # TODO: Update 'items' type hint and default
        return await self._post(
            endpoint="data",
            payload=self._make_game_data_payload(
                version=game_version,
                include_pve_units=include_pve_units,
                request_segment=request_segment,
                enums=enums,
                items=items,
                device_platform=device_platform,
            ),
        )

    # alias for non PEP usage of direct endpoint calls
    getGameData = get_game_data

    async def get_localization(
            self,
            id: str | Sentinel = OPTIONAL,
            locale: str | Sentinel = OPTIONAL,
            unzip: bool = False,
            enums: bool = False
    ) -> dict:
        """Get localization data from game

        Args:
            id: latestLocalizationBundleVersion found in game metadata. This method will collect the latest language
                            version if the 'id' argument is not provided.
            locale: String indicating the desired localized language. For example, "eng_us" or "ger_de"
            unzip: Flag to indicate whether the localization bundle should be unzipped. [Default: False]
            enums: Flag to indicate whether ENUMs should be translated. [Default: False]

        Returns:
            Dictionary containing each localization file in a separate element value

        Raises:
            ValueError: If 'locale' is not a supported localized language.
        """

        if isinstance(locale, str):
            if locale not in Constants.LANGUAGES:
                err_str = f"{self._get_function_name()}: Unknown locale {locale}. Please use only supported languages."
                self.logger.error(err_str)
                raise ValueError(err_str)

        if isinstance(id, Sentinel):
            current_game_version = await self.get_latest_game_data_version()
            id = current_game_version["language"]

        if isinstance(locale, str):
            id = id + ":" + locale.upper()

        payload = {"unzip": unzip, "enums": enums, "payload": {"id": id}}
        self.logger.debug(f"{self._get_function_name()}, {payload=}")

        return await self._post(
            endpoint="localization",
            payload=payload,
        )

    # aliases for non PEP usage of direct endpoint calls
    getLocalization = get_localization
    getLocalizationBundle = get_localization
    get_localization_bundle = get_localization

    # Introduced in 1.12.0
    # Use decorator to alias the request_payload parameter to 'units_list' to maintain backward compatibility
    # while fixing the original naming format mistake.
    @param_alias(param="request_payload", alias="units_list")
    async def get_unit_stats(
            self,
            request_payload: dict | list[dict] | Sentinel = REQUIRED,
            flags: list[str] | Sentinel = OPTIONAL,
            language: str = "eng_us",
    ) -> dict | list[dict]:
        """Calculate unit stats using swgoh-stats service interface to swgoh-comlink

        Args:

            request_payload: Single character/ship dictionary or list containing units for which to calculate stats
            flags: Flags to include in the request URI
            language: String indicating the desired localized language.

        Returns:
            The input object with 'stats' element containing the results of the calculations added.

        Raises:
            RuntimeError: if the request payload is not provided or flags is not a list object

        """

        if request_payload is MISSING:
            err_msg = f"{self._get_function_name()}, 'request_payload'' must be provided."
            self.logger.error(err_msg)
            raise ValueError(err_msg)

        # Convert a single character/ship object to a one item list of obj for StatCalc
        if isinstance(request_payload, dict):
            request_payload = [request_payload]

        if flags is not NotSet and not isinstance(flags, list):
            err_msg = f"{self._get_function_name()}, 'flags' must be a list when it is provided. Got {type(flags)}"
            self.logger.error(err_msg)
            raise ValueError(err_msg)

        query_string = self._construct_unit_stats_query_string(flags, language)
        endpoint_string = "api" + query_string if query_string else "api"
        return await self._post(
            endpoint=endpoint_string,
            payload=request_payload,
            stats=True,
        )

    async def get_player(
            self, allycode: str | int | Sentinel = MutualExclusiveRequired,
            *,
            player_id: str | Sentinel = MutualExclusiveRequired,
            enums: bool = False
    ) -> dict:
        """Get player information from game

        Args:
            allycode: integer or string representing player allycode
            player_id: string representing player game ID
            enums: Flag signifying whether enums in response should be translated to text. [Default: False]

        Returns:
            Dictionary of player information

        Raises:
            ValueError: if neither an allycode nor player_id is provided

        """
        if allycode is MutualRequiredNotSet and player_id is MutualRequiredNotSet:
            err_msg = f"{self._get_function_name()}: Either allycode or player_id must be provided."
            self.logger.debug(err_msg)
            raise ValueError(err_msg)

        if not isinstance(allycode, Sentinel) and not isinstance(player_id, Sentinel):
            err_msg = f"{self._get_function_name()}: Only one of allycode or player_id can be provided."
            self.logger.debug(err_msg)
            raise ValueError(err_msg)

        payload = self._get_player_payload(
            allycode=allycode, player_id=player_id, enums=enums
        )
        return await self._post(endpoint="player", payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getPlayer = get_player

    # Introduced in 1.12.0
    # Use decorator to alias the player_details_only parameter to 'playerDetailsOnly' to maintain backward compatibility
    # while fixing the original naming format mistake.
    @param_alias(param="player_details_only", alias="playerDetailsOnly")
    async def get_player_arena(
            self,
            allycode: str | int | Sentinel = MutualExclusiveRequired,
            player_id: str | Sentinel = MutualExclusiveRequired,
            player_details_only: bool = False,
            enums: bool = False,
    ) -> dict:
        """Get player arena information from game

        Args:
            allycode: integer or string representing player allycode
            player_id: string representing player game ID
            player_details_only: filter results to only player details. Can also be provided as 'playerDetailOnly'
                                        alias. [Defaults to False]
            enums: Flag to enable ENUM translation [Defaults to False]

        Returns:
            Current player arena information as a dictionary

        Raises:
            ValueError: if neither a player_id nor allycode is provided

        """
        if allycode is MutualRequiredNotSet and player_id is MutualRequiredNotSet:
            err_msg = f"{self._get_function_name()}: Either allycode or player_id must be provided."
            self.logger.debug(err_msg)
            raise ValueError(err_msg)

        if not isinstance(allycode, Sentinel) and not isinstance(player_id, Sentinel):
            err_msg = f"{self._get_function_name()}: Only one of allycode or player_id can be provided."
            self.logger.debug(err_msg)
            raise ValueError(err_msg)

        return await self._post(
            endpoint="playerArena",
            payload=self._get_player_payload(
                allycode=allycode,
                player_id=player_id,
                enums=enums,
                include_player_details_flag=True,
                player_details_only=player_details_only,
            ),
        )

    # alias to allow for get_arena() calls as a shortcut for get_player_arena() and non PEP variations
    get_arena = get_player_arena
    get_player_arena_profile = get_player_arena
    getPlayerArena = get_player_arena
    getPlayerArenaProfile = get_player_arena

    @param_alias(param="include_recent_guild_activity_info", alias="includeRecent")
    async def get_guild(
            self,
            guild_id: str | Sentinel = REQUIRED,
            include_recent_guild_activity_info: bool = False,
            enums: bool = False,
    ) -> dict:
        """Get guild information for a specific Guild ID.

        Args:
            guild_id: String ID of guild to retrieve. Guild ID can be found in the output
                                of the get_player() call. (Required)
            include_recent_guild_activity_info: Can also be identified by the alias 'includeRecent'
            enums: Should enums in response be translated to text

        Returns:
            Current guild information as a dictionary

        Raises:
            ValueError: if guild ID is not provided

        """
        if isinstance(guild_id, Sentinel):
            raise ValueError(f"{self._get_function_name()}: Guild ID must be provided.")

        guild = await self._post(
            endpoint="guild",
            payload=self._make_guild_payload(
                guild_id=guild_id,
                include_recent_activity=include_recent_guild_activity_info,
                enums=enums,
            ),
        )
        if "guild" in guild.keys():
            self.logger.debug(f"'guild' key found in response from _post()")
            return guild["guild"]
        else:
            self.logger.debug(f"'guild' key not found in response from _post()'")
            return {}

    # alias for non PEP usage of direct endpoint calls
    getGuild = get_guild

    async def get_guilds_by_name(
            self, name: str | Sentinel = OPTIONAL, start_index: int = 0, count: int = 10, enums: bool = False
    ) -> dict:
        """Search for guild by name and return match.

        Args:
            name: string for guild name search
            start_index: integer representing where in the resulting list of guild name matches
                                the return object should begin
            count: integer representing the maximum number of matches to return, [Default: 10]
            enums: Whether to translate enums in response to text, [Default: False]

        Returns:
            Guild information as a dictionary

        Raises:
            ValueError: if the 'name' argument is not provided

        """
        return await self._post(
            endpoint="getGuilds",
            payload=self._make_guilds_by_name_payload(
                guild_name=name, index=start_index, count=count, enums=enums
            ),
        )

    # alias for non PEP usage of direct endpoint calls
    getGuildByName = get_guilds_by_name

    async def get_guilds_by_criteria(
            self,
            search_criteria: dict,
            start_index: int = 0,
            count: int = 10,
            enums: bool = False,
    ) -> dict:
        """Search for guild by guild criteria and return matches.

        Args:
            search_criteria: Dictionary of search criteria
            start_index: integer representing where in the result list of matches the return object should begin
            count: integer representing the maximum number of matches to return
            enums: Whether to translate enum values to text [Default: False]

        Returns:
            Search results as a list of dictionaries

        Examples:
            ```python
            search_criteria = {
                "minMemberCount": 1,
                "maxMemberCount": 50,
                "includeInviteOnly": True,
                "minGuildGalacticPower": 1,
                "maxGuildGalacticPower": 500000000,
                "recentTbParticipatedIn": []
            }
            ```
        """
        return await self._post(
            endpoint="getGuilds",
            payload=self._make_guilds_by_criteria_payload(
                criteria=search_criteria, index=start_index, count=count, enums=enums
            ),
        )

    # alias for non PEP usage of direct endpoint calls
    getGuildByCriteria = get_guilds_by_criteria

    async def get_leaderboard(
            self,
            leaderboard_type: int = 6,
            *,
            league: int | str = "carbonite",
            division: int | str = 5,
            event_instance_id: str | Sentinel = OPTIONAL,
            group_id: str | Sentinel = OPTIONAL,
            enums: bool = False,
    ) -> dict:
        """Retrieve Grand Arena Championship leaderboard information.

        Args:
            leaderboard_type:
                        Type 4 is for scanning gac brackets, and only returns results while an event is active.
                            When type 4 is indicated, the "league" and "division" arguments must also be provided.
                        Type 6 is for the global leaderboards for the league + divisions.
                            When type 6 is indicated, the "event_instance_id" and "group_id" must also be provided.
            league:
                        Enum values 20, 40, 60, 80, and 100 correspond to carbonite, bronzium, chromium, aurodium,
                           and kyber respectively. Also accepts string values for each league.
            division:
                        Enum values 5, 10, 15, 20, and 25 correspond to divisions 5 through 1 respectively.
                             Also accepts string or int values for each division.
            event_instance_id:
                        When leaderboard_type 4 is indicated, a combination of the event Id and the instance ID
                        separated by ':'
                            Example: CHAMPIONSHIPS_GRAND_ARENA_GA2_EVENT_SEASON_36:O1675202400000
            group_id:
                        When leaderboard_type 4 is indicated, must start with the same eventInstanceId, followed
                        by the league and bracketId, separated by :. The number at the end is the bracketId, and
                        goes from 0 to N, where N is the last group of 8 players.
                            Example: CHAMPIONSHIPS_GRAND_ARENA_GA2_EVENT_SEASON_36:O1675202400000:CARBONITE:10431
            enums: Whether to translate enum values to text [Default: False]

        Returns:
            Object containing 'player' and 'playerStatus' elements. The 'player' element is a list of players

        """
        leaderboard = await self._post(
            endpoint="getLeaderboard",
            payload=self._make_get_leaderboards_payload(
                lb_type=leaderboard_type,
                league=league,
                division=division,
                event_instance_id=event_instance_id,
                group_id=group_id,
                enums=enums,
            ),
        )
        return leaderboard

    # alias for non PEP usage of direct endpoint calls
    getLeaderboard = get_leaderboard
    get_gac_leaderboard = get_leaderboard
    getGacLeaderboard = get_leaderboard

    async def get_guild_leaderboard(
            self, leaderboard_id: list | Sentinel = REQUIRED, count: int = 200, enums: bool = False
    ) -> dict:
        """Retrieve leaderboard information from SWGOH game servers.

        Args:
            leaderboard_id: List of objects indicating leaderboard type, month offset, and depending on the
                                    leaderboard type, a defId. For example, leaderboard type 2 would also require a
                                    defId of one of "sith_raid", "rancor", "rancor_challenge", or "aat".
            count: Number of entries to retrieve [Default: 200]
            enums: Convert enums to strings [Default: False]

        Returns:
            List of the leaderboard objects

        Raises:
            ValueError: If leaderboard_id is not a list object

        """
        if leaderboard_id is MISSING or not isinstance(leaderboard_id, list):
            err_msg = f"{self._get_function_name()}: 'leaderboard_id' argument is required."
            self.logger.error(err_msg)
            raise ValueError(err_msg)

        return await self._post(
            endpoint="getGuildLeaderboard",
            payload=self._make_get_guild_leaderboard_payload(
                lb_id=leaderboard_id, count=count, enums=enums
            ),
        )

    # alias for non PEP usage of direct endpoint calls
    getGuildLeaderboard = get_guild_leaderboard

    async def get_latest_game_data_version(self, game_version: str | Sentinel = OPTIONAL) -> dict:
        """Get the latest game data and language bundle versions

        Args:
            game_version: String of specific game data version to retrieve

        Returns:
            Dictionary containing only the current 'game' and 'language' versions

        """
        client_specs: dict = {}
        if not isinstance(game_version, Sentinel):
            client_specs = {"externalVersion": game_version}
        current_metadata = await self.get_metadata(client_specs=client_specs)
        return {
            "game": current_metadata["latestGamedataVersion"],
            "language": current_metadata["latestLocalizationBundleVersion"],
        }

    # alias for shorthand call
    getVersion = get_latest_game_data_version
