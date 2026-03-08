# coding=utf-8
"""Scan Python files for deprecated swgoh_comlink patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ._rules import RULES, MigrationRule


@dataclass
class Finding:
    """A single migration issue found in a file."""

    file: str
    line_number: int
    line_text: str
    rule: MigrationRule


_DEFAULT_EXCLUDES = frozenset({
    ".venv", "venv", "__pycache__", ".git", "node_modules",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".eggs", "*.egg-info",
})


def scan_file(file_path: Path) -> list[Finding]:
    """Scan a single Python file against all migration rules."""
    findings: list[Finding] = []
    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return findings

    compiled = [(re.compile(rule.pattern), rule) for rule in RULES]

    for line_no, line in enumerate(text.splitlines(), start=1):
        for pattern, rule in compiled:
            if pattern.search(line):
                findings.append(Finding(
                    file=str(file_path),
                    line_number=line_no,
                    line_text=line.strip(),
                    rule=rule,
                ))
    return findings


def scan_directory(
    directory: Path,
    exclude_patterns: list[str] | None = None,
) -> list[Finding]:
    """Recursively scan a directory for Python files."""
    findings: list[Finding] = []
    excludes = set(exclude_patterns) if exclude_patterns else set(_DEFAULT_EXCLUDES)

    for py_file in sorted(directory.rglob("*.py")):
        if any(part in excludes for part in py_file.parts):
            continue
        findings.extend(scan_file(py_file))
    return findings
