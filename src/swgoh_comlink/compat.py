# coding=utf-8
"""v2 → v3 compatibility + interop helpers.

* :func:`to_dict` — convert a :class:`msgspec.Struct` instance to the
  ``dict[str, Any]`` shape v2's clients returned. Bridges callers who
  can't migrate to attribute access yet. Removed in **v3.2**.

* :func:`to_pydantic` — convert a Struct to a user-defined
  :class:`pydantic.BaseModel` instance. Lives behind the ``[pydantic]``
  extra; raises a friendly install hint if pydantic isn't installed.
  This is v3.0's pydantic story per ADR-0006 / Phase 3 D6.

Migration path for to_dict: prefer attribute access
(``player.roster_unit`` instead of ``to_dict(player)['rosterUnit']``)
or pin to ``swgoh-comlink<3.2`` if you depend on this module.
"""

from __future__ import annotations

import warnings
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

import msgspec

from ._models import UNIT_LIST_DECODER, Unit
from ._optional import require

if TYPE_CHECKING:
    from pydantic import BaseModel

__all__ = ["decode_units_segment", "to_dict", "to_pydantic"]

_TModel = TypeVar("_TModel", bound="BaseModel")


def to_dict(struct: Any) -> Any:
    """Convert a :class:`msgspec.Struct` (or nested graph) to a plain dict/list.

    Keys are emitted in their wire form (camelCase) — so the result is
    byte-compatible with what v2's ``client.get_player(...)`` returned.

    Raises a :class:`DeprecationWarning` on first use. Suppress with
    ``warnings.filterwarnings("ignore", category=DeprecationWarning,
    module=r"swgoh_comlink\\.compat")``; or, better, migrate to attribute
    access and stop calling this.

    Args:
        struct: A msgspec Struct instance, or a container (list/dict)
            of Structs and primitives.

    Returns:
        A pure-Python ``dict`` / ``list`` / scalar shape with camelCase keys.
    """
    warnings.warn(
        "swgoh_comlink.compat.to_dict is a v2 -> v3 migration helper and "
        "will be removed in v3.2. Migrate to attribute access "
        "(player.roster_unit) or pin swgoh-comlink<3.2.",
        DeprecationWarning,
        stacklevel=2,
    )
    return msgspec.to_builtins(struct)


def to_pydantic(struct: Any, model_class: type[_TModel]) -> _TModel:
    """Convert a :class:`msgspec.Struct` to an instance of *model_class*.

    Requires the ``[pydantic]`` extra
    (``pip install swgoh-comlink[pydantic]``). The conversion goes
    Struct → dict (via :func:`msgspec.to_builtins`) → pydantic
    (via ``model_class.model_validate``), so the user-defined
    :class:`pydantic.BaseModel` gets full pydantic validation +
    coercion semantics.

    Example::

        from pydantic import BaseModel, Field
        from swgoh_comlink import compat

        class MyPlayer(BaseModel):
            name: str
            ally_code: str = Field(alias="allyCode")
            level: int

        client = SwgohComlink(url="...")
        player_struct = client.get_player(allycode=123456789)
        player_model = compat.to_pydantic(player_struct, MyPlayer)

    Notes:
        v3.0 chose the dynamic-adapter path (one round-trip through dict)
        rather than pre-defining pydantic models for every endpoint
        (would have doubled the type surface). See Phase 3 D6 in
        ``v3_implementation_plan.md`` for the rationale.

    Args:
        struct: A :class:`msgspec.Struct` instance (typically returned
            by an endpoint method).
        model_class: A pydantic ``BaseModel`` subclass to validate into.

    Returns:
        An instance of *model_class*.

    Raises:
        ImportError: If the ``[pydantic]`` extra isn't installed.
        pydantic.ValidationError: If *struct*'s shape doesn't match
            *model_class*.
    """
    # Trigger the install-hint error early if pydantic is missing —
    # otherwise the caller would see a confusing AttributeError on
    # model_class.model_validate.
    require("pydantic", "pydantic")
    return model_class.model_validate(msgspec.to_builtins(struct))


def decode_units_segment(payload: Mapping[str, Any]) -> list[Unit]:
    """Decode the ``units`` list inside a ``/data`` response into typed Structs.

    Pass the dict returned by :meth:`SwgohComlink.get_game_data`; the helper
    extracts ``payload["units"]``, re-encodes it as JSON, and decodes via
    a cached :class:`msgspec.json.Decoder` typed as ``list[Unit]``.

    The re-encode round-trip is the honest cost users pay for opting into
    typed access *after* the dict has materialized (e.g. after a
    :class:`GameDataCache` hit). If a future v3.x release plumbs the
    typed decoder straight through ``_request``, this helper still works
    — its contract is "raw ``/data`` dict in, typed unit list out."

    Args:
        payload: The dict returned by ``client.get_game_data(...)``. May
            contain a ``units`` key holding a ``list[dict]``; other
            segments are ignored.

    Returns:
        A list of :class:`Unit` Structs. Returns ``[]`` if *payload*
        contains no ``units`` key or the list is empty.

    Example::

        from swgoh_comlink import SwgohComlink, compat

        client = SwgohComlink(url="...")
        raw = client.get_game_data(request_segment=0)
        units = compat.decode_units_segment(raw)
        print(f"{len(units)} units; first: {units[0].name_key}")
    """
    units = payload.get("units")
    if not units:
        return []
    return UNIT_LIST_DECODER.decode(msgspec.json.encode(units))
