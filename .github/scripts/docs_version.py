"""Decide how a ``release/*`` branch publishes its docs with mike.

Used by ``.github/workflows/docs.yml``. The docs version is the PEP 440 version
in the branch name (``release/v2.5.0`` -> ``2.5.0``, ``release/v3.0.0a2`` ->
``3.0.0a2``). The alias depends on what is already on gh-pages:

* A stable version takes ``latest`` (and becomes the site default) when it is
  at least as new as every stable version already deployed; an older one, such
  as a 2.4.2 patch after 2.5.0, is deployed with no alias.
* A pre-release takes the alias for its kind (``alpha``, ``beta``, ``rc`` or
  ``dev``) when it is at least as new as every deployed version of that kind,
  and never touches ``latest`` or the default.

Usage::

    python docs_version.py <ref name> <mike list --json output>

The decision is written to ``$GITHUB_OUTPUT`` as ``version``, ``alias`` (may be
empty), ``title``, ``set_default`` and ``prerelease``, and printed.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any

from packaging.version import InvalidVersion, Version

BRANCH_PREFIX = "release/"
LATEST = "latest"
_PRE_ALIASES = {"a": "alpha", "b": "beta", "rc": "rc"}


@dataclass(frozen=True)
class Decision:
    """How mike should deploy one version."""

    version: str
    alias: str
    title: str
    set_default: bool
    prerelease: bool


def parse_branch(ref_name: str) -> Version:
    """Return the PEP 440 version named by a ``release/[v]X.Y.Z...`` branch.

    Raises:
        ValueError: If the branch is not under ``release/`` or its name is not
            a public PEP 440 version.
    """
    if not ref_name.startswith(BRANCH_PREFIX):
        raise ValueError(f"branch {ref_name!r} is not a {BRANCH_PREFIX}* branch")
    name = ref_name.removeprefix(BRANCH_PREFIX)
    name = name.removeprefix("v")
    try:
        version = Version(name)
    except InvalidVersion:
        raise ValueError(
            f"branch {ref_name!r} does not name a PEP 440 version (expected e.g. release/v2.5.0 or release/v3.0.0a2)"
        ) from None
    if version.local is not None:
        raise ValueError(f"branch {ref_name!r} names a local version ({version}); use a public version")
    return version


def kind(version: Version) -> str | None:
    """Return the alias for a pre-release's kind, or ``None`` for a stable version.

    A ``.devN`` suffix wins over the pre-release marker, so ``3.0.0a2.dev1`` is
    ``dev``.
    """
    if version.dev is not None:
        return "dev"
    if version.pre is not None:
        return _PRE_ALIASES[version.pre[0]]
    return None


def deployed_versions(mike_list: str) -> list[Version]:
    """Return the PEP 440 versions in ``mike list --json`` output.

    Empty output (no gh-pages branch yet) means nothing is deployed. Entries
    whose name is not a PEP 440 version are ignored.
    """
    if not mike_list.strip():
        return []
    entries: list[dict[str, Any]] = json.loads(mike_list)
    versions = []
    for entry in entries:
        try:
            versions.append(Version(str(entry["version"])))
        except InvalidVersion:
            continue
    return versions


def decide(ref_name: str, mike_list: str) -> Decision:
    """Decide the docs version, alias and title for *ref_name*."""
    version = parse_branch(ref_name)
    this_kind = kind(version)
    peers = [v for v in deployed_versions(mike_list) if kind(v) == this_kind]
    newest = all(version >= v for v in peers)

    if this_kind is None:
        alias = LATEST if newest else ""
        return Decision(str(version), alias, str(version), set_default=newest, prerelease=False)

    alias = this_kind if newest else ""
    return Decision(str(version), alias, f"{version} ({this_kind})", set_default=False, prerelease=True)


def main(argv: list[str]) -> int:
    """Write the decision for ``argv[1]`` (ref name) and ``argv[2]`` (mike list JSON)."""
    if len(argv) != 3:
        print("usage: docs_version.py <ref name> <mike list --json output>", file=sys.stderr)
        return 2
    try:
        decision = decide(argv[1], argv[2])
    except ValueError as exc:
        print(f"::error::{exc}")
        return 1

    lines = [
        f"version={decision.version}",
        f"alias={decision.alias}",
        f"title={decision.title}",
        f"set_default={str(decision.set_default).lower()}",
        f"prerelease={str(decision.prerelease).lower()}",
    ]
    print("\n".join(lines))
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
