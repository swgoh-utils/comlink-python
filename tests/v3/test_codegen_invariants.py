# coding=utf-8
"""Codegen invariants — guard the 2x2 client matrix's shape contract.

These tests don't exercise the wire; they exercise the *generated code's
structure*. A failure here means the generator drifted from the manifest
or the four output files diverged in a way that breaks the surface
contract:

* Every method named in the manifest exists on all four client classes.
* Sync / async signatures match (modulo ``async`` keyword + return-type
  wrapping).
* Dict / typed surfaces differ only in (a) typed-endpoint return
  annotations and (b) presence/absence of ``raw`` kwarg.

Plus two end-to-end parity tests confirming the surface split:

* The dict client returns ``dict`` for typed-endpoint calls.
* The typed client returns a :class:`msgspec.Struct` for those calls.
"""

from __future__ import annotations

import inspect
import typing
from typing import Any

import pytest

from swgoh_comlink import SwgohComlink as DictSyncClient
from swgoh_comlink import SwgohComlinkAsync as DictAsyncClient
from swgoh_comlink._codegen.endpoints import ENDPOINTS
from swgoh_comlink.typed import SwgohComlink as TypedSyncClient
from swgoh_comlink.typed import SwgohComlinkAsync as TypedAsyncClient

_ALL_CLIENTS = [
    ("dict-sync", DictSyncClient),
    ("dict-async", DictAsyncClient),
    ("typed-sync", TypedSyncClient),
    ("typed-async", TypedAsyncClient),
]


# ── Surface presence ────────────────────────────────────────────────────────


@pytest.mark.parametrize("ep", ENDPOINTS, ids=[ep.name for ep in ENDPOINTS])
@pytest.mark.parametrize("client_id,client_cls", _ALL_CLIENTS, ids=[c[0] for c in _ALL_CLIENTS])
def test_every_manifest_endpoint_exists_on_every_client(
    ep: Any,
    client_id: str,
    client_cls: type,
) -> None:
    """The 2x2 matrix x 15 endpoints = 60 method-presence checks."""
    assert hasattr(client_cls, ep.name), f"{client_id}: missing method {ep.name!r} from manifest"
    assert callable(getattr(client_cls, ep.name))


@pytest.mark.parametrize("ep", ENDPOINTS, ids=[ep.name for ep in ENDPOINTS])
def test_aliases_resolve_to_canonical_method(ep: Any) -> None:
    """Every camelCase alias resolves to the same underlying method."""
    for client_id, client_cls in _ALL_CLIENTS:
        canonical = getattr(client_cls, ep.name)
        for alias in ep.aliases:
            aliased = getattr(client_cls, alias, None)
            assert aliased is canonical, f"{client_id}: alias {alias!r} doesn't resolve to {ep.name!r}"


# ── Sync / async signature parity ───────────────────────────────────────────


@pytest.mark.parametrize("ep", ENDPOINTS, ids=[ep.name for ep in ENDPOINTS])
def test_sync_async_signatures_match_per_surface(ep: Any) -> None:
    """For a given surface (dict or typed), sync and async methods share params."""
    for surface_label, sync_cls, async_cls in (
        ("dict", DictSyncClient, DictAsyncClient),
        ("typed", TypedSyncClient, TypedAsyncClient),
    ):
        sync_sig = inspect.signature(getattr(sync_cls, ep.name))
        async_sig = inspect.signature(getattr(async_cls, ep.name))
        # Compare parameter names + kinds + defaults (ignore annotations
        # because Metadata|dict vs dict differ across typed/dict, but
        # sync and async share that within a surface).
        sync_params = [(p.name, p.kind, p.default) for p in sync_sig.parameters.values()]
        async_params = [(p.name, p.kind, p.default) for p in async_sig.parameters.values()]
        assert sync_params == async_params, (
            f"{surface_label} surface: sync/async signature drift on {ep.name!r}\n"
            f"  sync:  {sync_params}\n"
            f"  async: {async_params}"
        )


# ── Dict vs typed: kwargs differ only by `raw=` ─────────────────────────────


@pytest.mark.parametrize("ep", ENDPOINTS, ids=[ep.name for ep in ENDPOINTS])
def test_dict_vs_typed_signature_diff_only_in_raw_default(ep: Any) -> None:
    """Dict and typed surfaces accept the same kwargs.

    Both surfaces have a ``raw=`` kwarg on typed-endpoint methods (the
    typed surface flips it to ``False``-defaulting; the dict surface
    keeps it as a ``True``-defaulting no-op for source-compat with
    helper code that passes ``raw=True``).

    For passthrough endpoints (no ``typed_return``), neither surface
    has ``raw=``.
    """
    dict_params = list(inspect.signature(getattr(DictSyncClient, ep.name)).parameters.values())
    typed_params = list(inspect.signature(getattr(TypedSyncClient, ep.name)).parameters.values())
    dict_names = {p.name for p in dict_params}
    typed_names = {p.name for p in typed_params}

    if ep.typed_return is None:
        # Pure passthrough — neither surface has raw=.
        assert dict_names == typed_names
        assert "raw" not in dict_names
    else:
        # Both surfaces have the same parameter names (raw= on both).
        assert dict_names == typed_names, f"{ep.name!r}: surface drift dict vs typed; diff = {dict_names ^ typed_names}"
        assert "raw" in dict_names
        # Defaults differ: typed-side raw=False, dict-side raw=True.
        typed_raw_default = next(p.default for p in typed_params if p.name == "raw")
        dict_raw_default = next(p.default for p in dict_params if p.name == "raw")
        assert typed_raw_default is False
        assert dict_raw_default is True


_TYPED_ENDPOINTS = [ep for ep in ENDPOINTS if ep.typed_return is not None]


@pytest.mark.parametrize("ep", _TYPED_ENDPOINTS, ids=[ep.name for ep in _TYPED_ENDPOINTS])
@pytest.mark.parametrize("client_cls", [TypedSyncClient, TypedAsyncClient], ids=["typed-sync", "typed-async"])
def test_typed_overloads_narrow_on_raw(ep: Any, client_cls: type) -> None:
    """Typed methods overload on ``raw`` so checkers see the Struct or the dict, not their union.

    Each overload must accept the implementation's parameters (plus the legacy
    ``@param_alias`` spellings) so the overloads never reject a call that works.
    """
    impl = getattr(client_cls, ep.name)
    overloads = typing.get_overloads(impl)
    assert [o.__annotations__["raw"] for o in overloads] == ["Literal[False]", "Literal[True]", "bool"]
    assert [o.__annotations__["return"] for o in overloads] == [
        ep.typed_return,
        "dict[str, Any]",
        f"{ep.typed_return} | dict[str, Any]",
    ]

    impl_params = {p.name: p.default for p in inspect.signature(impl).parameters.values() if p.name != "raw"}
    for overload_fn in overloads:
        params = inspect.signature(overload_fn).parameters
        aliases = {name: params[name].default for name in ep.param_aliases.values()}
        assert aliases == dict.fromkeys(ep.param_aliases.values())
        own = {name: p.default for name, p in params.items() if name != "raw" and name not in aliases}
        assert own == impl_params, f"{ep.name!r}: overload params drifted from the implementation"


# ── End-to-end parity: shapes match the surface ─────────────────────────────


def test_dict_client_returns_dict_for_player(
    cassette_server: Any,
    recorded_comlink: Any,
) -> None:
    """Dict client + get_player → ``dict[str, Any]``."""
    cassette_server.use("player", "player_small")
    p = recorded_comlink.get_player(allycode=855566316)
    assert isinstance(p, dict), f"expected dict, got {type(p).__name__}"
    assert "name" in p


def test_typed_client_returns_struct_for_player(
    cassette_server: Any,
    recorded_comlink_typed: Any,
) -> None:
    """Typed client + get_player → :class:`Player` Struct."""
    import msgspec

    from swgoh_comlink._models import Player

    cassette_server.use("player", "player_small")
    p = recorded_comlink_typed.get_player(allycode=855566316)
    assert isinstance(p, msgspec.Struct)
    assert isinstance(p, Player)
    assert p.name
