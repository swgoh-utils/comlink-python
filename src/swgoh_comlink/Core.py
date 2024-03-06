"""
Core module for swgoh_comlink
"""
import os

from swgoh_comlink.Utils import (
    construct_url_base,
    get_logger,
)


class SwgohComlinkBase:
    """
    Base class definition for comlink-python interface and supported methods.
    This base class is meant to be inherited by extension classes for actual method definitions
    using synchronous and asynchronous interfaces.

    Parameters:
        url: The URL where swgoh-comlink is running. Defaults to 'http://localhost:3000'
        access_key: The HMAC public key. Default to None which indicates HMAC is not used.
        secret_key: The HMAC private key. Default to None which indicates HMAC is not used.
        stats_url: The url of the swgoh-stats service (if used), such as 'http://localhost:3223'
        protocol: The protocol to use for connecting to comlink. Typically, http or https.
        host: IP address or DNS name of server where the swgoh-comlink service is running
        port: TCP port number where the swgoh-comlink service is running [Default: 3000]
        stats_port: TCP port number of where the comlink-stats service is running [Default: 3223]

    Note: url and stat_url are mutually exclusive of the protocol/host/port/stats_port parameters.
        Either of the options should be chosen but not both.
    """

    DEFAULT_URL = construct_url_base(host="localhost", port=3000, protocol="http")
    DEFAULT_STATS_URL = construct_url_base(host="localhost", port=3223, protocol="http")

    def __init__(self,
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

        :param url: The URL where swgoh-comlink is running. Defaults to 'http://localhost:3000'
        :param access_key: The HMAC public key. Default to None which indicates HMAC is not used.
        :param secret_key: The HMAC private key. Default to None which indicates HMAC is not used.
        :param stats_url: The url of the swgoh-stats service (if used), such as 'http://localhost:3223'
        :param host: IP address or DNS name of server where the swgoh-comlink service is running
        :param port: TCP port number where the swgoh-comlink service is running [Default: 3000]
        :param stats_port: TCP port number of where the comlink-stats service is running [Default: 3223]
        :param default_logger: Flag to indicate whether the default logger should be used.

        """

        self.logger = get_logger('SwgohComlink')
        if url is None:
            self.url_base = self.DEFAULT_URL
            self.logger.info(f"No URL provided. Using {self.url_base}")
        else:
            self.url_base = url
        if stats_url is None:
            self.stats_url_base = self.DEFAULT_STATS_URL
            self.logger.info(f"No stats URL provided. Using {self.stats_url_base}")
        else:
            self.stats_url_base = stats_url
        self.hmac = False  # HMAC use disabled by default

        # host and port parameters override defaults
        if host is not None:
            self.url_base = construct_url_base(protocol, host, port)
            self.stats_url_base = construct_url_base(protocol, host, stats_port)

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

        self.logger.info(f"{self.url_base=}")
        self.logger.info(f"{self.stats_url_base=}")
