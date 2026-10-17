# coding=utf-8
"""Sync escape-hatch methods — hand-written, mixed into the generated client.

These four methods stay outside the codegen manifest because their
shapes diverge from the uniform endpoint template:

* :meth:`healthcheck` — returns ``bool``; exception-safe; bypasses retry.
* :meth:`raw_request` — returns raw :class:`httpx.Response`; bypasses decode.
* :meth:`stream_game_data` — returns a streaming context manager.
* :meth:`stream_localization` — same; pre-fetch fallback uses sync helper.

Plus :meth:`get_latest_game_data_version` — a tiny helper that wraps
:meth:`get_game_metadata`; trivially duplicated across the four
client variants so it lives here too.

The generated client classes (`swgoh_comlink.py`,
`swgoh_comlink_async.py`, `typed/swgoh_comlink.py`,
`typed/swgoh_comlink_async.py`) inherit from this mixin (or its async
twin) to compose the full public surface.
"""

from __future__ import annotations

import contextlib
from collections.abc import Generator
from typing import TYPE_CHECKING, Any

import httpx

from ._base import GAME_DATA_TIMEOUT
from ._payloads import game_data_payload, localization_payload
from .exceptions import SwgohComlinkException, SwgohComlinkHTTPError

if TYPE_CHECKING:
    from ._base import _CachedVersions
    from .helpers import DataItems


@contextlib.contextmanager
def _checked_stream(stream: contextlib.AbstractContextManager[httpx.Response]) -> Generator[httpx.Response, None, None]:
    """Enter an ``httpx`` stream and raise the typed HTTP error for an error status.

    The body of an error response is read (it is small) so the raised
    :class:`SwgohComlinkHTTPError` carries the comlink error message. Transport
    failures while opening the stream raise :class:`SwgohComlinkException`.
    """
    try:
        with stream as response:
            if response.is_error:
                response.read()
                raise SwgohComlinkHTTPError.from_response(response)
            yield response
    except httpx.RequestError as e:
        raise SwgohComlinkException(str(e)) from e


class _SyncEscapeHatchMixin:
    """Mixed into sync client classes (dict and typed variants alike)."""

    if TYPE_CHECKING:
        # The attributes/methods below are provided at runtime by
        # :class:`SwgohComlinkBase` / the generated client class. Declared
        # here (type-checking only) so the mixin's contract is explicit.
        client: httpx.Client

        def _build_request_kwargs(
            self,
            method: str,
            endpoint: str,
            payload: dict[str, Any] | list[Any] | None,
            timeout: float | None,
        ) -> tuple[str, dict[str, Any]]: ...

        def _get_game_version(self) -> str: ...

        def _get_versions(self, refresh: bool = False) -> _CachedVersions: ...

    def healthcheck(self, *, timeout: float = 5.0) -> bool:
        """Probe ``/enums`` and report reachability.

        Returns ``True`` on a 200 response within *timeout* seconds;
        ``False`` on any HTTP / network / timeout error. Does NOT raise.
        Intended for bot startup probes — "is comlink up before I begin
        the per-tick loop?"

        Bypasses the retry loop. ``/enums`` is a cheap GET that serves
        static data, so the only meaningful failure modes are
        "comlink down" and "network unreachable" — both should fail
        fast, not retry.
        """
        try:
            r = self.client.request("GET", "/enums", timeout=timeout)
        except (httpx.HTTPError, httpx.TimeoutException, httpx.RequestError):
            return False
        return bool(r.status_code == 200)

    def raw_request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | list[Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Issue a request to *path* and return the raw :class:`httpx.Response`.

        Escape hatch for endpoints the SDK doesn't model, debugging, or
        any case where the typed/retry pipeline isn't wanted. Bypasses:
        the retry loop, status classification, msgspec decode, the
        Struct/typed-decoder dispatch — everything past
        ``_build_request_kwargs``.

        HMAC headers are still attached.
        """
        method_u = method.upper()
        endpoint = path.lstrip("/")
        full_path, request_kwargs = self._build_request_kwargs(method_u, endpoint, payload, timeout)
        return self.client.request(method_u, full_path, **request_kwargs)

    def stream_game_data(
        self,
        version: str = "",
        include_pve_units: bool = True,
        request_segment: int = 0,
        enums: bool = False,
        items: str | DataItems | int | None = None,
        device_platform: str = "Android",
    ) -> Any:
        """Return an ``httpx.Client.stream`` context manager for ``/data``.

        Use when the payload is too large to materialize in memory at
        once. The caller treats the returned object as a context manager
        and iterates ``response.iter_bytes()`` (or ``.iter_text()`` /
        ``.iter_lines()`` / ``.iter_raw()``).

        Bypasses the retry loop (streaming + retry doesn't compose
        cleanly — a half-streamed response can't be replayed). An HTTP
        error status raises :class:`~swgoh_comlink.exceptions.SwgohComlinkHTTPError`
        (or a subclass) when the context manager is entered.
        """
        game_version = version or self._get_game_version()
        payload = game_data_payload(
            game_version=game_version,
            include_pve_units=include_pve_units,
            request_segment=request_segment,
            enums=enums,
            items=items,
            device_platform=device_platform,
        )
        full_path, request_kwargs = self._build_request_kwargs("POST", "data", payload, GAME_DATA_TIMEOUT)
        return _checked_stream(self.client.stream("POST", full_path, **request_kwargs))

    def stream_localization(
        self,
        localization_id: str | None = None,
        locale: str | None = None,
        unzip: bool = False,
        enums: bool = False,
    ) -> Any:
        """Return an ``httpx.Client.stream`` context manager for ``/localization``."""
        if not localization_id:
            localization_id = self.get_latest_game_data_version()["language"]
        payload = localization_payload(localization_id, locale, unzip, enums)
        full_path, request_kwargs = self._build_request_kwargs("POST", "localization", payload, None)
        return _checked_stream(self.client.stream("POST", full_path, **request_kwargs))

    def get_latest_game_data_version(self, refresh: bool = False) -> dict[str, Any]:
        """Get the latest game data + language bundle versions.

        Results are served from the instance version cache (see ``version_cache_ttl``).

        Args:
            refresh: When True, bypass the cache and fetch fresh values from /metadata.

        Returns:
            Dictionary with ``"game"`` and ``"language"`` version strings.
        """
        versions = self._get_versions(refresh=refresh)
        return {"game": versions.require_game(), "language": versions.require_language()}

    # alias for shorthand call
    getVersion = get_latest_game_data_version
