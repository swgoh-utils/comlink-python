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

from typing import TYPE_CHECKING, Any, cast

import httpx

from ._base import GAME_DATA_TIMEOUT
from ._payloads import game_data_payload, localization_payload

if TYPE_CHECKING:
    from ._models import Metadata


class _SyncEscapeHatchMixin:
    """Mixed into sync client classes (dict and typed variants alike)."""

    # The attributes used here are provided by :class:`SwgohComlinkBase` /
    # the generated client class. Mixins don't redeclare them; they just
    # reach in.

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
            r = self.client.request("GET", "/enums", timeout=timeout)  # type: ignore[attr-defined]
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
        full_path, request_kwargs = self._build_request_kwargs(  # type: ignore[attr-defined]
            method_u, endpoint, payload, timeout
        )
        return cast(httpx.Response, self.client.request(method_u, full_path, **request_kwargs))  # type: ignore[attr-defined]

    def stream_game_data(
        self,
        version: str = "",
        include_pve_units: bool = True,
        request_segment: int = 0,
        enums: bool = False,
        items: str | None = None,
        device_platform: str = "Android",
    ) -> Any:
        """Return an ``httpx.Client.stream`` context manager for ``/data``.

        Use when the payload is too large to materialize in memory at
        once. The caller treats the returned object as a context manager
        and iterates ``response.iter_bytes()`` (or ``.iter_text()`` /
        ``.iter_lines()`` / ``.iter_raw()``).

        Bypasses the retry loop (streaming + retry doesn't compose
        cleanly — a half-streamed response can't be replayed).
        """
        game_version = version or self._get_game_version()  # type: ignore[attr-defined]
        payload = game_data_payload(
            game_version=game_version,
            include_pve_units=include_pve_units,
            request_segment=request_segment,
            enums=enums,
            items=items,
            device_platform=device_platform,
        )
        full_path, request_kwargs = self._build_request_kwargs(  # type: ignore[attr-defined]
            "POST", "data", payload, GAME_DATA_TIMEOUT
        )
        return self.client.stream("POST", full_path, **request_kwargs)  # type: ignore[attr-defined]

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
        full_path, request_kwargs = self._build_request_kwargs(  # type: ignore[attr-defined]
            "POST", "localization", payload, None
        )
        return self.client.stream("POST", full_path, **request_kwargs)  # type: ignore[attr-defined]

    def get_latest_game_data_version(self) -> dict[str, Any]:
        """Get the latest game data + language bundle versions.

        Returns:
            Dictionary with ``"game"`` and ``"language"`` version strings.
        """
        # Both typed and dict variants of the client expose get_game_metadata.
        # On the typed variant it returns a Metadata Struct; on the dict
        # variant it returns the raw v2 dict. Handle both.
        md: Any = self.get_game_metadata()  # type: ignore[attr-defined]
        if hasattr(md, "latest_gamedata_version"):
            md_struct = cast("Metadata", md)
            return {
                "game": md_struct.latest_gamedata_version,
                "language": md_struct.latest_localization_bundle_version,
            }
        return {
            "game": md["latestGamedataVersion"],
            "language": md["latestLocalizationBundleVersion"],
        }

    # alias for shorthand call
    getVersion = get_latest_game_data_version
