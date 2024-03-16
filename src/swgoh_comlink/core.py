# coding=utf-8
"""
Base definitions for the core swgoh_comlink module
"""
from __future__ import annotations, absolute_import, print_function

import hashlib
import hmac
import logging
import os
import time
from hmac import HMAC
from json import dumps
from typing import Union

import swgoh_comlink.const as const
import swgoh_comlink.utils as utils

logger = const.Constants.get_logger()


class SwgohComlinkBase:
    """Base class for comlink-python interface and supported methods.

    This base class is meant to be inherited by extension classes for actual method definitions
    using synchronous and asynchronous interfaces.

    """

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

    DEFAULT_URL = construct_url_base(host="localhost", port=3000, protocol="http")
    # str: The URL of the swgoh-comlink service. Defaults to http://localhost:3000

    DEFAULT_STATS_URL = construct_url_base(host="localhost", port=3223, protocol="http")
    # str: The URL of the swgoh-stats service. Defaults to http://localhost:3223

    DEFAULT_LOGGER = False

    # bool: Flag indicating whether the built-in logging framework is enabled

    @staticmethod
    def get_player_payload(
            allycode: Union[str, int] = None, player_id: str = None, enums: bool = False
    ) -> dict:
        """Create a swgoh-comlink payload object for player endpoints

        Args:
            allycode (str|int): Player allycode
            player_id (str): Player ID
            enums (bool): Flag to indicate whether ENUM values should be translated

        Returns:
            Dict: swgoh-comlink payload object

        """
        if allycode is None and player_id is None:
            raise ValueError("Either allycode or player_id must be provided.")
        if allycode is not None and player_id is not None:
            raise ValueError("Only one of allycode or player_id can be provided.")
        payload = {"payload": {}, "enums": enums}
        if allycode is not None:
            allycode = utils.sanitize_allycode(allycode)
            payload["payload"]["allyCode"] = f"{allycode}"
        else:
            payload["payload"]["playerId"] = f"{player_id}"
        if enums:
            payload["enums"] = True
        return payload

    def __init__(
            self,
            url: str = None,
            access_key: str = None,
            secret_key: str = None,
            stats_url: str = None,
            protocol: str = "http",
            host: str = None,
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

        global logger

        if not default_logger:
            logger_name: str = str(const.Constants.logger_name)
            logging.getLogger(logger_name).addHandler(logging.NullHandler())
            logger = logging.getLogger(logger_name)
            const.Constants.logger = logger
        if url is None:
            self.url_base = self.DEFAULT_URL
            logger.info(f"No URL provided. Using {self.url_base}")
        else:
            self.url_base = url
        if stats_url is None:
            self.stats_url_base = self.DEFAULT_STATS_URL
            logger.info(f"No stats URL provided. Using {self.stats_url_base}")
        else:
            self.stats_url_base = stats_url
        self.hmac = False  # HMAC use disabled by default

        # host and port parameters override defaults
        if host is not None:
            self.url_base = self.construct_url_base(protocol, host, port)
            self.stats_url_base = self.construct_url_base(protocol, host, stats_port)

        # Use values passed from client first, otherwise check for environment variables
        if access_key:
            self.access_key = access_key
        elif os.environ.get("ACCESS_KEY"):
            self.access_key = os.environ.get("ACCESS_KEY")
        else:
            self.access_key = None
        if secret_key:
            self.secret_key = secret_key
        elif os.environ.get("SECRET_KEY"):
            self.secret_key = os.environ.get("SECRET_KEY")
        else:
            self.secret_key = None
        if self.access_key and self.secret_key:
            self.hmac = True

        logger.info(f"{self.url_base=}")
        logger.info(f"{self.stats_url_base=}")

    def construct_request_headers(self, endpoint: str, payload: dict) -> dict:
        """Create HTTP request headers for the given endpoint and payload

        Args:
            endpoint (str): The swgoh-comlink endpoint to use
            payload (dict): The object to be passed to the endpoint for processing

        Returns:
            dict: The HTTP request headers

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
