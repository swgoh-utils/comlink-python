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

from sentinels import Sentinel

from swgoh_comlink.constants import get_logger, OPTIONAL, NotGiven
from swgoh_comlink.utils import (
    sanitize_allycode,
    convert_league_to_int,
    convert_divisions_to_int,
)

__all__ = ["SwgohComlinkBase"]


def _get_function_name() -> str:
    """Return the name for the calling function"""
    return f"{inspect.stack()[1].function}()"


class SwgohComlinkBase:
    """Base class for comlink-python interface and supported methods.

    This base class is meant to be inherited by extension classes for actual method definitions
    using synchronous and asynchronous interfaces.

    """

    url: str
    stats_url: str
    access_key: str | Sentinel
    secret_key: str | Sentinel
    host: str = "localhost"
    protocol: str = "http"
    port: int = 3000
    stats_port: int = 3223
    default_logger: bool = False
    hmac: bool = False

    def __new__(cls, *args, **kwargs):
        """Prevent instances of this base class from being created directly"""
        if cls is SwgohComlinkBase:
            raise TypeError(f"Only children of '{cls.__name__}' may be instantiated.")
        return object.__new__(cls)

    def __init__(
            self,
            url: str = "http://localhost:3000",
            stats_url: str = "http://localhost:3223",
            access_key: str | Sentinel = OPTIONAL,
            secret_key: str | Sentinel = OPTIONAL,
            host: str = "localhost",
            protocol: str = "http",
            port: int = 3000,
            stats_port: int = 3223,
            default_logger_enabled: bool = False,
    ):
        """
        Set initial values when new class instance is created

        Args:
            url (str): The URL where swgoh-comlink is running.
            stats_url (str): The url of the swgoh-stats service (if used), such as 'http://localhost:3223'
            access_key (str): The HMAC public key. Default to None which indicates HMAC is not used.
            secret_key (str): The HMAC private key. Default to None which indicates HMAC is not used.
            protocol (str): The protocol to use for connecting to comlink. Typically, http or https.
            host (str): IP address or DNS name of server where the swgoh-comlink service is running
            port (int): TCP port number between 1024 and 65535 where the swgoh-comlink service is running.
            stats_port (int): TCP port number between 1024 and 65535 where the comlink-stats service is running.
            default_logger_enabled (bool): Flag to enable default logging. Should only be used if testing.

        Note:
            'url' and 'stat_url' are mutually exclusive of the protocol/host/port/stats_port parameters.
                Either of the options should be chosen but not both.

        """

        self.logger = get_logger(default_logger=default_logger_enabled)

        if not url:
            self.url_base = self.DEFAULT_URL
            self.logger.warning(f"No URL provided. Using {self.url_base}")
        else:
            self.url_base = url
            self.logger.debug("url_base= %s" % self.url_base)
        if not stats_url:
            self.stats_url_base = self.DEFAULT_STATS_URL
            self.logger.warning(f"No stats URL provided. Using {self.stats_url_base}")
        else:
            self.stats_url_base = stats_url
            self.logger.debug("stats_url_base= %s" % self.stats_url_base)

        # host and port parameters override defaults
        if host:
            self.url_base = self.construct_url_base(protocol, host, port)
            self.logger.debug("url_base= %s" % self.url_base)
            self.stats_url_base = self.construct_url_base(protocol, host, stats_port)
            self.logger.debug("stats_url_base= %s" % self.stats_url_base)

        # Use values passed from client first, otherwise check for environment variables
        if access_key:
            self.access_key = access_key
        elif "ACCESS_KEY" in os.environ.keys():
            self.access_key = os.getenv("ACCESS_KEY", "")
        else:
            self.access_key = NotGiven

        if secret_key:
            self.secret_key = secret_key
        elif "SECRET_KEY" in os.environ.keys():
            self.secret_key = os.getenv("SECRET_KEY", "")
        else:
            self.secret_key = NotGiven

        self.hmac = False if self.access_key is NotGiven and self.secret_key is NotGiven else True

        self.logger.debug("url_base= %s" % self.url_base)
        self.logger.debug("stats_url_base= %s" % self.stats_url_base)
        self.logger.debug("hmac= %s" % self.hmac)

    @staticmethod
    def _update_hmac_obj(hmac_obj: HMAC, values: list[str]) -> HMAC:
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
    def _construct_unit_stats_query_string(flags: list[str], language: str = "eng_us") -> str | None:
        """Constructs query string from provided flags and language to be used with the get_unit_stats() function

        Args:
            flags: List of strings indicating the flags to enable for the unit_stats function call
            language: Language of the localization to use for returned data

        Returns:
            The query string portion of a URL

        """

        allowed_flags: set = set(
            sorted(
                [
                    "gameStyle",
                    "calcGP",
                    "onlyGP",
                    "withoutModCalc",
                    "percentVals",
                    "useMax",
                    "scaled",
                    "unscaled",
                    "statIDs",
                    "enums",
                    "noSpace",
                ]
            )
        )
        language_string = f"language={language}" if language else None
        if flags:
            if not isinstance(flags, list):
                raise ValueError(
                    f"{_get_function_name()}, Invalid flags '{flags}', must be type list of strings."
                )
            tmp_flags: set = set(sorted(list(dict.fromkeys(flags))))
            flag_string = (
                f'flags={",".join(sorted(tmp_flags.intersection(allowed_flags)))}'
                if flags
                else str()
            )
            constructed_string = "&".join(filter(None, [flag_string, language_string]))
            return f"?{constructed_string}"
        else:
            return None

    @staticmethod
    def construct_url_base(protocol: str, host: str, port: int) -> str:
        """Construct a URL base string from protocol, host and port inputs

        Args:
            protocol: http or https protocol
            host: host address
            port: port number

        Returns:
            URL string

        Raises:
            ValueError: If protocol is not 'http' or 'https' or port is not between 1024 and 65535.

        """
        if protocol not in ["http", "https"]:
            raise ValueError(f"Protocol must be http or https.")
        if 65535 < port < 1024:
            raise ValueError(f"Port number must be between 1024 and 65535.")
        return f"{protocol}://{host}:{port}"

    DEFAULT_URL: str = construct_url_base(host=host, port=port, protocol=protocol)
    # str: The URL of the swgoh-comlink service. Defaults to http://localhost:3000

    DEFAULT_STATS_URL: str = construct_url_base(
        host=host, port=stats_port, protocol=protocol
    )

    # str: The URL of the swgoh-stats service. Defaults to http://localhost:3223

    @staticmethod
    def _get_player_payload(
            allycode: str | int | Sentinel = OPTIONAL,
            player_id: str | Sentinel = OPTIONAL,
            enums: bool = False,
            include_player_details_flag: bool = False,
            player_details_only: bool = False,
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
        if allycode is NotGiven and player_id is NotGiven:
            raise ValueError("Either allycode or player_id must be provided.")
        if isinstance(allycode, int):
            allycode = str(allycode)
        if isinstance(allycode, str) and allycode != "" and isinstance(player_id, str) and player_id != "":
            raise ValueError("Only one of allycode or player_id can be provided.")
        payload: dict[str, Any] = {"payload": {}, "enums": enums}
        if allycode is not OPTIONAL and (isinstance(allycode, int) or isinstance(allycode, str)):
            allycode = sanitize_allycode(allycode)
            payload["payload"]["allyCode"] = allycode
        else:
            payload["payload"]["playerId"] = player_id
        if enums:
            payload["enums"] = True
        if include_player_details_flag:
            payload["payload"]["playerDetailsOnly"] = player_details_only
        return payload

    @staticmethod
    def _make_client_specs(
            client_specs: dict | Sentinel = OPTIONAL, enums: bool = False
    ) -> dict:
        """Create client_spec dictionary for get_metadata() method"""
        payload = {}
        if client_specs:
            payload = {"payload": {"clientSpecs": client_specs}, "enums": enums}
        return payload

    @staticmethod
    def _make_game_data_payload(
            version: str | Sentinel = OPTIONAL,
            include_pve_units: bool = False,
            request_segment: int = 0,
            enums: bool = False,
    ) -> dict:
        """Create game_data payload object and return"""
        if version is NotGiven:
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
    def _make_guild_payload(
            guild_id: str | Sentinel = OPTIONAL, include_recent_activity: bool = False, enums: bool = False
    ) -> dict:
        """Create get_guild() method payload object"""
        if guild_id is NotGiven:
            raise ValueError(f"{_get_function_name()}, 'guild_id' must be provided.")

        return {
            "payload": {
                "guildId": guild_id,
                "includeRecentGuildActivityInfo": include_recent_activity,
            },
            "enums": enums,
        }

    @staticmethod
    def _make_guilds_by_name_payload(
            guild_name: str | Sentinel = OPTIONAL, index: int = 0, count: int = 10, enums: bool = False
    ) -> dict:
        """Create get_builds_by_name() method payload object"""
        if guild_name is NotGiven:
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
    def _make_guilds_by_criteria_payload(
            criteria: dict, index: int = 0, count: int = 10, enums: bool = False
    ) -> dict:
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
    def _make_get_leaderboards_payload(
            lb_type: int = 0,
            league: int | str | Sentinel = OPTIONAL,
            division: int | str | Sentinel = OPTIONAL,
            event_instance_id: str | Sentinel = OPTIONAL,
            group_id: str | Sentinel = OPTIONAL,
            enums: bool = False,
    ) -> dict:
        """Create get_leaderboards() method payload"""
        if lb_type != 4 and lb_type != 6:
            raise ValueError(
                f"{_get_function_name()}, 'leaderboard_type' must be either 4 (GAC brackets) or 6 (Global "
                f"Leaderboards"
            )

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
            league = convert_league_to_int(league) if isinstance(league, str) else league
            division = convert_divisions_to_int(division) if isinstance(division, str) else division
            payload["payload"]["league"] = league
            payload["payload"]["division"] = division
        return payload

    @staticmethod
    def _make_get_guild_leaderboard_payload(
            lb_id: list, count: int, enums: bool = False
    ) -> dict:
        """Create get_guild_leaderboards() method payload"""
        if not isinstance(lb_id, list):
            raise ValueError(
                f"{_get_function_name()}, leaderboard_id argument should be type list not {type(lb_id)}."
            )
        return {"payload": {"leaderboardId": lb_id, "count": count}, "enums": enums}

    def _construct_request_headers(
            self, endpoint: str, payload: dict | list[dict]
    ) -> dict:
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
            hmac_obj = self._update_hmac_obj(
                hmac_obj, [req_time, "POST", f"/{endpoint}", payload_hash_digest]
            )

            hmac_digest = hmac_obj.hexdigest()
            headers["Authorization"] = (
                f"HMAC-SHA256 Credential={self.access_key},Signature={hmac_digest}"
            )
        return headers

    @staticmethod
    def _get_function_name() -> str:
        """Return the name for the calling function"""
        return f"{inspect.stack()[1].function}()"
