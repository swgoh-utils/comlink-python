"""
Python 3 interface library for swgoh-comlink (https://github.com/swgoh-utils/swgoh-comlink)
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from json import loads, dumps

import requests

from .version import __version__


def _get_player_payload(allycode=None, player_id=None, enums=False):
    """
    Helper function to build payload for get_player functions
    :param allycode: player allyCode
    :param player_id: player game ID
    :param enums: boolean
    :return: dict
    """
    payload = {
        "payload": {},
        "enums": enums}
    # If player ID is provided use that instead of allyCode
    if not allycode and player_id:
        payload['payload']['playerId'] = f'{player_id}'
    # Otherwise use allyCode to lookup player data
    else:
        payload['payload']['allyCode'] = f'{allycode}'
    return payload


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

    def _get_game_version(self):
        """ Get the current game version """
        md = self.get_game_metadata()
        return md['latestGamedataVersion']

    def _post(self,
              url_base: str = None,
              endpoint: str = None,
              payload: dict = None
              ):
        """
        Execute HTTP POST operation against swgoh-comlink
        :param url_base: Base URL for the request method
        :param endpoint: which game endpoint to call
        :param payload: POST payload json data
        :return: dict
        """
        if not url_base:
            url_base = self.url_base
        post_url = url_base + f'/{endpoint}'
        req_headers = {}
        # If access_key and secret_key are set, perform HMAC security
        if self.hmac:
            req_time = str(int(time.time() * 1000))
            req_headers = {"X-Date": f'{req_time}'}
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
            req_headers['Authorization'] = f'HMAC-SHA256 Credential={self.access_key},Signature={hmac_digest}'
        try:
            r = requests.post(post_url, json=payload, headers=req_headers)
            return loads(r.content.decode('utf-8'))
        except Exception as e:
            raise e

    def get_unit_stats(self, request_payload, flags=None, language=None):
        """
        Calculate unit stats using swgoh-stats service interface to swgoh-comlink

        :param request_payload:
        :param flags: List of flags to include in the request URI
        :param language: String indicating the desired localized language
        :return: object
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
        return self._post(url_base=self.stats_url_base, endpoint=endpoint_string, payload=request_payload)

    def get_enums(self):
        """
        Get an object containing the game data enums
        :return: object
        """
        url = self.url_base + '/enums'
        try:
            r = requests.request('GET', url)
            return loads(r.content.decode('utf-8'))
        except Exception as e:
            raise e

    # alias for non PEP usage of direct endpoint calls
    getEnums = get_enums

    def get_events(self, enums=False):
        """
        Get an object containing the events game data
        :return: object
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
                      include_pve_units=True,
                      request_segment: int = 0,
                      enums=False
                      ):
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
                         unzip=False,
                         enums=False
                         ):
        """
        Get localization data from game
        :param id: latestLocalizationBundleVersion found in game metadata. (Required)
        :param unzip: boolean [Defaults to False]
        :param enums: boolean [Defaults to False]
        :return: dict
        """
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

    def get_game_metadata(self, client_specs=None, enums=False):
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
                   allycode: str or int = None,
                   player_id: str = None,
                   enums=False
                   ):
        """
        Get player information from game
        :param allycode: integer or string representing player allycode
        :param player_id: string representing player game ID
        :param enums: boolean [Defaults to False]
        :return: dict
        """
        payload = _get_player_payload(allycode=allycode, player_id=player_id, enums=enums)
        return self._post(endpoint='player', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getPlayer = get_player

    def get_player_arena(self,
                         allycode: int = None,
                         player_id: str = None,
                         playerDetailsOnly=False,
                         enums=False
                         ):
        """
        Get player arena information from game
        :param allycode: integer or string representing player allycode
        :param player_id: string representing player game ID
        :param playerDetailsOnly: filter results to only player details [Defaults to False]
        :param enums: boolean [Defaults to False]
        :return: dict
        """
        payload = _get_player_payload(allycode=allycode, player_id=player_id, enums=enums)
        payload['payload']['playerDetailsOnly'] = playerDetailsOnly
        return self._post(endpoint='playerArena', payload=payload)

    # alias to allow for get_arena() calls as a shortcut for get_player_arena() and non PEP variations
    get_arena = get_player_arena
    get_player_arena_profile = get_player_arena
    getPlayerArena = get_player_arena
    getPlayerArenaProfile = get_player_arena

    def get_guild(self,
                  guild_id: str,
                  include_recent_guild_activity_info=False,
                  enums=False
                  ):
        """
        Get guild information for a specific Guild ID.
        :param guild_id: ID of guild to retrieve. Guild ID can be found in the output of the get_player() call. (Required)
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
                           enums=False
                           ):
        """
        Search for guild by name and return match.
        :param name: string for guild name search
        :param start_index: integer representing where in the resulting list of guild name matches the return object should begin
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
                               enums=False
                               ):
        """
        Search for guild by guild criteria and return matches.
        :param search_criteria: Dictionary
        :param start_index: integer representing where in the resulting list of guild name matches the return object should begin
        :param count: integer representing the maximum number of matches to return
        :param enums: Whether to translate enum values to text [Default: False]
        :return: dict

        search_criteria_template = {
            "min_member_count": 1,
            "max_member_count": 50,
            "include_invite_only": True,
            "min_guild_galactic_power": 1,
            "max_guild_galactic_power": 500000000,
            "recent_tb_participated_in": []
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
                        enums=False
                        ):
        """
        Retrieve Grand Arena Championship leaderboard information.
        :param leaderboard_type: Type 4 is for scanning gac brackets, and only returns results while an event is active.
                                    When type 4 is indicated, the "league" and "division" arguments must also be provided.
                                 Type 6 is for the global leaderboards for the league + divisions.
                                    When type 6 is indicated, the "event_instance_id" and "group_id" must also be provided.
        :param league: Enum values 20, 40, 60, 80, and 100 correspond to carbonite, bronzium, chromium, aurodium,
                       and kyber respectively. Also accepts string values for each league.
        :param division: Enum values 5, 10, 15, 20, and 25 correspond to divisions 5 through 1 respectively.
                         Also accepts string or int values for each division.
        :param event_instance_id: When leaderboard_type 4 is indicated, a combination of the event Id and the instance
                                ID separated by ':'
                                Example: CHAMPIONSHIPS_GRAND_ARENA_GA2_EVENT_SEASON_36:O1675202400000
        :param group_id: When leaderboard_type 4 is indicated, must start with the same eventInstanceId, followed
                         by the league and bracketId, separated by :. The number at the end is the bracketId, and
                         goes from 0 to N, where N is the last group of 8 players.
                            Example: CHAMPIONSHIPS_GRAND_ARENA_GA2_EVENT_SEASON_36:O1675202400000:CARBONITE:10431
        :param enums: Whether to translate enum values to text [Default: False]
        :return: object
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
        leaderboard = self._post(endpoint='getLeaderboard', payload=payload)
        return leaderboard

    # alias for non PEP usage of direct endpoint calls
    getLeaderboard = get_leaderboard
