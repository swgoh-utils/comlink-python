"""Shared fixtures for running one test body against both the sync and async Comlink clients.

``make_comlink``/``comlink`` are parametrized over :class:`SwgohComlink` and
:class:`SwgohComlinkAsync`; drive the client through the ``call`` fixture, which awaits the
result only when the client is async::

    async def test_something(comlink, call):
        assert await call(comlink, "get_enums") == ...
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import pytest

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync

Client = SwgohComlink | SwgohComlinkAsync

COMLINK_URL = "http://localhost:3000"
STATS_URL = "http://localhost:3223"


@pytest.fixture(params=[SwgohComlink, SwgohComlinkAsync], ids=["sync", "async"])
async def make_comlink(request: pytest.FixtureRequest) -> AsyncIterator[Callable[..., Client]]:
    """Build clients of the parametrized type and close every one of them on teardown."""
    clients: list[Client] = []

    def factory(**kwargs: Any) -> Client:
        client = request.param(**{"url": COMLINK_URL, "stats_url": STATS_URL, **kwargs})
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


async def _call(client: Client, method: str, /, *args: Any, **kwargs: Any) -> Any:
    result = getattr(client, method)(*args, **kwargs)
    return await result if inspect.isawaitable(result) else result


@pytest.fixture
def call() -> Callable[..., Awaitable[Any]]:
    """``await call(client, "method", **kwargs)`` works for either client type."""
    return _call


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> dict[str, float]:
    """Controllable monotonic clock for version cache expiry."""
    state = {"t": 1000.0}
    monkeypatch.setattr("swgoh_comlink._base._now", lambda: state["t"])
    return state
