# coding=utf-8
"""v2 → v3 compatibility helpers.

The only public surface today is :func:`to_dict`, which converts any
v3 :class:`msgspec.Struct` instance to the equivalent ``dict[str, Any]``
shape that v2 returned. Bridges callers who can't migrate to attribute
access immediately.

Marked for removal in **v3.2**. Either migrate to attribute access
(``player.roster_unit`` instead of ``to_dict(player)['rosterUnit']``)
or pin to ``swgoh-comlink<3.2`` if you depend on this module.
"""

from __future__ import annotations

import warnings
from typing import Any

import msgspec

__all__ = ["to_dict"]


def to_dict(struct: Any) -> Any:
    """Convert a :class:`msgspec.Struct` (or nested graph) to a plain dict/list.

    Keys are emitted in their wire form (camelCase) — so the result is
    byte-compatible with what v2's ``client.get_player(...)`` returned.

    Raises a :class:`DeprecationWarning` on first use per import. Suppress
    with ``warnings.filterwarnings("ignore", category=DeprecationWarning,
    module=r"swgoh_comlink\\.compat")``; or, better, migrate to attribute
    access and stop calling this.

    Args:
        struct: A msgspec Struct instance, or a container (list/dict)
            of Structs and primitives.

    Returns:
        A pure-Python ``dict``/``list``/scalar shape with camelCase keys.
    """
    warnings.warn(
        "swgoh_comlink.compat.to_dict is a v2 -> v3 migration helper and "
        "will be removed in v3.2. Migrate to attribute access "
        "(player.roster_unit) or pin swgoh-comlink<3.2.",
        DeprecationWarning,
        stacklevel=2,
    )
    return msgspec.to_builtins(struct)
