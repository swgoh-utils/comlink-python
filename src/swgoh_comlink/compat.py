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
from typing import TYPE_CHECKING, Any, TypeVar

import msgspec

from ._optional import require

if TYPE_CHECKING:
    from pydantic import BaseModel

__all__ = ["to_dict", "to_pydantic"]

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
