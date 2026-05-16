# coding=utf-8
"""swgoh_comlink — Python interface to the swgoh-comlink HTTP service.

Phase 5: lazy package-level imports via PEP 562 ``__getattr__``.

``import swgoh_comlink`` no longer eagerly loads httpx, msgspec, the
StatCalc subpackage, or any of the SDK's own modules. The first
attribute access resolves and caches the import, paying the cost only
when actually needed. Short-lived CLI scripts and code that touches a
single subset of the surface pay nothing for what they don't use.

Public surface (still importable as ``from swgoh_comlink import X``):

* :class:`SwgohComlink`, :class:`SwgohComlinkAsync` — clients
* :class:`StatCalc`, :class:`StatCalcAsync` — stat calculation
* :class:`GameDataBuilder`, :class:`GameDataBuilderAsync` — data shaping
* ``compat`` — the v2→v3 migration helper module (lazy)
* ``version`` — string version constant
"""

from __future__ import annotations

import importlib
import logging
import sys
from typing import TYPE_CHECKING, Any

# ── Eagerly loaded ─────────────────────────────────────────────────────────
#
# Version is tiny + universally needed (e.g. logging tags, telemetry).
# Everything else defers.
from .version import __version__ as version

# ── Type-checking-only re-exports ──────────────────────────────────────────
#
# These run during static analysis (mypy, ty, IDE jump-to-definition) but
# are not executed at runtime — TYPE_CHECKING is False.
if TYPE_CHECKING:
    from . import compat
    from .StatCalc import GameDataBuilder, GameDataBuilderAsync, StatCalc, StatCalcAsync
    from .swgoh_comlink import SwgohComlink
    from .swgoh_comlink_async import SwgohComlinkAsync


# ── Lazy attribute map ─────────────────────────────────────────────────────
#
# Each public name → the dotted submodule path it lives in. First access
# triggers ``importlib.import_module`` + ``getattr(module, name)`` + cache.
#
# StatCalc the *class* lives inside swgoh_comlink.StatCalc the *module*
# (case collision); both map here to the same module — getattr picks the
# class by name.
_LAZY: dict[str, str] = {
    "SwgohComlink": "swgoh_comlink.swgoh_comlink",
    "SwgohComlinkAsync": "swgoh_comlink.swgoh_comlink_async",
    "StatCalc": "swgoh_comlink.StatCalc",
    "StatCalcAsync": "swgoh_comlink.StatCalc",
    "GameDataBuilder": "swgoh_comlink.StatCalc",
    "GameDataBuilderAsync": "swgoh_comlink.StatCalc",
}

# Names that resolve to the submodule itself rather than an attribute on it.
_LAZY_MODULES: dict[str, str] = {
    "compat": "swgoh_comlink.compat",
}


__all__ = [
    "GameDataBuilder",
    "GameDataBuilderAsync",
    "StatCalc",
    "StatCalcAsync",
    "SwgohComlink",
    "SwgohComlinkAsync",
    "compat",
    "version",
]


# Capture references that must not be shadowed by the
# ``swgoh_comlink.globals`` submodule. Once any caller does
# ``from swgoh_comlink.globals import ...``, Python sets
# ``swgoh_comlink.globals = <module>`` as a side effect — which would
# shadow the builtin ``globals`` function inside this module's namespace.
# Snapshotting the *module* itself sidesteps the problem.
_this_module = sys.modules[__name__]


def __getattr__(name: str) -> Any:
    """Resolve a lazy public name via :data:`_LAZY` / :data:`_LAZY_MODULES`.

    PEP 562 (Python 3.7+) — invoked when an attribute isn't already on
    the module. Unknown names raise :class:`AttributeError` so typos
    fail loudly.
    """
    value: Any
    if name in _LAZY_MODULES:
        value = importlib.import_module(_LAZY_MODULES[name])
    elif name in _LAZY:
        module = importlib.import_module(_LAZY[name])
        value = getattr(module, name)
    else:
        raise AttributeError(f"module 'swgoh_comlink' has no attribute {name!r}")
    # Cache on the module so subsequent accesses skip __getattr__ entirely.
    # Use setattr (not globals()[...]) because ``globals`` may have been
    # shadowed by the submodule of the same name.
    setattr(_this_module, name, value)
    return value


def __dir__() -> list[str]:
    """Make ``dir(swgoh_comlink)`` show lazy names (helps REPL completion)."""
    return sorted(set(vars(_this_module)) | set(_LAZY) | set(_LAZY_MODULES))


# Library logging hygiene — only add NullHandler so the application
# controls all logging configuration.
# https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger(__name__).addHandler(logging.NullHandler())
