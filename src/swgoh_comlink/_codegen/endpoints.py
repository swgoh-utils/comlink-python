# coding=utf-8
"""Endpoint manifest — single source of truth for the four generated clients.

Editing this file requires regenerating the four client modules::

    make generate
    # or:
    uv run python -m swgoh_comlink._codegen.generate

A pre-commit hook enforces ``git diff --exit-code`` after regeneration so
manifest edits can't be committed without their corresponding generated
output.

Conventions
-----------
- Method names + parameter names are snake_case Python.
- ``typed_decoder`` / ``typed_decoder_callable`` populate the typed-client
  variant only; absent means "always returns dict, even in the typed module."
- ``aliases`` are emitted as ``getPlayer = get_player`` after the method.
- ``pre_fetch_version=True`` emits the ``version or self._get_game_version()``
  prologue (sync) / ``version or await self._get_game_version()`` (async).
- ``pre_fetch_locale_bundle=True`` emits the localization-id fallback.
- ``cached_enums`` / ``refresh_version_cache`` wire an endpoint into the
  instance caches (``enums`` and the /metadata version cache).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Param:
    """One endpoint parameter."""

    name: str
    """snake_case Python name."""

    type: str
    """Full type annotation as a string (e.g. ``"int | None"``)."""

    default: str | None = None
    """Python literal as string (``"None"``, ``"False"``, ``"0"``). ``None`` = required."""

    keyword_only: bool = False
    """True if the param must appear after ``*`` in the signature."""


@dataclass(frozen=True)
class Endpoint:
    """One uniform endpoint — covers the bulk of the client surface."""

    name: str
    """snake_case method name."""

    http_method: str
    """``"GET"`` or ``"POST"``."""

    path: str
    """Comlink endpoint path (no leading slash)."""

    docstring: str
    """One-line method docstring."""

    params: tuple[Param, ...] = ()
    """Positional + keyword parameters."""

    # ── Payload construction (exactly one populated) ───────────────────
    payload_builder: str | None = None
    """Name of a function in ``_payloads.py`` (e.g. ``"player_payload"``)."""

    payload_args: tuple[str, ...] | None = None
    """Param names to pass to the payload builder (defaults to all ``params``)."""

    inline_payload: str | None = None
    """Raw Python expression — used when no builder fits (e.g. ``"{"payload": ...}"``)."""

    # ── Decoder dispatch (typed surface only) ──────────────────────────
    typed_decoder: str | None = None
    """Decoder symbol from ``_models.py`` (e.g. ``"PLAYER_DECODER"``)."""

    typed_decoder_callable: str | None = None
    """Module-level callable to use directly (e.g. ``"decode_guild"`` for envelope unwrap)."""

    typed_return: str | None = None
    """Typed return type name (e.g. ``"Player"``). ``None`` = no typed variant."""

    dict_decoder_callable: str | None = None
    """If set, the dict-default client uses this callable as its decoder
    (e.g. ``"decode_guild_dict"`` to unwrap the ``{"guild": {...}}``
    envelope before returning to the caller). Defaults to the untyped
    msgspec decoder (returns the raw dict shape)."""

    # ── Quirks (flags) ─────────────────────────────────────────────────
    stats_sub_service: bool = False
    """Routes to ``self.stats_client`` (used by ``get_unit_stats``)."""

    timeout_const: str | None = None
    """Constant from ``_base.py`` (e.g. ``"GAME_DATA_TIMEOUT"``)."""

    pre_fetch_version: bool = False
    """Emit ``game_version = version or [await ]self._get_game_version()``."""

    pre_fetch_locale_bundle: bool = False
    """Emit the ``localization_id`` fallback prologue."""

    param_aliases: Mapping[str, str] = field(default_factory=dict)
    """``{python_name: wire_name}`` for the ``@param_alias`` decorator."""

    endpoint_builder: str | None = None
    """If set, use this callable from ``_payloads.py`` to build the endpoint string at call time."""

    endpoint_builder_args: tuple[str, ...] = ()
    """Param names to pass to ``endpoint_builder``."""

    payload_var_name: str | None = None
    """If set, the payload is passed as this argument (e.g. ``"request_payload"`` for ``get_unit_stats``)."""

    list_wrap_single_dict: bool = False
    """If True (only ``get_unit_stats``): wrap a single-dict payload in a list."""

    cached_enums: bool = False
    """If True (only ``get_enums``): serve the response from the per-game-data-version
    ``enums`` cache. The endpoint must declare a ``refresh`` parameter."""

    refresh_version_cache: bool = False
    """If True (only ``get_game_metadata``): store the versions from a non-enums
    response in the instance version cache."""

    # ── API surface ────────────────────────────────────────────────────
    aliases: tuple[str, ...] = ()
    """camelCase / convenience shims emitted as ``alias = method_name``."""


# ── Manifest ────────────────────────────────────────────────────────────


ENDPOINTS: tuple[Endpoint, ...] = (
    Endpoint(
        name="get_unit_stats",
        http_method="POST",
        path="",  # built via endpoint_builder
        docstring="Calculate unit stats via the swgoh-stats sub-service.",
        params=(
            Param("request_payload", "dict[str, Any] | list[Any]"),
            Param("flags", "list[str] | None", default="None"),
            Param("language", "str | None", default="None"),
        ),
        endpoint_builder="unit_stats_endpoint",
        endpoint_builder_args=("flags", "language"),
        payload_var_name="request_payload",
        list_wrap_single_dict=True,
        stats_sub_service=True,
    ),
    Endpoint(
        name="get_enums",
        http_method="GET",
        path="enums",
        docstring=(
            "Get the game data enums. Uses GET (not POST).\n\n"
            "        The response is cached on the instance as ``enums``, with the game data version it was\n"
            "        fetched under as ``enums_version``. Later calls return the cached response while the game\n"
            "        data version (read through the version cache, see ``version_cache_ttl``) is unchanged.\n"
            "        When the version cannot be determined, the enums are fetched and returned uncached.\n"
            "        ``refresh=True`` fetches the version and the enums again. A cached response is the same\n"
            "        object as ``enums``: copy it before changing it.\n"
            "        "
        ),
        params=(Param("refresh", "bool", default="False"),),
        cached_enums=True,
        aliases=("getEnums",),
    ),
    Endpoint(
        name="get_events",
        http_method="POST",
        path="getEvents",
        docstring="Get the events game data.",
        params=(Param("enums", "bool", default="False"),),
        inline_payload='{"payload": {}, "enums": enums}',
        aliases=("getEvents",),
    ),
    Endpoint(
        name="get_game_data",
        http_method="POST",
        path="data",
        docstring='Get game data. ``version=""`` uses the latest version from the version cache (see ``version_cache_ttl``).',
        params=(
            Param("version", "str", default='""'),
            Param("include_pve_units", "bool", default="True"),
            Param("request_segment", "int", default="0"),
            Param("enums", "bool", default="False"),
            Param("items", "str | DataItems | int | None", default="None"),
            Param("device_platform", "str", default='"Android"'),
        ),
        payload_builder="game_data_payload",
        payload_args=("game_version", "include_pve_units", "request_segment", "enums", "items", "device_platform"),
        pre_fetch_version=True,
        timeout_const="GAME_DATA_TIMEOUT",
        aliases=("getGameData",),
    ),
    Endpoint(
        name="get_localization",
        http_method="POST",
        path="localization",
        docstring="Get localization bundle. ``localization_id=None`` uses the latest bundle version from the version cache.",
        params=(
            Param("localization_id", "str | None", default="None"),
            Param("locale", "str | None", default="None"),
            Param("unzip", "bool", default="False"),
            Param("enums", "bool", default="False"),
        ),
        payload_builder="localization_payload",
        payload_args=("localization_id", "locale", "unzip", "enums"),
        pre_fetch_locale_bundle=True,
        aliases=("getLocalization", "getLocalizationBundle", "get_localization_bundle"),
    ),
    Endpoint(
        name="get_game_metadata",
        http_method="POST",
        path="metadata",
        docstring="Get game metadata. Returns :class:`Metadata` by default (typed surface); ``raw=True`` for the v2 dict.",
        params=(
            Param("client_specs", "dict[str, Any] | None", default="None"),
            Param("enums", "bool", default="False"),
        ),
        payload_builder="game_metadata_payload",
        refresh_version_cache=True,
        typed_decoder="METADATA_DECODER",
        typed_return="Metadata",
        aliases=("getGameMetaData", "getMetaData", "get_metadata"),
    ),
    Endpoint(
        name="get_player",
        http_method="POST",
        path="player",
        docstring="Get player info. Returns :class:`Player` by default (typed surface); ``raw=True`` for the v2 dict.",
        params=(
            Param("allycode", "str | int | None", default="None"),
            Param("player_id", "str | None", default="None"),
            Param("enums", "bool", default="False"),
        ),
        payload_builder="player_payload",
        typed_decoder="PLAYER_DECODER",
        typed_return="Player",
        aliases=("getPlayer",),
    ),
    Endpoint(
        name="get_player_arena",
        http_method="POST",
        path="playerArena",
        docstring="Get player arena info.",
        params=(
            Param("allycode", "str | int | None", default="None"),
            Param("player_id", "str | None", default="None"),
            Param("player_details_only", "bool", default="False"),
            Param("enums", "bool", default="False"),
        ),
        payload_builder="player_arena_payload",
        param_aliases={"player_details_only": "playerDetailsOnly"},
        aliases=("get_arena", "get_player_arena_profile", "getPlayerArena", "getPlayerArenaProfile"),
    ),
    Endpoint(
        name="get_guild",
        http_method="POST",
        path="guild",
        docstring='Get guild info. Returns :class:`Guild` by default (typed surface); ``raw=True`` unwraps the ``"guild"`` envelope into a v2-shaped dict.',
        params=(
            Param("guild_id", "str"),
            Param("include_recent_guild_activity_info", "bool", default="False"),
            Param("enums", "bool", default="False"),
        ),
        payload_builder="guild_payload",
        typed_decoder_callable="decode_guild",
        typed_return="Guild",
        dict_decoder_callable="decode_guild_dict",
        param_aliases={"include_recent_guild_activity_info": "includeRecent"},
        aliases=("getGuild",),
    ),
    Endpoint(
        name="get_guilds_by_name",
        http_method="POST",
        path="getGuilds",
        docstring="Search for guild by name.",
        params=(
            Param("name", "str"),
            Param("start_index", "int", default="0"),
            Param("count", "int", default="10"),
            Param("enums", "bool", default="False"),
        ),
        payload_builder="guild_search_payload",
        aliases=("getGuildByName",),
    ),
    Endpoint(
        name="get_guilds_by_criteria",
        http_method="POST",
        path="getGuilds",
        docstring="Search for guild by criteria dict.",
        params=(
            Param("search_criteria", "dict[str, Any]"),
            Param("start_index", "int", default="0"),
            Param("count", "int", default="10"),
            Param("enums", "bool", default="False"),
        ),
        payload_builder="guild_criteria_payload",
        aliases=("getGuildByCriteria",),
    ),
    Endpoint(
        name="get_leaderboard",
        http_method="POST",
        path="getLeaderboard",
        docstring="Get GAC leaderboard (type 4) or global leaderboard (type 6).",
        params=(
            Param("leaderboard_type", "int"),
            Param("league", "int | str | None", default="None", keyword_only=True),
            Param("division", "int | str | None", default="None", keyword_only=True),
            Param("event_instance_id", "str | None", default="None", keyword_only=True),
            Param("group_id", "str | None", default="None", keyword_only=True),
            Param("enums", "bool", default="False", keyword_only=True),
        ),
        payload_builder="leaderboard_payload",
        typed_decoder="LEADERBOARD_DECODER",
        typed_return="LeaderboardResponse",
        aliases=("getLeaderboard", "get_gac_leaderboard", "getGacLeaderboard"),
    ),
    Endpoint(
        name="get_guild_leaderboard",
        http_method="POST",
        path="getGuildLeaderboard",
        docstring="Fetch the guild leaderboard for a given ID.",
        params=(
            Param("leaderboard_id", "list[dict[str, Any]]"),
            Param("count", "int", default="200"),
            Param("enums", "bool", default="False"),
        ),
        payload_builder="guild_leaderboard_payload",
        aliases=("getGuildLeaderboard",),
    ),
    Endpoint(
        name="get_name_spaces",
        http_method="POST",
        path="getNameSpaces",
        docstring="Fetch namespaces.",
        params=(
            Param("only_compatible", "bool", default="False"),
            Param("enums", "bool", default="False"),
        ),
        inline_payload='{"payload": {"onlyCompatible": only_compatible}, "enums": enums}',
    ),
    Endpoint(
        name="get_segmented_content",
        http_method="POST",
        path="getSegmentedContent",
        docstring="Retrieve segmented content from a namespace.",
        params=(
            Param("content_name_space", "str", default='"current"'),
            Param("accept_language", "str", default='"ENG_US"'),
            Param("enums", "bool", default="False"),
        ),
        inline_payload=(
            '{"payload": {"contentNameSpace": content_name_space, "acceptLanguage": accept_language}, "enums": enums}'
        ),
    ),
)


__all__ = ["ENDPOINTS", "Endpoint", "Param"]
