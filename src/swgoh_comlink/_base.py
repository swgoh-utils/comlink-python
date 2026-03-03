# coding=utf-8
"""
Base class for swgoh-comlink interface providing shared logic for sync and async clients.
"""

from __future__ import annotations

import functools
import hashlib
import hmac
import os
import re
import time
from collections.abc import Callable
from json import dumps
from typing import Any

from .exceptions import SwgohComlinkValueError
from .helpers import Constants

__all__ = ["SwgohComlinkBase"]

# Keys whose values must be masked in logs, repr, and debug output.
_SENSITIVE_KEYS = frozenset({"secret_key", "access_key"})

url_port_re = re.compile(r"^https://\S+:(\d+)$", re.VERBOSE | re.IGNORECASE)

DEFAULT_TIMEOUT: float = 120.0
GAME_DATA_TIMEOUT: float = 300.0


def param_alias(param: str, alias: str) -> Callable:
    """Decorator to support legacy camelCase parameter aliases.

    Translates a keyword argument from *alias* to *param* so callers
    can use either spelling.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if alias in kwargs:
                kwargs[param] = kwargs.pop(alias)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def sanitize_url(url: str) -> str:
    """Make sure provided URL is in the expected format and return sanitized."""
    url = url.strip("/")
    if url.startswith("https") and not re.fullmatch(url_port_re, url):
        url = f"{url}:443"
    return url


class SwgohComlinkBase:
    """Base class for comlink-python interface and supported methods.

    This base class is meant to be inherited by extension classes providing
    synchronous and asynchronous HTTP transport implementations.

    Direct instantiation is prevented; use ``SwgohComlink`` or ``SwgohComlinkAsync``.
    """

    PROTOCOL = "http"

    @staticmethod
    def _mask(value: str | None, visible: int = 4) -> str:
        """Return a masked version of a sensitive string.

        Shows up to *visible* leading characters followed by ``***``.
        Returns ``"None"`` when the value is ``None``.
        """
        if value is None:
            return "None"
        if len(value) <= visible:
            return "***"
        return value[:visible] + "***"

    def __repr__(self) -> str:
        cls_name = type(self).__name__
        return (
            f"{cls_name}("
            f"url={self.url_base!r}, "
            f"hmac={self.hmac}, "
            f"access_key={self._mask(self.access_key)!r}, "
            f"secret_key={self._mask(self.secret_key)!r})"
        )

    def __new__(cls, *args, **kwargs):
        """Prevent instances of this base class from being created directly."""
        if cls is SwgohComlinkBase:
            raise TypeError(f"Only subclasses of '{cls.__name__}' may be instantiated.")
        return object.__new__(cls)

    def __init__(
        self,
        url: str = "http://localhost:3000",
        stats_url: str = "http://localhost:3223",
        access_key: str | None = None,
        secret_key: str | None = None,
        host: str | None = None,
        port: int = 3000,
        stats_port: int = 3223,
        verify_ssl: bool = True,
    ):
        from swgoh_comlink import version

        self.__version__ = version
        self.url_base = sanitize_url(url)
        self.stats_url_base = sanitize_url(stats_url)
        self.hmac = False
        self.verify_ssl = verify_ssl

        # host and port parameters override defaults
        if host:
            self.url_base = self.PROTOCOL + f"://{host}:{port}"
            self.stats_url_base = self.PROTOCOL + f"://{host}:{stats_port}"

        # Use values passed from client first, otherwise check for environment variables
        self.access_key = access_key or os.environ.get("ACCESS_KEY")
        self.secret_key = secret_key or os.environ.get("SECRET_KEY")
        if self.access_key and self.secret_key:
            self.hmac = True

    def _construct_request_headers(
        self, method: str, endpoint: str, payload: dict | list | None = None
    ) -> dict:
        """Create HTTP request headers with optional HMAC authentication.

        Args:
            method: HTTP method (e.g. ``"GET"`` or ``"POST"``).
            endpoint: API endpoint path.
            payload: JSON body for the request.

        Returns:
            Dictionary of HTTP headers.
        """
        req_headers: dict[str, str] = {}
        if self.hmac:
            req_time = str(int(time.time() * 1000))
            req_headers = {"X-Date": f"{req_time}"}
            hmac_obj = hmac.new(key=self.secret_key.encode(), digestmod=hashlib.sha256)
            hmac_obj.update(req_time.encode())
            hmac_obj.update(method.upper().encode())
            hmac_obj.update(f"/{endpoint}".encode())
            # json dumps separators needed for compact string formatting required for compatibility with
            # comlink since it is written with javascript as the primary object model
            if payload:
                payload_string = dumps(payload, separators=(",", ":"))
            else:
                payload_string = dumps({})
            # NOTE: MD5 is used here because the comlink service (JavaScript) requires it for
            # HMAC payload verification. This is a protocol constraint, not a security choice.
            payload_hash_digest = hashlib.md5(payload_string.encode()).hexdigest()  # noqa: S324
            hmac_obj.update(payload_hash_digest.encode())
            hmac_digest = hmac_obj.hexdigest()
            req_headers["Authorization"] = f"HMAC-SHA256 Credential={self.access_key},Signature={hmac_digest}"
        return req_headers

    # ── Static payload builders ──────────────────────────────────────────

    @staticmethod
    def _get_player_payload(
        allycode: str | int | None = None, player_id: str | None = None, enums: bool = False
    ) -> dict:
        """Build payload for get_player functions.

        Args:
            allycode: player allyCode
            player_id: player game ID
            enums: boolean

        Returns:
            The constructed payload.

        Raises:
            SwgohComlinkValueError: If neither allycode nor player_id is provided.
        """
        if not allycode and not player_id:
            raise SwgohComlinkValueError("Either 'allycode' or 'player_id' must be provided.")
        payload: dict[str, Any] = {"payload": {}, "enums": enums}
        if player_id:
            payload["payload"]["playerId"] = str(player_id)
        else:
            payload["payload"]["allyCode"] = str(allycode)
        return payload

    @staticmethod
    def _build_game_data_payload(
        game_version: str,
        include_pve_units: bool = True,
        request_segment: int = 0,
        enums: bool = False,
        items: str | None = None,
        device_platform: str = "Android",
    ) -> dict:
        """Build payload for get_game_data().

        Raises:
            SwgohComlinkValueError: If request_segment is out of range.
        """
        payload: dict[str, Any] = {
            "payload": {
                "version": f"{game_version}",
                "devicePlatform": device_platform,
                "includePveUnits": include_pve_units,
            },
            "enums": enums,
        }
        if items:
            if isinstance(items, int) and str(abs(items)).isdigit():
                payload["payload"]["items"] = str(items)
            else:
                payload["payload"]["items"] = Constants.get(items) or "-1"
        else:
            if request_segment < 0 or request_segment > 4:
                raise SwgohComlinkValueError(
                    "Invalid argument. <request_segment> should be an integer between 0 and 4, inclusive."
                )
            payload["payload"]["requestSegment"] = request_segment
        return payload

    @staticmethod
    def _build_unit_stats_endpoint(
        flags: list[str] | None = None, language: str | None = None
    ) -> str:
        """Build the stats endpoint string with query parameters.

        Returns:
            Endpoint string like ``"api?flags=calcGP&language=eng_us"``.

        Raises:
            SwgohComlinkValueError: If flags contains invalid values.
        """
        _allowed_flags = {
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
        }

        flag_str = None
        if flags:
            if isinstance(flags, list) and set(flags).issubset(_allowed_flags):
                flag_str = "flags=" + ",".join(flags)
            else:
                raise SwgohComlinkValueError(
                    f'Invalid argument. <flags> should be a list of strings with one or more of "'
                    f"{_allowed_flags} flag values."
                )

        lang_str = f"language={language}" if language else None

        query_string = None
        if flag_str or lang_str:
            query_string = "?" + "&".join(filter(None, iter([flag_str, lang_str])))

        return "api" + query_string if query_string else "api"
