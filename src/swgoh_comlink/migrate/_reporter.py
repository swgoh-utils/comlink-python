# coding=utf-8
"""Format scan results for console output."""

from __future__ import annotations

from ._scanner import Finding

# ANSI color codes
_COLORS = {
    "ERROR": "\033[91m",
    "WARNING": "\033[93m",
    "INFO": "\033[94m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "DIM": "\033[2m",
}


def format_findings(findings: list[Finding], *, use_color: bool = True) -> str:
    """Format findings as a human-readable report."""
    if not findings:
        return "No migration issues found."

    lines: list[str] = []

    # Group by file
    grouped: dict[str, list[Finding]] = {}
    for f in findings:
        grouped.setdefault(f.file, []).append(f)

    # Count by severity
    counts = {"ERROR": 0, "WARNING": 0, "INFO": 0}
    for f in findings:
        counts[f.rule.severity] += 1

    # Summary header
    lines.append(f"Found {len(findings)} migration issue(s) in {len(grouped)} file(s):")
    lines.append(f"  {counts['ERROR']} error(s), {counts['WARNING']} warning(s), {counts['INFO']} info")
    lines.append("")

    for file_path, file_findings in sorted(grouped.items()):
        lines.append(f"--- {file_path} ---")
        for f in sorted(file_findings, key=lambda x: x.line_number):
            sev = f.rule.severity
            if use_color:
                sev_str = f"{_COLORS[sev]}{sev}{_COLORS['RESET']}"
            else:
                sev_str = sev
            lines.append(f"  Line {f.line_number}: [{sev_str}] {f.rule.id}: {f.rule.message}")
            lines.append(f"    {f.line_text}")
            lines.append(f"    -> {f.rule.suggestion}")
            lines.append("")

    return "\n".join(lines)
