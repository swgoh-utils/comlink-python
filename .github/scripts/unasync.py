"""Generate the sync clients from the async ones.

The async client is the source. Each sync client is its async twin with these token rewrites, passed
through ``ruff`` so it is import-sorted and formatted like any hand-written file:

* ``async`` before ``def``, ``with`` or ``for`` is dropped, and so is every ``await``. Parentheses that
  only group an awaited primary expression, as in ``(await self._get_versions()).require_game()``, go too.
* Names are renamed by :data:`NAME_RENAMES` and dotted names by :data:`DOTTED_RENAMES`;
  ``import asyncio`` becomes ``import threading``.
* Docstrings and comments get :data:`NAME_RENAMES` as whole words plus :data:`TEXT_RENAMES`, which turn
  the code in examples sync. Everything else in them is copied verbatim, so their prose must hold for both
  runtimes.

Usage::

    uv run python .github/scripts/unasync.py          # rewrite the sync files
    uv run python .github/scripts/unasync.py --check  # exit 1 and print a diff when one is out of date

Only the standard library and ``ruff``, already a dev dependency, are used.
"""

from __future__ import annotations

import argparse
import difflib
import io
import keyword
import re
import shutil
import subprocess
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "swgoh_comlink"

#: (async source, sync target) pairs, relative to the package directory.
FILES: tuple[tuple[str, str], ...] = (("swgoh_comlink_async.py", "swgoh_comlink.py"),)

#: Whole-name renames, applied to NAME tokens in code and as whole words in docstrings and comments.
NAME_RENAMES: dict[str, str] = {
    "SwgohComlinkAsync": "SwgohComlink",
    "swgoh_comlink_async": "swgoh_comlink",
    "AsyncClient": "Client",
    "aclose": "close",
    "__aenter__": "__enter__",
    "__aexit__": "__exit__",
    "aiter_bytes": "iter_bytes",
    "_async_sleep": "_sleep",
}

#: Dotted-name renames in code, matched as ``NAME . NAME``.
DOTTED_RENAMES: dict[tuple[str, str], tuple[str, str]] = {("asyncio", "Lock"): ("threading", "Lock")}

#: Module renames in a bare ``import x`` statement.
IMPORT_RENAMES: dict[str, str] = {"asyncio": "threading"}

#: Extra regex renames for docstrings and comments: the runtime adjective and the code in examples.
TEXT_RENAMES: tuple[tuple[str, str], ...] = (
    (r"\bAsynchronous\b", "Synchronous"),
    (r"\basync (def|with|for)\b", r"\1"),
    (r"\bawait\s+", ""),
)

HEADER = "# GENERATED from {source} by .github/scripts/unasync.py. Do not edit: change the source and rerun.\n"

_TEXT_PATTERNS = tuple(
    (re.compile(pattern), new)
    for pattern, new in [*((rf"\b{re.escape(old)}\b", new) for old, new in NAME_RENAMES.items()), *TEXT_RENAMES]
)

# Tokens after which ``(`` opens a call or subscript rather than a group.
_CALLABLE_ENDS = {")", "]"}


def _rename_text(text: str) -> str:
    for pattern, replacement in _TEXT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _closing_paren(tokens: list[tokenize.TokenInfo], open_index: int) -> int:
    """Index of the token that closes the bracket at *open_index*."""
    depth = 0
    for j in range(open_index, len(tokens)):
        if tokens[j].string in "([{":
            depth += 1
        elif tokens[j].string in ")]}":
            depth -= 1
            if depth == 0:
                return j
    raise ValueError(f"unbalanced bracket at line {tokens[open_index].start[0]}")


def _is_grouping_paren(tokens: list[tokenize.TokenInfo], index: int) -> bool:
    """Whether the ``(`` at *index* groups an expression instead of opening a call or a subscript."""
    if index == 0:
        return True
    before = tokens[index - 1]
    if before.type == tokenize.NAME:
        return keyword.iskeyword(before.string) and before.string not in ("True", "False", "None")
    return before.string not in _CALLABLE_ENDS and before.type not in (tokenize.STRING, tokenize.NUMBER)


def _is_primary(tokens: list[tokenize.TokenInfo], start: int, stop: int) -> bool:
    """Whether ``tokens[start:stop]`` is one primary expression: names, dots, calls and subscripts only."""
    j = start
    while j < stop:
        tok = tokens[j]
        if tok.string in "([":
            j = _closing_paren(tokens, j) + 1
        elif tok.type == tokenize.NAME and not keyword.iskeyword(tok.string) or tok.string == ".":
            j += 1
        else:
            return False
    return True


def _ends_line(tok: tokenize.TokenInfo | None) -> bool:
    return tok is None or tok.type == tokenize.NEWLINE


def unasync_source(source: str) -> str:
    """Rewrite async Python *source* as its sync twin, before import sorting and formatting."""
    line_starts = [0]
    for line in source.splitlines(keepends=True):
        line_starts.append(line_starts[-1] + len(line))

    def offset(point: tuple[int, int]) -> int:
        return line_starts[point[0] - 1] + point[1]

    skipped = (tokenize.NL, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER)
    tokens = [t for t in tokenize.generate_tokens(io.StringIO(source).readline) if t.type not in skipped]
    edits: dict[int, tuple[int, str]] = {}  # start offset -> (end offset, replacement)

    def replace(first: tokenize.TokenInfo, until: tokenize.TokenInfo | None, text: str) -> None:
        """Replace from the start of *first* to the start of *until* (or the end of *first*) with *text*."""
        end = offset(until.start) if until is not None else offset(first.end)
        edits[offset(first.start)] = (end, text)

    for i, tok in enumerate(tokens):
        prev = tokens[i - 1] if i else None
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if tok.type in (tokenize.STRING, tokenize.COMMENT):
            if (renamed := _rename_text(tok.string)) != tok.string:
                replace(tok, None, renamed)
        elif tok.type != tokenize.NAME:
            continue
        elif tok.string == "async" and nxt is not None and nxt.string in ("def", "with", "for"):
            replace(tok, nxt, "")
        elif tok.string == "await":
            assert nxt is not None
            replace(tok, nxt, "")
            if prev is not None and prev.string == "(" and _is_grouping_paren(tokens, i - 1):
                close = _closing_paren(tokens, i - 1)
                if _is_primary(tokens, i + 1, close):
                    replace(prev, tok, "")
                    replace(tokens[close], None, "")
        elif prev is not None and prev.string == "import" and tok.string in IMPORT_RENAMES and _ends_line(nxt):
            replace(tok, None, IMPORT_RENAMES[tok.string])
        elif nxt is not None and nxt.string == "." and i + 2 < len(tokens):
            pair = (tok.string, tokens[i + 2].string)
            if pair in DOTTED_RENAMES:
                replace(tok, None, DOTTED_RENAMES[pair][0])
                replace(tokens[i + 2], None, DOTTED_RENAMES[pair][1])
            elif tok.string in NAME_RENAMES:
                replace(tok, None, NAME_RENAMES[tok.string])
        elif tok.string in NAME_RENAMES:
            replace(tok, None, NAME_RENAMES[tok.string])

    out = source
    for start in sorted(edits, reverse=True):
        end, text = edits[start]
        out = out[:start] + text + out[end:]
    return out


def _ruff(source: str, filename: Path) -> str:
    """Import-sort and format *source* with the project's ruff settings."""
    ruff = shutil.which("ruff")
    if ruff is None:
        raise SystemExit("ruff not found: run this through `uv run` so the dev dependencies are on PATH.")
    for args in (["check", "--select", "I", "--fix", "--exit-zero", "--quiet"], ["format", "--quiet"]):
        source = subprocess.run(
            [ruff, *args, "--stdin-filename", str(filename), "-"],
            input=source,
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT,
        ).stdout
    return source


def generate(source_path: Path, target_path: Path) -> str:
    """The text *source_path* generates for *target_path*, header included."""
    body = unasync_source(source_path.read_text(encoding="utf-8"))
    header = HEADER.format(source=source_path.name)
    # A leading ``# coding`` line must stay first; the header follows it.
    first, sep, rest = body.partition("\n")
    body = f"{first}{sep}{header}{rest}" if first.startswith("# coding") else header + body
    return _ruff(body, target_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the sync clients from the async ones.")
    parser.add_argument("--check", action="store_true", help="exit 1 and print a diff when a sync file is stale")
    args = parser.parse_args(argv)
    stale = []
    for source_name, target_name in FILES:
        source_path, target_path = PACKAGE / source_name, PACKAGE / target_name
        expected = generate(source_path, target_path)
        current = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
        if current == expected:
            continue
        rel = target_path.relative_to(ROOT).as_posix()
        if args.check:
            stale.append(rel)
            sys.stdout.writelines(
                difflib.unified_diff(
                    current.splitlines(keepends=True), expected.splitlines(keepends=True), rel, f"{rel} (generated)"
                )
            )
        else:
            target_path.write_text(expected, encoding="utf-8")
            print(f"wrote {rel}")
    if stale:
        print(f"\nOut of date: {', '.join(stale)}. Run `uv run python .github/scripts/unasync.py`.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
