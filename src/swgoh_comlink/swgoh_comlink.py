"""
Python 3 interface library for swgoh-comlink (https://github.com/swgoh-utils/swgoh-comlink)
"""

__version__ = '1.1.6'

from json import loads, dumps
import requests
import hmac
import hashlib
import os
import time

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

    def __init__(self, url="http://localhost:3000",
                 access_key=None,
                 secret_key=None,
                 stats_url="http://localhost:3223"):
        """
        Set initial values when new class instance is created
        :param url: The URL where swgoh-comlink is running. Defaults to 'http://localhost:3000'
        :param access_key: The HMAC public key. Default to None which indicates HMAC is not used.
        :param secret_key: The HMAC private key. Default to None which indicates HMAC is not used.
        :param stats_url: the url of the swgoh-stats service, such as http://localhost:3223
        """
        self.url_base = url
        self.stats_url_base = stats_url
        self.hmac = False # HMAC use disabled by default
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

    def _post(self, endpoint, payload):
        """
        Execute HTTP POST operation against swgoh-comlink
        :param payload: POST payload json data
        :return: json
        """
        # print(f'   ### [POST DEBUG] ### Received payload: {payload}, type: {type(payload)}')
        post_url = self.url_base + f'/{endpoint}'
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
                # print('   ### [PAYLOAD DEBUG] ### dumping JSON string')
                payload_string = dumps(payload, separators=(',', ':'))
            else:
                # print('   ### [PAYLOAD DEBUG] ### dumping regular string')
                payload_string = dumps({})
            # print(f'   ### [DEBUG] ### payload_string: {payload_string}')
            payload_hash_digest = hashlib.md5(payload_string.encode()).hexdigest()
            # print(f'   ### [DEBUG] ### payload MD5: {payload_hash_digest}')
            hmac_obj.update(payload_hash_digest.encode())
            hmac_digest = hmac_obj.hexdigest()
            req_headers['Authorization'] = f'HMAC-SHA256 Credential={self.access_key},Signature={hmac_digest}'
            # print(f'   ### [DEBUG] ### Auth Header: HMAC-SHA256 Credential={self.access_key},Signature={hmac_digest}')
        try:
            r = requests.request('POST', post_url, json=payload, headers=req_headers)
            return loads(r.content.decode('utf-8'))
        except Exception as e:
            raise e

    def get_enums(self):
        """
        Get an object containing the game data enums
        :return: json
        """
        url = self.url_base + '/enums'
        try:
            r = requests.request('GET', url)
            return loads(r.content.decode('utf-8'))
        except Exception as e:
            raise e

    def get_game_data(self, version="", include_pve_units=True, request_segment=0, enums=False):
        """
        Get game data
        :param version: string (found in metadata key value 'latestGamedataVersion')
        :param include_pve_units: boolean [Defaults to True]
        :param request_segment: integer >=0 [Defaults to 0]
        :param enums: boolean [Defaults to False]
        :return: json
        """
        payload = {
            "payload": {
                "version": f"{version}",
                "includePveUnits": include_pve_units,
                "requestSegment": request_segment
            },
            "enums": enums
        }
        # print(f'   ### [GAME DATA DEBUG] ### Sending payload: {payload}')
        return self._post('data', payload)

    def get_localization(self, id=None, unzip=False, enums=False):
        """
        Get localization data from game
        :param id: string (found in metadata key value 'latestLocalizationBundleVersion')
        :param unzip: boolean [Defaults to False]
        :param enums: boolean [Defaults to False]
        :return: json
        """
        payload = {}
        payload['unzip'] = unzip
        payload['enums'] = enums
        payload['payload'] = {}
        payload['payload']['id'] = id
        return self._post('localization', payload)

    def get_game_metadata(self):
        """
        Get the game metadata
        :return: json
        """
        return self._post('metadata', {})

    def get_player(self, allycode=None, player_id=None, enums=False):
        """
        Get player information from game
        :param allycode: integer
        :param player_id: player game ID
        :param enums: boolean [Defaults to False]
        :return: json
        """
        payload = _get_player_payload(allycode=allycode, player_id=player_id, enums=enums)
        return self._post('player', payload)

    def get_player_arena(self, allycode=None, player_id=None, enums=False):
        """
        Get player arena information from game
        :param allycode: integer
        :param player_id: player game ID
        :param enums: boolean [Defaults to False]
        :return: json
        """
        payload = _get_player_payload(allycode=allycode, player_id=player_id, enums=enums)
        return self._post('playerArena', payload)

    # alias to allow for get_arena() calls as a shortcut for get_player_arena()
    get_arena = get_player_arena
