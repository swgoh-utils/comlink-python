"""Explain, and police, a major version bump computed by git-changelog.

The angular convention marks a commit as breaking when ANY line of its message matches
``^break(s|ing changes?)?[ :].+$`` (case-insensitive), so a body line that merely wraps
onto "Breaking ..." or "breaks ..." silently bumps the major version. This script reuses
git-changelog's own parse (same commits, same regex) to list every line that triggered
the bump, and writes them to the GitHub job summary.

Usage (from the repo root)::

    uv run python .github/tools/breaking_changes.py --bump auto --next-tag v3.0.0

Exits 1 only when ``--bump auto`` produced a major and no commit carries the intentional
``BREAKING CHANGE: <description>`` footer; an explicit ``--bump major`` is never blocked.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass

from git_changelog import Changelog, Commit, read_config

# The Conventional Commits footer, exactly: upper-case, single space, colon, description.
# Anything else BREAK_REGEX accepts ("Breaking changes ...", "breaks the ...") is prose.
FOOTER_REGEX = re.compile(r"^BREAKING CHANGE: \S")


@dataclass(frozen=True)
class Trigger:
    """One message line that made git-changelog treat its commit as breaking."""

    commit: Commit
    line: str

    @property
    def is_footer(self) -> bool:
        return bool(FOOTER_REGEX.match(self.line))


def major(tag: str) -> int:
    return int(tag.lstrip("v").split(".", 1)[0])


def code(text: str) -> str:
    """Render ``text`` as an inline code span, even if it contains backticks."""
    return f"`` {text} ``" if "`" in text else f"`{text}`"


def find_triggers(changelog: Changelog) -> tuple[str | None, list[Trigger]]:
    """Return the last released tag and every breaking line in the unreleased commits."""
    unreleased = changelog.versions_list[0]
    if unreleased.tag:  # HEAD is already tagged: nothing to bump.
        return unreleased.tag, []
    previous = unreleased.previous_version.tag if unreleased.previous_version else None
    regex = changelog.convention.BREAK_REGEX
    triggers = [
        Trigger(commit, line)
        for commit in unreleased.commits
        if commit.convention["is_major"]
        for line in [commit.subject, *commit.body]
        if regex.match(line)
    ]
    return previous, triggers


def render(previous: str, next_tag: str, bump: str, triggers: list[Trigger], blocked: bool) -> str:
    out = [
        f"## ⚠️ Major version bump: {previous} → {next_tag}",
        "",
        f"`bump={bump}`. git-changelog's angular convention treats a commit as breaking when"
        " **any** line of its message matches `^break(s|ing changes?)?[ :].+$`"
        " (case-insensitive). These lines triggered it:",
        "",
    ]
    if not triggers:
        out.append("_No commit since the last tag matches — the major came from the bump input._")
    for t in triggers:
        sha = t.commit.hash[:7]
        ref = f"[`{sha}`]({t.commit.url})" if t.commit.url else f"`{sha}`"
        merge = " (merge)" if len(t.commit.parent_hashes) > 1 else ""
        kind = "✅ footer" if t.is_footer else "⚠️ prose"
        out.append(f"- {ref}{merge} {t.commit.subject}  \n  {kind}: {code(t.line)}")
    out.append("")
    if blocked:
        out += [
            "### ❌ Blocked: no intentional `BREAKING CHANGE:` footer",
            "",
            "None of these lines is the exact `BREAKING CHANGE: <description>` footer, so this major"
            " is almost certainly accidental. Re-run **prepare release** with `bump=minor` (or"
            " `patch`); if the break is real, re-run with `bump=major`.",
            "",
        ]
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Explain and police a major bump from git-changelog.")
    parser.add_argument("--bump", required=True, choices=["auto", "patch", "minor", "major"])
    parser.add_argument("--next-tag", required=True, help="the tag git-changelog computed")
    args = parser.parse_args()

    config = read_config()
    changelog = Changelog(".", convention=config["convention"], versioning=config["versioning"])
    previous, triggers = find_triggers(changelog)

    if previous is None or major(args.next_tag) <= major(previous):
        print(f"{previous} → {args.next_tag}: not a major bump, nothing to check.")
        return 0

    blocked = args.bump == "auto" and not any(t.is_footer for t in triggers)
    report = render(previous, args.next_tag, args.bump, triggers, blocked)
    print(report)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(report + "\n")
    if blocked:
        print(
            "::error title=Accidental major bump?::bump=auto computed a major without a"
            " 'BREAKING CHANGE:' footer; re-run with bump=minor/patch, or bump=major if intended."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
