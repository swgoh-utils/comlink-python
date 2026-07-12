# coding=utf-8
"""v2 → v3 compatibility + interop helpers.

* :func:`to_dict` — convert a :class:`msgspec.Struct` instance to the
  ``dict[str, Any]`` shape v2's clients returned. Bridges callers who
  can't migrate to attribute access yet. Removed in **v3.2**.

* :func:`to_pydantic` — convert a Struct to a user-defined
  :class:`pydantic.BaseModel` instance. Lives behind the ``[pydantic]``
  extra; raises a friendly install hint if pydantic isn't installed.
  This is v3.0's pydantic story per ADR-0006 / Phase 3 D6.

* :func:`decode_segment` — opt-in typed decode of any ``/data`` segment.
  Uses the :data:`STOCK_SEGMENT_TYPES` registry for canonical types or
  accepts a user-supplied ``msgspec.Struct`` via the ``target=`` kwarg.

Migration path for to_dict: prefer attribute access
(``player.roster_unit`` instead of ``to_dict(player)['rosterUnit']``)
or pin to ``swgoh-comlink<3.2`` if you depend on this module.
"""

from __future__ import annotations

import warnings
from collections.abc import Mapping
from types import GenericAlias
from typing import TYPE_CHECKING, Any, TypeVar, cast

import msgspec

from ._models import (
    Ability,
    Campaign,
    DatacronAffixTemplateSet,
    DatacronHelpEntry,
    DatacronSet,
    DatacronTemplate,
    Effect,
    Equipment,
    Material,
    Recipe,
    SkillDefinition,
    StatMod,
    StatModSet,
    Unit,
)
from ._optional import require

if TYPE_CHECKING:
    from pydantic import BaseModel

__all__ = [
    "STOCK_SEGMENT_TYPES",
    "decode_segment",
    "to_dict",
    "to_pydantic",
]

_TModel = TypeVar("_TModel", bound="BaseModel")
T = TypeVar("T")


#: Canonical typed Struct for each ``/data`` segment the SDK knows about.
#: Used by :func:`decode_segment` when no explicit ``target=`` is passed.
#:
#: Users with bespoke shapes pass their own ``msgspec.Struct`` subclass
#: to ``decode_segment(payload, segment, target=...)`` — they do not need
#: to mutate this registry.
STOCK_SEGMENT_TYPES: Mapping[str, type] = {
    "units": Unit,
    "skill": SkillDefinition,
    "material": Material,
    "ability": Ability,
    "campaign": Campaign,
    "effect": Effect,
    "equipment": Equipment,
    "recipe": Recipe,
    "statMod": StatMod,
    "statModSet": StatModSet,
    "datacronAffixTemplateSet": DatacronAffixTemplateSet,
    "datacronTemplate": DatacronTemplate,
    "datacronSet": DatacronSet,
    "datacronHelpEntry": DatacronHelpEntry,
}


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


def decode_segment(
    payload: Mapping[str, Any],
    segment: str,
    *,
    target: type[T] | None = None,
) -> list[T]:
    """Decode a ``/data`` segment into typed :class:`msgspec.Struct` instances.

    Two modes:

    * **Curated (default):** omit ``target`` and the helper looks up the
      canonical type for *segment* in :data:`STOCK_SEGMENT_TYPES`.
    * **Custom:** pass your own ``msgspec.Struct`` subclass via
      ``target=``. The segment key is used only for the dict lookup;
      the registry is not consulted.

    The helper calls :func:`msgspec.convert` on the existing dict tree —
    no JSON re-encode hop. That matters because the common caller is
    operating on a cached ``/data`` dict (e.g. via
    :class:`GameDataCache`), not raw HTTP bytes.

    Args:
        payload: The dict returned by ``client.get_game_data(...)``.
        segment: The top-level segment key (e.g. ``"units"``,
            ``"material"``, ``"datacronTemplate"``).
        target: Optional ``msgspec.Struct`` subclass. If ``None``, the
            canonical stock type for *segment* is used.

    Returns:
        A list of *target* (or canonical type) instances. Returns ``[]``
        if *payload* contains no entry for *segment* or the entry is
        empty.

    Raises:
        ValueError: If *target* is ``None`` and *segment* is not in
            :data:`STOCK_SEGMENT_TYPES`.

    Example::

        from swgoh_comlink import SwgohComlink, compat

        client = SwgohComlink(url="...")
        raw = client.get_game_data(request_segment=0)

        units = compat.decode_segment(raw, "units")              # stock
        materials = compat.decode_segment(raw, "material")       # stock

        # Bring your own Struct for ad-hoc shapes:
        import msgspec
        class MyTinyMaterial(msgspec.Struct, rename="camel"):
            id: str = ""
            rarity: int = 0
        tiny = compat.decode_segment(raw, "material", target=MyTinyMaterial)
    """
    if target is None:
        stock = STOCK_SEGMENT_TYPES.get(segment)
        if stock is None:
            raise ValueError(
                f"no stock type registered for segment {segment!r}; "
                f"pass target=<YourStruct>. Known segments: "
                f"{sorted(STOCK_SEGMENT_TYPES)}"
            )
        # The registry maps to the canonical Struct for the segment; the
        # caller's T binds to it when target is omitted.
        target = cast("type[T]", stock)
    items = payload.get(segment)
    if not items:
        return []
    # Runtime type construction: equivalent to `list[target]`, spelled as a
    # plain constructor call so type checkers don't read the subscript as a
    # (variable-containing) type expression. msgspec accepts the alias.
    item_list_type = GenericAlias(list, (target,))
    return cast("list[T]", msgspec.convert(items, item_list_type))
