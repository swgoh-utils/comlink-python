"""
Python 3 interface library for swgoh-comlink-async (https://github.com/swgoh-utils/swgoh-comlink-async)
"""
from __future__ import annotations, print_function

import hashlib
import hmac
import os
import time
from json import dumps
from typing import Callable
import functools

import aiohttp

from .version import __version__
from swgoh_comlink import utils


def _get_player_payload(allycode: str | int = None, player_id: str = None, enums: bool = False) -> dict:
    """
    Helper function to build payload for get_player functions

    :param allycode: player allyCode [Default: None]
    :type allycode: str
    :param player_id: player game ID [Default: None]
    :type player_id: str
    :param enums: Flag to indicate whether ENUMs should be converted to string values. [Default: False]
    :type enums: bool
    :return: Dictionary of Player payload information
    :rtype: dict

    """
    payload = {
        "payload": {},
        "enums": enums
    }
    # If player ID is provided use that instead of allyCode
    if player_id is not None:
        payload['payload']['playerId'] = f'{player_id}'
    # Otherwise use allyCode to lookup player data
    elif allycode is not None:
        payload['payload']['allyCode'] = f'{allycode}'
    else:
        raise RuntimeError("Either an allyCode or playerId is required.")
    return payload


def _param_alias(param: str, alias: str) -> Callable:
    def _decorator(func):
        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            alias_param_value = kwargs.get(alias)
            if alias_param_value:
                kwargs[param] = alias_param_value
                del kwargs[alias]
            return func(*args, **kwargs)

        return _wrapper

    return _decorator


class SwgohComlinkAsync:
    """Class definition for swgoh-comlink interface and supported async methods.

    Instances of this class are used to query the Star Wars Galaxy of Heroes
    game servers for exposed endpoints via the swgoh-comlink proxy library
    running on the same host.

    """

    def __init__(self,
                 url: str = "http://localhost:3000",
                 access_key: str = None,
                 secret_key: str = None,
                 stats_url: str = "http://localhost:3223",
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
        self.logger = utils.get_logger(__name__, logging_level, logging_terminal)
        self.logging_level = logging_level.upper()
        self.__version__ = __version__
        self.url_base = url
        self.stats_url_base = stats_url
        self.hmac = False  # HMAC use disabled by default

        # host and port parameters override defaults
        if host:
            self.url_base = f'http://{host}:{port}'
            self.stats_url_base = f'http://{host}:{stats_port}'

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

    def _create_auth_header_value(self, endpoint, payload):
        """Craft the HTTP X-Date and Authorization header values needed when HMAC access restriction is required"""
        req_time = str(int(time.time() * 1000))
        hmac_obj = hmac.new(key=self.secret_key.encode(), digestmod=hashlib.sha256)
        hmac_obj.update(req_time.encode())
        hmac_obj.update(b'POST')
        hmac_obj.update(f'/{endpoint}'.encode())
        # json dumps separators needed for compact string formatting required for compatibility with
        # comlink since it is written with javascript as the primary object model
        # ordered dicts are also required with the 'payload' key listed first for proper MD5 hash calculation
        if payload:
            payload_string = dumps(payload, separators=(',', ':'))
        else:
            payload_string = dumps({})
        payload_hash_digest = hashlib.md5(payload_string.encode()).hexdigest()
        hmac_obj.update(payload_hash_digest.encode())
        hmac_digest = hmac_obj.hexdigest()
        if self.logging_level == 'DEBUG':
            self.logger.debug(
                f"HTTP Authorization header = HMAC-SHA256 Credential={self.access_key},Signature={hmac_digest}")
        return f'{req_time}', f'HMAC-SHA256 Credential={self.access_key},Signature={hmac_digest}'

    async def _post(self,
                    endpoint: str = None,
                    payload: dict = None
                    ) -> dict:
        if self.logging_level == 'DEBUG':
            self.logger.debug("Executing _post() requesst...")
        req_headers = {}
        # If access_key and secret_key are set, perform HMAC security
        if self.hmac:
            req_headers['X-Date'], req_headers['Authorization'] = self._create_auth_header_value(endpoint, payload)
        try:
            if self.logging_level == 'DEBUG':
                self.logger.debug(f"Attempting Async HTTP POST on /{endpoint}")
                self.logger.debug(f"payload = {dumps(payload)}")
                self.logger.debug(f"headers = {req_headers}")
            async with self.client_session.post(f'/{endpoint}', json=payload, headers=req_headers) as resp:
                return await resp.json()
        except Exception as e:
            raise e

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
    asyncGetGameMetaData = get_game_metadata
    asyncGetMetaData = get_game_metadata
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
    asyncGetEnums = get_enums

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
    asyncGetVersion = get_latest_game_data_version

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
        return await self._post(endpoint='asyncGetEvents', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    asyncGetEvents = get_events

    async def get_game_data(self,
                            version: str = "",
                            include_pve_units: bool = True,
                            request_segment: int = 0,
                            enums: bool = False
                            ) -> dict:
        """Get game data

        :param version: Version of game data to retrieve. (found in metadata key value 'latestGamedataVersion')
        :type version: str
        :param include_pve_units: Flag to indicate whether PVE unit data should be included in the response.  [Default: True]
        :type include_pve_units: bool
        :param request_segment: Integer indicating the game data segment to return. [Default: 0] See https://github.com/swgoh-utils/swgoh-comlink/wiki/Game-Data
        :type request_segment: int
        :param enums: Boolean flag to indicate whether ENUM values should be converted in response. [Default: False]
        :type enums: bool
        :return: Dictionary containing all data segments requested.
        :rtype: dict

        """
        if version == "":
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
        return await self._post(endpoint='data', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    asyncGetGameData = get_game_data

    async def get_localization(self,
                               id: str,
                               unzip: bool = False,
                               enums: bool = False
                               ) -> dict:
        """Get localization data from game

        :param id: latestLocalizationBundleVersion found in game metadata. This method will collect the latest language version if the 'id' argument is not provided.
        :type id: str
        :param unzip: Specify whether to deliver data uncompressed. [Default: False]
        :type unzip: bool
        :param enums: Specify whether to translate ENUM values to strings [Default: False]
        :type enums: bool
        :return: A dictionary containing elements that represent either a Base64 encoded string of the compressed data, or the raw uncompressed data.
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
    asyncGetLocalization = get_localization
    asyncGetLocalizationBundle = get_localization
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
        query_string = None

        if flags:
            if isinstance(flags, list):
                flags = 'flags=' + ','.join(flags)
            else:
                raise RuntimeError('Invalid "flags" parameter. Expecting type "list"')
        if language:
            language = f'language={language}'
        if flags or language:
            query_string = f'?' + '&'.join(filter(None, [flags, language]))
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
        payload = _get_player_payload(allycode=allycode, player_id=player_id, enums=enums)
        return await self._post(endpoint='player', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    asyncGetPlayer = get_player

    # Introduced in 1.12.0
    # Use decorator to alias the player_details_only parameter to 'playerDetailsOnly' to maintain backward compatibility
    # while fixing the original naming format mistake.
    @_param_alias(param="player_details_only", alias='playerDetailsOnly')
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
        :param player_details_only: filter results to only player details [Default: False] [Parameter name can also be specified as 'playerDetailOnly']
        :type player_details_only: bool
        :param enums: Flag to indicate whether ENUMs should be translated to strings. [Default: False]
        :type enums: bool
        :return: Dictionary containing player arena information
        :rtype: dict

        """
        payload = _get_player_payload(allycode=allycode, player_id=player_id, enums=enums)
        payload['payload']['playerDetailsOnly'] = player_details_only
        return await self._post(endpoint='playerArena', payload=payload)

    # alias to allow for get_arena() calls as a shortcut for get_player_arena() and non PEP variations
    get_arena = get_player_arena
    get_player_arena_profile = get_player_arena
    asyncGetPlayerArena = get_player_arena
    asyncGetPlayerArenaProfile = get_player_arena

    @_param_alias(param="include_recent_guild_activity_info", alias="includeRecent")
    async def get_guild(self,
                        guild_id: str,
                        include_recent_guild_activity_info: bool = False,
                        enums: bool = False
                        ) -> dict:
        """Get guild information for a specific Guild ID.

        :param guild_id: String ID of guild to retrieve. Guild ID can be found in the output of the get_player() call. (Required)
        :type guild_id: str
        :param include_recent_guild_activity_info: boolean [Default: False] (Optional) [Parameter name can also be specified as 'includeRecent']
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
    asyncGetGuild = get_guild

    async def get_guilds_by_name(self,
                                 name: str,
                                 start_index: int = 0,
                                 count: int = 10,
                                 enums: bool = False
                                 ) -> dict:
        """Search for guild by name and return match.

        :param name: string for guild name search
        :type name: str
        :param start_index: integer representing where in the resulting list of guild name matches the return object should begin. [Default: 0]
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
    asyncGetGuildByName = get_guilds_by_name

    async def get_guilds_by_criteria(self,
                                     search_criteria: dict,
                                     start_index: int = 0,
                                     count: int = 10,
                                     enums: bool = False
                                     ) -> dict:
        """Search for guild by guild criteria and return matches.

        :param search_criteria: Dictionary
        :type search_criteria: dict
        :param start_index: integer representing where in the resulting list of guild name matches the return object should begin
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
    asyncGetGuildByCriteria = get_guilds_by_criteria

    async def get_leaderboard(self,
                              leaderboard_type: int,
                              league: int | str = None,
                              division: int | str = None,
                              event_instance_id: str = None,
                              group_id: str = None,
                              enums: bool = False
                              ) -> dict:
        """Retrieve Grand Arena Championship leaderboard information.

        See https://github.com/swgoh-utils/swgoh-comlink/wiki/Getting-Started#getLeaderboard for details

        :param leaderboard_type: Type 4 is for scanning gac brackets, and only returns results while an event is active. When type 4 is indicated, the "league" and "division" arguments must also be provided. Type 6 is for the global leaderboards for the league + divisions. When type 6 is indicated, the "event_instance_id" and "group_id" must also be provided.
        :type leaderboard_type: int
        :param league: Enum values 20, 40, 60, 80, and 100 correspond to carbonite, bronzium, chromium, aurodium, and kyber respectively. Also accepts string values for each league.
        :type league: str
        :param division: Enum values 5, 10, 15, 20, and 25 correspond to divisions 5 through 1 respectively. Also accepts string or int values for each division.
        :type division: str
        :param event_instance_id: When leaderboard_type 4 is indicated, a combination of the event Id and the instance ID separated by ':' Example: CHAMPIONSHIPS_GRAND_ARENA_GA2_EVENT_SEASON_36:O1675202400000
        :type event_instance_id: str
        :param group_id: When leaderboard_type 4 is indicated, must start with the same eventInstanceId, followed by the league and bracketId, separated by :. The number at the end is the bracketId, and goes from 0 to N, where N is the last group of 8 players. Example: CHAMPIONSHIPS_GRAND_ARENA_GA2_EVENT_SEASON_36:O1675202400000:CARBONITE:10431
        :type group_id: str
        :param enums: Whether to translate enum values to text [Default: False]
        :type enums: bool
        :return: Dictionary containing current leaderboard information
        :rtype: dict

        """
        leagues = {
            'kyber': 100,
            'aurodium': 80,
            'chromium': 60,
            'bronzium': 40,
            'carbonite': 20
        }
        divisions = {
            '1': 25,
            '2': 20,
            '3': 15,
            '4': 10,
            '5': 5
        }
        # Translate parameters if needed
        if isinstance(league, str):
            league = leagues[league.lower()]
        if isinstance(division, int) and len(str(division)) == 1:
            division = divisions[str(division).lower()]
        if isinstance(division, str):
            division = divisions[division.lower()]
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
    asyncGetLeaderboard = get_leaderboard
    get_gac_leaderboard = get_leaderboard
    asyncGetGacLeaderboard = get_leaderboard

    async def get_guild_leaderboard(self, leaderboard_id: list, count: int = 200, enums: bool = False) -> dict:
        """Retrieve leaderboard information from SWGOH game servers.

        See https://github.com/swgoh-utils/swgoh-comlink/wiki/Getting-Started#getGuildLeaderboard for details.

        :param leaderboard_id: List of objects indicating leaderboard type, month offset, and depending on the leaderboard type, a defId. For example, leaderboard type 2 would also require a defId of one of "sith_raid", "rancor", "rancor_challenge", or "aat".
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
    asyncGetGuildLeaderboard = get_guild_leaderboard
