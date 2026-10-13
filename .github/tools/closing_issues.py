"""Find the issues that merged pull requests resolve, for the develop -> main release flow.

GitHub only acts on closing keywords ("Closes #12") in a pull request that merges into the
DEFAULT branch (main). Work here merges into develop, so the keywords are recorded but never
fire, and the release PR that later carries the fix to main has no keywords of its own. This
script reads the keywords back out of the merged pull requests (descriptions and commit
messages) so they can be:

* ``release``: re-stated in the release PR body, so GitHub closes the issues when the release
  merges into main.
* ``develop``: announced on each still-open issue as soon as its fix merges into develop.

Matching follows GitHub's rules: a keyword (close/closes/closed, fix/fixes/fixed,
resolve/resolves/resolved, optional colon) directly before ONE reference — ``#12``,
``owner/repo#12`` or an issue URL in this repository. "Closes #1, #2" closes only #1, as on
GitHub. HTML comments (the PR template's hints) and code are ignored.

Usage (from the repo root, with ``gh`` authenticated)::

    python3 .github/tools/closing_issues.py release --since v2.5.0
    python3 .github/tools/closing_issues.py develop --sha <merge commit> [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

KEYWORD_REGEX = re.compile(
    r"(?<![\w/#-])(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?[ \t]+"
    r"(?:(?P<repo>[\w.-]+/[\w.-]+)?#(?P<number>\d+)"
    r"|https://github\.com/(?P<url_repo>[\w.-]+/[\w.-]+)/issues/(?P<url_number>\d+))\b",
    re.IGNORECASE,
)
# Text GitHub does not scan for keywords: HTML comments, fenced code blocks (including ones
# indented inside list items), and inline code.
IGNORED_REGEX = re.compile(
    r"<!--.*?-->|^[ \t]*(?P<fence>```|~~~).*?^[ \t]*(?P=fence)|`[^`\n]*`", re.DOTALL | re.MULTILINE
)
MERGE_SUBJECT_REGEX = re.compile(r"^Merge pull request #(\d+) from ")
# Marks comments this script posted, so a re-run never posts the same note twice.
MARKER = "<!-- closing-issues: pr={pr} -->"


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def referenced_issues(text: str, repo: str) -> list[int]:
    """Issue numbers in ``repo`` that ``text`` closes, in order of first mention."""
    text = IGNORED_REGEX.sub(" ", text)
    numbers: dict[int, None] = {}
    for m in KEYWORD_REGEX.finditer(text):
        ref_repo = m["repo"] or m["url_repo"] or repo
        if ref_repo.lower() == repo.lower():
            numbers[int(m["number"] or m["url_number"])] = None
    return list(numbers)


def pull_request_text(repo: str, pr: int) -> str:
    """The PR description plus every commit message in it."""
    body = gh("api", f"repos/{repo}/pulls/{pr}", "--jq", '.body // ""')
    messages = gh("api", "--paginate", f"repos/{repo}/pulls/{pr}/commits", "--jq", ".[].commit.message")
    return f"{body}\n\n{messages}"


def is_open_issue(repo: str, number: int) -> bool:
    """True for an open issue; False for a closed one, a pull request, or a missing number."""
    try:
        issue = json.loads(gh("api", f"repos/{repo}/issues/{number}"))
    except subprocess.CalledProcessError:
        return False
    return issue["state"] == "open" and "pull_request" not in issue


def issues_by_pr(repo: str, prs: list[int]) -> dict[int, list[int]]:
    """Map each still-open issue to the merged PRs that resolve it."""
    found: dict[int, list[int]] = {}
    for pr in prs:
        for number in referenced_issues(pull_request_text(repo, pr), repo):
            found.setdefault(number, []).append(pr)
    return {n: found[n] for n in sorted(found) if is_open_issue(repo, n)}


def refs(prs: list[int]) -> str:
    return ", ".join(f"#{pr}" for pr in prs)


def release(repo: str, since: str) -> int:
    """Print the release PR section that re-states the closing keywords merged since ``since``."""
    subjects = subprocess.run(
        ["git", "log", "--merges", "--format=%s", f"{since}..HEAD"], check=True, capture_output=True, text=True
    ).stdout.splitlines()
    prs = sorted({int(m[1]) for s in subjects if (m := MERGE_SUBJECT_REGEX.match(s))})
    found = issues_by_pr(repo, prs)
    if not found:
        print(f"_No open issues are referenced by the {len(prs)} pull requests merged since {since}._")
        return 0
    # One keyword per line: GitHub closes only the first reference after each keyword.
    print("### Issues resolved by this release\n")
    print("Merging this PR into `main` closes:\n")
    for number, by in found.items():
        print(f"- Closes #{number} (via {refs(by)})")
    return 0


def develop(repo: str, sha: str, dry_run: bool) -> int:
    """Comment on each open issue resolved by the PR(s) that ``sha`` merged into develop."""
    prs = [
        int(n)
        for n in gh(
            "api",
            f"repos/{repo}/commits/{sha}/pulls",
            "--jq",
            '.[] | select(.merged_at != null and .base.ref == "develop") | .number',
        ).split()
    ]
    if not prs:
        print(f"{sha[:7]} is not a pull request merge into develop; nothing to do.")
        return 0
    summary = []
    for number, by in issues_by_pr(repo, prs).items():
        for pr in by:
            marker = MARKER.format(pr=pr)
            existing = gh("api", "--paginate", f"repos/{repo}/issues/{number}/comments", "--jq", ".[].body")
            if marker in existing:
                summary.append(f"- #{number}: already noted for #{pr}")
                continue
            body = (
                f"{marker}\nAddressed by #{pr}, which is now merged into `develop`. This issue will close"
                " automatically when that change is released to `main`."
            )
            if not dry_run:
                gh("api", "-X", "POST", f"repos/{repo}/issues/{number}/comments", "-f", f"body={body}")
            summary.append(f"- #{number}: {'would comment' if dry_run else 'commented'} (resolved by #{pr})")
    report = "\n".join(summary) or f"No open issues are referenced by {refs(prs)}."
    print(report)
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"## Issues addressed by {refs(prs)}\n\n{report}\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Carry closing keywords from develop merges through to main.")
    sub = parser.add_subparsers(dest="command", required=True)
    rel = sub.add_parser("release", help="print the release PR's 'Closes #N' section")
    rel.add_argument("--since", required=True, help="the last release tag")
    dev = sub.add_parser("develop", help="comment on open issues resolved by a merge into develop")
    dev.add_argument("--sha", required=True, help="the merge commit pushed to develop")
    dev.add_argument("--dry-run", action="store_true", help="report without commenting")
    args = parser.parse_args()

    repo = os.environ.get("GITHUB_REPOSITORY") or gh(
        "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"
    )
    repo = repo.strip()
    if args.command == "release":
        return release(repo, args.since)
    return develop(repo, args.sha, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
