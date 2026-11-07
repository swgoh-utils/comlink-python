"""Tests for the StatCalc / StatCalcAsync game data download: size cap, SHA-256 check and URL override.

Every test runs against both the sync fetch (``httpx.Client``) and the async fetch
(``httpx.AsyncClient``); pytest-httpx mocks both, so nothing touches the network.
"""

from __future__ import annotations

import gzip
import hashlib
import inspect
import json
from collections.abc import Awaitable, Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from pytest_httpx import HTTPXMock, IteratorStream

from swgoh_comlink import StatCalc, StatCalcAsync
from swgoh_comlink.exceptions import SwgohComlinkValueError
from swgoh_comlink.StatCalc import calculator

DEFAULT_URL = StatCalc._DEFAULT_GAMEDATA_URL
MIRROR_URL = "https://mirror.example/gameData.json"
SMALL_CAP = 1024

Fetch = Callable[..., Awaitable[dict[str, Any]]]
Create = Callable[..., Awaitable[StatCalc]]


async def _sync_fetch(url: str | None = None, expected_sha256: str | None = None) -> dict[str, Any]:
    return StatCalc._fetch_game_data_from_github(url, expected_sha256)


async def _async_fetch(url: str | None = None, expected_sha256: str | None = None) -> dict[str, Any]:
    return await StatCalcAsync._async_fetch_game_data_from_github(url, expected_sha256)


async def _sync_create(**kwargs: Any) -> StatCalc:
    return StatCalc(**kwargs)


@pytest.fixture(params=[_sync_fetch, _async_fetch], ids=["sync", "async"])
def fetch(request: pytest.FixtureRequest) -> Fetch:
    """Call the sync or async game data fetch with the same signature."""
    return request.param


@pytest.fixture(params=[_sync_create, StatCalcAsync.create], ids=["sync", "async"])
def create(request: pytest.FixtureRequest) -> Create:
    """Build a calculator through ``StatCalc(...)`` or ``await StatCalcAsync.create(...)``."""
    return request.param


@pytest.fixture
def small_cap(monkeypatch: pytest.MonkeyPatch) -> int:
    """Lower the download cap so oversized bodies stay small in tests."""
    monkeypatch.setattr(calculator, "_MAX_GAMEDATA_BYTES", SMALL_CAP)
    return SMALL_CAP


@pytest.fixture(scope="module")
def body() -> bytes:
    """A valid wrapped game data payload, as served by swgoh-utils/gamedata."""
    return (Path(__file__).resolve().parent.parent / "resources" / "gameData.json").read_bytes()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── Transport ────────────────────────────────────────────────────────────


def test_statcalc_does_not_use_urllib():
    sources = Path(calculator.__file__).parent.rglob("*.py")
    assert [p.name for p in sources if "urllib" in p.read_text(encoding="utf-8")] == []


async def test_default_url_is_the_latest_main_branch(fetch: Fetch, httpx_mock: HTTPXMock):
    assert DEFAULT_URL == "https://raw.githubusercontent.com/swgoh-utils/gamedata/main/gameData.json"
    httpx_mock.add_response(url=DEFAULT_URL, json={"data": {"unitData": {"X": {}}}})

    assert await fetch() == {"unitData": {"X": {}}}


async def test_game_data_url_overrides_the_default(fetch: Fetch, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=MIRROR_URL, json={"unitData": {"Y": {}}})

    assert await fetch(MIRROR_URL) == {"unitData": {"Y": {}}}


async def test_redirects_are_followed(fetch: Fetch, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=DEFAULT_URL, status_code=302, headers={"Location": MIRROR_URL})
    httpx_mock.add_response(url=MIRROR_URL, json={"unitData": {"Z": {}}})

    assert await fetch() == {"unitData": {"Z": {}}}


async def test_http_errors_still_raise_runtime_error(fetch: Fetch, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=MIRROR_URL, status_code=404)

    with pytest.raises(RuntimeError, match=f"Unable to retrieve game data from {MIRROR_URL}"):
        await fetch(MIRROR_URL)


# ── Size cap ─────────────────────────────────────────────────────────────


def test_cap_is_64_mib():
    assert calculator._MAX_GAMEDATA_BYTES == 64 * 1024 * 1024


async def test_oversized_body_raises_before_it_is_fully_read(fetch: Fetch, httpx_mock: HTTPXMock, small_cap: int):
    chunk = b" " * 256
    total_chunks = 100
    served: list[int] = []

    def chunks() -> Iterator[bytes]:
        for i in range(total_chunks):
            served.append(i)
            yield chunk

    httpx_mock.add_response(url=DEFAULT_URL, stream=IteratorStream(chunks()))

    with pytest.raises(SwgohComlinkValueError, match=f"{small_cap} bytes"):
        await fetch()
    # The cap trips on the first chunk past 1 KiB; the remaining chunks are never pulled.
    assert len(served) == small_cap // len(chunk) + 1
    assert len(served) < total_chunks


async def test_body_at_the_cap_loads(fetch: Fetch, httpx_mock: HTTPXMock, small_cap: int):
    payload = json.dumps({"unitData": {}}).encode()
    httpx_mock.add_response(url=DEFAULT_URL, content=payload.ljust(small_cap))

    assert await fetch() == {"unitData": {}}


async def test_cap_counts_decompressed_bytes(fetch: Fetch, httpx_mock: HTTPXMock, small_cap: int):
    decompressed = json.dumps({"unitData": {}}).encode().ljust(small_cap * 64)
    compressed = gzip.compress(decompressed)
    assert len(compressed) < small_cap  # the wire size alone would pass the cap
    httpx_mock.add_response(url=DEFAULT_URL, stream=IteratorStream([compressed]), headers={"Content-Encoding": "gzip"})

    with pytest.raises(SwgohComlinkValueError, match="exceeds"):
        await fetch()


# ── SHA-256 check ────────────────────────────────────────────────────────


async def test_matching_hash_loads(fetch: Fetch, httpx_mock: HTTPXMock, body: bytes):
    httpx_mock.add_response(url=DEFAULT_URL, content=body)

    data = await fetch(expected_sha256=_sha256(body))

    assert set(StatCalc._REQUIRED_TABLES) <= set(data)


async def test_hash_is_taken_over_the_decompressed_body(fetch: Fetch, httpx_mock: HTTPXMock, body: bytes):
    gzipped = IteratorStream([gzip.compress(body)])
    httpx_mock.add_response(url=DEFAULT_URL, stream=gzipped, headers={"Content-Encoding": "gzip"})

    assert "unitData" in await fetch(expected_sha256=_sha256(body))


async def test_hash_mismatch_raises(fetch: Fetch, httpx_mock: HTTPXMock, body: bytes):
    httpx_mock.add_response(url=DEFAULT_URL, content=body)

    with pytest.raises(SwgohComlinkValueError, match="SHA-256 mismatch"):
        await fetch(expected_sha256=_sha256(b"something else"))


async def test_hash_mismatch_is_checked_before_parsing(fetch: Fetch, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=DEFAULT_URL, content=b"not json")

    with pytest.raises(SwgohComlinkValueError, match="SHA-256 mismatch"):
        await fetch(expected_sha256="0" * 64)


# ── Constructor arguments ────────────────────────────────────────────────


async def test_create_with_url_and_hash(create: Create, httpx_mock: HTTPXMock, body: bytes):
    httpx_mock.add_response(url=MIRROR_URL, content=body)

    calc = await create(game_data_url=MIRROR_URL, expected_sha256=_sha256(body).upper())

    assert calc.calc_char_gp({"defId": "BOSSK", "rarity": 7, "level": 85, "gear": 13}) > 0


async def test_create_rejects_a_hash_mismatch(create: Create, httpx_mock: HTTPXMock, body: bytes):
    httpx_mock.add_response(url=DEFAULT_URL, content=body)

    with pytest.raises(SwgohComlinkValueError, match="SHA-256 mismatch"):
        await create(expected_sha256="f" * 64)


@pytest.mark.parametrize("bad", ["", "abc", "g" * 64, "0" * 63, "0" * 65])
async def test_malformed_hash_is_rejected_before_fetching(create: Create, httpx_mock: HTTPXMock, bad: str):
    # No response is registered: any request would fail the test.
    with pytest.raises(SwgohComlinkValueError, match="expected_sha256"):
        await create(expected_sha256=bad)


@pytest.mark.parametrize("kwargs", [{"game_data_url": MIRROR_URL}, {"expected_sha256": "0" * 64}])
async def test_fetch_options_with_game_data_are_rejected(create: Create, game_data: dict[str, Any], kwargs: dict):
    with pytest.raises(SwgohComlinkValueError, match="game_data"):
        await create(game_data=game_data, **kwargs)


@pytest.mark.parametrize("name", ["game_data_url", "expected_sha256"])
def test_fetch_options_are_keyword_only(name: str):
    for func in (StatCalc.__init__, StatCalcAsync.create):
        assert inspect.signature(func).parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
