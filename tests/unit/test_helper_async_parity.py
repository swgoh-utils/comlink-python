"""Every helper that takes a comlink client must also work with the async client."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

import pytest

import swgoh_comlink.helpers as helpers

# Helpers that make no request and accept both the sync and the async client directly, so they need
# no async_ twin.
CLIENT_AGNOSTIC_HELPERS: frozenset[str] = frozenset()


def _client_helpers() -> list[str]:
    """Public sync helpers whose signature takes a ``comlink`` client."""
    return sorted(
        name
        for name in helpers.__all__
        if not name.startswith("async_")
        and inspect.isfunction(obj := getattr(helpers, name))
        and "comlink" in inspect.signature(obj).parameters
    )


def _parameters(func: Callable[..., Any]) -> list[tuple[str, inspect._ParameterKind, Any]]:
    return [(p.name, p.kind, p.default) for p in inspect.signature(func).parameters.values()]


def test_client_helpers_are_detected():
    assert "get_guild_members" in _client_helpers()


@pytest.mark.parametrize("name", _client_helpers())
def test_client_helper_has_matching_async_twin(name: str):
    if name in CLIENT_AGNOSTIC_HELPERS:
        return  # accepts the async client directly; _client_helpers() already found it in __all__
    twin = getattr(helpers, f"async_{name}", None)
    assert twin is not None, f"{name} takes a comlink client but has no async_{name}"
    assert f"async_{name}" in helpers.__all__
    assert inspect.iscoroutinefunction(twin)
    assert _parameters(twin) == _parameters(getattr(helpers, name))


@pytest.mark.parametrize("name", sorted(n for n in helpers.__all__ if n.startswith("async_")))
def test_async_helper_has_exported_sync_twin(name: str):
    assert name.removeprefix("async_") in helpers.__all__
