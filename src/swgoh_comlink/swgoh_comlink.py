# -*- coding: utf-8 -*-
"""Python 3 interface library for swgoh-comlink (https://github.com/swgoh-utils/swgoh-comlink)

This module provides interface methods for the swgoh-comlink service. The swgoh-comlink service
runs either as a standalone executable or in a docker container on a locally controlled server or virtual
machine.

Additional information on the swgoh-comlink service can be also be found on the development team's discord server
located at https://discord.gg/8ATYnUA746

"""
from __future__ import annotations

import hashlib
import hmac
import inspect
import os
import time
from hmac import HMAC
from json import dumps
from typing import Any

import httpx

from utils import *
from ._const import *

__all__ = [
    "SwgohComlink",
    "SwgohComlinkAsync"
]


def _get_function_name() -> str:
    """Return the name for the calling function"""
    return f"{inspect.stack()[1].function}()"


class SwgohComlinkBase:
    """Base class for comlink-python interface and supported methods.

    This base class is meant to be inherited by extension classes for actual method definitions
    using synchronous and asynchronous interfaces.

    """

    url: str
    access_key: str
    secret_key: str
    stats_url: str | None
    host: str | None = "localhost"
    protocol: str = "http"
    port: int = 3000
    stats_port: int = 3223
    default_logger: bool = False
    hmac: bool = False

    @staticmethod
    def update_hmac_obj(hmac_obj: HMAC, values: list[str]) -> HMAC:
        """Add encoded values to hmac object

        Args:
            hmac_obj (HMAC): An HMAC object to be updated
            values (list[str]): List of stings to add to the HMAC object

        Returns:
            The updated HMAC object

        """
        for value in values:
            hmac_obj.update(value.encode())
        return hmac_obj

    @staticmethod
    def construct_url_base(protocol: str, host: str, port: int) -> str:
        """Construct a URL base string from protocol, host and port inputs

        Args:
            protocol: http or https protocol
            host: host address
            port: port number

        Returns:
            URL string

        """
        return f"{protocol}://{host}:{port}"

    DEFAULT_URL: str = construct_url_base(host=host, port=port, protocol=protocol)
    # str: The URL of the swgoh-comlink service. Defaults to http://localhost:3000

    DEFAULT_STATS_URL: str = construct_url_base(host=host, port=stats_port, protocol=protocol)

    # str: The URL of the swgoh-stats service. Defaults to http://localhost:3223

    @staticmethod
    def get_player_payload(
            allycode: str | int = "",
            player_id: str = "",
            enums: bool = False,
            include_player_details_flag: bool = False,
            player_details_only: bool = False
    ) -> dict:
        """Create a swgoh-comlink payload object for player endpoints

        Args:
            allycode (str|int): Player allycode
            player_id (str): Player ID
            enums (bool): Flag to indicate whether ENUM values should be translated
            include_player_details_flag (bool): Flag to indicate whether player_details_only should be included
                                                in the response
            player_details_only (bool): Flag to enable filtering of get_player_arena() method results

        Returns:
            Dict: swgoh-comlink payload object

        """
        if not allycode and not player_id:
            raise ValueError("Either allycode or player_id must be provided.")
        if allycode and player_id:
            raise ValueError("Only one of allycode or player_id can be provided.")
        payload = {"payload": {}, "enums": enums}
        if allycode:
            allycode = sanitize_allycode(allycode)
            payload["payload"]["allyCode"] = f"{allycode}"
        else:
            payload["payload"]["playerId"] = f"{player_id}"
        if enums:
            payload["enums"] = True
        if include_player_details_flag:
            payload["payload"]["playerDetailsOnly"] = player_details_only
        return payload

    @staticmethod
    def make_client_specs(client_specs: dict | None = None, enums: bool = False) -> dict:
        """Create client_spec dictionary for get_metadata() method"""
        payload = {}
        if client_specs:
            payload = {"payload": {"clientSpecs": client_specs}, "enums": enums}
        return payload

    @staticmethod
    def make_game_data_payload(version: str = "",
                               include_pve_units: bool = False,
                               request_segment: int = 0,
                               enums: bool = False) -> dict:
        """Create game_data payload object and return"""
        if not version:
            return {}
        return {
            "payload": {
                "version": f"{version}",
                "includePveUnits": include_pve_units,
                "requestSegment": request_segment,
            },
            "enums": enums,
        }

    @staticmethod
    def make_guild_payload(guild_id: str = "", include_recent_activity: bool = False, enums: bool = False) -> dict:
        """Create get_guild() method payload object"""
        if not guild_id:
            raise ValueError(f"{_get_function_name()}, 'guild_id' must be provided.")

        return {
            "payload": {
                "guildId": guild_id,
                "includeRecentGuildActivityInfo": include_recent_activity,
            },
            "enums": enums,
        }

    @staticmethod
    def make_guilds_by_name_payload(guild_name: str = "", index: int = 0, count: int = 10, enums: bool = False) -> dict:
        """Create get_builds_by_name() method payload object"""
        if not guild_name:
            raise ValueError(f"{_get_function_name()}, 'guild_name' must be provided.")

        return {
            "payload": {
                "name": guild_name,
                "filterType": 4,
                "startIndex": index,
                "count": count,
            },
            "enums": enums,
        }

    @staticmethod
    def make_guilds_by_criteria_payload(criteria: dict, index: int = 0, count: int = 10, enums: bool = False) -> dict:
        """Create get_builds_by_name() method payload object"""
        if not criteria:
            raise ValueError(f"{_get_function_name()}, 'criteria' must be provided.")

        return {
            "payload": {
                "searchCriteria": criteria,
                "filterType": 5,
                "startIndex": index,
                "count": count,
            },
            "enums": enums,
        }

    @staticmethod
    def make_get_leaderboards_payload(lb_type: int = 0,
                                      league: int | str = "",
                                      division: int | str = "",
                                      event_instance_id: str = "",
                                      group_id: str = "",
                                      enums: bool = False) -> dict:
        """Create get_leaderboards() method payload"""
        if lb_type != 4 and lb_type != 6:
            raise ValueError(f"{_get_function_name()}, 'leaderboard_type' must be either 4 (GAC brackets) or 6 (Global "
                             f"Leaderboards")

        payload: dict = {
            "payload": {
                "leaderboardType": lb_type,
            },
            "enums": enums,
        }
        if lb_type == 4:
            payload["payload"]["eventInstanceId"] = event_instance_id
            payload["payload"]["groupId"] = group_id
        elif lb_type == 6:
            league = convert_league_to_int(league)
            division = convert_divisions_to_int(division)
            payload["payload"]["league"] = league
            payload["payload"]["division"] = division
        return payload

    @staticmethod
    def make_get_guild_leaderboard_payload(lb_id: list, count: int, enums: bool = False) -> dict:
        """Create get_guild_leaderboards() method payload"""
        if not isinstance(lb_id, list):
            raise ValueError(
                f"{_get_function_name()}, leaderboard_id argument should be type list not {type(lb_id)}."
            )
        return {'payload': {"leaderboardId": lb_id, "count": count}, 'enums': enums}

    def __init__(
            self,
            url: str = "",
            access_key: str = "",
            secret_key: str = "",
            stats_url: str | None = None,
            host: str | None = None,
            protocol: str = "http",
            port: int = 3000,
            stats_port: int = 3223,
            default_logger: bool = False,
    ):
        """
        Set initial values when new class instance is created

        Args:
            url (str): The URL where swgoh-comlink is running.
            access_key (str): The HMAC public key. Default to None which indicates HMAC is not used.
            secret_key (str): The HMAC private key. Default to None which indicates HMAC is not used.
            stats_url (str): The url of the swgoh-stats service (if used), such as 'http://localhost:3223'
            protocol (str): The protocol to use for connecting to comlink. Typically, http or https.
            host (str): IP address or DNS name of server where the swgoh-comlink service is running
            port (int): TCP port number where the swgoh-comlink service is running [Default: 3000]
            stats_port (int): TCP port number of where the comlink-stats service is running [Default: 3223]
            default_logger (bool): Flag to enable default logging. Should only be used if testing.

        Note:
            'url' and 'stat_url' are mutually exclusive of the protocol/host/port/stats_port parameters.
                Either of the options should be chosen but not both.

        """

        self.logger = get_logger(default_logger=default_logger)

        if not url:
            self.url_base = self.DEFAULT_URL
            self.logger.info(f"No URL provided. Using {self.url_base}")
        else:
            self.url_base = url
        if not stats_url:
            self.stats_url_base = self.DEFAULT_STATS_URL
            self.logger.info(f"No stats URL provided. Using {self.stats_url_base}")
        else:
            self.stats_url_base = stats_url

        # host and port parameters override defaults
        if host:
            self.url_base = self.construct_url_base(protocol, host, port)
            self.stats_url_base = self.construct_url_base(protocol, host, stats_port)

        # Use values passed from client first, otherwise check for environment variables
        if access_key:
            self.access_key = access_key
        elif "ACCESS_KEY" in os.environ.keys():
            self.access_key = os.getenv("ACCESS_KEY", "")
        else:
            self.access_key = access_key

        if secret_key:
            self.secret_key = secret_key
        elif "SECRET_KEY" in os.environ.keys():
            self.secret_key = os.getenv("SECRET_KEY", "")
        else:
            self.secret_key = secret_key

        if self.access_key and self.secret_key:
            self.hmac = True

        self.logger.info(f"{self.url_base=}")
        self.logger.info(f"{self.stats_url_base=}")

    def construct_request_headers(self, endpoint: str, payload: dict | list[dict]) -> dict:
        """Create HTTP request headers for the given endpoint and payload

        Args:
            endpoint (str): The swgoh-comlink endpoint to use
            payload (dict | list[dict]): The object to be passed to the endpoint for processing

        Returns:
            dict: The HTTP "X-Date" and "Authorization" request headers required by comlink

        """
        headers = {}
        # If access_key and secret_key are set, perform HMAC security
        if self.hmac:
            req_time = str(int(time.time() * 1000))
            headers = {"X-Date": req_time}

            payload_string = dumps(payload or {}, separators=(",", ":"))
            payload_hash_digest = hashlib.md5(payload_string.encode()).hexdigest()

            hmac_obj = hmac.new(key=self.secret_key.encode(), digestmod=hashlib.sha256)
            hmac_obj = self.update_hmac_obj(
                hmac_obj, [req_time, "POST", f"/{endpoint}", payload_hash_digest]
            )

            hmac_digest = hmac_obj.hexdigest()
            headers[
                "Authorization"
            ] = f"HMAC-SHA256 Credential={self.access_key},Signature={hmac_digest}"
        return headers


class SwgohComlink(SwgohComlinkBase):
    """Synchronous interface methods for the swgoh-comlink service.

    Instances of this class are used to query the Star Wars Galaxy of Heroes
    game servers for exposed endpoints via the swgoh-comlink proxy library
    running on the same host.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = httpx.Client(base_url=self.url_base)
        self.stats_client = httpx.Client(base_url=self.stats_url_base)

    def _get_game_version(self) -> str:
        """Get the current game version"""
        md = self.get_game_metadata(client_specs={})
        return md["latestGamedataVersion"]

    def _post(
            self,
            url_base: str,
            endpoint: str,
            payload: dict | list[dict],
            stats: bool = False
    ) -> Any:
        """
        Execute HTTP POST operation against swgoh-comlink

        Args:
            endpoint: which game endpoint to call
            payload: POST payload json data

        Returns:
            JSON decoded response or None

        Raises:
            requests.Exceptions
        """

        url_base = url_base or self.url_base
        post_url = url_base + f"/{endpoint}"
        req_headers = self.construct_request_headers(endpoint, payload)
        self.logger.info(f"Request headers: {req_headers}")
        self.logger.info(f"Post URL: {post_url}")

        try:
            if stats:
                resp = self.stats_client.post(f"/{endpoint}", json=payload, headers=req_headers)
            else:
                resp = self.client.post(f"/{endpoint}", json=payload, headers=req_headers)
            return resp.json()
        except Exception as e:
            self.logger.warning("%s: %s", type(e).__name__, e)
            raise e

    @param_alias(param="request_payload", alias="roster_list")
    def get_unit_stats(
            self,
            request_payload: dict | list[dict],
            flags: list[str],
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

        if not request_payload:
            raise RuntimeError(f"{_get_function_name()}, Request payload is must be provided.")
        # Convert a single character/ship object to a one item list of obj for StatCalc
        if isinstance(request_payload, dict):
            request_payload = [request_payload]
        if flags and not isinstance(flags, list):
            raise RuntimeError('Invalid "flags" parameter. Expecting type "list"')
        query_string = construct_unit_stats_query_string(flags, language)
        endpoint_string = "api" + query_string if query_string else "api"
        self.logger.info(f"{self.stats_url_base=}, {endpoint_string=}")
        return self._post(
            url_base=self.stats_url_base,
            endpoint=endpoint_string,
            payload=request_payload,
            stats=True
        )

    def get_enums(self) -> dict:
        """Get an object containing the game data enums

        Raises:
            requests.Exceptions: If the HTTP request encounters an error

        """
        try:
            # r = requests.get(f"{self.url_base}/enums")
            # return r.json()
            resp = self.client.get(f"{self.url_base}/enums")
            return resp.json()
        except Exception as e:
            raise e

    # alias for non PEP usage of direct endpoint calls
    getEnums = get_enums

    def get_events(self, enums: bool = False) -> dict:
        """Get an object containing the events game data

        Args:
            enums: Boolean flag to indicate whether enum value should be converted in response.

        Returns:
            Dictionary containing a single 'gameEvents' which is a list of events as dicts

        Raises:
            requests.Exception:
        """
        payload = {"payload": {}, "enums": enums}
        return self._post(url_base=self.url_base, endpoint="getEvents", payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getEvents = get_events

    def get_game_data(
            self,
            version: str = '',
            include_pve_units: bool = True,
            request_segment: int = 0,
            enums: bool = False,
    ) -> dict:
        """Get current game data from servers

        Args:
            version: Game data version (found in metadata key value 'latestGamedataVersion')
            include_pve_units: Flag to indicate whether PVE units should be included in results  [Defaults to True]
            request_segment: Identifier for whether to return all data (segment 0) or partial segments (values 1-4)
            enums: Flag to enable ENUM replace [Defaults to False]

        Returns:
            Current game data

        """

        if version:
            game_version = version
        else:
            game_version = self._get_game_version()

        return self._post(url_base=self.url_base,
                          endpoint="data",
                          payload=self.make_game_data_payload(version=game_version,
                                                              include_pve_units=include_pve_units,
                                                              request_segment=request_segment,
                                                              enums=enums))

    # alias for non PEP usage of direct endpoint calls
    getGameData = get_game_data

    def get_localization(
            self, id: str = '', unzip: bool = False, enums: bool = False
    ) -> dict:
        """Get localization data from game

        Args:
            id: latestLocalizationBundleVersion found in game metadata. This method will collect the latest language
                            version if the 'id' argument is not provided.
            unzip: Flag to indicate whether the localization bundle should be unzipped. [Default: False]
            enums: Flag to indicate whether ENUMs should be translated. [Default: False]

        Returns:
            Dictionary containing each localization file in a separate element value

        """
        if not id:
            current_game_version = self.get_latest_game_data_version()
            id = current_game_version["language"]

        return self._post(url_base=self.url_base,
                          endpoint="localization",
                          payload={"unzip": unzip, "enums": enums, "payload": {"id": id}})

    # aliases for non PEP usage of direct endpoint calls
    getLocalization = get_localization
    getLocalizationBundle = get_localization
    get_localization_bundle = get_localization

    def get_game_metadata(self, client_specs: dict[str, str] | None = None, enums: bool = False) -> dict:
        """Get the game metadata. Game metadata contains the current game and localization versions.

        Args:
            client_specs:  Optional dictionary containing
            enums: Flag signifying whether enums in response should be translated to text. [Default: False]

        Returns:
            Current game client metadata

        Examples:
            client_specs: {
                  "platform": "string",
                  "bundleId": "string",
                  "externalVersion": "string",
                  "internalVersion": "string",
                  "region": "string"
                }
        """
        return self._post(url_base=self.url_base,
                          endpoint="metadata",
                          payload=self.make_client_specs(client_specs, enums))

    # alias for non PEP usage of direct endpoint calls
    getGameMetaData = get_game_metadata
    getMetaData = get_game_metadata
    get_metadata = get_game_metadata

    def get_player(
            self, allycode: str | int = '', *, player_id: str = '', enums: bool = False
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
        if not allycode and not player_id:
            raise ValueError("Either 'allycode' or 'player_id' must be provided.")

        payload = self.get_player_payload(
            allycode=allycode, player_id=player_id, enums=enums
        )
        return self._post(url_base=self.url_base, endpoint="player", payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getPlayer = get_player

    # Introduced in 1.12.0
    # Use decorator to alias the player_details_only parameter to 'playerDetailsOnly' to maintain backward compatibility
    # while fixing the original naming format mistake.
    @param_alias(param="player_details_only", alias="playerDetailsOnly")
    def get_player_arena(
            self,
            allycode: str | int = '',
            player_id: str = '',
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
        return self._post(url_base=self.url_base,
                          endpoint="playerArena",
                          payload=self.get_player_payload(allycode=allycode,
                                                          player_id=player_id,
                                                          enums=enums,
                                                          include_player_details_flag=True,
                                                          player_details_only=player_details_only))

    # alias to allow for get_arena() calls as a shortcut for get_player_arena() and non PEP variations
    get_arena = get_player_arena
    get_player_arena_profile = get_player_arena
    getPlayerArena = get_player_arena
    getPlayerArenaProfile = get_player_arena

    @param_alias(
        param="include_recent_guild_activity_info", alias="includeRecent"
    )
    def get_guild(
            self,
            guild_id: str = '',
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
        guild = self._post(url_base=self.url_base,
                           endpoint="guild",
                           payload=self.make_guild_payload(
                               guild_id=guild_id,
                               include_recent_activity=include_recent_guild_activity_info,
                               enums=enums))
        if "guild" in guild.keys():
            return guild["guild"]

    # alias for non PEP usage of direct endpoint calls
    getGuild = get_guild

    def get_guilds_by_name(
            self,
            name: str = '',
            start_index: int = 0,
            count: int = 10,
            enums: bool = False,
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
        return self._post(
            url_base=self.url_base,
            endpoint="getGuilds",
            payload=self.make_guilds_by_name_payload(
                guild_name=name,
                index=start_index,
                count=count,
                enums=enums
            ))

    # alias for non PEP usage of direct endpoint calls
    getGuildByName = get_guilds_by_name

    def get_guilds_by_criteria(
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
            Search results as a dictionaries

        Examples
            search_criteria = {
                "minMemberCount": 1,
                "maxMemberCount": 50,
                "includeInviteOnly": True,
                "minGuildGalacticPower": 1,
                "maxGuildGalacticPower": 500000000,
                "recentTbParticipatedIn": []
            }
        """
        return self._post(
            url_base=self.url_base,
            endpoint="getGuilds",
            payload=self.make_guilds_by_criteria_payload(
                criteria=search_criteria,
                index=start_index,
                count=count,
                enums=enums
            ))

    # alias for non PEP usage of direct endpoint calls
    getGuildByCriteria = get_guilds_by_criteria

    def get_leaderboard(
            self,
            leaderboard_type: int = 6,
            *,
            league: int | str = "carbonite",
            division: int | str = 5,
            event_instance_id: str = '',
            group_id: str = '',
            enums: bool = False,
    ) -> dict:
        """Retrieve Grand Arena Championship leaderboard information.

        Args:
            leaderboard_type:
                        Type 4 is for scanning gac brackets, and only returns results while an event is active.
                            When type 4 is indicated, the "league" and "division" arguments must also be provided.
                        Type 6 is for the global leaderboards for the league + divisions.
                            When type 6 is indicated, the "event_instance_id" and "group_id" must also be provided.

            league: Enum values 20, 40, 60, 80, and 100 correspond to carbonite, bronzium, chromium,
                        aurodium, and kyber respectively. Also accepts string values for each league.
            division: Enum values 5, 10, 15, 20, and 25 correspond to divisions 5 through 1 respectively.
                             Also accepts string or int values for each division.
            event_instance_id: When leaderboard_type 4 is indicated, a combination of the event Id and the instance ID
                                separated by ':'
                                Example: CHAMPIONSHIPS_GRAND_ARENA_GA2_EVENT_SEASON_36:O1675202400000
            group_id: When leaderboard_type 4 is indicated, must start with the same eventInstanceId, followed
                        by the league and bracketId, separated by :. The number at the end is the bracketId, and
                        goes from 0 to N, where N is the last group of 8 players.
                            Example: CHAMPIONSHIPS_GRAND_ARENA_GA2_EVENT_SEASON_36:O1675202400000:CARBONITE:10431
            enums: Whether to translate enum values to text [Default: False]

        Returns:
            Object containing 'player' and 'playerStatus' elements. The 'player' element is a list of players

        """
        leaderboard = self._post(
            url_base=self.url_base,
            endpoint="getLeaderboard",
            payload=self.make_get_leaderboards_payload(
                lb_type=leaderboard_type,
                league=league,
                division=division,
                event_instance_id=event_instance_id,
                group_id=group_id,
                enums=enums
            ))
        return leaderboard

    # alias for non PEP usage of direct endpoint calls
    getLeaderboard = get_leaderboard
    get_gac_leaderboard = get_leaderboard
    getGacLeaderboard = get_leaderboard

    def get_guild_leaderboard(
            self, leaderboard_id: list, count: int = 200, enums: bool = False
    ) -> list[dict]:
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
        return self._post(
            url_base=self.url_base,
            endpoint="getGuildLeaderboard",
            payload=self.make_get_guild_leaderboard_payload(
                lb_id=leaderboard_id,
                count=count,
                enums=enums
            ))

    # alias for non PEP usage of direct endpoint calls
    getGuildLeaderboard = get_guild_leaderboard

    def get_latest_game_data_version(self, game_version: str = "") -> dict:
        """Get the latest game data and language bundle versions

        Optional Args:
            game_version: String of specific game data version to retrieve

        Returns:
            Dictionary containing only the current 'game' and 'language' versions

        """
        client_specs: dict = {}
        if game_version:
            client_specs = {"externalVersion": game_version}
        current_metadata = self.get_metadata(client_specs=client_specs)
        return {
            "game": current_metadata["latestGamedataVersion"],
            "language": current_metadata["latestLocalizationBundleVersion"],
        }

    # alias for shorthand call
    getVersion = get_latest_game_data_version
    get_version = get_latest_game_data_version


class SwgohComlinkAsync(SwgohComlinkBase):
    """
    Class definition for swgoh-comlink interface and supported methods.
    Instances of this class are used to query the Star Wars Galaxy of Heroes
    game servers for exposed endpoints via the swgoh-comlink proxy library
    running on the same host.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.client_session = aiohttp.ClientSession(base_url=self.url_base)
        self.client = httpx.AsyncClient(base_url=self.url_base)

    async def _post(self, endpoint: str, payload: dict | list[dict]) -> dict:
        req_headers = self.construct_request_headers(endpoint, payload)
        # If access_key and secret_key are set, perform HMAC security
        try:
            resp = await self.client.post(f"/{endpoint}", json=payload, headers=req_headers)
            return resp.json()
        except Exception as e:
            self.logger.exception(f"Exception occurred: {_get_function_name()}: {e}")
            raise e

    async def get_game_metadata(
            self, client_specs: dict[str, str] | None = None, enums: bool = False
    ) -> dict:
        """Get the game metadata. Game metadata contains the current game and localization versions.

        Args:
            client_specs:  Optional dictionary containing
            enums: Flag signifying whether enums in response should be translated to text. [Default: False]

        Returns:
            Current game client metadata

        Examples:
            client_specs: {
                  "platform": "string",
                  "bundleId": "string",
                  "externalVersion": "string",
                  "internalVersion": "string",
                  "region": "string"
                }

        """
        return await self._post(endpoint="metadata", payload=self.make_client_specs(client_specs, enums))

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
            requests.Exceptions: If the HTTP request encounters an error

        """
        try:
            resp = await self.client.get("/enums")
            return resp.json()
        except Exception as e:
            raise e

    # alias for non PEP usage of direct endpoint calls
    getEnums = get_enums

    async def get_events(self, enums: bool = False) -> dict:
        """Get an object containing the events game data

        Args:
            enums: Boolean flag to indicate whether enum value should be converted in response.

        Returns:
            Dictionary containing a single 'gameEvents' which is a list of events as dicts

        Raises:
            requests.Exception:

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
    ) -> dict:
        """Get current game data from servers

        Args:
            version: Game data version (found in metadata key value 'latestGamedataVersion')
            include_pve_units: Flag to indicate whether PVE units should be included in results  [Defaults to True]
            request_segment: Identifier for whether to return all data (segment 0) or partial segments (values 1-4)
            enums: Flag to enable ENUM replace [Defaults to False]

        Returns:
            Current game data

        """
        if version == "":
            game_version = await self._get_game_version()
        else:
            game_version = version
        return await self._post(endpoint="data",
                                payload=self.make_game_data_payload(version=game_version,
                                                                    include_pve_units=include_pve_units,
                                                                    request_segment=request_segment,
                                                                    enums=enums))

    # alias for non PEP usage of direct endpoint calls
    getGameData = get_game_data

    async def get_localization(
            self, id: str, unzip: bool = False, enums: bool = False
    ) -> dict:
        """Get localization data from game

        Args:
            id: latestLocalizationBundleVersion found in game metadata. This method will collect the latest language
                            version if the 'id' argument is not provided.
            unzip: Flag to indicate whether the localization bundle should be unzipped. [Default: False]
            enums: Flag to indicate whether ENUMs should be translated. [Default: False]

        Returns:
            Dictionary containing each localization file in a separate element value

        """

        if not id:
            current_game_version = await self.get_latest_game_data_version()
            id = current_game_version["language"]

        return await self._post(endpoint="localization",
                                payload={"unzip": unzip, "enums": enums, "payload": {"id": id}})

    # aliases for non PEP usage of direct endpoint calls
    getLocalization = get_localization
    getLocalizationBundle = get_localization
    get_localization_bundle = get_localization

    # Introduced in 1.12.0
    # Use decorator to alias the request_payload parameter to 'units_list' to maintain backward compatibility
    # while fixing the original naming format mistake.
    # TODO: fix below. Won't work with single shared async http client session instance to comlink. Another instance
    #  to statCalc is needed as well. Also the _post method does not handle list payloads
    @param_alias(param="request_payload", alias="units_list")
    async def get_unit_stats(
            self,
            request_payload: dict | list[dict],
            flags: list[str],
            language: str = "eng_us",
    ) -> dict:
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
        if flags is not None and not isinstance(flags, list):
            raise RuntimeError('Invalid "flags" parameter. Expecting type "list"')

        query_string = construct_unit_stats_query_string(flags, language)
        endpoint_string = "api" + query_string if query_string else "api"
        return await self._post(endpoint=endpoint_string, payload=request_payload)

    async def get_player(
            self, allycode: str | int = '', *, player_id: str = '', enums: bool = False
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
        payload = self.get_player_payload(
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
            allycode: str | int = '',
            player_id: str = '',
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
        return await self._post(endpoint="playerArena",
                                payload=self.get_player_payload(allycode=allycode,
                                                                player_id=player_id,
                                                                enums=enums,
                                                                include_player_details_flag=True,
                                                                player_details_only=player_details_only))

    # alias to allow for get_arena() calls as a shortcut for get_player_arena() and non PEP variations
    get_arena = get_player_arena
    get_player_arena_profile = get_player_arena
    getPlayerArena = get_player_arena
    getPlayerArenaProfile = get_player_arena

    @param_alias(
        param="include_recent_guild_activity_info", alias="includeRecent"
    )
    async def get_guild(
            self,
            guild_id: str = '',
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
        guild = await self._post(endpoint="guild",
                                 payload=self.make_guild_payload(
                                     guild_id=guild_id,
                                     include_recent_activity=include_recent_guild_activity_info,
                                     enums=enums))
        if "guild" in guild.keys():
            return guild["guild"]

    # alias for non PEP usage of direct endpoint calls
    getGuild = get_guild

    async def get_guilds_by_name(
            self, name: str = '',
            start_index: int = 0,
            count: int = 10, enums:
            bool = False
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
            payload=self.make_guilds_by_name_payload(
                guild_name=name,
                index=start_index,
                count=count,
                enums=enums
            ))

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

        Examples
            search_criteria = {
                "minMemberCount": 1,
                "maxMemberCount": 50,
                "includeInviteOnly": True,
                "minGuildGalacticPower": 1,
                "maxGuildGalacticPower": 500000000,
                "recentTbParticipatedIn": []
            }

        """
        return await self._post(
            endpoint="getGuilds",
            payload=self.make_guilds_by_criteria_payload(
                criteria=search_criteria,
                index=start_index,
                count=count,
                enums=enums
            ))

    # alias for non PEP usage of direct endpoint calls
    getGuildByCriteria = get_guilds_by_criteria

    async def get_leaderboard(
            self,
            leaderboard_type: int = 6,
            *,
            league: int | str = "carbonite",
            division: int | str = 5,
            event_instance_id: str = '',
            group_id: str = '',
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
            payload=self.make_get_leaderboards_payload(
                lb_type=leaderboard_type,
                league=league,
                division=division,
                event_instance_id=event_instance_id,
                group_id=group_id,
                enums=enums
            ))
        return leaderboard

    # alias for non PEP usage of direct endpoint calls
    getLeaderboard = get_leaderboard
    get_gac_leaderboard = get_leaderboard
    getGacLeaderboard = get_leaderboard

    async def get_guild_leaderboard(
            self, leaderboard_id: list, count: int = 200, enums: bool = False
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
        return await self._post(
            endpoint="getGuildLeaderboard",
            payload=self.make_get_guild_leaderboard_payload(
                lb_id=leaderboard_id,
                count=count,
                enums=enums
            ))

    # alias for non PEP usage of direct endpoint calls
    getGuildLeaderboard = get_guild_leaderboard

    async def get_latest_game_data_version(self, game_version: str = '') -> dict:
        """Get the latest game data and language bundle versions

        Args:
            game_version: String of specific game data version to retrieve

        Returns:
            Dictionary containing only the current 'game' and 'language' versions

        """
        client_specs: dict = {}
        if game_version:
            client_specs = {"externalVersion": game_version}
        current_metadata = await self.get_metadata(client_specs=client_specs)
        return {
            "game": current_metadata["latestGamedataVersion"],
            "language": current_metadata["latestLocalizationBundleVersion"],
        }

    # alias for shorthand call
    getVersion = get_latest_game_data_version
