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
from dataclasses import dataclass
from json import dumps
from typing import TYPE_CHECKING, Any, Self, cast
from urllib.parse import urlparse, urlunparse

import httpx
import msgspec

from .exceptions import (
    SwgohComlinkException,
    SwgohComlinkHTTPError,
    SwgohComlinkTypeError,
    SwgohComlinkValueError,
)
from .retry import RetryPolicy, _no_release, _Pacer

if TYPE_CHECKING:
    from .helpers import DataItems

__all__ = [
    "BOT_LIMITS",
    "BULK_LIMITS",
    "DEFAULT_LIMITS",
    "DEFAULT_TIMEOUT",
    "DEFAULT_VERSION_CACHE_TTL",
    "GAME_DATA_TIMEOUT",
    "NOT_GIVEN",
    "NotGiven",
    "PROFILES",
    "SwgohComlinkBase",
    "param_alias",
    "sanitize_url",
    "resolve_profile",
]

# Keys whose values must be masked in logs, repr, and debug output.
_SENSITIVE_KEYS = frozenset({"secret_key", "access_key"})

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
        port: int = 3000,
        stats_port: int = 3223,
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

        # host and port parameters override defaults
        if host:
            self.url_base = self.PROTOCOL + f"://{host}:{port}"
            self.stats_url_base = self.PROTOCOL + f"://{host}:{stats_port}"

        # Use values passed from client first, otherwise check for environment variables
        self.access_key = access_key or os.environ.get("ACCESS_KEY")
        self.secret_key = secret_key or os.environ.get("SECRET_KEY")
        if self.access_key and self.secret_key:
            self.hmac = True

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

    def _hold_endpoint(self, endpoint: str, stats: bool, seconds: float) -> bool:
        """Hold back calls to *endpoint* for *seconds*; return ``False`` when the caller must wait it out itself."""
        if self._pacer is None:
            return False
        name = endpoint.split("?", 1)[0]
        return self._pacer.hold(f"{'stats' if stats else 'comlink'}:{name}", name, seconds)

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
            #
            # The digest has to cover exactly the bytes that go on the wire. A POST sends
            # `json=payload`, so an empty dict is transmitted as `{}` — testing truthiness
            # here hashed `""` instead and every empty-payload signed POST (get_game_metadata
            # with no client_specs) was rejected with HTTP 403 HMACValidationError. Only a
            # bodiless request (GET, payload=None) hashes the empty string.
            if payload is not None:
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
    def _versions_from_metadata(metadata: Any) -> tuple[str | None, str | None]:
        """Extract the (game, language) version strings from a /metadata response, if present.

        Accepts the v2 dict shape and the typed :class:`~swgoh_comlink._models.Metadata`
        Struct; anything else yields ``(None, None)``.
        """
        if isinstance(metadata, dict):
            game = metadata.get("latestGamedataVersion")
            language = metadata.get("latestLocalizationBundleVersion")
        else:
            game = getattr(metadata, "latest_gamedata_version", None)
            language = getattr(metadata, "latest_localization_bundle_version", None)
        return str(game) if game else None, str(language) if language else None

    # ── Static payload builders (Phase 4: thin shims over _payloads.py) ───
    #
    # These were the canonical payload builders pre-Phase 4. They now
    # delegate to module-level pure functions in :mod:`._payloads` so the
    # logic is shared with the sync/async endpoint methods (and tests
    # can exercise the builders without instantiating a client).
    #
    # External callers reaching into the SDK via ``SwgohComlinkBase._foo``
    # keep working; the shims will be removed in v3.2.

    @staticmethod
    def _get_player_payload(
        allycode: str | int | None = None,
        player_id: str | None = None,
        enums: bool = False,
    ) -> dict[str, Any]:
        """Shim — use :func:`swgoh_comlink._payloads.player_payload`."""
        from ._payloads import player_payload

        return player_payload(allycode=allycode, player_id=player_id, enums=enums)

    @staticmethod
    def _build_game_data_payload(
        game_version: str,
        include_pve_units: bool = True,
        request_segment: int = 0,
        enums: bool = False,
        items: str | int | DataItems | None = None,
        device_platform: str = "Android",
    ) -> dict[str, Any]:
        """Shim — use :func:`swgoh_comlink._payloads.game_data_payload`."""
        from ._payloads import game_data_payload

        return game_data_payload(
            game_version=game_version,
            include_pve_units=include_pve_units,
            request_segment=request_segment,
            enums=enums,
            items=items,
            device_platform=device_platform,
        )

    @staticmethod
    def _build_unit_stats_endpoint(flags: list[str] | None = None, language: str | None = None) -> str:
        """Shim — use :func:`swgoh_comlink._payloads.unit_stats_endpoint`."""
        from ._payloads import unit_stats_endpoint

        return unit_stats_endpoint(flags=flags, language=language)

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
        """Raise the typed HTTP error for an error *response*; return ``None`` otherwise.

        * 4xx/5xx → the most specific :class:`SwgohComlinkHTTPError` subclass
          (:meth:`SwgohComlinkHTTPError.from_response`). Whether it is retried is
          decided by the client's :class:`~swgoh_comlink.retry.RetryPolicy`.
        * 1xx/2xx/3xx → returns ``None`` (caller proceeds to decode).
        """
        if response.is_error:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise SwgohComlinkHTTPError.from_response(response) from e

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
        """Translate a transport-level exception (:class:`httpx.RequestError`) into :class:`SwgohComlinkException`.

        Typed HTTP errors (:class:`SwgohComlinkHTTPError`) are passed through unchanged.
        """
        if isinstance(exc, SwgohComlinkException):
            return exc
        return SwgohComlinkException(str(exc))

    def with_options(self, *, retry: RetryPolicy | None | NotGiven = NOT_GIVEN, **overrides: Any) -> Self:
        """Return a shallow clone of this client with attribute *overrides* applied.

        Useful for one-off config tweaks without constructing a new SDK
        instance from scratch::

            quick = client.with_options(retry=None)  # one attempt, no waiting
            quick.get_player(allycode=...)

        Args:
            retry: A :class:`~swgoh_comlink.retry.RetryPolicy` for the clone, or
                ``None`` to make exactly one attempt per call. Omit it to keep this
                client's policy. A new policy gets its own pacing state; a kept
                policy shares the pacing state (and endpoint holds) with this client.
            **overrides: Other existing attributes to replace on the clone.

        **Lifetime semantics:** the clone *shares* the underlying httpx
        client(s) with the original — closing one closes both. This is
        intentional for cheap option-flipping; if you need a fully
        independent client (different timeout, different pool) construct
        a fresh instance instead.

        Raises:
            AttributeError: For an unknown option. Typos shouldn't pass undetected.
            SwgohComlinkTypeError: If *retry* is neither a ``RetryPolicy`` nor ``None``.
        """
        clone = copy.copy(self)
        if not isinstance(retry, NotGiven):
            if retry is not None and not isinstance(retry, RetryPolicy):
                raise SwgohComlinkTypeError(f"retry must be a RetryPolicy or None, got {type(retry).__name__}.")
            clone.retry_policy = retry
            clone._pacer = _Pacer(retry.min_interval, retry.unpaced_endpoints) if retry is not None else None
        for name, value in overrides.items():
            if name in {"retry_policy", "_pacer"}:
                raise AttributeError(f"set '{name}' through with_options(retry=...)")
            if not hasattr(clone, name):
                raise AttributeError(
                    f"unknown option '{name}' for {type(self).__name__}",
                )
            setattr(clone, name, value)
        return clone
