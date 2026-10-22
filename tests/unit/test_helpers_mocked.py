"""Tests for helpers that take a Comlink client, run against mocked HTTP.

Every client-backed helper is exercised three ways through the ``run`` fixture: the sync
client, the async client passed to the sync-named helper (which dispatches to the async
implementation and returns an awaitable), and the explicit ``async_`` twin. Data shaping is
covered by the pure-helper tests in test_helpers.py; these tests pin the wiring.
"""

from __future__ import annotations

import base64
import inspect
import io
import json
import re
import zipfile
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
from pytest_httpx import HTTPXMock

import swgoh_comlink.helpers as helpers
from swgoh_comlink import SwgohComlink, SwgohComlinkAsync
from swgoh_comlink.exceptions import SwgohComlinkValueError
from swgoh_comlink.helpers import (
    DataItems,
    get_era_units,
    get_event_schedule,
    get_game_config,
    get_game_config_int,
    get_guild_activity,
)

URL = "http://localhost:3000"
LEADERBOARD_URL = f"{URL}/getLeaderboard"

_GAC_EVENT = {
    "id": "CHAMPIONSHIPS_GRAND_ARENA_GA2_EVENT_SEASON_55",
    "type": 10,
    "instance": [{"id": "SEASON_55_INSTANCE"}],
}
_EVENT_INSTANCE = "CHAMPIONSHIPS_GRAND_ARENA_GA2_EVENT_SEASON_55:SEASON_55_INSTANCE"
_METADATA = {"latestGamedataVersion": "g1", "latestLocalizationBundleVersion": "loc-v1"}

Run = Callable[..., Awaitable[Any]]


@pytest.fixture(params=["sync", "async", "async-twin"])
async def run(request: pytest.FixtureRequest) -> AsyncIterator[Run]:
    """``await run("get_guild_members", **kwargs)`` through the parametrized client and entry point."""
    client = SwgohComlink(url=URL) if request.param == "sync" else SwgohComlinkAsync(url=URL)

    async def invoke(name: str, /, **kwargs: Any) -> Any:
        helper = getattr(helpers, f"async_{name}" if request.param == "async-twin" else name)
        result = helper(client, **kwargs)
        if isinstance(client, SwgohComlinkAsync):
            assert inspect.isawaitable(result), f"{name} must return an awaitable for the async client"
            return await result
        return result

    yield invoke
    if isinstance(client, SwgohComlinkAsync):
        await client.aclose()
    else:
        client.close()


def _payloads(httpx_mock: HTTPXMock, url: str) -> list[dict[str, Any]]:
    return [json.loads(request.content)["payload"] for request in httpx_mock.get_requests(url=url)]


# ── _gac ─────────────────────────────────────────────────────────────────


async def test_get_current_gac_event_picks_the_gac_event(run: Run, httpx_mock: HTTPXMock):
    httpx_mock.add_response(json={"gameEvent": [{"type": 5}, _GAC_EVENT]})

    assert await run("get_current_gac_event") == _GAC_EVENT


@pytest.mark.parametrize(
    ("helper", "kwargs"),
    [
        pytest.param("get_current_gac_event", {}, id="current-event"),
        pytest.param("get_gac_brackets", {"league": "kyber"}, id="brackets"),
    ],
)
async def test_gac_helpers_without_a_gac_event_raise(
    run: Run, httpx_mock: HTTPXMock, helper: str, kwargs: dict[str, str]
):
    httpx_mock.add_response(json={"gameEvent": [{"type": 5}]})

    with pytest.raises(SwgohComlinkValueError, match="No active GAC"):
        await run(helper, **kwargs)


def _players(index: int) -> list[dict[str, str]]:
    return [{"name": f"P{index}"}]


@pytest.mark.parametrize(
    ("last_bracket", "limit", "expected_brackets"),
    [
        pytest.param(-1, 0, [], id="bracket-0-empty"),
        pytest.param(0, 0, [0], id="one-bracket"),
        pytest.param(5, 0, [0, 1, 2, 3, 4, 5], id="several-brackets"),
        pytest.param(5, 3, [0, 1, 2], id="limit"),
        pytest.param(1, 3, [0, 1], id="limit-above-last-bracket"),
    ],
)
async def test_get_gac_brackets(
    run: Run, httpx_mock: HTTPXMock, last_bracket: int, limit: int, expected_brackets: list[int]
):
    def leaderboard(request: httpx.Request) -> httpx.Response:
        index = int(json.loads(request.content)["payload"]["groupId"].rsplit(":", 1)[1])
        return httpx.Response(200, json={"player": _players(index) if index <= last_bracket else []})

    httpx_mock.add_response(url=f"{URL}/getEvents", json={"gameEvent": [_GAC_EVENT]})
    httpx_mock.add_callback(leaderboard, url=LEADERBOARD_URL, is_reusable=True)

    result = await run("get_gac_brackets", league="kyber", limit=limit)

    assert result == {index: _players(index) for index in expected_brackets}
    payloads = _payloads(httpx_mock, LEADERBOARD_URL)
    assert {(p["leaderboardType"], p["eventInstanceId"]) for p in payloads} == {(4, _EVENT_INSTANCE)}
    assert all(re.fullmatch(rf"{_EVENT_INSTANCE}:kyber:\d+", p["groupId"]) for p in payloads)


# ── _guild ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("identifier", "player_payload"),
    [
        pytest.param({"player_id": "pid_123"}, {"playerId": "pid_123"}, id="player-id"),
        pytest.param({"allycode": 123456789}, {"allyCode": "123456789"}, id="allycode"),
    ],
)
async def test_get_guild_members(
    run: Run, httpx_mock: HTTPXMock, identifier: dict[str, Any], player_payload: dict[str, str]
):
    httpx_mock.add_response(url=f"{URL}/player", json={"guildId": "guild_abc"})
    httpx_mock.add_response(url=f"{URL}/guild", json={"member": [{"id": "m1"}, {"id": "m2"}]})

    assert await run("get_guild_members", **identifier) == [{"id": "m1"}, {"id": "m2"}]

    assert _payloads(httpx_mock, f"{URL}/player") == [player_payload]
    assert _payloads(httpx_mock, f"{URL}/guild") == [{"guildId": "guild_abc", "includeRecentGuildActivityInfo": True}]


# ── _game_data: get_localization_dictionary ──────────────────────────────


def _loc_bundle(*entries: tuple[str, str]) -> dict[str, str]:
    """A Comlink localization response: ``{"localizationBundle": <base64 zip of (filename, text) entries>}``."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries:
            zf.writestr(name, content)
    return {"localizationBundle": base64.b64encode(buf.getvalue()).decode("utf-8")}


_ENG_BUNDLE = _loc_bundle(("Loc_ENG_US.txt", "UNIT_A|Vader\n#comment line\nUNIT_B|Yoda\n"))


@pytest.mark.parametrize(
    ("kwargs", "bundle", "expected"),
    [
        pytest.param({}, _ENG_BUNDLE, {"UNIT_A": "Vader", "UNIT_B": "Yoda"}, id="default-language"),
        pytest.param(
            {"language": "fre_fr"}, _loc_bundle(("Loc_FRE_FR.txt", "UNIT_A|Vador\n")), {"UNIT_A": "Vador"}, id="fre_fr"
        ),
    ],
)
async def test_get_localization_dictionary(
    run: Run, httpx_mock: HTTPXMock, kwargs: dict[str, str], bundle: dict[str, str], expected: dict[str, str]
):
    httpx_mock.add_response(url=f"{URL}/metadata", json=_METADATA)
    httpx_mock.add_response(url=f"{URL}/localization", json=bundle)

    assert await run("get_localization_dictionary", **kwargs) == expected


@pytest.mark.parametrize(
    ("kwargs", "bundle", "match"),
    [
        pytest.param({}, {"notTheBundle": "oops"}, "localizationBundle", id="missing-bundle-key"),
        pytest.param({"language": "fre_fr"}, _ENG_BUNDLE, "Loc_FRE_FR.txt", id="language-not-in-bundle"),
    ],
)
async def test_get_localization_dictionary_bad_bundle_raises(
    run: Run, httpx_mock: HTTPXMock, kwargs: dict[str, str], bundle: dict[str, str], match: str
):
    httpx_mock.add_response(url=f"{URL}/metadata", json=_METADATA)
    httpx_mock.add_response(url=f"{URL}/localization", json=bundle)

    with pytest.raises(SwgohComlinkValueError, match=match):
        await run("get_localization_dictionary", **kwargs)


# ── Argument and client validation (every client-backed helper) ──────────

# Minimal valid arguments for each helper, so the client check is the only thing that can fail.
_CLIENT_HELPERS: dict[str, dict[str, Any]] = {
    "get_current_gac_event": {},
    "get_gac_brackets": {"league": "kyber"},
    "get_guild_members": {"player_id": "pid"},
    "get_localization_dictionary": {},
}


def test_every_client_backed_helper_is_covered():
    discovered = {
        name
        for name in helpers.__all__
        if not name.startswith("async_")
        and inspect.isfunction(obj := getattr(helpers, name))
        and "comlink" in inspect.signature(obj).parameters
    }
    assert discovered == set(_CLIENT_HELPERS)


@pytest.mark.parametrize(
    ("name", "kwargs", "match"),
    [
        pytest.param("get_gac_brackets", {"league": None}, "league", id="gac-league-none"),
        pytest.param("get_gac_brackets", {"league": 123}, "league", id="gac-league-not-str"),
        pytest.param("get_guild_members", {"player_id": "pid", "allycode": 123456789}, "not both", id="guild-both-ids"),
        pytest.param("get_guild_members", {}, "required", id="guild-no-id"),
        *(
            pytest.param("get_localization_dictionary", {"language": language}, "non-empty string", id=f"loc-{label}")
            for label, language in [("empty", ""), ("none", None), ("int", 123)]
        ),
    ],
)
async def test_invalid_arguments_raise_before_any_request(
    run: Run, httpx_mock: HTTPXMock, name: str, kwargs: dict[str, Any], match: str
):
    with pytest.raises(SwgohComlinkValueError, match=match):
        await run(name, **kwargs)

    assert httpx_mock.get_requests() == []


async def test_async_dispatch_defers_argument_errors_to_await():
    async with SwgohComlinkAsync(url=URL) as client:
        pending = helpers.get_guild_members(client)  # no error until awaited
        with pytest.raises(SwgohComlinkValueError, match="required"):
            await pending


def _bad_clients() -> list[Any]:
    rows = []
    for name, kwargs in _CLIENT_HELPERS.items():
        for helper in (name, f"async_{name}"):
            bad: list[tuple[str, Callable[[], Any]]] = [("none", lambda: None), ("object", object)]
            # The sync-named helper accepts both client kinds; only the async twin rejects a sync client.
            if helper != name:
                bad.append(("sync-client", lambda: SwgohComlink(url=URL)))
            rows += [pytest.param(helper, make, kwargs, id=f"{helper}-{label}") for label, make in bad]
    return rows


@pytest.mark.parametrize(("helper", "make_client", "kwargs"), _bad_clients())
async def test_invalid_client_is_rejected(helper: str, make_client: Callable[[], Any], kwargs: dict[str, Any]):
    client = make_client()
    with pytest.raises(SwgohComlinkValueError, match=rf"(?i)^{helper}\(\): .*comlink"):
        result = getattr(helpers, helper)(client, **kwargs)
        if inspect.isawaitable(result):
            await result
    if isinstance(client, SwgohComlink):
        client.close()


class _ExtendedComlink(SwgohComlink):
    __comlink_type__ = "ExtendedComlink"


class _ExtendedComlinkAsync(SwgohComlinkAsync):
    __comlink_type__ = "ExtendedComlinkAsync"


@pytest.mark.parametrize(
    ("client_class", "helper"),
    [
        pytest.param(_ExtendedComlink, "get_current_gac_event", id="sync-subclass"),
        pytest.param(_ExtendedComlinkAsync, "get_current_gac_event", id="async-subclass-dispatch"),
        pytest.param(_ExtendedComlinkAsync, "async_get_current_gac_event", id="async-subclass-twin"),
    ],
)
async def test_client_subclasses_are_accepted(httpx_mock: HTTPXMock, client_class: type, helper: str):
    httpx_mock.add_response(json={"gameEvent": [_GAC_EVENT]})
    client = client_class(url=URL)

    result = getattr(helpers, helper)(client)
    assert (await result if inspect.isawaitable(result) else result) == _GAC_EVENT

    if isinstance(client, SwgohComlinkAsync):
        await client.aclose()
    else:
        client.close()


# ── Pure helpers over real client responses ──────────────────────────────

_ACTIVITY_GUILD = {
    "guild": {
        "profile": {"id": "guild_abc", "name": "Test Guild", "memberCount": 2, "memberMax": 50},
        "member": [
            {"playerId": "p1", "playerName": "One", "memberLevel": 4, "guildJoinTime": "1655938556"},
            {"playerId": "p2", "playerName": "Two", "memberLevel": 2, "lastActivityTime": "1790164800000"},
        ],
        "recentTerritoryBattleResult": [{"definitionId": "t05D", "totalStars": 47}],
        "recentTerritoryWarResult": [{"score": "27361", "opponentScore": "11916"}],
        "recentRaidResult": [
            {
                "raidId": "order66",
                "guildRewardScore": "100",
                "raidMember": [{"playerId": "p2", "memberProgress": "100"}],
            }
        ],
    }
}


def _guild_summary(guild: dict[str, Any]) -> tuple[Any, ...]:
    activity = get_guild_activity(guild)
    last_raid = activity["last_raid"]
    assert last_raid is not None
    return (
        activity["guild_id"],
        activity["best_territory_battle"],
        (activity["territory_war_wins"], activity["territory_war_losses"]),
        last_raid["guild_score"],
        [(m["role"], m["raid_score"]) for m in activity["members"]],
    )


def _journey_summary(events: dict[str, Any]) -> list[tuple[Any, ...]]:
    loc = {"EVENT_JOURNEY_MANDALORIAN_NAME": "THE MANDALORIAN\\n[c][FFC891]Hero's Journey[-][/c]"}
    schedule = get_event_schedule(events, loc, now=datetime(2026, 9, 23, 12, tzinfo=timezone.utc))
    return [(e["name"], e["title"], e["subtitle"], e["status"], e["end"]) for e in schedule]


def _era_summary(game_data: dict[str, Any]) -> list[str]:
    return get_era_units(game_data, now=datetime(2026, 10, 22, tzinfo=timezone.utc), include_loaned=True)


def _config_summary(metadata: dict[str, Any]) -> tuple[Any, ...]:
    return get_game_config(metadata), get_game_config_int(metadata, "max-datacron-currency")


@pytest.mark.parametrize(
    ("method", "kwargs", "response", "summarize", "expected"),
    [
        pytest.param(
            "get_guild",
            {"guild_id": "guild_abc", "include_recent_guild_activity_info": True},
            _ACTIVITY_GUILD,
            _guild_summary,
            (
                "guild_abc",
                {"definition_id": "t05D", "total_stars": 47},
                (1, 0),
                100,
                [("Leader", None), ("Member", 100)],
            ),
            id="guild-activity",
        ),
        pytest.param(
            "get_events",
            {},
            {
                "gameEvent": [
                    _GAC_EVENT,
                    {
                        "id": "EVENT_JOURNEY_MANDALORIAN",
                        "nameKey": "EVENT_JOURNEY_MANDALORIAN_NAME",
                        "type": 3,
                        "instance": [{"id": "J1", "startTime": "1476532800000", "endTime": "4945772573272"}],
                    },
                ]
            },
            _journey_summary,
            [("THE MANDALORIAN - Hero's Journey", "THE MANDALORIAN", "Hero's Journey", "live", None)],
            id="event-schedule",
        ),
        pytest.param(
            "get_game_data",
            {"version": "g1", "items": DataItems.ERA_DEFINITION},
            {
                "eraDefinition": [
                    {
                        "id": "ERA10_MANDALORIANANDGROGU",
                        "startTimeMs": "1792519200000",
                        "endTimeMs": "1794942000000",
                        "eraUnitId": ["ADELPHIRANGER", "B1MERCDROID"],
                        "journeyUnit": "",
                        "loanedUnit": [{"expireTime": "1794942000000", "id": "CARSONTEVA"}],
                    }
                ]
            },
            _era_summary,
            ["ADELPHIRANGER", "B1MERCDROID", "CARSONTEVA"],
            id="era-units",
        ),
        pytest.param(
            "get_game_metadata",
            {},
            {
                "config": [
                    {"key": "max-datacron-currency", "value": "100000000"},
                    {"key": "stat-mod-max-storage", "value": "500"},
                ],
                **_METADATA,
            },
            _config_summary,
            ({"max-datacron-currency": "100000000", "stat-mod-max-storage": "500"}, 100_000_000),
            id="game-config",
        ),
    ],
)
async def test_pure_helpers_accept_client_responses(
    comlink: SwgohComlink | SwgohComlinkAsync,
    call: Callable[..., Awaitable[Any]],
    httpx_mock: HTTPXMock,
    method: str,
    kwargs: dict[str, Any],
    response: dict[str, Any],
    summarize: Callable[[Any], Any],
    expected: Any,
):
    httpx_mock.add_response(json=response)

    assert summarize(await call(comlink, method, **kwargs)) == expected
