"""The sync and async clients expose the same public API and share one retry core."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

import pytest

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync

# Lifecycle methods named for their runtime: async name -> sync name.
RUNTIME_NAMES = {"aclose": "close"}


def _public_methods(cls: type) -> dict[str, Callable[..., Any]]:
    return {name: member for name, member in inspect.getmembers(cls, callable) if not name.startswith("_")}


ASYNC_METHODS = _public_methods(SwgohComlinkAsync)
SYNC_METHODS = _public_methods(SwgohComlink)


def test_public_names_match() -> None:
    assert {RUNTIME_NAMES.get(name, name) for name in ASYNC_METHODS} == set(SYNC_METHODS)


@pytest.mark.parametrize("name", sorted(ASYNC_METHODS))
def test_every_async_method_exists_on_the_sync_client_with_the_same_signature(name: str) -> None:
    async_method = ASYNC_METHODS[name]
    sync_method = getattr(SwgohComlink, RUNTIME_NAMES.get(name, name), None)
    assert sync_method is not None, f"SwgohComlink has no {RUNTIME_NAMES.get(name, name)}"
    assert inspect.signature(async_method) == inspect.signature(sync_method)
    # An alias such as getPlayer names the same function in both clients.
    assert RUNTIME_NAMES.get(async_method.__name__, async_method.__name__) == sync_method.__name__
    # Methods defined on the client are coroutines in the async one and plain in the sync one.
    # unwrap() looks through param_alias, whose wrapper is a plain function in both.
    if async_method.__qualname__.startswith("SwgohComlinkAsync."):
        assert inspect.iscoroutinefunction(inspect.unwrap(async_method))
        assert not inspect.iscoroutinefunction(inspect.unwrap(sync_method))


@pytest.mark.parametrize("cls", [SwgohComlink, SwgohComlinkAsync])
def test_request_is_a_short_loop_without_retry_decisions(cls: type) -> None:
    source = inspect.getsource(cls._request)
    assert len(source.splitlines()) < 40
    for decision in ("retry_policy", "retry_delay", "jitter", "_hold_endpoint", "_hold_changed", "_pace_slot"):
        assert decision not in source
