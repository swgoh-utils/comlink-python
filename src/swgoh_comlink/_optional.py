# coding=utf-8
"""Helpers for gating code paths behind ``pip install swgoh-comlink[extra]``.

Each optional feature in the v3 SDK lives behind a pip extra. When user
code triggers one of those features without the extra installed,
:func:`require` raises an :class:`ImportError` with a copy-pasteable
install command — much friendlier than a stack trace ending in
"ModuleNotFoundError: No module named 'pydantic'".

Public surface:

* :func:`require` — eagerly import + return modules; raise with the
  install hint on failure.
* :func:`has_extra` — cheap True/False probe (no exception flow).
"""

from __future__ import annotations

import importlib
from types import ModuleType

__all__ = ["has_extra", "require"]


def require(extra: str, *modules: str) -> list[ModuleType]:
    """Import each of *modules*; raise a friendly :class:`ImportError` if any fails.

    Args:
        extra: The pip extra name (``"cache"``, ``"pydantic"``, etc.).
            Appears in the error message: ``pip install swgoh-comlink[X]``.
        *modules: Dotted import paths to require (typically the package
            name(s) the extra installs).

    Returns:
        List of imported module objects, in the same order as *modules*.

    Raises:
        ImportError: If any module is missing. The exception message
            tells the caller how to install.

    Example::

        diskcache, cachetools = require("cache", "diskcache", "cachetools")
        cache = diskcache.Cache(directory="...")
    """
    if not modules:
        raise ValueError("require() needs at least one module name")
    imported: list[ModuleType] = []
    for name in modules:
        try:
            imported.append(importlib.import_module(name))
        except ImportError as e:
            raise ImportError(
                f"This feature requires the '{extra}' extra. Install with: pip install swgoh-comlink[{extra}]",
            ) from e
    return imported


def has_extra(extra: str, *modules: str) -> bool:
    """Return True if every module in *modules* can be imported.

    Probe form of :func:`require`. Useful in tests (``skipif``) or in
    code paths that want to *adapt* rather than *fail* when an extra is
    missing — e.g. picking a fallback implementation.

    The *extra* argument is accepted for symmetry with :func:`require`
    but unused here (it has no effect on the import probe).
    """
    del extra  # unused — kept for API symmetry
    for name in modules:
        try:
            importlib.import_module(name)
        except ImportError:
            return False
    return True
