# coding=utf-8
"""Expose the installed package version as ``__version__``.

The version is derived from the Git tag at build time via ``hatch-vcs``
(see ``[tool.hatch.version]`` in ``pyproject.toml``). The build hook
writes the resolved value to the git-ignored ``_version.py``; we read
it from there, falling back to installed package metadata, then to a
v3 sentinel for an unbuilt source tree.

On the ``release/v3.0.0a1`` branch:
  - CI builds use ``SETUPTOOLS_SCM_PRETEND_VERSION=3.0.0a1 hatch build``
    so the wheel is named correctly before the git tag exists.
  - After the tag is created by the alpha-release workflow, hatch-vcs
    resolves ``_version.py`` to ``3.0.0a1`` automatically on
    subsequent builds.
  - The sentinel ``"3.0.0a1"`` below is only reached in an unbuilt
    source checkout with no installed package.
"""

from __future__ import annotations

# Pre-declared so mypy knows __version__ is always str regardless of
# which branch of the try/except resolves it.
__version__: str

try:
    # Generated at build time by hatch-vcs (git-ignored).
    from swgoh_comlink._version import __version__
except ImportError:  # pragma: no cover - exercised only in unbuilt trees
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _package_version

    try:
        __version__ = _package_version("swgoh_comlink")
    except PackageNotFoundError:
        # Unbuilt release/v3.0.0a1 source tree — no tag and not installed.
        __version__ = "3.0.0a1"

__all__ = ["__version__"]
