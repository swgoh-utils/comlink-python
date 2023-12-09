"""
Python 3 interface library for swgoh-comlink-async (https://github.com/swgoh-utils/swgoh-comlink-async)
"""
from __future__ import annotations, print_function

import hashlib
import hmac
import os
import time
from json import dumps

import aiohttp

from swgoh_comlink import Utils
from .version import __version__


class SwgohComlinkAsync:
    """
    Class definition for swgoh-comlink interface and supported methods.
    Instances of this class are used to query the Star Wars Galaxy of Heroes
    game servers for exposed endpoints via the swgoh-comlink proxy library
    running on the same host.

    """

    def __init__(self,
                 url: str = "http://localhost:3000",
                 access_key: str = None,
                 secret_key: str = None,
                 stats_url: str = "http://localhost:3223",
                 protocol: str = "http",
                 host: str = None,
                 port: int = 3000,
                 stats_port: int = 3223,
                 logging_level: str = 'INFO',
                 logging_terminal: bool = False,
                 ):
        """Set initial values for instances of SwgohComlinkAsync class

        :param url: The URL where swgoh-comlink is running. Defaults to 'http://localhost:3000'
        :type url: str
        :param access_key: The HMAC public key. Default to None which indicates HMAC is not used.
        :type access_key: str
        :param secret_key: The HMAC private key. Default to None which indicates HMAC is not used.
        :type secret_key: str
        :param stats_url: The url of the swgoh-stats service (if used), such as 'http://localhost:3223'
        :type stats_url: str
        :param host: IP address or DNS name of server where the swgoh-comlink service is running
        :type host: str
        :param port: TCP port number where the swgoh-comlink service is running [Default: 3000]
        :type port: int
        :param stats_port: TCP port number of where the comlink-stats service is running [Default: 3223]
        :type stats_port: int

        """
        self.logger = Utils.get_logger(__name__, logging_level, logging_terminal)
        self.logging_level = logging_level.upper()
        self.__version__ = __version__
        self.url_base = url
        self.stats_url_base = stats_url
        self.hmac = False  # HMAC use disabled by default

        # host and port parameters override defaults
        if host:
            self.url_base = Utils.construct_url_base(protocol, host, port)
            self.stats_url_base = Utils.construct_url_base(protocol, host, stats_port)

        # Use values passed from client first, otherwise check for environment variables
        if access_key:
            self.access_key = access_key
        elif os.environ.get('ACCESS_KEY'):
            self.access_key = os.environ.get('ACCESS_KEY')
        else:
            self.access_key = None
        if secret_key:
            self.secret_key = secret_key
        elif os.environ.get('SECRET_KEY'):
            self.secret_key = os.environ.get('SECRET_KEY')
        else:
            self.secret_key = None
        if self.access_key and self.secret_key:
            self.hmac = True

        self.client_session = aiohttp.ClientSession(self.url_base)

    def __del__(self):
        self.client_session.close()

    def __str__(self):
        if self.access_key is None:
            access_str = ''
        else:
            access_str = self.access_key
        return f'{self.url_base=!r} {access_str=!r} {self.stats_url_base=!r} {self.logging_level=!r}'

    async def _post(self,
                    endpoint: str = None,
                    payload: dict = None
                    ) -> dict:
        if self.logging_level == 'DEBUG':
            self.logger.debug("Executing _post() requesst...")
        req_headers = self._construct_request_headers(endpoint, payload)
        # If access_key and secret_key are set, perform HMAC security
        try:
            if self.logging_level == 'DEBUG':
                self.logger.debug(f"Attempting Async HTTP POST on /{endpoint}")
                self.logger.debug(f"payload = {dumps(payload)}")
                self.logger.debug(f"headers = {req_headers}")
            async with self.client_session.post(f'/{endpoint}', json=payload, headers=req_headers) as resp:
                return await resp.json()
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
            Utils.update_hmac_obj(hmac_obj, [req_time, 'POST', f'/{endpoint}', payload_hash_digest])

            hmac_digest = hmac_obj.hexdigest()
            headers['Authorization'] = f'HMAC-SHA256 Credential={self.access_key},Signature={hmac_digest}'
        return headers

    async def get_game_metadata(self, client_specs: dict = None, enums: bool = False) -> dict:
        """Get the game metadata. Game metadata contains the current game and localization versions.

        :param client_specs:  Optional dictionary containing. [Default: None]
        :type client_specs: dict
        :param enums: Boolean signifying whether enums in response should be translated to text. [Default: False]
        :type enums: bool
        :return: Dictionary with game metadata
        :rtype: dict

        """
        if client_specs:
            payload = {"payload": {"client_specs": client_specs}, "enums": enums}
        else:
            payload = {}
        return await self._post(endpoint='metadata', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGameMetaData = get_game_metadata
    getMetaData = get_game_metadata
    get_metadata = get_game_metadata

    async def _get_game_version(self) -> str:
        """ Get the current game version """
        md = await self.get_game_metadata()
        return md['latestGamedataVersion']

    async def get_enums(self) -> dict:
        """Get an object containing the game data enums

        :return: Dictionary of ENUMs and corresponding string values
        :rtype: dict

        """
        try:
            async with self.client_session.get('/enums') as resp:
                return await resp.json()
        except Exception as e:
            raise e

    # alias for non PEP usage of direct endpoint calls
    getEnums = get_enums

    # Get the latest game data and language bundle versions
    async def get_latest_game_data_version(self) -> dict:
        """Get the latest game data and language bundle versions

        :return: Dictionary containing only the current 'game' and 'language' versions
        :rtype: dict

        """
        current_metadata = await self.get_metadata()
        return {'game': current_metadata['latestGamedataVersion'],
                'language': current_metadata['latestLocalizationBundleVersion']}

    # alias for shorthand call
    getVersion = get_latest_game_data_version

    async def get_events(self, enums: bool = False) -> dict:
        """Get an object containing the events game data

        :param enums: Boolean flag to indicate whether ENUM values should be converted in response. [Default is False]
        :type enums: bool
        :return: Dictionary of current and upcoming events
        :rtype: dict

        """
        payload = {
            'payload': {},
            'enums': enums
        }
        return await self._post(endpoint='getEvents', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getEvents = get_events

    async def get_game_data(self,
                            version: str = "",
                            include_pve_units: bool = True,
                            request_segment: int = 0,
                            enums: bool = False
                            ) -> dict:
        """

        :param version: The version of the game data to retrieve. If left blank, the method will automatically
        retrieve the game version using the _get_game_version function. :type version: str

        :param include_pve_units: Flag indicating whether to include PVE (Player vs. Environment) units in the
        retrieved game data. Defaults to True. :type include_pve_units: bool

        :param request_segment: The segment of the game data to request. Defaults to 0.
        :type request_segment: int

        :param enums: Flag indicating whether to include enumerated values in the retrieved game data. Defaults to
        False. :type enums: bool

        :return: A dictionary containing the requested game data.
        :rtype: dict

        """
        if version == "":
            game_version = await self._get_game_version()
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
        return await self._post(endpoint='data', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGameData = get_game_data

    async def get_localization(self,
                               id: str,
                               unzip: bool = False,
                               enums: bool = False
                               ) -> dict:
        """Get localization data from game

        :param id: latestLocalizationBundleVersion found in game metadata. This method will collect the latest
        language version if the 'id' argument is not provided.
        :type id: str
        :param unzip: Specify whether to deliver data uncompressed. [Default: False]
        :type unzip: bool
        :param enums: Specify whether to translate ENUM values
        to strings [Default: False]
        :type enums: bool
        :return: A dictionary containing elements that represent either
        a Base64 encoded string of the compressed data, or the raw uncompressed data.
        :rtype: dict

        """

        if id == "":
            current_game_version = await self.get_latest_game_data_version()
            id = current_game_version['language']

        payload = {
            'unzip': unzip,
            'enums': enums,
            'payload': {
                'id': id
            }
        }
        return await self._post(endpoint='localization', payload=payload)

    # aliases for non PEP usage of direct endpoint calls
    getLocalization = get_localization
    getLocalizationBundle = get_localization
    get_localization_bundle = get_localization

    async def get_unit_stats(self, request_payload: dict, flags: list = None, language: str = None) -> dict:
        """Calculate unit stats using swgoh-stats service interface to swgoh-comlink

        :param request_payload: Dictionary containing units for which to calculate stats
        :type request_payload: dict
        :param flags: List of flags to include in the request URI
        :type flags: list
        :param language: String indicating the desired localized language
        :type language: str
        :return: Dictionary containing all the submitted unit information along with newly computed stat values.
        :rtype: dict

        """
        if flags and not isinstance(flags, list):
            raise RuntimeError('Invalid "flags" parameter. Expecting type "list"')

        query_string = Utils.construct_unit_stats_query_string(flags, language)
        endpoint_string = f'api' + query_string if query_string else 'api'
        return await self._post(endpoint=endpoint_string, payload=request_payload)

    async def get_player(self,
                         allycode: str | int = None,
                         player_id: str = None,
                         enums: bool = False
                         ) -> dict:
        """Get player information from game

        :param allycode: Player allycode. [Default: None]
        :type allycode: str
        :param player_id: Player ID from game. [Default: None]
        :type player_id: str
        :param enums: Flag to indicate whether ENUMs should be translated to strings. [Defaults to False]
        :type enums: bool
        :return: Dictionary containing player data
        :rtype: dict

        """
        if self.logging_level == 'DEBUG':
            self.logger.debug(f"Executing get_player(allycode={allycode}, player_id={player_id}, enums={enums})")
        payload = Utils.get_player_payload(allycode=allycode, player_id=player_id, enums=enums)
        return await self._post(endpoint='player', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getPlayer = get_player

    # Introduced in 1.12.0
    # Use decorator to alias the player_details_only parameter to 'playerDetailsOnly' to maintain backward compatibility
    # while fixing the original naming format mistake.
    @Utils.param_alias(param="player_details_only", alias='playerDetailsOnly')
    async def get_player_arena(self,
                               allycode: str | int = None,
                               player_id: str = None,
                               player_details_only: bool = False,
                               enums: bool = False
                               ) -> dict:
        """Get player arena information from game

        :param allycode: Player allycode. [Default: None]
        :type allycode: str
        :param player_id: Player ID from game. [Default: None]
        :type player_id: str
        :param player_details_only: filter results to only player details [Default: False] [Parameter name can also be
        specified as 'playerDetailOnly']
        :type player_details_only: bool
        :param enums: Flag to indicate whether ENUMs should be translated to strings. [Default: False]
        :type enums: bool
        :return: Dictionary containing player arena information
        :rtype: dict

        """
        payload = Utils.get_player_payload(allycode=allycode, player_id=player_id, enums=enums)
        payload['payload']['playerDetailsOnly'] = player_details_only
        return await self._post(endpoint='playerArena', payload=payload)

    # alias to allow for get_arena() calls as a shortcut for get_player_arena() and non PEP variations
    get_arena = get_player_arena
    get_player_arena_profile = get_player_arena
    getPlayerArena = get_player_arena
    getPlayerArenaProfile = get_player_arena

    @Utils.param_alias(param="include_recent_guild_activity_info", alias="includeRecent")
    async def get_guild(self,
                        guild_id: str,
                        include_recent_guild_activity_info: bool = False,
                        enums: bool = False
                        ) -> dict:
        """Get guild information for a specific Guild ID.

        :param guild_id: String ID of guild to retrieve. Guild ID can be found in the output of the get_player() call.
        :type guild_id: str
        :param include_recent_guild_activity_info: boolean [Default: False] (Optional) [Parameter name can also be
        specified as 'includeRecent']
        :type include_recent_guild_activity_info: bool
        :param enums: Flag to indicate whether ENUMs should be translated to strings. [Default: False]
        :type enums: bool
        :return: Dictionary of guild information
        :rtype: dict

        """
        payload = {
            "payload": {
                "guildId": guild_id,
                "includeRecentGuildActivityInfo": include_recent_guild_activity_info
            },
            "enums": enums
        }
        guild = await self._post(endpoint='guild', payload=payload)
        if 'guild' in guild.keys():
            guild = guild['guild']
        return guild

    # alias for non PEP usage of direct endpoint calls
    getGuild = get_guild

    async def get_guilds_by_name(self,
                                 name: str,
                                 start_index: int = 0,
                                 count: int = 10,
                                 enums: bool = False
                                 ) -> dict:
        """Search for guild by name and return match.

        :param name: string for guild name search
        :type name: str
        :param start_index: integer representing where in the resulting list of guild name matches the return object
        should begin. [Default: 0]
        :type start_index: int
        :param count: integer representing the maximum number of matches to return, [Default: 10]
        :type count: int
        :param enums: Whether to translate enums in response to text, [Default: False]
        :type enums: bool
        :return: Dictionary containing matching guild information
        :rtype: dict

        """
        payload = {
            "payload": {
                "name": name,
                "filterType": 4,
                "startIndex": start_index,
                "count": count
            },
            "enums": enums
        }
        return await self._post(endpoint='getGuilds', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGuildByName = get_guilds_by_name

    async def get_guilds_by_criteria(self,
                                     search_criteria: dict,
                                     start_index: int = 0,
                                     count: int = 10,
                                     enums: bool = False
                                     ) -> dict:
        """Search for guild by guild criteria and return matches.

        :param search_criteria: Dictionary
        :type search_criteria: dict
        :param start_index: integer representing where in the resulting list of guild name matches the return object
        should begin
        :type start_index: int
        :param count: integer representing the maximum number of matches to return
        :type count: int
        :param enums: Whether to translate enum values to text [Default: False]
        :type enums: bool
        :return: Dictionary containing matching guild information.
        :rtype: dict

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
        return await self._post(endpoint='getGuilds', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGuildByCriteria = get_guilds_by_criteria

    async def get_leaderboard(self,
                              leaderboard_type: int,
                              league: int | str = None,
                              division: int | str = None,
                              event_instance_id: str = None,
                              group_id: str = None,
                              enums: bool = False
                              ) -> dict:
        """Retrieve Grand Arena Championship leaderboard information.

        :param leaderboard_type: ...
        :param league: ...
        :param division: ...
        :param event_instance_id: ...
        :param group_id: ...
        :param enums: ...
        :return: dict
        """

        league = Utils.convert_league_to_int(league)
        division = Utils.convert_divisions_to_int(division)

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
        leaderboard = await self._post(endpoint='getLeaderboard', payload=payload)
        return leaderboard

    # alias for non PEP usage of direct endpoint calls
    getLeaderboard = get_leaderboard
    get_gac_leaderboard = get_leaderboard
    getGacLeaderboard = get_leaderboard

    async def get_guild_leaderboard(self, leaderboard_id: list, count: int = 200, enums: bool = False) -> dict:
        """Retrieve leaderboard information from SWGOH game servers.

        See https://github.com/swgoh-utils/swgoh-comlink/wiki/Getting-Started#getGuildLeaderboard for details.

        :param leaderboard_id: List of objects indicating leaderboard type, month offset, and depending on the
        leaderboard type, a defId. For example, leaderboard type 2 would also require a defId of one of "sith_raid",
        "rancor", "rancor_challenge", or "aat".
        :type leaderboard_id: list
        :param count: Number of entries to retrieve [Default: 200]
        :type count: int
        :param enums: Convert enums to strings [Default: False]
        :type enums: bool
        :return: Dictionary containing current guild leaderboard information
        :rtype: dict

        """
        if not isinstance(leaderboard_id, list):
            raise ValueError(f"leaderboard_id argument should be type list not {type(leaderboard_id)}.")
        payload = dict(payload={
            'leaderboardId': leaderboard_id,
            'count': count
        }, enums=enums)
        return await self._post(endpoint='getGuildLeaderboard', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGuildLeaderboard = get_guild_leaderboard
