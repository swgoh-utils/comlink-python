# coding=utf-8
"""Typed-Struct surface for swgoh-comlink.

``from swgoh_comlink.typed import SwgohComlink, SwgohComlinkAsync``

Endpoint methods that have a typed return value
(``get_player``, ``get_guild``, ``get_game_metadata``,
``get_leaderboard``) return a :class:`msgspec.Struct` by default;
pass ``raw=True`` per call for the v2-compatible dict shape.

The dict-default surface lives at the top-level
``swgoh_comlink.SwgohComlink`` / ``swgoh_comlink.SwgohComlinkAsync``.
See ``docs/adr/0005-typed-dict-client-split.md`` for the rationale.

Both submodules' clients are code-generated from
``swgoh_comlink._codegen.endpoints``; edit the manifest, then
``make generate``.
"""

from __future__ import annotations

from .swgoh_comlink import SwgohComlink
from .swgoh_comlink_async import SwgohComlinkAsync

__all__ = ["SwgohComlink", "SwgohComlinkAsync"]
