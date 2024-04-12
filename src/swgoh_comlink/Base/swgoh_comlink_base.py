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

import swgoh_comlink.utils as utils
from swgoh_comlink.constants import (
    get_logger,
    LANGUAGES,
    MISSING,
    MutualExclusiveRequired,
    MutualRequiredNotSet,
    NotGiven,
    NotSet,
    OPTIONAL,
    REQUIRED,
    SET,
    LEAGUES,
    DIVISIONS
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

    __access_key: str | Sentinel
    __secret_key: str | Sentinel
    DEFAULT_HOST: str = "localhost"
    DEFAULT_PROTOCOL: str = "http"
    DEFAULT_PORT: int = 3000
    DEFAULT_STATS_PORT: int = 3223
    hmac: bool = False

    ALLOWED_PROTOCOLS: tuple[str, str, ...] = ("http", "https",)
    MINIMUM_PORT_VALUE = 1024
    MAXIMUM_PORT_VALUE = 65535

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
            host: str | Sentinel = OPTIONAL,
            protocol: str | Sentinel = OPTIONAL,
            port: int | Sentinel = OPTIONAL,
            stats_port: int | Sentinel = OPTIONAL,
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
        # self.logger = utils.default_logger
        self.logger.debug("Initializing SwgohComlinkBase")
        self.logger.debug(f"Logger is {self.logger}")

        self.url_base = url
        self.logger.debug("Initial url_base= %s" % self.url_base)

        self.stats_url_base = stats_url
        self.logger.debug("Initial stats_url_base= %s" % self.stats_url_base)

        def verify_port(input_port: int | str | Sentinel) -> None:
            port_name = self._get_var_name(input_port)
            self.logger.debug(f"{port_name} is not NotSet: {input_port is not NotSet}")
            self.logger.debug(f"{port_name} ({type(input_port)}) = {input_port}")

            if input_port is not NotSet and not isinstance(input_port, int):
                err_msg = (f"{_get_function_name()}: '{port_name}' must be an integer between "
                           f"{self.MINIMUM_PORT_VALUE} and {self.MAXIMUM_PORT_VALUE} or not provided. "
                           f"[type={type(port)}, should be <int>]")
                self.logger.error(err_msg)
                raise ValueError(err_msg)

            if input_port is not NotSet and not (self.MINIMUM_PORT_VALUE <= input_port <= self.MAXIMUM_PORT_VALUE):
                err_msg = (f"'{port_name}' is between {self.MINIMUM_PORT_VALUE} and "
                           f"{self.MAXIMUM_PORT_VALUE}: "
                           f"{not (self.MINIMUM_PORT_VALUE <= input_port <= self.MAXIMUM_PORT_VALUE)}"
                           )
                self.logger.debug(err_msg)
                raise ValueError(
                    f"'{port_name}' must be between {self.MINIMUM_PORT_VALUE} and {self.MAXIMUM_PORT_VALUE}.")

        for param in [port, stats_port]:
            verify_port(param)

        # host and port parameters override defaults
        if not all(map(lambda list_item: list_item is NotSet, [host, port, protocol, stats_port])):
            com_host = host
            if protocol is not OPTIONAL and protocol.lower() not in self.ALLOWED_PROTOCOLS:
                err_msg = f"{_get_function_name()}: 'protocol' argument must be one of {self.ALLOWED_PROTOCOLS}"
                self.logger.error(err_msg)
                raise ValueError(err_msg)
            com_proto = protocol
            com_port = port
            com_stats_port = stats_port

            if host is NotSet:
                com_host = self.DEFAULT_HOST

            if port is NotSet:
                com_port = self.DEFAULT_PORT

            if protocol is NotSet:
                com_proto = self.DEFAULT_PROTOCOL

            if stats_port is NotSet:
                com_stats_port = self.DEFAULT_STATS_PORT

            self.url_base = self.construct_url_base(com_proto, com_host, com_port)
            self.logger.debug("Updated url_base= %s" % self.url_base)

            self.stats_url_base = self.construct_url_base(com_proto, com_host, com_stats_port)
            self.logger.debug("Updated stats_url_base= %s" % self.stats_url_base)

        # Use values passed from client first, otherwise check for environment variables
        if access_key is not OPTIONAL:
            self.__access_key = access_key
        elif "ACCESS_KEY" in os.environ.keys():
            self.logger.debug(f"{_get_function_name()}: 'ACCESS_KEY' found in environment variable.")
            self.__access_key = os.getenv("ACCESS_KEY", "")
            self.logger.debug(f"{_get_function_name()}: 'ACCESS_KEY' has been set to {self.__access_key!r}.")
        else:
            self.__access_key = NotSet

        if secret_key is not OPTIONAL:
            self.__secret_key = secret_key
        elif "SECRET_KEY" in os.environ.keys():
            self.logger.debug(f"{_get_function_name()}: 'SECRET_KEY' found in environment variable.")
            self.__secret_key = os.getenv("SECRET_KEY", "")
        else:
            self.__secret_key = NotSet

        self.hmac = False if self.__access_key is NotSet and self.__secret_key is NotSet else True

        self.logger.debug("Final url_base= %s" % self.url_base)
        self.logger.debug("Final stats_url_base= %s" % self.stats_url_base)
        self.logger.debug("hmac = %s" % self.hmac)

    @property
    def access_key(self) -> str:
        return self.__access_key

    @property
    def secret_key(self) -> str:
        return "<HIDDEN>"

    @property
    def instance_type(self) -> str:
        return str(self.__class__).replace("<class ", "").replace(">", "").replace("'", "")

    @property
    def is_async(self) -> bool:
        if self.instance_type == 'SwgohComlinkAsync':
            return True
        else:
            return False

    @staticmethod
    def _get_function_name() -> str:
        """Return the name for the calling function"""
        return f"{inspect.stack()[1].function}()"

    @staticmethod
    def _get_var_name(var) -> str:
        """Return the name of the requested variable as a string"""
        for fi in reversed(inspect.stack()):
            names = [var_name for var_name, var_val in fi.frame.f_locals.items() if var_val is var]
            if len(names) > 0:
                return names[0]

    @staticmethod
    def _update_hmac_obj(hmac_obj: HMAC | Sentinel = REQUIRED, values: list[str] | Sentinel = REQUIRED) -> HMAC:
        """Add encoded values to hmac object

        Args:
            hmac_obj (HMAC): An HMAC object to be updated
            values (list[str]): List of stings to add to the HMAC object

        Returns:
            The updated HMAC object

        """
        if hmac_obj is MISSING or values is MISSING:
            raise ValueError(f"{_get_function_name()}: Both 'hmac_obj' and 'values' arguments are required.")

        if not isinstance(hmac_obj, HMAC):
            raise ValueError(f"{_get_function_name()}: 'hmac_obj' argument must be type <HMAC>")

        if not isinstance(values, list):
            raise ValueError(f"{_get_function_name()}: 'values' argument must be type <list>")

        for value in values:
            hmac_obj.update(value.encode())
        return hmac_obj

    @staticmethod
    def _construct_unit_stats_query_string(flags: list[str] | Sentinel = OPTIONAL,
                                           language: str = "eng_us") -> str | None:
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

        if language not in LANGUAGES:
            language = "eng_us"

        language_string = f"language={language}"

        if not isinstance(flags, list) and flags is not OPTIONAL:
            raise ValueError(f"{_get_function_name()}, Invalid flags '{flags}', must be type list of strings.")

        if flags is NotSet:
            flags = []
        tmp_flags: set = set(sorted(list(dict.fromkeys(flags))))
        flag_string = (
            f'flags={",".join(sorted(tmp_flags.intersection(allowed_flags)))}'
            if flags
            else str()
        )
        constructed_string = "&".join(filter(None, [flag_string, language_string]))
        return f"?{constructed_string}"

    def construct_url_base(self, protocol: str, host: str, port: int) -> str:
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
        if protocol not in self.ALLOWED_PROTOCOLS:
            err_msg = f"Protocol must be http or https."
            self.logger.debug(err_msg)
            raise ValueError(err_msg)

        if not self.MAXIMUM_PORT_VALUE >= port >= self.MINIMUM_PORT_VALUE:
            err_msg = f"Port number must be between {self.MINIMUM_PORT_VALUE} and {self.MAXIMUM_PORT_VALUE}."
            self.logger.debug(err_msg)
            raise ValueError(err_msg)

        return f"{protocol}://{host}:{port}"

    @staticmethod
    def _get_player_payload(
            allycode: str | int | Sentinel = MutualExclusiveRequired,
            player_id: str | Sentinel = MutualExclusiveRequired,
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
        if allycode is MutualRequiredNotSet and player_id is MutualRequiredNotSet:
            err_msg = f"{_get_function_name()}: Either allycode or player_id must be provided."
            get_logger(default_logger=True).debug(err_msg)
            raise ValueError(err_msg)

        if not isinstance(allycode, Sentinel) and not isinstance(player_id, Sentinel):
            err_msg = f"{_get_function_name()}: Only one of allycode or player_id can be provided."
            get_logger(default_logger=True).debug(err_msg)
            raise ValueError(err_msg)

        payload: dict[str, Any] = {"payload": {}, "enums": enums}

        if isinstance(allycode, int) or isinstance(allycode, str):
            allycode = utils.sanitize_allycode(allycode)
            payload["payload"]["allyCode"] = allycode
        else:
            payload["payload"]["playerId"] = player_id

        if include_player_details_flag:
            payload["payload"]["playerDetailsOnly"] = player_details_only
        return payload

    @staticmethod
    def _make_client_specs(
            client_specs: dict | Sentinel = OPTIONAL, enums: bool = False
    ) -> dict:
        """Create client_spec dictionary for get_metadata() method"""
        get_logger().debug(f"{_get_function_name()}, client_specs={client_specs}, enums={enums}")
        payload = {"payload": {}, "enums": enums}
        if isinstance(client_specs, dict):
            payload["payload"]["clientSpecs"] = client_specs
        get_logger().debug(f"{_get_function_name()}, payload={payload}")
        return payload

    @staticmethod
    def _make_game_data_payload(
            version: str | Sentinel = OPTIONAL,
            include_pve_units: bool = False,
            request_segment: int = 0,
            enums: bool = False,
    ) -> dict:
        """Create game_data payload object and return"""
        if version is NotSet:
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
            guild_id: str | Sentinel = REQUIRED, include_recent_activity: bool = False, enums: bool = False
    ) -> dict:
        """Create get_guild() method payload object"""
        if guild_id is REQUIRED and guild_id is not SET:
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
            guild_name: str | Sentinel = REQUIRED, index: int = 0, count: int = 10, enums: bool = False
    ) -> dict:
        """Create get_builds_by_name() method payload object"""
        if guild_name is REQUIRED and guild_name is not SET:
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
            criteria: dict | Sentinel = REQUIRED, index: int = 0, count: int = 10, enums: bool = False
    ) -> dict:
        """Create get_builds_by_name() method payload object"""
        if criteria is REQUIRED and criteria is not SET:
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
            lb_type: int | Sentinel = REQUIRED,
            league: int | str | Sentinel = NotGiven,
            division: int | str | Sentinel = NotGiven,
            event_instance_id: str | Sentinel = NotGiven,
            group_id: str | Sentinel = NotGiven,
            enums: bool = False,
    ) -> dict:
        """Create get_leaderboards() method payload"""
        if lb_type is REQUIRED and lb_type is not SET:
            raise ValueError(f"{_get_function_name()}, 'lb_type' must be provided.")

        if lb_type not in (4, 6):
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
            if ((event_instance_id is NotGiven and event_instance_id is not SET) or
                    not isinstance(event_instance_id, str)):
                raise ValueError(f"{_get_function_name()}, 'event_instance_id' string must be provided.")

            if (group_id is NotGiven and group_id is not SET) or not isinstance(group_id, str):
                raise ValueError(f"{_get_function_name()}, 'group_id' string must be provided.")
            payload["payload"]["eventInstanceId"] = event_instance_id
            payload["payload"]["groupId"] = group_id
        elif lb_type == 6:
            if league is NotGiven and league is not SET:
                raise ValueError(f"{_get_function_name()}, 'league' must be provided.")
            if division is NotGiven and division is not SET:
                raise ValueError(f"{_get_function_name()}, 'division' must be provided.")

            league = utils.convert_league_to_int(league) if isinstance(league, str) else league
            if league not in LEAGUES.values():
                raise ValueError(f"{_get_function_name()}: Invalid league {league}.")

            division = utils.convert_divisions_to_int(division) if isinstance(division, str) else division
            if division not in DIVISIONS.values():
                raise ValueError(f"{_get_function_name()}: Invalid division {division}.")

            payload["payload"]["league"] = league
            payload["payload"]["division"] = division
        return payload

    @staticmethod
    def _make_get_guild_leaderboard_payload(
            lb_id: list | Sentinel = REQUIRED, count: int = 5, enums: bool = False
    ) -> dict:
        """Create get_guild_leaderboards() method payload"""
        if lb_id is MISSING or not isinstance(lb_id, list):
            err_msg = f"{_get_function_name()}: 'leaderboard_id' argument is required as type <list>."
            get_logger().error(err_msg)
            raise ValueError(err_msg)
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

            hmac_obj = hmac.new(key=self.__secret_key.encode(), digestmod=hashlib.sha256)
            hmac_obj = self._update_hmac_obj(
                hmac_obj, [req_time, "POST", f"/{endpoint}", payload_hash_digest]
            )

            hmac_digest = hmac_obj.hexdigest()
            headers["Authorization"] = (
                f"HMAC-SHA256 Credential={self.__access_key},Signature={hmac_digest}"
            )
        return headers
