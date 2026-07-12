# coding=utf-8
"""Async escape-hatch methods — hand-written, mixed into the generated async client.

Async twin of :mod:`_escape_hatches_sync`. The streaming methods have a
small but real semantic difference from sync: they can't call ``await``
to resolve the metadata fallback (the wrapper itself is non-async — it
just returns the async-context-manager object). So ``stream_game_data``
requires ``version=`` explicitly and ``stream_localization`` requires
``localization_id=``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import httpx

from ._base import GAME_DATA_TIMEOUT
from ._payloads import game_data_payload, localization_payload

if TYPE_CHECKING:
    from ._models import Metadata


class _AsyncEscapeHatchMixin:
    """Mixed into async client classes (dict and typed variants alike)."""

    if TYPE_CHECKING:
        # The attributes/methods below are provided at runtime by
        # :class:`SwgohComlinkBase` / the generated client class. Declared
        # here (type-checking only) so the mixin's contract is explicit.
        client: httpx.AsyncClient

        def _build_request_kwargs(
            self,
            method: str,
            endpoint: str,
            payload: dict[str, Any] | list[Any] | None,
            timeout: float | None,
        ) -> tuple[str, dict[str, Any]]: ...

        async def get_game_metadata(self, *args: Any, **kwargs: Any) -> Any: ...

    async def healthcheck(self, *, timeout: float = 5.0) -> bool:
        """Async mirror of :meth:`_SyncEscapeHatchMixin.healthcheck`."""
        try:
            r = await self.client.request("GET", "/enums", timeout=timeout)
        except (httpx.HTTPError, httpx.TimeoutException, httpx.RequestError):
            return False
        return bool(r.status_code == 200)

    async def raw_request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | list[Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Async escape hatch — returns the raw :class:`httpx.Response`.

        Bypasses retry, classify, decode. HMAC headers are still attached.
        """
        method_u = method.upper()
        endpoint = path.lstrip("/")
        full_path, request_kwargs = self._build_request_kwargs(method_u, endpoint, payload, timeout)
        return await self.client.request(method_u, full_path, **request_kwargs)

    def stream_game_data(
        self,
        version: str = "",
        include_pve_units: bool = True,
        request_segment: int = 0,
        enums: bool = False,
        items: str | None = None,
        device_platform: str = "Android",
    ) -> Any:
        """Return an ``httpx.AsyncClient.stream`` context manager for ``/data``.

        ``async with client.stream_game_data(version=v) as r:`` — caller
        uses ``response.aiter_bytes()``. Bypasses retry.

        Note: this method is synchronous and returns the async context
        manager. Pass ``version=`` explicitly — the metadata fallback
        needs an async call, which a non-async function can't await.
        """
        if not version:
            raise ValueError(
                "stream_game_data: pass version= explicitly. The metadata fallback "
                "needs an async call; do `v = await client._get_game_version()` first "
                "or use get_game_data() for in-memory access.",
            )
        payload = game_data_payload(
            game_version=version,
            include_pve_units=include_pve_units,
            request_segment=request_segment,
            enums=enums,
            items=items,
            device_platform=device_platform,
        )
        full_path, request_kwargs = self._build_request_kwargs("POST", "data", payload, GAME_DATA_TIMEOUT)
        return self.client.stream("POST", full_path, **request_kwargs)

    def stream_localization(
        self,
        localization_id: str,
        locale: str | None = None,
        unzip: bool = False,
        enums: bool = False,
    ) -> Any:
        """Return an ``httpx.AsyncClient.stream`` context manager for ``/localization``.

        ``localization_id`` is required — the metadata fallback would need an
        async call, which a non-async function can't await.
        """
        payload = localization_payload(localization_id, locale, unzip, enums)
        full_path, request_kwargs = self._build_request_kwargs("POST", "localization", payload, None)
        return self.client.stream("POST", full_path, **request_kwargs)

    async def get_latest_game_data_version(self) -> dict[str, Any]:
        """Get the latest game data + language bundle versions."""
        md: Any = await self.get_game_metadata()
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

    getVersion = get_latest_game_data_version
