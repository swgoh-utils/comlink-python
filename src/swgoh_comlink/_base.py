# coding=utf-8
"""
Base class for swgoh-comlink interface providing shared logic for sync and async clients.
"""

from __future__ import annotations

import copy
import functools
import hashlib
import hmac
import os
import time
from collections.abc import Callable
from json import dumps
from typing import Any, Self, cast
from urllib.parse import urlparse, urlunparse

import httpx
import msgspec

from ._retry import RETRYABLE_STATUSES, RetryableStatusError
from .exceptions import SwgohComlinkException, SwgohComlinkValueError
from .helpers import Constants

__all__ = [
    "BOT_LIMITS",
    "BULK_LIMITS",
    "DEFAULT_LIMITS",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT",
    "GAME_DATA_TIMEOUT",
    "NOT_GIVEN",
    "NotGiven",
    "PROFILES",
    "SwgohComlinkBase",
    "param_alias",
    "sanitize_url",
]

# Keys whose values must be masked in logs, repr, and debug output.
_SENSITIVE_KEYS = frozenset({"secret_key", "access_key"})

DEFAULT_TIMEOUT: float = 120.0
GAME_DATA_TIMEOUT: float = 300.0
DEFAULT_MAX_RETRIES: int = 3


# ── NOT_GIVEN sentinel ──────────────────────────────────────────────────────


class NotGiven:
    """Sentinel type for "argument not supplied" distinct from ``None``.

    ``None`` is a legitimate value for several SDK kwargs (e.g. ``timeout=None``
    meaning "no timeout"). A separate sentinel lets methods distinguish
    "caller passed nothing" from "caller passed None on purpose" — useful
    for :meth:`SwgohComlinkBase.with_options` and Phase 3+ method signatures.
    """

    _instance: NotGiven | None = None

    def __new__(cls) -> NotGiven:
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "NOT_GIVEN"

    def __bool__(self) -> bool:
        return False


NOT_GIVEN: NotGiven = NotGiven()
"""Singleton :class:`NotGiven` instance."""


# ── Connection pool presets ─────────────────────────────────────────────────

#: Default httpx connection limits. Suitable for general-purpose SDK use.
#: ``keepalive_expiry=30`` (up from httpx default 5s) is a Phase 2 win for
#: low-frequency bot users that make one call every ~10s — without 30s
#: keepalive every call would pay a fresh TCP+TLS handshake.
DEFAULT_LIMITS: httpx.Limits = httpx.Limits(
    max_connections=100,
    max_keepalive_connections=20,
    keepalive_expiry=30.0,
)

#: Long-lived bot use case. Tighter keepalive, more pooled connections.
BOT_LIMITS: httpx.Limits = httpx.Limits(
    max_connections=200,
    max_keepalive_connections=50,
    keepalive_expiry=120.0,
)

#: Bulk analytics use case. High concurrency, broader pool.
BULK_LIMITS: httpx.Limits = httpx.Limits(
    max_connections=500,
    max_keepalive_connections=200,
    keepalive_expiry=60.0,
)

#: Map of profile name → preset. Public so callers can introspect / extend.
PROFILES: dict[str, httpx.Limits] = {
    "default": DEFAULT_LIMITS,
    "bot": BOT_LIMITS,
    "bulk": BULK_LIMITS,
}


def resolve_profile(profile: str) -> httpx.Limits:
    """Look up a named pool preset; raises ValueError on unknown name."""
    try:
        return PROFILES[profile]
    except KeyError as e:
        raise ValueError(
            f"unknown profile '{profile}'. known: {sorted(PROFILES)}",
        ) from e


def param_alias(param: str, alias: str) -> Callable[..., Any]:
    """Decorator to support legacy camelCase parameter aliases.

    Translates a keyword argument from *alias* to *param* so callers
    can use either spelling.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if alias in kwargs:
                kwargs[param] = kwargs.pop(alias)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def sanitize_url(url: str) -> str:
    """Make sure provided URL is in the expected format and return sanitized."""
    url = url.strip("/")
    if url.startswith("https"):
        parsed = urlparse(url)
        if parsed.port is None:
            netloc = f"{parsed.hostname}:443"
            url = urlunparse(parsed._replace(netloc=netloc))
    return url


class SwgohComlinkBase:
    """Base class for comlink-python interface and supported methods.

    This base class is meant to be inherited by extension classes providing
    synchronous and asynchronous HTTP transport implementations.

    Direct instantiation is prevented; use ``SwgohComlink`` or ``SwgohComlinkAsync``.
    """

    __comlink_type__: str | None = None
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
            f"{cls_name} version {self.__version__!r} ("
            f"url={self.url_base!r}, "
            f"hmac={self.hmac}, "
            f"access_key={self._mask(self.access_key)!r}, "
            f"secret_key={self._mask(self.secret_key)!r})"
        )

    def __new__(cls, *args: Any, **kwargs: Any) -> SwgohComlinkBase:
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
        self, method: str, endpoint: str, payload: dict[str, Any] | list[Any] | None = None
    ) -> dict[str, str]:
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
            assert self.secret_key is not None
            hmac_obj = hmac.new(key=self.secret_key.encode(), digestmod=hashlib.sha256)
            hmac_obj.update(req_time.encode())
            hmac_obj.update(method.upper().encode())
            hmac_obj.update(f"/{endpoint}".encode())
            # json dumps separators needed for compact string formatting required for compatibility with
            # comlink since it is written with javascript as the primary object model
            if payload:
                payload_string = dumps(payload, separators=(",", ":"))
            else:
                payload_string = dumps("")
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
    ) -> dict[str, Any]:
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
            code_str = str(allycode).replace("-", "")
            if not code_str.isdigit() or len(code_str) != 9:
                raise SwgohComlinkValueError("Allycode must be a 9-digit number.")
            payload["payload"]["allyCode"] = code_str
        return payload

    @staticmethod
    def _build_game_data_payload(
        game_version: str,
        include_pve_units: bool = True,
        request_segment: int = 0,
        enums: bool = False,
        items: str | int | None = None,
        device_platform: str = "Android",
    ) -> dict[str, Any]:
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
            if isinstance(items, int):
                # Direct integer (e.g. from IntFlag arithmetic)
                payload["payload"]["items"] = str(items)
            elif items.lstrip("-").isdigit():
                # Numeric string — pass through as-is
                payload["payload"]["items"] = items
            else:
                # Named constant — resolve via Constants lookup
                payload["payload"]["items"] = Constants.get(items) or "-1"
        else:
            if request_segment < 0 or request_segment > 4:
                raise SwgohComlinkValueError(
                    "Invalid argument. <request_segment> should be an integer between 0 and 4, inclusive."
                )
            payload["payload"]["requestSegment"] = request_segment
        return payload

    @staticmethod
    def _build_unit_stats_endpoint(flags: list[str] | None = None, language: str | None = None) -> str:
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

    @property
    def version(self) -> str:
        return self.__version__

    @version.setter
    def version(self, value: str) -> None:
        raise AttributeError("Module 'version' is read-only")

    @version.deleter
    def version(self) -> None:
        raise AttributeError("Module 'version' is read-only")

    # ── Phase 2 _BaseClient surface ──────────────────────────────────────
    #
    # The methods below are shared HTTP-pipeline plumbing used by both
    # SwgohComlink and SwgohComlinkAsync. They have no httpx send call
    # of their own (because the sync vs async call shape differs) — they
    # handle everything *around* the send: building the request kwargs,
    # classifying the response, decoding the body, mapping errors,
    # and cloning the client with overrides.

    def _build_request_kwargs(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | list[Any] | None,
        timeout: float | None,
    ) -> tuple[str, dict[str, Any]]:
        """Construct the path + kwargs for ``client.request(method, path, **kwargs)``.

        Returns a tuple ``(full_path, kwargs)`` ready to be unpacked by the
        subclass's sync or async send. Centralizes header construction,
        timeout passthrough, and the GET-vs-POST body distinction.
        """
        req_headers = self._construct_request_headers(method, endpoint, payload)
        kwargs: dict[str, Any] = {"headers": req_headers}
        if timeout is not None:
            kwargs["timeout"] = timeout
        if method.upper() != "GET":
            kwargs["json"] = payload
        return f"/{endpoint}", kwargs

    @staticmethod
    def _classify_response(response: httpx.Response) -> None:
        """Inspect *response* and raise the appropriate exception for the retry loop.

        * Retryable status (5xx, 408, 425, 429) → :class:`RetryableStatusError`
        * Other 4xx/5xx → :class:`SwgohComlinkException` (non-retryable)
        * 2xx/3xx → returns None (caller proceeds to decode)
        """
        if response.status_code in RETRYABLE_STATUSES:
            raise RetryableStatusError(response)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise SwgohComlinkException(
                f"HTTP {response.status_code}: {response.text}",
            ) from e

    @staticmethod
    def _decode(response: httpx.Response) -> dict[str, Any] | list[Any]:
        """Parse *response*'s body to a JSON object via msgspec's untyped decoder.

        This is the fallback path used when a caller does not supply an
        explicit ``decoder=`` to :meth:`_request`. msgspec's untyped
        decode produces the same dict/list shape ``json.loads`` would,
        but is meaningfully faster (~2x) on large payloads, so even the
        raw/passthrough path benefits from the Phase 3 swap.

        Typed endpoints (get_player, get_game_metadata, etc.) bypass
        this and call their cached :class:`msgspec.json.Decoder` directly.
        """
        # Local import keeps base-module load cheap when only the base
        # class is touched (Phase 5 lazy-import work cares).
        from ._models import UNTYPED_DECODER

        try:
            return cast(dict[str, Any] | list[Any], UNTYPED_DECODER.decode(response.content))
        except msgspec.DecodeError as e:
            raise SwgohComlinkException(f"failed to decode response body: {e}") from e

    @staticmethod
    def _map_error(exc: BaseException) -> SwgohComlinkException:
        """Translate a transport-level exception into :class:`SwgohComlinkException`.

        Catches the retry loop's final raise for both transient flavors:

        * :class:`httpx.RequestError` (connection failure, timeout, etc.)
        * :class:`RetryableStatusError` (status exhausted retries)
        """
        if isinstance(exc, RetryableStatusError):
            resp = exc.response
            status = getattr(resp, "status_code", "?")
            text = getattr(resp, "text", "")
            return SwgohComlinkException(f"HTTP {status}: {text}")
        return SwgohComlinkException(str(exc))

    def with_options(self, **overrides: Any) -> Self:
        """Return a shallow clone of this client with attribute *overrides* applied.

        Useful for one-off config tweaks without constructing a new SDK
        instance from scratch::

            quick = client.with_options(max_retries=0)
            quick.get_player(allycode=...)

        **Lifetime semantics:** the clone *shares* the underlying httpx
        client(s) with the original — closing one closes both. This is
        intentional for cheap option-flipping; if you need a fully
        independent client (different timeout, different pool) construct
        a fresh instance instead.

        Unknown attributes raise :class:`AttributeError` rather than
        silently adding to the clone — typos shouldn't pass undetected.
        """
        clone = copy.copy(self)
        for name, value in overrides.items():
            if not hasattr(clone, name):
                raise AttributeError(
                    f"unknown option '{name}' for {type(self).__name__}",
                )
            setattr(clone, name, value)
        return clone
