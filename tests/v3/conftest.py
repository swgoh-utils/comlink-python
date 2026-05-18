# coding=utf-8
"""Pytest fixtures for the v3 test suite.

Replay the cassettes captured in Phase 0 (``benchmarks/v3/fixtures/*.json.gz``)
through `pytest-httpx`. Tests get a real :class:`SwgohComlink` /
:class:`SwgohComlinkAsync` whose underlying ``httpx.Client`` is transparently
served by a mock transport — no `_post`-level monkey-patching, no real network.

Public surface:

* :class:`CassetteServer` — replay catalog with per-endpoint override.
* :func:`cassette_server` — fixture that wires the catalog into ``httpx_mock``.
* :func:`recorded_comlink` — sync client backed by the catalog.
* :func:`recorded_comlink_async` — async client backed by the catalog.
* :func:`golden` — loader that returns parsed JSON from ``tests/v3/golden/``.

Cassette regen lives at ``benchmarks/v3/_record.py``; golden regen lives at
``tests/v3/_regen_goldens.py``.
"""

from __future__ import annotations

import gzip
import json
from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import pytest

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock

# ── Paths ────────────────────────────────────────────────────────────────────

_REPO_ROOT: Path = Path(__file__).resolve().parents[2]
FIXTURES_DIR: Path = _REPO_ROOT / "benchmarks" / "v3" / "fixtures"
GOLDEN_DIR: Path = Path(__file__).resolve().parent / "golden"
"""Where canonical SDK-output snapshots live."""

# ── Endpoint → cassette catalog (defaults) ──────────────────────────────────

#: Default cassette per endpoint path. Tests that need a different mapping
#: (e.g. ``player_small`` instead of ``player_large``) call
#: :meth:`CassetteServer.use` to override.
DEFAULT_CASSETTES: dict[str, str] = {
    "metadata": "metadata",
    "data": "data",
    "localization": "localization_eng_us",
    "player": "player_large",
    "guild": "guild",
    "getLeaderboard": "leaderboard",
}

# Cassette bytes are read once and cached for the test session. The /data
# cassette is ~15 MiB gzipped (~80 MiB decoded) so we don't want a per-test
# disk read.
_CASSETTE_CACHE: dict[str, bytes] = {}


def load_cassette_bytes(name: str) -> bytes:
    """Return decompressed cassette bytes for *name* (without ``.json.gz``).

    Cached per process. Raises a friendly error if the cassette is missing.
    """
    if name not in _CASSETTE_CACHE:
        path = FIXTURES_DIR / f"{name}.json.gz"
        if not path.exists():
            pytest.fail(
                f"cassette '{name}' missing at {path}. "
                f"Run `uv run python -m benchmarks.v3._record` "
                f"(see benchmarks/v3/fixtures/README.md)."
            )
        with gzip.open(path, "rb") as fh:
            _CASSETTE_CACHE[name] = fh.read()
    return _CASSETTE_CACHE[name]


def load_cassette_json(name: str) -> Any:
    """Return the parsed-JSON form of cassette *name* (cached)."""
    return json.loads(load_cassette_bytes(name))


# ── Cassette server ─────────────────────────────────────────────────────────


class CassetteServer:
    """Dispatch cassettes to endpoints over a ``pytest-httpx`` mock transport.

    The server registers one reusable callback on ``httpx_mock`` that inspects
    every incoming request, looks the endpoint up in :attr:`mapping`, and
    returns the gzipped cassette bytes inline. Unknown endpoints return 404
    so tests catch typos and missing fixtures explicitly.

    Test bodies can rebind endpoints on the fly::

        def test_small_roster(cassette_server, recorded_comlink, golden):
            cassette_server.use("player", "player_small")
            assert recorded_comlink.get_player(allycode=855566316) == golden("player_small")

    The default ``status_code=200`` can be overridden with :meth:`fail` to
    test retry / error paths (used by Phase 2).
    """

    def __init__(self, httpx_mock: HTTPXMock) -> None:
        self.mapping: dict[str, str] = dict(DEFAULT_CASSETTES)
        self._status: dict[str, int] = {}
        # is_reusable so a single registration serves N calls per endpoint.
        httpx_mock.add_callback(self._handle, is_reusable=True)

    def use(self, endpoint: str, cassette: str) -> None:
        """Bind *endpoint* (path without leading ``/``) to cassette *cassette*."""
        self.mapping[endpoint] = cassette

    def fail(self, endpoint: str, *, status_code: int) -> None:
        """Make subsequent calls to *endpoint* return *status_code* (for retry tests)."""
        self._status[endpoint] = status_code

    def _handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.lstrip("/")
        status = self._status.get(path, 200)
        if status != 200:
            return httpx.Response(
                status,
                content=json.dumps({"error": f"forced {status}"}).encode(),
                headers={"content-type": "application/json"},
            )
        cassette = self.mapping.get(path)
        if cassette is None:
            return httpx.Response(
                404,
                content=json.dumps({"error": f"no cassette bound for endpoint '{path}'"}).encode(),
                headers={"content-type": "application/json"},
            )
        return httpx.Response(
            200,
            content=load_cassette_bytes(cassette),
            headers={"content-type": "application/json"},
        )


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def cassette_server(httpx_mock: HTTPXMock) -> CassetteServer:
    """Cassette dispatcher; auto-wires to ``httpx_mock``."""
    return CassetteServer(httpx_mock)


@pytest.fixture
def recorded_comlink(cassette_server: CassetteServer) -> Iterator[Any]:
    """Sync :class:`SwgohComlink` backed by the cassette server.

    ``cassette_server`` is consumed for its side effect (registering the
    mock callback) — we don't use the parameter here but the fixture is
    required to ensure it's wired before the client makes any call.
    """
    # Lazy import: avoids httpx getting pulled in if a test only wants
    # the cassette server and not the SDK.
    from swgoh_comlink import SwgohComlink

    _ = cassette_server  # keep linters honest about the dependency
    client = SwgohComlink(url="http://comlink.test")
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
async def recorded_comlink_async(cassette_server: CassetteServer) -> AsyncIterator[Any]:
    """Async :class:`SwgohComlinkAsync` backed by the cassette server."""
    from swgoh_comlink import SwgohComlinkAsync

    _ = cassette_server
    client = SwgohComlinkAsync(url="http://comlink.test")
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
def recorded_comlink_typed(cassette_server: CassetteServer) -> Iterator[Any]:
    """Sync typed-Struct :class:`swgoh_comlink.typed.SwgohComlink`.

    For tests that need attribute access on typed Structs
    (``player.name`` etc.). The default :func:`recorded_comlink` fixture
    yields the dict-default client (``player["name"]``).
    """
    from swgoh_comlink.typed import SwgohComlink

    _ = cassette_server
    client = SwgohComlink(url="http://comlink.test")
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
async def recorded_comlink_async_typed(cassette_server: CassetteServer) -> AsyncIterator[Any]:
    """Async typed-Struct :class:`swgoh_comlink.typed.SwgohComlinkAsync`."""
    from swgoh_comlink.typed import SwgohComlinkAsync

    _ = cassette_server
    client = SwgohComlinkAsync(url="http://comlink.test")
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
def golden() -> Callable[[str], Any]:
    """Loader for golden snapshot files under ``tests/v3/golden/``.

    Usage::

        def test_metadata(recorded_comlink, golden):
            assert recorded_comlink.get_game_metadata() == golden("metadata")

    Fails fast with a regen hint when the requested golden is missing.
    """

    def loader(name: str) -> Any:
        path = GOLDEN_DIR / f"{name}.json"
        if not path.exists():
            pytest.fail(
                f"golden '{name}.json' missing at {path}. Run `uv run python -m tests.v3._regen_goldens` to regenerate."
            )
        return json.loads(path.read_text())

    return loader
