# coding=utf-8
"""Expose the installed package version as ``__version__``.

The version is derived from the Git tag at build time via ``hatch-vcs``
(see ``[tool.hatch.version]`` in ``pyproject.toml``). The build writes the
resolved value to the git-ignored ``_version.py``; we read it from there,
falling back to installed package metadata, then to a sentinel for an
unbuilt source tree.
"""

from __future__ import annotations

try:
    # Generated at build time by hatch-vcs (git-ignored).
    from swgoh_comlink._version import __version__
except ImportError:  # pragma: no cover - exercised only in unbuilt trees
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _package_version

    try:
        __version__ = _package_version("swgoh_comlink")
    except PackageNotFoundError:
        __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
