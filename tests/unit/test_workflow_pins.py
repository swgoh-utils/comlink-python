"""Guard that every third-party GitHub Action is pinned to a full commit SHA."""

import re
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github/workflows"
USES = re.compile(r"^\s*(?:-\s+)?uses:\s*(?P<ref>\S+)(?P<rest>.*)$")
PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
VERSION_COMMENT = re.compile(r"^\s+#\s+v\d+\.\d+\.\d+\s*$")


def _uses_lines() -> list[tuple[str, int, str, str]]:
    return [
        (path.name, number, match["ref"], match["rest"])
        for path in sorted(WORKFLOWS.glob("*.y*ml"))
        for number, line in enumerate(path.read_text().splitlines(), start=1)
        if (match := USES.match(line)) and not match["ref"].startswith("./")
    ]


def test_workflows_have_uses_lines():
    assert _uses_lines(), "no `uses:` lines found; the workflow glob is wrong"


def test_every_action_is_pinned_to_a_commit_sha_with_a_version_comment():
    unpinned = [
        f"{name}:{number}: {ref}{rest}"
        for name, number, ref, rest in _uses_lines()
        if not PINNED.match(ref) or not VERSION_COMMENT.match(rest)
    ]
    assert not unpinned, "actions must use `@<40-char sha>  # vX.Y.Z`:\n" + "\n".join(unpinned)
