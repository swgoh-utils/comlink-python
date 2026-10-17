"""Shared fixtures for integration tests against a live Comlink service.

``make_comlink``/``comlink`` are parametrized over :class:`SwgohComlink` and
:class:`SwgohComlinkAsync`, so each test body runs against both clients. Drive the client
through the ``call`` fixture, which awaits the result only when the client is async::

    async def test_something(comlink, call):
        assert await call(comlink, "get_enums")
"""

from __future__ import annotations

import inspect
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import pytest

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync

Client = SwgohComlink | SwgohComlinkAsync

# Override to run against another Comlink, e.g. COMLINK_URL=http://comlink.lab:3200.
# Unset or empty falls back to the local services CI starts.
COMLINK_URL = os.environ.get("COMLINK_URL") or "http://localhost:3000"
COMLINK_HMAC_URL = os.environ.get("COMLINK_HMAC_URL") or "http://localhost:3001"
HMAC_ACCESS_KEY = os.environ.get("HMAC_ACCESS_KEY", "")
HMAC_SECRET_KEY = os.environ.get("HMAC_SECRET_KEY", "")

# Known public allycode used in example scripts
TEST_ALLYCODE = 314927874


@pytest.fixture(params=[SwgohComlink, SwgohComlinkAsync], ids=["sync", "async"])
async def make_comlink(request: pytest.FixtureRequest) -> AsyncIterator[Callable[..., Client]]:
    """Build clients of the parametrized type and close every one of them on teardown."""
    clients: list[Client] = []

    def factory(**kwargs: Any) -> Client:
        client = request.param(**{"url": COMLINK_URL, **kwargs})
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
    """A client of the parametrized type connected to the open Comlink instance."""
    return make_comlink()


async def _call(client: Client, method: str, /, *args: Any, **kwargs: Any) -> Any:
    result = getattr(client, method)(*args, **kwargs)
    return await result if inspect.isawaitable(result) else result


@pytest.fixture
def call() -> Callable[..., Awaitable[Any]]:
    """``await call(client, "method", **kwargs)`` works for either client type."""
    return _call
