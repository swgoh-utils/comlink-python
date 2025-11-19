# coding=utf-8
"""
Python 3 interface library for swgoh-comlink (https://github.com/swgoh-utils/swgoh-comlink)
"""
from __future__ import annotations

import functools
import hashlib
import hmac
import os
import re
import time
from json import dumps, loads
from typing import Any, Callable

import requests
import urllib3

from swgoh_comlink import version
from .exceptions import SwgohComlinkException, SwgohComlinkValueError
from .globals import get_logger
from .helpers import Constants

logger = get_logger(__name__)

__all__ = ['SwgohComlink']

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
url_port_re = re.compile(r'^https://\S+:(\d+)$', re.VERBOSE | re.IGNORECASE)


def _get_player_payload(allycode: str | int = None, player_id: str = None, enums: bool = False) -> dict:
    """
    Helper function to build payload for get_player functions
    :param allycode: player allyCode
    :param player_id: player game ID
    :param enums: boolean
    :return: dict
    """
    payload = {"payload": {}, "enums": enums}
    # If player ID is provided use that instead of allyCode
    if not allycode and player_id:
        payload['payload']['playerId'] = f'{player_id}'
    # Otherwise use allyCode to lookup player data
    else:
        payload['payload']['allyCode'] = f'{allycode}'
    return payload


def param_alias(param: str, alias: str) -> Callable:
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            alias_param_value = kwargs.get(alias)
            if alias_param_value:
                kwargs[param] = alias_param_value
                del kwargs[alias]
            return func(*args, **kwargs)

        return wrapper

    return decorator


def sanitize_url(url: str) -> str:
    """Make sure provided URL is in the expected format and return sanitized"""
    url = url.strip("/")
    if url.startswith("https") and not re.fullmatch(url_port_re, url):
        url = f"{url}:443"
    return url


class SwgohComlink:
    """
    Class definition for swgoh-comlink interface and supported methods.
    Instances of this class are used to query the Star Wars Galaxy of Heroes
    game servers for exposed endpoints via the swgoh-comlink proxy library
    running on the same host.

    Args:
        url: The URL where swgoh-comlink is running. Defaults to 'http://localhost:3000'
        access_key: The HMAC public key. Default to None which indicates HMAC is not used.
        secret_key: The HMAC private key. Default to None which indicates HMAC is not used.
        stats_url: The url of the swgoh-stats service (if used), such as 'http://localhost:3223'
        host: IP address or DNS name of server where the swgoh-comlink service is running
        port: TCP port number where the swgoh-comlink service is running [Default: 3000]
        stats_port: TCP port number of where the comlink-stats service is running [Default: 3223]

    Notes:
        If the 'host' and 'port' parameters are provided, the 'url' and 'stats_url' parameters are ignored.
    """

    __comlink_type__ = 'SwgohComlink'

    PROTOCOL = 'http'

    def __init__(
            self, url: str = "http://localhost:3000", stats_url: str = "http://localhost:3223",
            access_key: str | None = None, secret_key: str | None = None, host: str | None = None,
            port: int = 3000, stats_port: int = 3223
            ):
        self.__version__ = version
        self.url_base = sanitize_url(url)
        self.stats_url_base = sanitize_url(stats_url)
        self.hmac = False  # HMAC use disabled by default

        # host and port parameters override defaults
        if host:
            self.url_base = self.PROTOCOL + f'://{host}:{port}'
            self.stats_url_base = self.PROTOCOL + f'://{host}:{stats_port}'

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
        md = self.get_game_metadata()
        return md['latestGamedataVersion']

    def _post(self, url_base: str = None, endpoint: str = None, payload: dict | list = None, ) -> dict:
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
            r = requests.post(post_url, json=payload, headers=req_headers, verify=False)
            return loads(r.content.decode('utf-8'))
        except Exception as e:
            raise SwgohComlinkException(e)

    def get_unit_stats(
            self, request_payload: dict | list, flags: list[str] = None,
            language: str = None
            ) -> list | dict:
        """
        Calculate unit stats using the swgoh-stats service interface to swgoh-comlink.

        This method communicates with an external StatCalc container/service to calculate stats for the
        given units. If the unit for which stats are being calculated is a ship, the 'request_payload' *MUST*
        include crew members along with the ship unit.

        The most common use of this method is to provide an entire player roster as the 'request_payload' argument. This
        action will calculate the stats for each character and ship in the player roster. The resulting stats are
        included in a new 'stats' key in the result object.

        Args:
            request_payload: Dictionary or list of dictionaries containing units for which to calculate stats.
            flags: List of strings specifying which flags to include in the request URI.
            language: String indicating the desired localized language. Default "eng_us".

        Returns:
            Input object with the calculated stats for the specified units included.

        """
        # Define the flags that StatCalc understands
        _allowed_flags = {"gameStyle", "calcGP", "onlyGP", "withoutModCalc", "percentVals", "useMax", "scaled",
                          "unscaled", "statIDs", "enums", "noSpace"}

        query_string = None
        flag_str = None

        if flags:
            if isinstance(flags, list) and set(flags).issubset(_allowed_flags):
                flag_str = 'flags=' + ','.join(flags)
            else:
                raise SwgohComlinkValueError(
                        f'Invalid argument. <flags> should be a list of strings with one or more of "'
                        f'{_allowed_flags} flag values.'
                        )

        if language:
            language = f'language={language}'

        if flag_str or language:
            query_string = f'?' + '&'.join(filter(None, iter([flag_str, language])))

        endpoint_string = f'api' + query_string if query_string else 'api'

        if isinstance(request_payload, dict):
            request_payload = [request_payload]
        return self._post(url_base=self.stats_url_base, endpoint=endpoint_string, payload=request_payload)

    def get_enums(self) -> dict:
        """
        Get an object containing the game data enums

        Returns:
            A dictionary containing the game data enums.
        """
        url = self.url_base + '/enums'
        try:
            r = requests.request('GET', url)
            return loads(r.content.decode('utf-8'))
        except Exception as e:
            raise SwgohComlinkException(e)

    # alias for non PEP usage of direct endpoint calls
    getEnums = get_enums

    def get_events(self, enums: bool = False) -> dict[str, list]:
        """
        Get an object containing the events game data

        Args:
            enums: Boolean flag to indicate whether enum value should be converted in response. [Default is False]

        Returns:
            A single element dictionary containing a list of the events game data.
        """
        payload = {'payload': {}, 'enums': enums}
        return self._post(endpoint='getEvents', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getEvents = get_events

    def get_game_data(
            self,
            version: str = "",
            include_pve_units: bool = True,
            request_segment: int = 0,
            enums: bool = False,
            items: str = None,
            device_platform: str = "Android"
            ) -> dict:
        """
        Get game data

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
            game_version = self._get_game_version()
        else:
            game_version = version
        payload: dict[str, Any] = {
                "payload": {
                        "version": f"{game_version}",
                        "devicePlatform": device_platform,
                        "includePveUnits": include_pve_units,
                        },
                "enums": enums
                }

        if items:  # presence of 'items' argument overrides the 'request_segment' argument
            if isinstance(items, int) and str(abs(items)).isdigit():
                payload['payload']['items'] = str(items)
            else:
                payload['payload']['items'] = Constants.get(items) or "-1"
        else:
            if request_segment < 0 or request_segment > 4:
                raise SwgohComlinkValueError(
                        f'Invalid argument. <request_segment> should be an integer between 0 and 4, inclusive.'
                        )
            payload['payload']['requestSegment'] = request_segment

        return self._post(endpoint='data', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGameData = get_game_data

    def get_localization(self, id: str = None, locale: str = None, unzip: bool = False, enums: bool = False) -> dict:
        """
        Get localization data from game

        Args:
            id: latestLocalizationBundleVersion found in game metadata. This method will collect the latest language
                    version if the 'id' argument is not provided.
            locale: string Specify only a specific locale to retrieve [for example "ENG_US"]
            unzip: boolean [Defaults to False]
            enums: boolean [Defaults to False]

        Returns:
            A dictionary containing the localization data.
        """
        if not id:
            current_game_version = self.get_latest_game_data_version()
            id = current_game_version['language']

        if locale:
            id = id + ":" + locale.upper()

        payload = {'unzip': unzip, 'enums': enums, 'payload': {'id': id}}
        return self._post(endpoint='localization', payload=payload)

    # aliases for non PEP usage of direct endpoint calls
    getLocalization = get_localization
    getLocalizationBundle = get_localization
    get_localization_bundle = get_localization

    def get_game_metadata(self, client_specs: dict = None, enums: bool = False) -> dict:
        """
        Get the game metadata. Game metadata contains the current game and localization versions.

        Args:
            client_specs:  Optional dictionary containing
            enums: Boolean signifying whether enums in response should be translated to text. [Default: False]

        Returns:
            A dictionary containing the game metadata.

        Examples:

            client_specs_template = {
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

    def get_player(self, allycode: str | int = None, player_id: str = None, enums: bool = False) -> dict:
        """
        Get player information from game. Either allycode or player_id must be provided.

        Args:
            allycode: integer or string representing player allycode
            player_id: string representing player game ID
            enums: boolean [Defaults to False]

        Returns:
            A dictionary containing the player information.
        """
        payload = _get_player_payload(allycode=allycode, player_id=player_id, enums=enums)
        return self._post(endpoint='player', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getPlayer = get_player

    # Introduced in 1.12.0
    # Use decorator to alias the player_details_only parameter to 'playerDetailsOnly' to maintain backward compatibility
    # while fixing the original naming format mistake.
    @param_alias(param="player_details_only", alias='playerDetailsOnly')
    def get_player_arena(
            self, allycode: str | int = None, player_id: str = None, player_details_only: bool = False,
            enums: bool = False
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
        payload = _get_player_payload(allycode=allycode, player_id=player_id, enums=enums)
        payload['payload']['playerDetailsOnly'] = player_details_only
        return self._post(endpoint='playerArena', payload=payload)

    # alias to allow for get_arena() calls as a shortcut for get_player_arena() and non PEP variations
    get_arena = get_player_arena
    get_player_arena_profile = get_player_arena
    getPlayerArena = get_player_arena
    getPlayerArenaProfile = get_player_arena

    @param_alias(param="include_recent_guild_activity_info", alias="includeRecent")
    def get_guild(self, guild_id: str, include_recent_guild_activity_info: bool = False, enums: bool = False) -> dict:
        """
        Get guild information for a specific Guild ID.

        Args:
            guild_id: String ID of guild to retrieve. Guild ID can be found in the output
                        of the get_player() call. (Required)
            include_recent_guild_activity_info: boolean [Default: False] (Optional)
            enums: Should enums in response be translated to text. [Default: False] (Optional)

        Returns:
            A dictionary containing the guild information.
        """
        payload = {
                "payload": {"guildId": guild_id, "includeRecentGuildActivityInfo": include_recent_guild_activity_info},
                "enums": enums
                }
        guild = self._post(endpoint='guild', payload=payload)
        if 'guild' in guild.keys():
            guild = guild['guild']
        return guild

    # alias for non PEP usage of direct endpoint calls
    getGuild = get_guild

    def get_guilds_by_name(self, name: str, start_index: int = 0, count: int = 10, enums: bool = False) -> dict:
        """
        Search for guild by name and return match.

        Args:
            name: string for guild name search
            start_index: integer representing where in the resulting list of guild name matches
                            the return object should begin
            count: integer representing the maximum number of matches to return, [Default: 10]
            enums: Whether to translate enums in response to text, [Default: False]

        Returns:
            A dictionary containing the guild search results.
        """
        payload = {
                "payload": {"name": name, "filterType": 4, "startIndex": start_index, "count": count},
                "enums": enums
                }
        return self._post(endpoint='getGuilds', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGuildByName = get_guilds_by_name

    def get_guilds_by_criteria(
            self, search_criteria: dict, start_index: int = 0, count: int = 10,
            enums: bool = False
            ) -> dict:
        """
        Search for guild by guild criteria and return matches.

        Args:
            search_criteria: Dictionary

            start_index: integer representing where in the resulting list of guild name matches the return object
                            should begin
            count: integer representing the maximum number of matches to return
            enums: Whether to translate enum values to text [Default: False]

        Returns:
            A dictionary containing the guild search results.

        Examples:
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
                        "searchCriteria": search_criteria, "filterType": 5, "startIndex": start_index,
                        "count": count
                        }, "enums": enums
                }
        return self._post(endpoint='getGuilds', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGuildByCriteria = get_guilds_by_criteria

    def get_leaderboard(
            self, leaderboard_type: int, *, league: int | str = None, division: int | str = None,
            event_instance_id: str = None, group_id: str = None, enums: bool = False
            ) -> dict:
        """
        Retrieve Grand Arena Championship leaderboard information.

        Args:
            leaderboard_type (int): Type 4 is for scanning gac brackets, and only returns results while an event
                is active.
                    When type 4 is indicated, the "league" and "division" arguments must also be provided.

                                    Type 6 is for the global leaderboards for the league + divisions.
                    When type 6 is indicated, the "event_instance_id" and "group_id" must also be provided.

            league (int|str): Enum values 20, 40, 60, 80, and 100 correspond to carbonite, bronzium, chromium, aurodium,
                       and kyber respectively. Also accepts string values for each league.

            division (int|str): Enum values 5, 10, 15, 20, and 25 correspond to divisions 5 through 1 respectively.
                         Also accepts string or int values for each division.

            event_instance_id (str): When leaderboard_type 4 is indicated, a combination of the event Id and
                the instance ID separated by ':'
                                Example: CHAMPIONSHIPS_GRAND_ARENA_GA2_EVENT_SEASON_36:O1675202400000

            group_id (str): When leaderboard_type 4 is indicated, must start with the same eventInstanceId, followed
                         by the league and bracketId, separated by ':'. The number at the end is the bracketId, and
                         goes from 0 to N, where N is the last group of 8 players.
                            Example: CHAMPIONSHIPS_GRAND_ARENA_GA2_EVENT_SEASON_36:O1675202400000:CARBONITE:10431

            enums (bool): Whether to translate enum values to text [Default: False]

        Returns:
            dict: A dictionary containing the leaderboard data.
        """
        leagues = {'kyber': 100, 'aurodium': 80, 'chromium': 60, 'bronzium': 40, 'carbonite': 20}
        divisions = {'1': 25, '2': 20, '3': 15, '4': 10, '5': 5}
        # Translate parameters if needed
        if isinstance(league, str):
            league = leagues[league.lower()]
        if isinstance(division, int) and len(str(division)) == 1:
            division = divisions[str(division).lower()]
        if isinstance(division, str):
            division = divisions[division.lower()]
        payload: dict[str, Any] = {"payload": {"leaderboardType": leaderboard_type, }, "enums": enums}
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
        Fetches the guild leaderboard data for given leaderboard ID.

        This function interacts with an external API to retrieve the leaderboard
        data for the supplied guild leaderboard ID. The user can specify the
        number of entries to fetch.

        Parameters:
            leaderboard_id: list
                A list containing one leaderboard ID dictionary for the data to be fetched.
            count: int, optional
                The number of leaderboard entries to retrieve. Defaults to 200.
            enums: bool, optional
                Whether or not to translate enum values. Defaults to False.

        Returns:
                A dictionary containing the guild leaderboard data.
        """
        payload = dict(payload={'leaderboardId': leaderboard_id, 'count': count}, enums=enums)
        return self._post(endpoint='getGuildLeaderboard', payload=payload)

    # alias for non PEP usage of direct endpoint calls
    getGuildLeaderboard = get_guild_leaderboard

    def get_name_spaces(self, only_compatible: bool = False, enums: bool = False) -> dict:
        """
                    *** (PLACEHOLDER) - Actual use is unknown at this time ***
        Fetches namespaces based on the specified filter criteria.

        Args:
            only_compatible (bool): Determines whether to fetch only compatible namespaces.
            enums (bool): Specifies whether enum types should be included in the response.

        Returns:
            dict: A dictionary containing the information about the retrieved namespaces.
        """
        payload = {'payload': {'onlyCompatible': only_compatible}, 'enums': enums}
        return self._post(endpoint='getNameSpaces', payload=payload)

    def get_segmented_content(
            self, content_name_space: str = "current", accept_language: str = "ENG_US",
            enums: bool = False
            ) -> dict:
        """
                     *** (PLACEHOLDER) - Actual use is unknown at this time ***
        Retrieves segmented content from a specified namespace with the option to localize content
        based on the provided language preference and control the inclusion of enumerations.

        Args:
            content_name_space (str): The namespace from which the content is to be retrieved.
                Defaults to "current".
            accept_language (str): The language in which the content should be localized. Defaults
                to "ENG_US".
            enums (bool): Specifies whether enumerations should be included in the response.
                Defaults to False.

        Returns:
            dict: A dictionary containing the segmented content retrieved based on the input
            parameters.
        """
        payload = {
                'payload': {
                        'contentNameSpace': content_name_space,
                        'acceptLanguage': accept_language
                        },
                'enums': enums
                }
        return self._post(endpoint='getSegmentedContent', payload=payload)


    """
    Helper methods are below
    """

    # Get the latest game data and language bundle versions
    def get_latest_game_data_version(self) -> dict:
        """
        Retrieves the latest game data and language version information.

        This method fetches metadata and extracts the most recent versions for the
        game data and localization bundle.

        Returns:
            dict: A dictionary containing the latest versions for 'game' and
            'language'. The 'game' key refers to the latestGamedataVersion, and
            the 'language' key refers to the latestLocalizationBundleVersion.
        """
        current_metadata = self.get_metadata()
        return {
                'game': current_metadata['latestGamedataVersion'],
                'language': current_metadata['latestLocalizationBundleVersion']
                }

    # alias for shorthand call
    getVersion = get_latest_game_data_version
