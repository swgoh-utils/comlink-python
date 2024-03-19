# coding=utf-8
"""
Base definitions for the core swgoh_comlink module
"""
from __future__ import annotations, absolute_import, print_function

import hashlib
import hmac
import os
import time
from hmac import HMAC
from json import dumps

import swgoh_comlink.const as Constants
import swgoh_comlink.utils as utils
from swgoh_comlink.const import DEFAULT_LOGGER_ENABLED, get_logger, HMAC_ENABLED, LOGGER
from swgoh_comlink.int.helpers import get_function_name

logger = LOGGER


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
    default_logger: bool = DEFAULT_LOGGER_ENABLED
    hmac: bool = HMAC_ENABLED

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
            allycode = utils.sanitize_allycode(allycode)
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
            raise ValueError(f"{get_function_name()}, 'guild_id' must be provided.")

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
            raise ValueError(f"{get_function_name()}, 'guild_name' must be provided.")

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
            raise ValueError(f"{get_function_name()}, 'criteria' must be provided.")

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
        if lb_type != 4 or lb_type != 6:
            raise ValueError(f"{get_function_name()}, 'leaderboard_type' must be either 4 (GAC brackets) or 6 (Global "
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
            league = utils.convert_league_to_int(league)
            division = utils.convert_divisions_to_int(division)
            payload["payload"]["league"] = league
            payload["payload"]["division"] = division
        return payload

    @staticmethod
    def make_get_guild_leaderboard_payload(lb_id: list, count: int, enums: bool = False) -> dict:
        """Create get_guild_leaderboards() method payload"""
        if not isinstance(lb_id, list):
            raise ValueError(
                f"{get_function_name()}, leaderboard_id argument should be type list not {type(lb_id)}."
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

        if default_logger:
            Constants.DEFAULT_LOGGER_ENABLED = True
            global logger
            logger = get_logger()
        else:
            logger = LOGGER

        if not url:
            self.url_base = self.DEFAULT_URL
            logger.info(f"No URL provided. Using {self.url_base}")
        else:
            self.url_base = url
        if not stats_url:
            self.stats_url_base = self.DEFAULT_STATS_URL
            logger.info(f"No stats URL provided. Using {self.stats_url_base}")
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

        logger.info(f"{self.url_base=}")
        logger.info(f"{self.stats_url_base=}")

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
