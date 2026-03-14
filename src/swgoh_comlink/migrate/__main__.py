# coding=utf-8
"""CLI entry point for the migration checker.

Usage::

    python -m swgoh_comlink.migrate [path] [--no-color] [--severity=WARNING]
    swgoh-migrate [path] [--no-color] [--severity=WARNING]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ._reporter import format_findings
from ._scanner import scan_directory, scan_file

_SEVERITY_ORDER = {"INFO": 0, "WARNING": 1, "ERROR": 2}


def main(argv: list[str] | None = None) -> int:
    """Run the migration checker and return an exit code."""
    parser = argparse.ArgumentParser(
        prog="swgoh_comlink.migrate",
        description="Check Python code for swgoh_comlink migration issues.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="File or directory to scan (default: current directory).",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output.",
    )
    parser.add_argument(
        "--severity",
        choices=["ERROR", "WARNING", "INFO"],
        default="INFO",
        help="Minimum severity level to report (default: INFO).",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=None,
        help="Additional directory names to exclude from scanning.",
    )

    args = parser.parse_args(argv)
    target = Path(args.path)

    if target.is_file():
        findings = scan_file(target)
    elif target.is_dir():
        findings = scan_directory(target, exclude_patterns=args.exclude)
    else:
        print(f"Error: '{target}' is not a valid file or directory.", file=sys.stderr)
        return 1

    # Filter by minimum severity
    min_severity = _SEVERITY_ORDER[args.severity]
    findings = [
        f for f in findings
        if _SEVERITY_ORDER[f.rule.severity] >= min_severity
    ]

    report = format_findings(findings, use_color=not args.no_color)
    print(report)

    # Exit code: 1 if any ERROR-level findings, 0 otherwise
    has_errors = any(f.rule.severity == "ERROR" for f in findings)
    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
