"""
Python 3 interface library for swgoh-comlink (https://github.com/swgoh-utils/swgoh-comlink)
"""
from __future__ import annotations, print_function, absolute_import

import hashlib
import hmac
import time
from json import loads, dumps

import requests

import swgoh_comlink
from swgoh_comlink.Core import SwgohComlinkBase


class SwgohComlink(SwgohComlinkBase):
    """
    Class definition for comlink-python interface and supported methods.
    Instances of this class are used to query the Star Wars Galaxy of Heroes
    game servers for exposed endpoints via the swgoh-comlink proxy library
    running on the same host.

    """

    def __init__(self, url: str = None, access_key: str = None, secret_key: str = None, stats_url: str = None,
                 protocol: str = "http", host: str = None, port: int = 3000, stats_port: int = 3223,
                 default_logger: bool = False):
        super().__init__(url, access_key, secret_key, stats_url, protocol, host, port, stats_port, default_logger)

    def _get_game_version(self) -> str:
        """ Get the current game version """
        md = self.get_game_metadata()
        return md['latestGamedataVersion']

    def _post(self, url_base: str = None, endpoint: str = None, payload: dict or list = None) -> dict or list or None:

        """
        Execute HTTP POST operation against swgoh-comlink
        :param url_base: Base URL for the request method
        :param endpoint: which game endpoint to call
        :param payload: POST payload json data
        :return: JSON decoded response or None
        :rtype: dict or list or None
        :raises: requests.Exceptions
        """

        url_base = url_base or self.url_base
        post_url = url_base + f'/{endpoint}'
        req_headers = self._construct_request_headers(endpoint, payload)
        self.logger.info(f"Request headers: {req_headers}")
        self.logger.info(f"Post URL: {post_url}")

        try:
            r = requests.post(post_url, json=payload, headers=req_headers)
            return loads(r.content.decode())
        except Exception as e:
            raise e

    def _construct_request_headers(self, endpoint: str, payload: dict) -> dict:
        headers = {}
        # If access_key and secret_key are set, perform HMAC security
        if self.hmac:
            req_time = str(int(time.time() * 1000))
            headers = {"X-Date": req_time}

            payload_string = dumps(payload or {}, separators=(',', ':'))
            payload_hash_digest = hashlib.md5(payload_string.encode()).hexdigest()

            hmac_obj = hmac.new(key=self.secret_key.encode(), digestmod=hashlib.sha256)
            swgoh_comlink.Utils.update_hmac_obj(hmac_obj, [req_time, 'POST', f'/{endpoint}', payload_hash_digest])

            hmac_digest = hmac_obj.hexdigest()
            headers['Authorization'] = f'HMAC-SHA256 Credential={self.access_key},Signature={hmac_digest}'
        return headers

    @swgoh_comlink.Utils.param_alias(param="request_payload", alias='roster_list')
    def get_unit_stats(self,
                       request_payload: dict or list[dict] = None,
                       flags: list[str] = None,
                       language: str = "eng_us") -> dict or list[dict]:
        """
        Calculate unit stats using swgoh-stats service interface to swgoh-comlink

        :param request_payload: Single character/ship dictionary or list containing units for which to calculate stats
        :type request_payload: dict or list
        :param flags: Flags to include in the request URI
        :type flags: list[str]
        :param language: String indicating the desired localized language. [Default "eng_us"]
        :type language: str
        :return: The input object with 'stats' element containing the results of the calculations added.
        :rtype: dict or list[dict]

        :raises RuntimeError: if the request payload is not provided or flags is not a list object

        """

        if request_payload is None:
            raise RuntimeError(f"Request payload is must be provided.")
        # Convert a single character/ship object to a one item list of obj for StatCalc
        if isinstance(request_payload, dict):
            request_payload = [request_payload]
        if flags and not isinstance(flags, list):
            raise RuntimeError('Invalid "flags" parameter. Expecting type "list"')
        query_string = swgoh_comlink.Utils.construct_unit_stats_query_string(flags, language)
        endpoint_string = f'api' + query_string if query_string else 'api'
        self.logger.info(f"{self.stats_url_base=}, {endpoint_string=}")
        return self._post(url_base=self.stats_url_base, endpoint=endpoint_string, payload=request_payload)

    def get_enums(self) -> dict:
        """
        Get an object containing the game data enums
        :return: dict
        """
        url = self.url_base + '/enums'
        try:
            r = requests.request('GET', url)
            return loads(r.content.decode())
        except Exception as e:
            raise e

    # alias for non PEP usage of direct endpoint calls
    getEnums = get_enums

    def get_events(self, enums: bool = False):
        """
        Get an object containing the events game data
        :param enums: Boolean flag to indicate whether enum value should be converted in response. [Default is False]
        :return: dict
        """
        payload = {
            'payload': {},
            'enums': enums
        }
        return self._post(endpoint='getEvents', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getEvents = get_events

    def get_game_data(self,
                      version: str = None,
                      include_pve_units: bool = True,
                      request_segment: int = 0,
                      enums: bool = False
                      ) -> dict:
        """
        Get current game data from servers

        :param version: Game data version (found in metadata key value 'latestGamedataVersion')
        :type version: str
        :param include_pve_units: Flag to indicate whether PVE units should be included in results  [Defaults to True]
        :type include_pve_units: bool
        :param request_segment: Identifier for whether to return all data (segment 0) or partial segments (values 1-4)
                                [Defaults to 0]
        :type request_segment: int
        :param enums: Flag to enable ENUM replace [Defaults to False]
        :type enums: bool
        :return: Current game data
        :rtype: dict
        """

        if version is None:
            game_version = self._get_game_version()
        else:
            game_version = version
        payload = {
            "payload": {
                "version": f"{game_version}",
                "includePveUnits": include_pve_units,
                "requestSegment": request_segment
            },
            "enums": enums
        }
        return self._post(endpoint='data', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGameData = get_game_data

    def get_localization(self,
                         id: str = None,
                         unzip: bool = False,
                         enums: bool = False
                         ) -> dict:
        """
        Get localization data from game
        :param id: latestLocalizationBundleVersion found in game metadata. This method will collect the latest language
                    version if the 'id' argument is not provided.
        :type id: str or None
        :param unzip: Flag to indicate whether the localization bundle should be unzipped. [Default: False]
        :type unzip: bool
        :param enums: Flag to indicate whether ENUMs should be translated. [Default: False]
        :type enums: bool
        :return: Dictionary containing each localization file in a separate element value
        :rtype: dict
        """
        if id is None:
            current_game_version = self.get_latest_game_data_version()
            id = current_game_version['language']

        payload = {
            'unzip': unzip,
            'enums': enums,
            'payload': {
                'id': id
            }
        }
        return self._post(endpoint='localization', payload=payload)

    # aliases for non PEP usage of direct endpoint calls
    getLocalization = get_localization
    getLocalizationBundle = get_localization
    get_localization_bundle = get_localization

    def get_game_metadata(self, client_specs: dict = None, enums: bool = False) -> dict:
        """
        Get the game metadata. Game metadata contains the current game and localization versions.

        :param client_specs:  Optional dictionary containing
        :type client_specs: dict
        :param enums: Flag signifying whether enums in response should be translated to text. [Default: False]
        :type enums: bool
        :return: Current game client metadata
        :rtype: dict

        {
          "payload": {
            "clientSpecs": {
              "platform": "string",
              "bundleId": "string",
              "externalVersion": "string",
              "internalVersion": "string",
              "region": "string"
            }
          },
          "enums": false
        }
        """
        if client_specs is not None:
            payload = {"payload": {"clientSpecs": client_specs}, "enums": enums}
        else:
            payload = {}
        return self._post(endpoint='metadata', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGameMetaData = get_game_metadata
    getMetaData = get_game_metadata
    get_metadata = get_game_metadata

    def get_player(self,
                   allycode: str | int = None,
                   player_id: str = None,
                   enums: bool = False
                   ) -> dict:
        """
        Get player information from game
        :param allycode: integer or string representing player allycode
        :param player_id: string representing player game ID
        :param enums: boolean [Defaults to False]
        :return: dict

        :raises ValueError: if neither an allycode nor player_id is provided

        """
        if allycode is None and player_id is None:
            raise ValueError("Either 'allycode' or 'player_id' must be provided.")

        payload = swgoh_comlink.Utils.get_player_payload(allycode=allycode, player_id=player_id, enums=enums)
        return self._post(endpoint='player', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getPlayer = get_player

    # Introduced in 1.12.0
    # Use decorator to alias the player_details_only parameter to 'playerDetailsOnly' to maintain backward compatibility
    # while fixing the original naming format mistake.
    @swgoh_comlink.Utils.param_alias(param="player_details_only", alias='playerDetailsOnly')
    def get_player_arena(self,
                         allycode: str or int = None,
                         player_id: str = None,
                         player_details_only: bool = False,
                         enums: bool = False
                         ) -> dict:
        """
        Get player arena information from game

        :param allycode: integer or string representing player allycode
        :type allycode: str or int
        :param player_id: string representing player game ID
        :type player_id: str
        :param player_details_only: filter results to only player details. Can also be provided as 'playerDetailOnly'
                                    alias. [Defaults to False]
        :type player_details_only: bool
        :param enums: Flag to enable ENUM translation [Defaults to False]
        :type enums: boolean
        :return: Current player arena information
        :rtype: dict

        :raises ValueError: if neither a player_id nor allycode is provided

        """

        if allycode is None and player_id is None:
            raise ValueError("Either 'allycode' or 'player_id' must be provided.")

        payload = swgoh_comlink.Utils.get_player_payload(allycode=allycode, player_id=player_id, enums=enums)
        payload['payload']['playerDetailsOnly'] = player_details_only
        return self._post(endpoint='playerArena', payload=payload)

    # alias to allow for get_arena() calls as a shortcut for get_player_arena() and non PEP variations
    get_arena = get_player_arena
    get_player_arena_profile = get_player_arena
    getPlayerArena = get_player_arena
    getPlayerArenaProfile = get_player_arena

    @swgoh_comlink.Utils.param_alias(param="include_recent_guild_activity_info", alias="includeRecent")
    def get_guild(self,
                  guild_id: str = None,
                  include_recent_guild_activity_info: bool = False,
                  enums: bool = False
                  ) -> dict:
        """
        Get guild information for a specific Guild ID.
        :param guild_id: String ID of guild to retrieve. Guild ID can be found in the output
                            of the get_player() call. (Required)
        :type guild_id: str
        :param include_recent_guild_activity_info: Can also be identified by the alias 'includeRecent' [Default: False]
        :type include_recent_guild_activity_info: bool
        :param enums: Should enums in response be translated to text. [Default: False] (Optional)
        :type enums: boolean
        :return: Current guild information
        :rtype: dict

        :raises ValueError: if guild ID is not provided

        """

        if guild_id is None:
            raise ValueError("'guild_id' must be provided.")

        payload = {
            "payload": {
                "guildId": guild_id,
                "includeRecentGuildActivityInfo": include_recent_guild_activity_info
            },
            "enums": enums
        }
        guild = self._post(endpoint='guild', payload=payload)
        if 'guild' in guild.keys():
            guild = guild['guild']
        return guild

    # alias for non PEP usage of direct endpoint calls
    getGuild = get_guild

    def get_guilds_by_name(self,
                           name: str = None,
                           /,
                           *,
                           start_index: int = 0,
                           count: int = 10,
                           enums: bool = False
                           ) -> dict:
        """
        Search for guild by name and return match.

        :param name: string for guild name search
        :type name: str
        :param start_index: integer representing where in the resulting list of guild name matches
                            the return object should begin
        :type start_index: int
        :param count: integer representing the maximum number of matches to return, [Default: 10]
        :type count: int
        :param enums: Whether to translate enums in response to text, [Default: False]
        :type enums: boolean
        :return: Guild information
        :rtype: dict

        :raises ValueError: if the 'name' argument is not provided
        """

        if name is None:
            raise ValueError("'name' must be provided.")

        payload = {
            "payload": {
                "name": name,
                "filterType": 4,
                "startIndex": start_index,
                "count": count
            },
            "enums": enums
        }
        return self._post(endpoint='getGuilds', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGuildByName = get_guilds_by_name

    def get_guilds_by_criteria(self,
                               search_criteria: dict,
                               /,
                               *,
                               start_index: int = 0,
                               count: int = 10,
                               enums: bool = False
                               ) -> list[dict]:
        """
        Search for guild by guild criteria and return matches.

        :param search_criteria: Dictionary of search criteria
        :type search_criteria: dict
        :param start_index: integer representing where in the result list of matches the return object should begin
        :type start_index: int
        :param count: integer representing the maximum number of matches to return
        :type count: int
        :param enums: Whether to translate enum values to text [Default: False]
        :type enums: boolean

        :return: Search results
        :rtype: list[dict]

        search_criteria_template = {
            "minMemberCount": 1,
            "maxMemberCount": 50,
            "includeInviteOnly": True,
            "minGuildGalacticPower": 1,
            "maxGuildGalacticPower": 500000000,
            "recentTbParticipatedIn": []
        }
        """
        payload = {
            "payload": {
                "searchCriteria": search_criteria,
                "filterType": 5,
                "startIndex": start_index,
                "count": count
            },
            "enums": enums
        }
        return self._post(endpoint='getGuilds', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGuildByCriteria = get_guilds_by_criteria

    def get_leaderboard(self,
                        leaderboard_type: int = 6,
                        league: int | str = "carbonite",
                        division: int | str = 5,
                        event_instance_id: str = None,
                        group_id: str = None,
                        enums: bool = False
                        ) -> dict:
        """
        Retrieve Grand Arena Championship leaderboard information.
        :param int leaderboard_type:
                    Type 4 is for scanning gac brackets, and only returns results while an event is active.
                        When type 4 is indicated, the "league" and "division" arguments must also be provided.
                    Type 6 is for the global leaderboards for the league + divisions.
                        When type 6 is indicated, the "event_instance_id" and "group_id" must also be provided.
        :param (str|int) league:
                    Enum values 20, 40, 60, 80, and 100 correspond to carbonite, bronzium, chromium, aurodium,
                       and kyber respectively. Also accepts string values for each league.
        :param (str|int) division:
                    Enum values 5, 10, 15, 20, and 25 correspond to divisions 5 through 1 respectively.
                         Also accepts string or int values for each division.
        :param str event_instance_id:
                    When leaderboard_type 4 is indicated, a combination of the event Id and the instance ID
                    separated by ':'
                        Example: CHAMPIONSHIPS_GRAND_ARENA_GA2_EVENT_SEASON_36:O1675202400000
        :param str group_id:
                    When leaderboard_type 4 is indicated, must start with the same eventInstanceId, followed
                    by the league and bracketId, separated by :. The number at the end is the bracketId, and
                    goes from 0 to N, where N is the last group of 8 players.
                        Example: CHAMPIONSHIPS_GRAND_ARENA_GA2_EVENT_SEASON_36:O1675202400000:CARBONITE:10431
        :param bool enums: Whether to translate enum values to text [Default: False]

        :return dict:
                    Object containing 'player' and 'playerStatus' elements. The 'player' element is a list of players

        """

        league = swgoh_comlink.Utils.convert_league_to_int(league)
        division = swgoh_comlink.Utils.convert_divisions_to_int(division)

        payload = {
            "payload": {
                "leaderboardType": leaderboard_type,
            },
            "enums": enums
        }
        if leaderboard_type == 4:
            payload['payload']['eventInstanceId'] = event_instance_id
            payload['payload']['groupId'] = group_id
        elif leaderboard_type == 6:
            payload['payload']['league'] = league
            payload['payload']['division'] = division
        leaderboard = self._post(endpoint='getLeaderboard', payload=payload)
        return leaderboard

    # alias for non PEP usage of direct endpoint calls
    getLeaderboard = get_leaderboard
    get_gac_leaderboard = get_leaderboard
    getGacLeaderboard = get_leaderboard

    def get_guild_leaderboard(self, leaderboard_id: list, count: int = 200, enums: bool = False) -> list[dict]:
        """
        Retrieve leaderboard information from SWGOH game servers.

        :param int leaderboard_id: List of objects indicating leaderboard type, month offset, and depending on the
                                leaderboard type, a defId. For example, leaderboard type 2 would also require a
                                defId of one of "sith_raid", "rancor", "rancor_challenge", or "aat".
        :param int count: Number of entries to retrieve [Default: 200]
        :param bool enums: Convert enums to strings [Default: False]

        :return list[dict]: List of the leaderboard objects

        :raises ValueError: If leaderboard_id is not a list object

        """
        if not isinstance(leaderboard_id, list):
            raise ValueError(f"leaderboard_id argument should be type list not {type(leaderboard_id)}.")
        payload = dict(payload={
            'leaderboardId': leaderboard_id,
            'count': count
        }, enums=enums)
        return self._post(endpoint='getGuildLeaderboard', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGuildLeaderboard = get_guild_leaderboard

    def get_latest_game_data_version(self, game_version: str = None) -> dict:
        """
        Get the latest game data and language bundle versions

        :param str game_version: String of specific game data version to retrieve
        :return dict: Dictionary containing only the current 'game' and 'language' versions

        """
        if game_version is not None:
            client_specs = {"externalVersion": game_version}
        else:
            client_specs = None
        current_metadata = self.get_metadata(client_specs=client_specs)
        return {'game': current_metadata['latestGamedataVersion'],
                'language': current_metadata['latestLocalizationBundleVersion']}

    # alias for shorthand call
    getVersion = get_latest_game_data_version
