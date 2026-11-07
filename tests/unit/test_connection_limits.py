"""Connection-pool ``limits`` parity between the sync and async clients."""

from __future__ import annotations

import inspect
from typing import Any

import httpx
import pytest

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync
from swgoh_comlink._base import DEFAULT_TIMEOUT, SwgohComlinkBase
from swgoh_comlink.exceptions import SwgohComlinkTypeError

_MISSING = object()


def _record_client_kwargs(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Patch both httpx client classes to record the keyword arguments each instance is built with."""
    calls: list[dict[str, Any]] = []

    for cls in (httpx.Client, httpx.AsyncClient):

        def init(self: Any, *args: Any, _original: Any = cls.__init__, **kwargs: Any) -> None:
            calls.append(kwargs)
            _original(self, *args, **kwargs)

        monkeypatch.setattr(cls, "__init__", init)
    return calls


def _limits_passed(calls: list[dict[str, Any]]) -> list[Any]:
    return [kwargs.get("limits", _MISSING) for kwargs in calls]


def _pool(client: Any) -> Any:
    """The httpcore connection pool behind an httpx client's default transport."""
    return client._transport._pool


@pytest.mark.parametrize(
    "limits",
    [None, httpx.Limits(max_connections=7, max_keepalive_connections=3, keepalive_expiry=30.0)],
    ids=["default", "custom"],
)
def test_sync_and_async_pass_identical_limits_to_httpx(monkeypatch: pytest.MonkeyPatch, limits: Any) -> None:
    calls = _record_client_kwargs(monkeypatch)
    sync = SwgohComlink(limits=limits)
    sync_limits = _limits_passed(calls)
    calls.clear()
    SwgohComlinkAsync(limits=limits)
    async_limits = _limits_passed(calls)

    assert len(sync_limits) == len(async_limits) == 2  # client and stats_client
    assert sync_limits == async_limits
    expected = _MISSING if limits is None else limits
    assert sync_limits == [expected, expected]
    sync.close()


def test_default_keepalive_expiry_matches_httpx_default_in_both_clients() -> None:
    reference = _pool(httpx.Client())
    sync = SwgohComlink()
    async_client = SwgohComlinkAsync()
    for pool in (_pool(c) for c in (sync.client, sync.stats_client, async_client.client, async_client.stats_client)):
        assert pool._keepalive_expiry == reference._keepalive_expiry == 5.0
        assert pool._max_connections == reference._max_connections
        assert pool._max_keepalive_connections == reference._max_keepalive_connections
    sync.close()


@pytest.mark.parametrize("cls", [SwgohComlink, SwgohComlinkAsync])
def test_custom_limits_reach_both_connection_pools(cls: type[SwgohComlink] | type[SwgohComlinkAsync]) -> None:
    client = cls(limits=httpx.Limits(max_connections=7, max_keepalive_connections=3, keepalive_expiry=None))
    for pool in (_pool(client.client), _pool(client.stats_client)):
        assert (pool._max_connections, pool._max_keepalive_connections, pool._keepalive_expiry) == (7, 3, None)


def test_limits_is_keyword_only() -> None:
    param = inspect.signature(SwgohComlinkBase.__init__).parameters["limits"]
    assert param.kind is inspect.Parameter.KEYWORD_ONLY
    assert param.default is None


@pytest.mark.parametrize("cls", [SwgohComlink, SwgohComlinkAsync])
@pytest.mark.parametrize("bad", [{"max_connections": 5}, 5, "limits"])
def test_limits_must_be_httpx_limits(cls: type[SwgohComlink] | type[SwgohComlinkAsync], bad: Any) -> None:
    with pytest.raises(SwgohComlinkTypeError, match="limits must be an httpx.Limits or None"):
        cls(limits=bad)


@pytest.mark.parametrize("cls", [SwgohComlink, SwgohComlinkAsync])
def test_limits_do_not_change_timeouts(cls: type[SwgohComlink] | type[SwgohComlinkAsync]) -> None:
    client = cls(limits=httpx.Limits(keepalive_expiry=1.0))
    assert client.client.timeout == client.stats_client.timeout == httpx.Timeout(DEFAULT_TIMEOUT)
