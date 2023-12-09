"""
Python 3 interface library for swgoh-comlink (https://github.com/swgoh-utils/swgoh-comlink)
"""
from __future__ import annotations, print_function

import hashlib
import hmac
import os
import time
from json import loads, dumps

import requests

from swgoh_comlink import Utils
from .version import __version__


class SwgohComlink:
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
                 stats_port: int = 3223
                 ):
        """
        Set initial values when new class instance is created

        :param url: The URL where swgoh-comlink is running. Defaults to 'http://localhost:3000'
        :param access_key: The HMAC public key. Default to None which indicates HMAC is not used.
        :param secret_key: The HMAC private key. Default to None which indicates HMAC is not used.
        :param stats_url: The url of the swgoh-stats service (if used), such as 'http://localhost:3223'
        :param host: IP address or DNS name of server where the swgoh-comlink service is running
        :param port: TCP port number where the swgoh-comlink service is running [Default: 3000]
        :param stats_port: TCP port number of where the comlink-stats service is running [Default: 3223]
        """

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

    def _get_game_version(self) -> str:
        """ Get the current game version """
        md = self.get_game_metadata()
        return md['latestGamedataVersion']

    def _post(self, url_base: str = None, endpoint: str = None, payload: dict = None) -> dict:

        """
        Execute HTTP POST operation against swgoh-comlink
        :param url_base: Base URL for the request method
        :param endpoint: which game endpoint to call
        :param payload: POST payload json data
        :return: dict
        """

        url_base = url_base or self.url_base
        post_url = url_base + f'/{endpoint}'
        req_headers = self._construct_request_headers(endpoint, payload)

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
            Utils.update_hmac_obj(hmac_obj, [req_time, 'POST', f'/{endpoint}', payload_hash_digest])

            hmac_digest = hmac_obj.hexdigest()
            headers['Authorization'] = f'HMAC-SHA256 Credential={self.access_key},Signature={hmac_digest}'
        return headers

    def get_unit_stats(self, request_payload: dict, flags: list = None, language: str = None) -> dict:
        """
        Calculate unit stats using swgoh-stats service interface to swgoh-comlink

        :param request_payload: Dictionary containing units for which to calculate stats
        :param flags: List of flags to include in the request URI
        :param language: String indicating the desired localized language
        :return: dict
        """
        if flags and not isinstance(flags, list):
            raise RuntimeError('Invalid "flags" parameter. Expecting type "list"')

        query_string = Utils.construct_unit_stats_query_string(flags, language)
        endpoint_string = f'api' + query_string if query_string else 'api'
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
                      version: str = "",
                      include_pve_units: bool = True,
                      request_segment: int = 0,
                      enums: bool = False
                      ) -> dict:
        """
        Get game data
        :param version: string (found in metadata key value 'latestGamedataVersion')
        :param include_pve_units: boolean [Defaults to True]
        :param request_segment: integer >=0 [Defaults to 0]
        :param enums: boolean [Defaults to False]
        :return: dict
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
        return self._post(endpoint='data', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGameData = get_game_data

    def get_localization(self,
                         id: str,
                         unzip: bool = False,
                         enums: bool = False
                         ) -> dict:
        """
        Get localization data from game
        :param id: latestLocalizationBundleVersion found in game metadata. This method will collect the latest language
                    version if the 'id' argument is not provided.
        :param unzip: boolean [Defaults to False]
        :param enums: boolean [Defaults to False]
        :return: dict
        """
        if id == "":
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
        :param enums: Boolean signifying whether enums in response should be translated to text. [Default: False]
        :return: dict

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
        if client_specs:
            payload = {"payload": {"client_specs": client_specs}, "enums": enums}
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
        """
        payload = Utils.get_player_payload(allycode=allycode, player_id=player_id, enums=enums)
        return self._post(endpoint='player', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getPlayer = get_player

    # Introduced in 1.12.0
    # Use decorator to alias the player_details_only parameter to 'playerDetailsOnly' to maintain backward compatibility
    # while fixing the original naming format mistake.
    @Utils.param_alias(param="player_details_only", alias='playerDetailsOnly')
    def get_player_arena(self,
                         allycode: str | int = None,
                         player_id: str = None,
                         player_details_only: bool = False,
                         enums: bool = False
                         ) -> dict:
        """
        Get player arena information from game
        :param allycode: integer or string representing player allycode
        :param player_id: string representing player game ID
        :param player_details_only: filter results to only player details [Defaults to False]
        :param enums: boolean [Defaults to False]
        :return: dict
        """
        payload = Utils.get_player_payload(allycode=allycode, player_id=player_id, enums=enums)
        payload['payload']['playerDetailsOnly'] = player_details_only
        return self._post(endpoint='playerArena', payload=payload)

    # alias to allow for get_arena() calls as a shortcut for get_player_arena() and non PEP variations
    get_arena = get_player_arena
    get_player_arena_profile = get_player_arena
    getPlayerArena = get_player_arena
    getPlayerArenaProfile = get_player_arena

    @Utils.param_alias(param="include_recent_guild_activity_info", alias="includeRecent")
    def get_guild(self,
                  guild_id: str,
                  include_recent_guild_activity_info: bool = False,
                  enums: bool = False
                  ) -> dict:
        """
        Get guild information for a specific Guild ID.
        :param guild_id: String ID of guild to retrieve. Guild ID can be found in the output
                            of the get_player() call. (Required)
        :param include_recent_guild_activity_info: boolean [Default: False] (Optional)
        :param enums: Should enums in response be translated to text. [Default: False] (Optional)
        :return: dict
        """
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
                           name: str,
                           start_index: int = 0,
                           count: int = 10,
                           enums: bool = False
                           ) -> dict:
        """
        Search for guild by name and return match.
        :param name: string for guild name search
        :param start_index: integer representing where in the resulting list of guild name matches
                            the return object should begin
        :param count: integer representing the maximum number of matches to return, [Default: 10]
        :param enums: Whether to translate enums in response to text, [Default: False]
        :return: dict
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
        return self._post(endpoint='getGuilds', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGuildByName = get_guilds_by_name

    def get_guilds_by_criteria(self,
                               search_criteria: dict,
                               start_index: int = 0,
                               count: int = 10,
                               enums: bool = False
                               ) -> dict:
        """
        Search for guild by guild criteria and return matches.
        :param search_criteria: Dictionary of search criteria
        :type search_criteria: dict
        :param start_index: integer representing where in the result list of matches the return object should begin
        :param count: integer representing the maximum number of matches to return
        :param enums: Whether to translate enum values to text [Default: False]
        :return: dict

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
                        leaderboard_type: int,
                        league: int | str = None,
                        division: int | str = None,
                        event_instance_id: str = None,
                        group_id: str = None,
                        enums: bool = False
                        ) -> dict:
        """
        Retrieve Grand Arena Championship leaderboard information.

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
        leaderboard = self._post(endpoint='getLeaderboard', payload=payload)
        return leaderboard

    # alias for non PEP usage of direct endpoint calls
    getLeaderboard = get_leaderboard
    get_gac_leaderboard = get_leaderboard
    getGacLeaderboard = get_leaderboard

    def get_guild_leaderboard(self, leaderboard_id: list, count: int = 200, enums: bool = False) -> dict:
        """
        Retrieve leaderboard information from SWGOH game servers.
        :param leaderboard_id: List of objects indicating leaderboard type, month offset, and depending on the
                                leaderboard type, a defId. For example, leaderboard type 2 would also require a
                                defId of one of "sith_raid", "rancor", "rancor_challenge", or "aat".
        :param count: Number of entries to retrieve [Default: 200]
        :param enums: Convert enums to strings [Default: False]
        :return: dict
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

    """
    Helper methods are below
    """

    # Get the latest game data and language bundle versions
    def get_latest_game_data_version(self) -> dict:
        """
        Get the latest game data and language bundle versions
        :return: dict
        """
        current_metadata = self.get_metadata()
        return {'game': current_metadata['latestGamedataVersion'],
                'language': current_metadata['latestLocalizationBundleVersion']}

    # alias for shorthand call
    getVersion = get_latest_game_data_version
