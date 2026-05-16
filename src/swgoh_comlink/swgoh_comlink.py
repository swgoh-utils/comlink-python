# coding=utf-8
"""
Synchronous Python 3 interface for swgoh-comlink.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import httpx

from ._base import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    GAME_DATA_TIMEOUT,
    SwgohComlinkBase,
    param_alias,
    resolve_profile,
)
from ._models import (
    LEADERBOARD_DECODER,
    METADATA_DECODER,
    PLAYER_DECODER,
    UNTYPED_DECODER,
    Guild,
    LeaderboardResponse,
    Metadata,
    Player,
    decode_guild,
)
from ._payloads import (
    game_data_payload,
    game_metadata_payload,
    guild_criteria_payload,
    guild_leaderboard_payload,
    guild_payload,
    guild_search_payload,
    leaderboard_payload,
    localization_payload,
    player_arena_payload,
    player_payload,
    unit_stats_endpoint,
)
from ._retry import RetryableStatusError, retrying_sync
from .exceptions import SwgohComlinkException

__all__ = ["SwgohComlink"]


class SwgohComlink(SwgohComlinkBase):
    """Synchronous interface for the swgoh-comlink service.

    Instances of this class are used to query the Star Wars Galaxy of Heroes
    game servers for exposed endpoints via the swgoh-comlink proxy library
    running on the same host.

    Args:
        url (str): The URL where swgoh-comlink is running. Defaults to 'http://localhost:3000'
        access_key (str): The HMAC public key. Default to None which indicates HMAC is not used.
        secret_key (str): The HMAC private key. Default to None which indicates HMAC is not used.
        stats_url (str): The url of the swgoh-stats service (if used), such as 'http://localhost:3223'
        host (str): IP address or DNS name of server where the swgoh-comlink service is running
        port (int): TCP port number where the swgoh-comlink service is running [Default: 3000]
        stats_port (int): TCP port number of where the comlink-stats service is running [Default: 3223]
        verify_ssl (bool): Whether to verify TLS certificates. [Default: True]

    Notes:
        If the 'host' and 'port' parameters are provided, the 'url' and 'stats_url' parameters are ignored.

    Examples:
        Basic usage::

            comlink = SwgohComlink()
            player = comlink.get_player(allycode=123456789)

        As a context manager::

            with SwgohComlink() as comlink:
                player = comlink.get_player(allycode=123456789)
    """

    __comlink_type__ = "SwgohComlink"

    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        profile: str = "default",
        max_retries: int = DEFAULT_MAX_RETRIES,
        **kwargs: Any,
    ) -> None:
        """Construct a sync client.

        Args:
            http_client: Inject your own :class:`httpx.Client`. When provided,
                the SDK *does not* auto-close it on :meth:`close` — you own
                its lifecycle. When omitted, the SDK constructs one per the
                ``profile`` preset and closes it on :meth:`close`.
                The ``stats_url`` connection is always SDK-managed.
            profile: Connection pool preset name — ``"default"``, ``"bot"``,
                or ``"bulk"``. Ignored when ``http_client`` is supplied
                (you've already chosen your own pool).
            max_retries: Number of *additional* attempts after the first
                failure for transient errors (5xx, 408, 425, 429, connection
                drops). ``0`` disables retries. Default is 3.
            **kwargs: Passed through to :class:`SwgohComlinkBase` (``url``,
                ``access_key``, ``secret_key``, ``host``, ``port``,
                ``stats_url``, etc.).
        """
        super().__init__(**kwargs)
        self.max_retries = max_retries

        if http_client is not None:
            self.client = http_client
            self._owns_client = False
        else:
            self.client = httpx.Client(
                base_url=self.url_base,
                headers={"Content-Type": "application/json"},
                verify=self.verify_ssl,
                timeout=DEFAULT_TIMEOUT,
                limits=resolve_profile(profile),
            )
            self._owns_client = True
        self.stats_client = httpx.Client(
            base_url=self.stats_url_base,
            headers={"Content-Type": "application/json"},
            verify=self.verify_ssl,
            timeout=DEFAULT_TIMEOUT,
            limits=resolve_profile(profile),
        )

    def __enter__(self) -> SwgohComlink:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client connections we own.

        An injected ``http_client`` is NOT closed — the caller owns its
        lifecycle. The internal ``stats_client`` is always closed.
        """
        if getattr(self, "_owns_client", True):
            self.client.close()
        self.stats_client.close()

    # ── Phase 8 ergonomics ──────────────────────────────────────────────

    def healthcheck(self, *, timeout: float = 5.0) -> bool:
        """Probe the comlink ``/enums`` endpoint and report reachability.

        Returns True on a 200 response within *timeout* seconds; False on
        any HTTP error, network error, or timeout. Does NOT raise.
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
        return r.status_code == 200

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

        Args:
            method: HTTP method (``"GET"``, ``"POST"``, etc.).
            path: Endpoint path (with or without leading slash).
            payload: Optional JSON body (sent verbatim for non-GET).
            timeout: Per-request timeout override.

        Returns:
            :class:`httpx.Response`. Caller is responsible for status
            checking and decoding.
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
        items: str | None = None,
        device_platform: str = "Android",
    ) -> Any:
        """Return an ``httpx.Client.stream`` context manager for ``/data``.

        Use when the payload is too large to materialize in memory at
        once. The caller treats the returned object as a context manager
        and iterates ``response.iter_bytes()`` (or ``.iter_text()`` /
        ``.iter_lines()`` / ``.iter_raw()``).

        Bypasses the retry loop (streaming + retry doesn't compose
        cleanly — a half-streamed response can't be replayed). For
        retry-on-fail, use :meth:`get_game_data` and accept the
        in-memory cost.

        Example::

            with client.stream_game_data() as r:
                r.raise_for_status()
                with open("data.json", "wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
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
        return self.client.stream("POST", full_path, **request_kwargs)

    def stream_localization(
        self,
        localization_id: str | None = None,
        locale: str | None = None,
        unzip: bool = False,
        enums: bool = False,
    ) -> Any:
        """Return an ``httpx.Client.stream`` context manager for ``/localization``.

        Same semantics as :meth:`stream_game_data` — caller iterates
        ``response.iter_bytes()`` and is responsible for status checking.
        """
        if not localization_id:
            localization_id = self.get_latest_game_data_version()["language"]
        payload = localization_payload(localization_id, locale, unzip, enums)
        full_path, request_kwargs = self._build_request_kwargs("POST", "localization", payload, None)
        return self.client.stream("POST", full_path, **request_kwargs)

    # ── Internal request plumbing ────────────────────────────────────────

    def _request(
        self,
        method: str = "POST",
        endpoint: str = "",
        payload: dict[str, Any] | list[Any] | None = None,
        stats: bool = False,
        timeout: float | None = None,
        *,
        decoder: Callable[[bytes], Any] | None = None,
    ) -> Any:
        """Send an HTTP request to the comlink service.

        Routes every call through a single retry-wrapped send. Per-request
        ``timeout`` overrides the client default; per-call retry behavior
        is controlled by the client-wide ``max_retries`` (or rebind via
        :meth:`with_options`).

        Args:
            method: HTTP method (``"GET"`` or ``"POST"``).
            endpoint: API endpoint path (without leading slash).
            payload: JSON body (ignored for GET).
            stats: If True, route to the stats sub-service.
            timeout: Per-request timeout override.
            decoder: How to decode ``response.content``. Pass a
                ``msgspec.json.Decoder`` instance or any
                ``Callable[[bytes], T]``. Defaults to the untyped msgspec
                decoder (returns ``dict[str, Any] | list[Any]``).

        Returns:
            Whatever the *decoder* produces — typed Struct, dict, list,
            or anything else.

        Raises:
            SwgohComlinkException: Any network, status, or decode error
                that survived the retry loop.
        """
        method_u = method.upper()
        full_path, request_kwargs = self._build_request_kwargs(method_u, endpoint, payload, timeout)
        client = self.stats_client if stats else self.client

        def attempt() -> httpx.Response:
            r = client.request(method_u, full_path, **request_kwargs)
            self._classify_response(r)
            return r

        try:
            response = retrying_sync(
                attempt,
                attempts=self.max_retries + 1,
                on=httpx.RequestError,
            )
        except (httpx.RequestError, RetryableStatusError) as e:
            raise self._map_error(e) from e
        except SwgohComlinkException:
            raise

        decode = decoder if decoder is not None else UNTYPED_DECODER.decode
        try:
            return decode(response.content)
        except Exception as e:  # noqa: BLE001 — msgspec.DecodeError, ValidationError, etc.
            raise SwgohComlinkException(f"failed to decode response body: {e}") from e

    def _post(
        self,
        endpoint: str = "",
        payload: dict[str, Any] | list[Any] | None = None,
        stats: bool = False,
        timeout: float | None = None,
        *,
        decoder: Callable[[bytes], Any] | None = None,
    ) -> Any:
        """Send a POST request to the comlink service.

        Convenience wrapper around :meth:`_request`. Forwards ``decoder=``
        so typed-endpoint methods can opt into a specific Struct decoder.
        """
        return self._request(
            method="POST",
            endpoint=endpoint,
            payload=payload,
            stats=stats,
            timeout=timeout,
            decoder=decoder,
        )

    def _get_game_version(self) -> str:
        # v3: get_game_metadata returns a Metadata Struct by default (raw=False).
        md = cast(Metadata, self.get_game_metadata())
        return str(md.latest_gamedata_version)

    # ── Public API methods ───────────────────────────────────────────────

    def get_unit_stats(
        self,
        request_payload: dict[str, Any] | list[Any],
        flags: list[str] | None = None,
        language: str | None = None,
    ) -> list[Any] | dict[str, Any]:
        """Calculate unit stats via the swgoh-stats sub-service.

        Args:
            request_payload: Single unit dict or list of unit dicts.
            flags: Optional list of recognized stat-calc flags.
            language: Optional locale ("eng_us").
        """
        if isinstance(request_payload, dict):
            request_payload = [request_payload]
        return cast(
            "list[Any] | dict[str, Any]",
            self._post(endpoint=unit_stats_endpoint(flags, language), payload=request_payload, stats=True),
        )

    def get_enums(self) -> dict[str, Any]:
        """Get the game data enums. Uses GET (not POST)."""
        return cast(dict[str, Any], self._request(method="GET", endpoint="enums"))

    getEnums = get_enums

    def get_events(self, enums: bool = False) -> dict[str, list[Any]]:
        """Get the events game data."""
        return cast(
            dict[str, list[Any]],
            self._post(endpoint="getEvents", payload={"payload": {}, "enums": enums}),
        )

    getEvents = get_events

    def get_game_data(
        self,
        version: str = "",
        include_pve_units: bool = True,
        request_segment: int = 0,
        enums: bool = False,
        items: str | None = None,
        device_platform: str = "Android",
    ) -> dict[str, Any]:
        """Get game data. ``version=""`` triggers a metadata fetch for the latest version."""
        game_version = version or self._get_game_version()
        payload = game_data_payload(
            game_version=game_version,
            include_pve_units=include_pve_units,
            request_segment=request_segment,
            enums=enums,
            items=items,
            device_platform=device_platform,
        )
        return cast(dict[str, Any], self._post(endpoint="data", payload=payload, timeout=GAME_DATA_TIMEOUT))

    getGameData = get_game_data

    def get_localization(
        self,
        localization_id: str | None = None,
        locale: str | None = None,
        unzip: bool = False,
        enums: bool = False,
    ) -> dict[str, Any]:
        """Get localization data. ``localization_id=None`` triggers a metadata fetch."""
        if not localization_id:
            localization_id = self.get_latest_game_data_version()["language"]
        return cast(
            dict[str, Any],
            self._post(endpoint="localization", payload=localization_payload(localization_id, locale, unzip, enums)),
        )

    getLocalization = get_localization
    getLocalizationBundle = get_localization
    get_localization_bundle = get_localization

    def get_game_metadata(
        self,
        client_specs: dict[str, Any] | None = None,
        enums: bool = False,
        *,
        raw: bool = False,
    ) -> Metadata | dict[str, Any]:
        """Get game metadata. Returns :class:`Metadata` by default; ``raw=True`` for the v2 dict."""
        decoder = None if raw else METADATA_DECODER.decode
        return cast(
            "Metadata | dict[str, Any]",
            self._post(endpoint="metadata", payload=game_metadata_payload(client_specs, enums), decoder=decoder),
        )

    getGameMetaData = get_game_metadata
    getMetaData = get_game_metadata
    get_metadata = get_game_metadata

    def get_player(
        self,
        allycode: str | int | None = None,
        player_id: str | None = None,
        enums: bool = False,
        *,
        raw: bool = False,
    ) -> Player | dict[str, Any]:
        """Get player info. Returns :class:`Player` by default; ``raw=True`` for the v2 dict."""
        decoder = None if raw else PLAYER_DECODER.decode
        return cast(
            "Player | dict[str, Any]",
            self._post(endpoint="player", payload=player_payload(allycode, player_id, enums), decoder=decoder),
        )

    getPlayer = get_player

    @param_alias(param="player_details_only", alias="playerDetailsOnly")
    def get_player_arena(
        self,
        allycode: str | int | None = None,
        player_id: str | None = None,
        player_details_only: bool = False,
        enums: bool = False,
    ) -> dict[str, Any]:
        """Get player arena info."""
        return cast(
            dict[str, Any],
            self._post(
                endpoint="playerArena", payload=player_arena_payload(allycode, player_id, player_details_only, enums)
            ),
        )

    get_arena = get_player_arena
    get_player_arena_profile = get_player_arena
    getPlayerArena = get_player_arena
    getPlayerArenaProfile = get_player_arena

    @param_alias(param="include_recent_guild_activity_info", alias="includeRecent")
    def get_guild(
        self,
        guild_id: str,
        include_recent_guild_activity_info: bool = False,
        enums: bool = False,
        *,
        raw: bool = False,
    ) -> Guild | dict[str, Any]:
        """Get guild info. Returns :class:`Guild` by default; ``raw=True`` unwraps the ``"guild"`` envelope into a v2-shaped dict."""
        payload = guild_payload(guild_id, include_recent_guild_activity_info, enums)
        if raw:
            guild: dict[str, Any] = cast(dict[str, Any], self._post(endpoint="guild", payload=payload))
            return guild.get("guild", guild) if "guild" in guild else guild
        return cast(Guild, self._post(endpoint="guild", payload=payload, decoder=decode_guild))

    getGuild = get_guild

    def get_guilds_by_name(
        self,
        name: str,
        start_index: int = 0,
        count: int = 10,
        enums: bool = False,
    ) -> dict[str, Any]:
        """Search for guild by name."""
        return cast(
            dict[str, Any],
            self._post(endpoint="getGuilds", payload=guild_search_payload(name, start_index, count, enums)),
        )

    getGuildByName = get_guilds_by_name

    def get_guilds_by_criteria(
        self,
        search_criteria: dict[str, Any],
        start_index: int = 0,
        count: int = 10,
        enums: bool = False,
    ) -> dict[str, Any]:
        """Search for guild by criteria dict."""
        return cast(
            dict[str, Any],
            self._post(
                endpoint="getGuilds", payload=guild_criteria_payload(search_criteria, start_index, count, enums)
            ),
        )

    getGuildByCriteria = get_guilds_by_criteria

    def get_leaderboard(
        self,
        leaderboard_type: int,
        *,
        league: int | str | None = None,
        division: int | str | None = None,
        event_instance_id: str | None = None,
        group_id: str | None = None,
        enums: bool = False,
        raw: bool = False,
    ) -> LeaderboardResponse | dict[str, Any]:
        """Get GAC leaderboard (type 4) or global leaderboard (type 6)."""
        decoder = None if raw else LEADERBOARD_DECODER.decode
        payload = leaderboard_payload(leaderboard_type, league, division, event_instance_id, group_id, enums)
        return cast(
            "LeaderboardResponse | dict[str, Any]",
            self._post(endpoint="getLeaderboard", payload=payload, decoder=decoder),
        )

    getLeaderboard = get_leaderboard
    get_gac_leaderboard = get_leaderboard
    getGacLeaderboard = get_leaderboard

    def get_guild_leaderboard(
        self,
        leaderboard_id: list[dict[str, Any]],
        count: int = 200,
        enums: bool = False,
    ) -> dict[str, Any]:
        """Fetch the guild leaderboard for a given ID."""
        return cast(
            dict[str, Any],
            self._post(endpoint="getGuildLeaderboard", payload=guild_leaderboard_payload(leaderboard_id, count, enums)),
        )

    getGuildLeaderboard = get_guild_leaderboard

    def get_name_spaces(self, only_compatible: bool = False, enums: bool = False) -> dict[str, Any]:
        """Fetch namespaces."""
        return cast(
            dict[str, Any],
            self._post(
                endpoint="getNameSpaces", payload={"payload": {"onlyCompatible": only_compatible}, "enums": enums}
            ),
        )

    def get_segmented_content(
        self,
        content_name_space: str = "current",
        accept_language: str = "ENG_US",
        enums: bool = False,
    ) -> dict[str, Any]:
        """Retrieve segmented content from a namespace."""
        return cast(
            dict[str, Any],
            self._post(
                endpoint="getSegmentedContent",
                payload={
                    "payload": {"contentNameSpace": content_name_space, "acceptLanguage": accept_language},
                    "enums": enums,
                },
            ),
        )

    # ── Helper methods ───────────────────────────────────────────────────

    def get_latest_game_data_version(self) -> dict[str, Any]:
        """Get the latest game data and language bundle versions.

        Returns:
            Dictionary with 'game' and 'language' version strings.
        """
        # v3: get_game_metadata returns a Metadata Struct by default (raw=False).
        current_metadata = cast(Metadata, self.get_game_metadata())
        return {
            "game": current_metadata.latest_gamedata_version,
            "language": current_metadata.latest_localization_bundle_version,
        }

    # alias for shorthand call
    getVersion = get_latest_game_data_version
