"""Request-building tests run against both the sync and async Comlink clients.

Every test receives a client from the ``make_comlink``/``comlink`` fixtures, which are
parametrized over :class:`SwgohComlink` and :class:`SwgohComlinkAsync`, and drives it
through :func:`call` so one test body covers both implementations.
"""

from __future__ import annotations

import hashlib
import hmac
import inspect
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx
import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync
from swgoh_comlink.exceptions import SwgohComlinkException, SwgohComlinkValueError

Client = SwgohComlink | SwgohComlinkAsync

URL = "http://localhost:3000"
STATS_URL = "http://localhost:3223"
# get_enums() first reads the game data version through /metadata, then fetches /enums.
ENUMS_URL = f"{URL}/enums"
METADATA_URL = f"{URL}/metadata"
METADATA = {"latestGamedataVersion": "game-v1", "latestLocalizationBundleVersion": "lang-v1"}


@pytest.fixture(params=[SwgohComlink, SwgohComlinkAsync], ids=["sync", "async"])
async def make_comlink(request: pytest.FixtureRequest) -> AsyncIterator[Callable[..., Client]]:
    """Build clients of the parametrized type and close every one of them on teardown."""
    clients: list[Client] = []

    def factory(**kwargs: Any) -> Client:
        client = request.param(**{"url": URL, "stats_url": STATS_URL, **kwargs})
        clients.append(client)
        return client

    yield factory
    for client in clients:
        if isinstance(client, SwgohComlinkAsync):
            await client.aclose()
        else:
            client.close()


@pytest.fixture
def comlink(make_comlink: Callable[..., Client]) -> Client:
    return make_comlink()


async def call(client: Client, method: str, /, **kwargs: Any) -> Any:
    """Call ``method`` on either client, awaiting the result when the client is async."""
    result = getattr(client, method)(**kwargs)
    return await result if inspect.isawaitable(result) else result


# ── Request shape ────────────────────────────────────────────────────────

REQUEST_CASES = [
    pytest.param(
        "get_player",
        {"allycode": 123456789},
        f"{URL}/player",
        {"payload": {"allyCode": "123456789"}, "enums": False},
        id="player-allycode",
    ),
    pytest.param(
        "get_player",
        {"player_id": "abc-123"},
        f"{URL}/player",
        {"payload": {"playerId": "abc-123"}, "enums": False},
        id="player-id",
    ),
    pytest.param(
        "get_game_data",
        {"version": "1.2.3", "include_pve_units": False, "request_segment": 4, "enums": True},
        f"{URL}/data",
        {
            "payload": {
                "version": "1.2.3",
                "devicePlatform": "Android",
                "includePveUnits": False,
                "requestSegment": 4,
            },
            "enums": True,
        },
        id="game-data",
    ),
    pytest.param(
        "get_guild",
        {"guild_id": "guild-1", "include_recent_guild_activity_info": True},
        f"{URL}/guild",
        {"payload": {"guildId": "guild-1", "includeRecentGuildActivityInfo": True}, "enums": False},
        id="guild",
    ),
    pytest.param(
        "get_guild",
        {"guild_id": "guild-1", "includeRecent": True},
        f"{URL}/guild",
        {"payload": {"guildId": "guild-1", "includeRecentGuildActivityInfo": True}, "enums": False},
        id="guild-alias",
    ),
    pytest.param(
        "get_events",
        {"enums": True},
        f"{URL}/getEvents",
        {"payload": {}, "enums": True},
        id="events",
    ),
    pytest.param(
        "get_localization",
        {"localization_id": "loc-v1"},
        f"{URL}/localization",
        {"unzip": False, "enums": False, "payload": {"id": "loc-v1"}},
        id="localization",
    ),
    pytest.param(
        "get_localization",
        {"localization_id": "loc-v1", "locale": "fra_fr"},
        f"{URL}/localization",
        {"unzip": False, "enums": False, "payload": {"id": "loc-v1:FRA_FR"}},
        id="localization-locale",
    ),
    pytest.param("get_game_metadata", {}, METADATA_URL, {}, id="metadata"),
    pytest.param(
        "get_game_metadata",
        {"client_specs": {"platform": "Android", "bundleId": "com.ea.game"}, "enums": True},
        METADATA_URL,
        {"payload": {"clientSpecs": {"platform": "Android", "bundleId": "com.ea.game"}}, "enums": True},
        id="metadata-client-specs",
    ),
    pytest.param(
        "get_player_arena",
        {"allycode": 123456789},
        f"{URL}/playerArena",
        {"payload": {"allyCode": "123456789", "playerDetailsOnly": False}, "enums": False},
        id="arena",
    ),
    pytest.param(
        "get_player_arena",
        {"allycode": 123456789, "player_details_only": True},
        f"{URL}/playerArena",
        {"payload": {"allyCode": "123456789", "playerDetailsOnly": True}, "enums": False},
        id="arena-details-only",
    ),
    pytest.param(
        "get_player_arena",
        {"allycode": 123456789, "playerDetailsOnly": True},
        f"{URL}/playerArena",
        {"payload": {"allyCode": "123456789", "playerDetailsOnly": True}, "enums": False},
        id="arena-alias-true",
    ),
    # Regression guard: param_alias once dropped a falsy camelCase alias value.
    pytest.param(
        "get_player_arena",
        {"allycode": 123456789, "playerDetailsOnly": False},
        f"{URL}/playerArena",
        {"payload": {"allyCode": "123456789", "playerDetailsOnly": False}, "enums": False},
        id="arena-alias-false",
    ),
    pytest.param(
        "get_guilds_by_name",
        {"name": "Test Guild", "start_index": 5, "count": 20},
        f"{URL}/getGuilds",
        {"payload": {"name": "Test Guild", "filterType": 4, "startIndex": 5, "count": 20}, "enums": False},
        id="guilds-by-name",
    ),
    pytest.param(
        "get_guilds_by_criteria",
        {"search_criteria": {"minMemberCount": 40}},
        f"{URL}/getGuilds",
        {
            "payload": {"searchCriteria": {"minMemberCount": 40}, "filterType": 5, "startIndex": 0, "count": 10},
            "enums": False,
        },
        id="guilds-by-criteria",
    ),
    pytest.param(
        "get_leaderboard",
        {"leaderboard_type": 4, "event_instance_id": "event1", "group_id": "group1"},
        f"{URL}/getLeaderboard",
        {"payload": {"leaderboardType": 4, "eventInstanceId": "event1", "groupId": "group1"}, "enums": False},
        id="leaderboard-type-4",
    ),
    pytest.param(
        "get_leaderboard",
        {"leaderboard_type": 6, "league": "kyber", "division": "1"},
        f"{URL}/getLeaderboard",
        {"payload": {"leaderboardType": 6, "league": 100, "division": 25}, "enums": False},
        id="leaderboard-type-6-str-division",
    ),
    pytest.param(
        "get_leaderboard",
        {"leaderboard_type": 6, "league": "carbonite", "division": 3},
        f"{URL}/getLeaderboard",
        {"payload": {"leaderboardType": 6, "league": 20, "division": 15}, "enums": False},
        id="leaderboard-type-6-int-division",
    ),
    pytest.param(
        "get_guild_leaderboard",
        {"leaderboard_id": [{"id": "lb1"}], "count": 50},
        f"{URL}/getGuildLeaderboard",
        {"payload": {"leaderboardId": [{"id": "lb1"}], "count": 50}, "enums": False},
        id="guild-leaderboard",
    ),
    pytest.param(
        "get_name_spaces",
        {"only_compatible": True},
        f"{URL}/getNameSpaces",
        {"payload": {"onlyCompatible": True}, "enums": False},
        id="name-spaces",
    ),
    pytest.param(
        "get_segmented_content",
        {"content_name_space": "test", "accept_language": "FRA_FR"},
        f"{URL}/getSegmentedContent",
        {"payload": {"contentNameSpace": "test", "acceptLanguage": "FRA_FR"}, "enums": False},
        id="segmented-content",
    ),
    # A dict payload is wrapped in a list before posting.
    pytest.param(
        "get_unit_stats",
        {"request_payload": {"unit": "data"}},
        f"{STATS_URL}/api",
        [{"unit": "data"}],
        id="unit-stats-dict",
    ),
    pytest.param(
        "get_unit_stats",
        {"request_payload": [{"unit": "data"}]},
        f"{STATS_URL}/api",
        [{"unit": "data"}],
        id="unit-stats-list",
    ),
    pytest.param(
        "get_unit_stats",
        {"request_payload": [{"unit": "data"}], "flags": ["calcGP", "gameStyle"], "language": "eng_us"},
        f"{STATS_URL}/api?flags=calcGP,gameStyle&language=eng_us",
        [{"unit": "data"}],
        id="unit-stats-flags",
    ),
]


@pytest.mark.parametrize(("method", "kwargs", "url", "body"), REQUEST_CASES)
async def test_request_shape(
    comlink: Client,
    httpx_mock: HTTPXMock,
    method: str,
    kwargs: dict[str, Any],
    url: str,
    body: Any,
) -> None:
    httpx_mock.add_response(json={"ok": 1})

    out = await call(comlink, method, **kwargs)

    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert str(request.url) == url
    assert json.loads(request.content) == body
    assert out == {"ok": 1}


# ── Response handling ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        pytest.param({"guild": {"profile": {"name": "Wrapped"}}}, {"profile": {"name": "Wrapped"}}, id="unwraps"),
        pytest.param({"profile": {"name": "Direct"}}, {"profile": {"name": "Direct"}}, id="no-guild-key"),
    ],
)
async def test_get_guild_unwraps_guild_key(
    comlink: Client, httpx_mock: HTTPXMock, response: dict[str, Any], expected: dict[str, Any]
) -> None:
    httpx_mock.add_response(json=response)

    assert await call(comlink, "get_guild", guild_id="guild-1") == expected


@pytest.mark.parametrize(
    ("method", "metadata", "endpoint", "payload_key", "version"),
    [
        pytest.param(
            "get_game_data", {"latestGamedataVersion": "auto-1.0"}, "data", "version", "auto-1.0", id="game-data"
        ),
        pytest.param("get_localization", METADATA, "localization", "id", "lang-v1", id="localization"),
    ],
)
async def test_missing_version_is_read_from_metadata(
    comlink: Client,
    httpx_mock: HTTPXMock,
    method: str,
    metadata: dict[str, str],
    endpoint: str,
    payload_key: str,
    version: str,
) -> None:
    httpx_mock.add_response(url=METADATA_URL, json=metadata)
    httpx_mock.add_response(url=f"{URL}/{endpoint}", json={})

    await call(comlink, method)

    first, second = httpx_mock.get_requests()
    assert str(first.url) == METADATA_URL
    assert str(second.url) == f"{URL}/{endpoint}"
    assert json.loads(second.content)["payload"][payload_key] == version


async def test_get_enums_sends_get_without_body(comlink: Client, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=METADATA_URL, json=METADATA)
    httpx_mock.add_response(url=ENUMS_URL, json={"CombatType": {"1": "CHARACTER"}})

    out = await call(comlink, "get_enums")

    request = httpx_mock.get_request(url=ENUMS_URL)
    assert request is not None
    assert request.method == "GET"
    assert request.content == b""
    assert out == {"CombatType": {"1": "CHARACTER"}}


async def test_get_latest_game_data_version(comlink: Client, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"latestGamedataVersion": "game-v2", "latestLocalizationBundleVersion": "lang-v2"})

    assert await call(comlink, "get_latest_game_data_version") == {"game": "game-v2", "language": "lang-v2"}


# ── Errors ───────────────────────────────────────────────────────────────


async def test_request_error_raises_comlink_exception(comlink: Client, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"), is_reusable=True)

    with pytest.raises(SwgohComlinkException):
        await call(comlink, "get_enums")


@pytest.mark.parametrize(
    ("method", "kwargs"),
    [
        pytest.param("get_player", {}, id="player-no-identifier"),
        pytest.param("get_game_data", {"version": "v1", "request_segment": 5}, id="game-data-segment-too-high"),
        pytest.param("get_game_data", {"version": "v1", "request_segment": -1}, id="game-data-segment-negative"),
        pytest.param("get_unit_stats", {"request_payload": [{}], "flags": ["invalidFlag"]}, id="unit-stats-bad-flag"),
        pytest.param("get_guild", {"guild_id": ""}, id="guild-empty-id"),
    ],
)
async def test_invalid_arguments_raise_before_any_request(
    comlink: Client, httpx_mock: HTTPXMock, method: str, kwargs: dict[str, Any]
) -> None:
    with pytest.raises(SwgohComlinkValueError):
        await call(comlink, method, **kwargs)

    assert httpx_mock.get_requests() == []


# ── Authentication ───────────────────────────────────────────────────────


def _comlink_signature(request: httpx.Request, secret_key: str) -> str:
    """Recompute an HMAC signature the way Comlink verifies it: from the request as it arrived.

    Comlink re-serializes the parsed JSON body compactly, and a bodiless request hashes ``""``.
    Deriving the expected value from the wire (not from the client's own inputs) catches any
    drift between the bytes that were signed and the bytes that were sent (see #51).
    """
    body = json.loads(request.content) if request.content else ""
    signature = hmac.new(secret_key.encode(), digestmod=hashlib.sha256)
    signature.update(request.headers["X-Date"].encode())
    signature.update(request.method.encode())
    signature.update(request.url.path.encode())
    signature.update(hashlib.md5(json.dumps(body, separators=(",", ":")).encode()).hexdigest().encode())  # noqa: S324
    return signature.hexdigest()


@pytest.mark.parametrize(
    ("method", "kwargs"),
    [
        pytest.param("get_enums", {}, id="get-without-body"),
        pytest.param("get_player", {"allycode": 123456789}, id="post-with-body"),
        pytest.param("get_game_metadata", {}, id="post-with-empty-body"),
    ],
)
async def test_hmac_signature_matches_the_request_sent(
    make_comlink: Callable[..., Client], httpx_mock: HTTPXMock, method: str, kwargs: dict[str, Any]
) -> None:
    httpx_mock.add_response(json=METADATA, is_reusable=True)

    await call(make_comlink(access_key="pub", secret_key="priv"), method, **kwargs)

    requests = httpx_mock.get_requests()
    assert requests
    for request in requests:
        expected = f"HMAC-SHA256 Credential=pub,Signature={_comlink_signature(request, 'priv')}"
        assert request.headers["Authorization"] == expected, request.url


# ── Client construction ──────────────────────────────────────────────────


@pytest.mark.parametrize("verify_ssl", [True, False])
async def test_verify_ssl_reaches_both_http_clients(
    make_comlink: Callable[..., Client], monkeypatch: pytest.MonkeyPatch, verify_ssl: bool
) -> None:
    seen: list[Any] = []

    def recording(constructor: Callable[..., Any]) -> Callable[..., Any]:
        def construct(*args: Any, **kwargs: Any) -> Any:
            seen.append(kwargs.get("verify"))
            return constructor(*args, **kwargs)

        return construct

    monkeypatch.setattr(httpx, "Client", recording(httpx.Client))
    monkeypatch.setattr(httpx, "AsyncClient", recording(httpx.AsyncClient))

    make_comlink(verify_ssl=verify_ssl)

    # One HTTP client for Comlink, one for the stats service.
    assert seen == [verify_ssl, verify_ssl]


# ── Context managers ─────────────────────────────────────────────────────
# Kept per client: the ``with`` / ``async with`` statement is the behavior under test.


def test_sync_context_manager_closes_clients(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=METADATA_URL, json=METADATA)
    httpx_mock.add_response(url=ENUMS_URL, json={"CombatType": 1})

    with SwgohComlink(url=URL) as client:
        assert client.get_enums() == {"CombatType": 1}

    assert client.client.is_closed
    assert client.stats_client.is_closed


async def test_async_context_manager_closes_clients(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=METADATA_URL, json=METADATA)
    httpx_mock.add_response(url=ENUMS_URL, json={"CombatType": 1})

    async with SwgohComlinkAsync(url=URL) as client:
        assert await client.get_enums() == {"CombatType": 1}

    assert client.client.is_closed
    assert client.stats_client.is_closed
