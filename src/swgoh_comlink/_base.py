# coding=utf-8
"""
Base class for swgoh-comlink interface providing shared logic for sync and async clients.
"""

from __future__ import annotations

import functools
import hashlib
import hmac
import ipaddress
import logging
import os
import re
import time
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from json import dumps
from typing import Any, Self
from urllib.parse import urlencode, urlparse, urlunparse

from .exceptions import SwgohComlinkException, SwgohComlinkTypeError, SwgohComlinkValueError
from .helpers import Constants, DataItems
from .helpers._data_items import _items_wire_value
from .retry import RetryPolicy, _no_release, _Pacer

logger = logging.getLogger(__name__)

# A swgoh-stats language code such as ``eng_us``. Nothing that matches can carry ``&``, ``#``, ``=`` or ``/``
# into the stats query string.
_LANGUAGE_CODE = re.compile(r"[A-Za-z]{2,3}_[A-Za-z]{2}")

__all__ = [
    "SwgohComlinkBase",
    "param_alias",
    "DEFAULT_TIMEOUT",
    "GAME_DATA_TIMEOUT",
    "DEFAULT_VERSION_CACHE_TTL",
]

# Keys whose values must be masked in logs, repr, and debug output.
_SENSITIVE_KEYS = frozenset({"secret_key", "access_key"})

# Environment variables holding the HMAC (access, secret) key pair. The generic names are deprecated and are
# read only when neither namespaced name is set, so a pair is never assembled from both namespaces.
_CREDENTIAL_ENV_VARS = ("COMLINK_ACCESS_KEY", "COMLINK_SECRET_KEY")
_DEPRECATED_CREDENTIAL_ENV_VARS = ("ACCESS_KEY", "SECRET_KEY")

DEFAULT_TIMEOUT: float = 120.0
GAME_DATA_TIMEOUT: float = 300.0
DEFAULT_VERSION_CACHE_TTL: float = 3600.0

# Indirection over the monotonic clock so tests can control cache expiry.
_now: Callable[[], float] = time.monotonic


@dataclass(frozen=True)
class _CachedVersions:
    """Game data and localization bundle versions cached from a /metadata response.

    Fields are optional because mocked or unusual /metadata responses may omit
    either key; accessors raise only when the missing value is actually needed.
    """

    game: str | None
    language: str | None
    expires_at: float

    def require_game(self) -> str:
        if self.game is None:
            raise SwgohComlinkException("'latestGamedataVersion' was missing from the /metadata response.")
        return self.game

    def require_language(self) -> str:
        if self.language is None:
            raise SwgohComlinkException("'latestLocalizationBundleVersion' was missing from the /metadata response.")
        return self.language


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


def _is_plain_http_remote(url: str) -> bool:
    """Whether *url* is plain ``http`` to a host other than ``localhost``, ``127.0.0.0/8`` or ``::1``."""
    parsed = urlparse(url)
    if parsed.scheme.lower() != "http":
        return False
    host = (parsed.hostname or "").rstrip(".")
    if host == "localhost":
        return False
    try:
        return not ipaddress.ip_address(host).is_loopback
    except ValueError:  # a host name; resolving it would need a DNS lookup
        return True


def _replace_port(url: str, port: int) -> str:
    """Return *url* with its port set to *port*, keeping its scheme and host."""
    parsed = urlparse(url)
    return urlunparse(parsed._replace(netloc=f"{parsed.hostname}:{port}"))


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

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        """Prevent instances of this base class from being created directly."""
        if cls is SwgohComlinkBase:
            raise TypeError(f"Only subclasses of '{cls.__name__}' may be instantiated.")
        return super().__new__(cls)

    def __init__(
        self,
        url: str = "http://localhost:3000",
        stats_url: str = "http://localhost:3223",
        access_key: str | None = None,
        secret_key: str | None = None,
        host: str | None = None,
        port: int | None = None,
        stats_port: int | None = None,
        verify_ssl: bool = True,
        version_cache_ttl: float = DEFAULT_VERSION_CACHE_TTL,
        *,
        retry: RetryPolicy | None = None,
    ):
        from swgoh_comlink import version

        self.__version__ = version
        self.url_base = sanitize_url(url)
        self.stats_url_base = sanitize_url(stats_url)
        self.hmac = False
        self.verify_ssl = verify_ssl
        # NaN fails the >= comparison, so it is rejected here along with negatives.
        if not version_cache_ttl >= 0:
            raise SwgohComlinkValueError("version_cache_ttl must be a non-negative number of seconds.")
        self.version_cache_ttl = version_cache_ttl
        self._version_cache: _CachedVersions | None = None
        # The last get_enums() response and the game data version it was fetched under.
        self.enums: dict[str, Any] | None = None
        self.enums_version: str | None = None
        if retry is not None and not isinstance(retry, RetryPolicy):
            raise SwgohComlinkTypeError(f"retry must be a RetryPolicy or None, got {type(retry).__name__}.")
        self.retry_policy = retry
        self._pacer = _Pacer(retry.min_interval, retry.unpaced_endpoints) if retry is not None else None

        # host replaces url and stats_url outright; port and stats_port alone replace only their ports
        if host:
            self.url_base = self.PROTOCOL + f"://{host}:{3000 if port is None else port}"
            self.stats_url_base = self.PROTOCOL + f"://{host}:{3223 if stats_port is None else stats_port}"
        else:
            if port is not None:
                self.url_base = _replace_port(self.url_base, port)
            if stats_port is not None:
                self.stats_url_base = _replace_port(self.stats_url_base, stats_port)

        self.access_key, self.secret_key = self._resolve_credentials(access_key, secret_key)
        if self.access_key and self.secret_key:
            self.hmac = True
            if plain := [url for url in (self.url_base, self.stats_url_base) if _is_plain_http_remote(url)]:
                logger.warning(
                    "HMAC signing is on but %s uses plain HTTP to a non-loopback host. Signing does not protect "
                    "responses from being altered in transit or stop signed requests from being replayed; use "
                    "https or a private network.",
                    " and ".join(plain),
                )
        elif self.access_key or self.secret_key:
            present, missing = ("access_key", "secret_key") if self.access_key else ("secret_key", "access_key")
            logger.warning(
                "HMAC signing is off: %s is set but %s is not. Pass both keys, or set both %s and %s.",
                present,
                missing,
                *_CREDENTIAL_ENV_VARS,
            )

    @staticmethod
    def _resolve_credentials(access_key: str | None, secret_key: str | None) -> tuple[str | None, str | None]:
        """Return the HMAC (access, secret) keys: constructor arguments first, then the environment.

        Emits one ``DeprecationWarning`` when a key is taken from ``ACCESS_KEY`` or ``SECRET_KEY``.
        """
        env_names = _CREDENTIAL_ENV_VARS
        env_values = [os.environ.get(name) or None for name in env_names]
        if not any(env_values):
            env_names = _DEPRECATED_CREDENTIAL_ENV_VARS
            env_values = [os.environ.get(name) or None for name in env_names]
        args = (access_key or None, secret_key or None)
        if env_names is _DEPRECATED_CREDENTIAL_ENV_VARS and (
            used := [name for name, arg, value in zip(env_names, args, env_values, strict=True) if value and not arg]
        ):
            # stacklevel 4: this method, SwgohComlinkBase.__init__, the client's __init__, then the caller.
            warnings.warn(
                f"Reading HMAC keys from {' and '.join(used)} is deprecated and will be removed in v3. "
                f"Set {' and '.join(_CREDENTIAL_ENV_VARS)} instead.",
                DeprecationWarning,
                stacklevel=4,
            )
        access, secret = (arg or value for arg, value in zip(args, env_values, strict=True))
        return access, secret

    def _pace_delay(self, endpoint: str, stats: bool) -> float:
        """Reserve the next call slot for *endpoint* and return the seconds to wait for it.

        Always ``0.0`` unless the client's retry policy sets ``min_interval``.
        """
        return self._pace_slot(endpoint, stats)[0]

    def _pace_slot(self, endpoint: str, stats: bool) -> tuple[float, Callable[[], None]]:
        """Like :meth:`_pace_delay`, also returning a callable that gives the slot back if it goes unused."""
        if self._pacer is None:
            return 0.0, _no_release
        name = endpoint.split("?", 1)[0]
        return self._pacer.reserve_slot(f"{'stats' if stats else 'comlink'}:{name}", name)

    def _hold_changed(self, endpoint: str, stats: bool, deadline: float) -> bool:
        """Whether a rate hold on *endpoint* now ends after *deadline*, the time a caller was due to send.

        A refusal can land while a queued caller sleeps toward its slot; ``True`` tells it to requeue.
        """
        if self._pacer is None:
            return False
        name = endpoint.split("?", 1)[0]
        return self._pacer.held_after(f"{'stats' if stats else 'comlink'}:{name}", name, deadline)

    def _hold_endpoint(self, endpoint: str, stats: bool, seconds: float) -> bool:
        """Hold back calls to *endpoint* for *seconds*; return ``False`` when the caller must wait it out itself."""
        if self._pacer is None:
            return False
        name = endpoint.split("?", 1)[0]
        return self._pacer.hold(f"{'stats' if stats else 'comlink'}:{name}", name, seconds)

    def _construct_request_headers(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | list[Any] | None = None,
        *,
        body: bytes | None = None,
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
            # Sign the exact serialized bytes used by the transport. Signing a separate
            # re-serialization drifted from the wire twice: an empty dict hashed as `""`
            # (HTTP 403 HMACValidationError on every empty-payload POST), and non-ASCII
            # text hashed as `\uXXXX` escapes while httpx sent raw UTF-8 (HTTP 401).
            # Only a bodiless request (GET, payload=None) hashes the JSON empty string.
            if body is None:
                body = self._serialize_payload(payload) if payload is not None else dumps("").encode()
            # NOTE: MD5 is used here because the comlink service (JavaScript) requires it for
            # HMAC payload verification. This is a protocol constraint, not a security choice.
            payload_hash_digest = hashlib.md5(body).hexdigest()  # noqa: S324
            hmac_obj.update(payload_hash_digest.encode())
            hmac_digest = hmac_obj.hexdigest()
            req_headers["Authorization"] = f"HMAC-SHA256 Credential={self.access_key},Signature={hmac_digest}"
        return req_headers

    @staticmethod
    def _serialize_payload(payload: dict[str, Any] | list[Any]) -> bytes:
        """Serialize once for both authentication and transport.

        Matches JavaScript's ``JSON.stringify``: compact separators, raw UTF-8 and no NaN/Infinity.
        """
        try:
            return dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        except ValueError as exc:
            raise SwgohComlinkValueError(f"Request payload cannot be sent as JSON: {exc}") from exc

    # ── Version cache ────────────────────────────────────────────────────

    def invalidate_version_cache(self) -> None:
        """Discard the cached game/localization versions so the next lookup re-fetches /metadata."""
        self._version_cache = None

    def _cached_versions(self) -> _CachedVersions | None:
        """Return the cached version entry when caching is enabled and the entry is fresh."""
        cached = self._version_cache
        if cached is None or _now() >= cached.expires_at:
            return None
        return cached

    def _store_versions(self, game: str | None, language: str | None) -> _CachedVersions:
        """Build a version entry from *game* and *language* and cache it when caching applies."""
        entry = _CachedVersions(game=game, language=language, expires_at=_now() + self.version_cache_ttl)
        if self.version_cache_ttl > 0 and (game is not None or language is not None):
            self._version_cache = entry
        return entry

    @staticmethod
    def _versions_from_metadata(metadata: dict[str, Any]) -> tuple[str | None, str | None]:
        """Extract the (game, language) version strings from a /metadata response, if present."""
        game = metadata.get("latestGamedataVersion")
        language = metadata.get("latestLocalizationBundleVersion")
        return str(game) if game else None, str(language) if language else None

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
        items: str | int | DataItems | None = None,
        device_platform: str = "Android",
    ) -> dict[str, Any]:
        """Build payload for get_game_data().

        Raises:
            SwgohComlinkValueError: If request_segment is out of range.
        """
        inner_payload: dict[str, Any] = {
            "version": f"{game_version}",
            "devicePlatform": device_platform,
            "includePveUnits": include_pve_units,
        }
        payload: dict[str, Any] = {"payload": inner_payload, "enums": enums}
        if items:
            if isinstance(items, int):
                # Direct integer (e.g. from IntFlag arithmetic)
                inner_payload["items"] = _items_wire_value(items)
            elif items.lstrip("-").isdigit():
                # Numeric string — pass through as-is
                inner_payload["items"] = items
            else:
                # Named constant — resolve via Constants lookup
                inner_payload["items"] = Constants.get(items) or "-1"
        else:
            if request_segment < 0 or request_segment > 4:
                raise SwgohComlinkValueError(
                    "Invalid argument. <request_segment> should be an integer between 0 and 4, inclusive."
                )
            inner_payload["requestSegment"] = request_segment
        return payload

    @staticmethod
    def _build_unit_stats_endpoint(flags: list[str] | None = None, language: str | None = None) -> str:
        """Build the stats endpoint string with query parameters.

        A well-formed ``language`` that is not in ``Constants.LANGUAGES`` logs a warning and is still sent,
        so a language the game adds before the list is updated keeps working.

        Returns:
            Endpoint string like ``"api?flags=calcGP&language=eng_us"``.

        Raises:
            SwgohComlinkValueError: If flags contains invalid values, or language is not a language code
                such as ``eng_us``.
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

        query: dict[str, str] = {}
        if flags:
            if isinstance(flags, list) and set(flags).issubset(_allowed_flags):
                query["flags"] = ",".join(flags)
            else:
                raise SwgohComlinkValueError(
                    f'Invalid argument. <flags> should be a list of strings with one or more of "'
                    f"{_allowed_flags} flag values."
                )

        if language:
            if not isinstance(language, str) or not _LANGUAGE_CODE.fullmatch(language):
                raise SwgohComlinkValueError(
                    f"Invalid argument. <language> should be a language code such as 'eng_us', got {language!r}."
                )
            if language.lower() not in Constants.LANGUAGES:
                logger.warning(
                    "Unknown language %r; sending it anyway. Known languages: %s",
                    language,
                    ", ".join(Constants.LANGUAGES),
                )
            query["language"] = language

        return f"api?{urlencode(query, safe=',')}" if query else "api"

    @property
    def version(self) -> str:
        return self.__version__

    @version.setter
    def version(self, value: str) -> None:
        raise AttributeError("Module 'version' is read-only")

    @version.deleter
    def version(self) -> None:
        raise AttributeError("Module 'version' is read-only")
