"""Tests for the migration checker tool."""

from __future__ import annotations

from pathlib import Path

import pytest

# ── MigrationRule ──────────────────────────────────────────────────────


class TestMigrationRule:
    def test_instantiation(self):
        from swgoh_comlink.migrate._rules import MigrationRule

        rule = MigrationRule(
            id="TEST01",
            pattern=r"foo",
            severity="WARNING",
            message="Test rule",
            suggestion="Fix it",
        )
        assert rule.id == "TEST01"
        assert rule.severity == "WARNING"

    def test_frozen(self):
        from dataclasses import FrozenInstanceError

        from swgoh_comlink.migrate._rules import MigrationRule

        rule = MigrationRule(id="T", pattern="p", severity="INFO", message="m", suggestion="s")
        with pytest.raises(FrozenInstanceError):
            rule.id = "NEW"

    def test_rules_list_not_empty(self):
        from swgoh_comlink.migrate._rules import RULES

        assert len(RULES) > 0
        assert all(r.id.startswith("DEP") for r in RULES)


# ── scan_file ──────────────────────────────────────────────────────────


class TestScanFile:
    def test_finds_deprecated_patterns(self, tmp_path: Path):
        from swgoh_comlink.migrate._scanner import scan_file

        f = tmp_path / "test_code.py"
        f.write_text("import requests\n")
        findings = scan_file(f)
        assert len(findings) >= 1
        assert any(f.rule.id == "DEP002" for f in findings)

    def test_clean_file_returns_empty(self, tmp_path: Path):
        from swgoh_comlink.migrate._scanner import scan_file

        f = tmp_path / "clean.py"
        f.write_text("import json\nprint('hello')\n")
        findings = scan_file(f)
        assert findings == []

    def test_nonexistent_file_returns_empty(self, tmp_path: Path):
        from swgoh_comlink.migrate._scanner import scan_file

        findings = scan_file(tmp_path / "does_not_exist.py")
        assert findings == []

    def test_finding_has_correct_line_info(self, tmp_path: Path):
        from swgoh_comlink.migrate._scanner import scan_file

        f = tmp_path / "code.py"
        f.write_text("# line 1\nimport requests\n# line 3\n")
        findings = scan_file(f)
        match = [x for x in findings if x.rule.id == "DEP002"]
        assert len(match) == 1
        assert match[0].line_number == 2
        assert "import requests" in match[0].line_text


# ── scan_directory ─────────────────────────────────────────────────────


class TestScanDirectory:
    def test_recursive_scan(self, tmp_path: Path):
        from swgoh_comlink.migrate._scanner import scan_directory

        sub = tmp_path / "pkg"
        sub.mkdir()
        (sub / "module.py").write_text("import requests\n")
        (tmp_path / "top.py").write_text("import requests\n")

        findings = scan_directory(tmp_path)
        files = {f.file for f in findings}
        assert len(files) == 2

    def test_excludes_patterns(self, tmp_path: Path):
        from swgoh_comlink.migrate._scanner import scan_directory

        excluded = tmp_path / "vendor"
        excluded.mkdir()
        (excluded / "old.py").write_text("import requests\n")
        (tmp_path / "main.py").write_text("import requests\n")

        findings = scan_directory(tmp_path, exclude_patterns=["vendor"])
        files = {f.file for f in findings}
        assert all("vendor" not in f for f in files)

    def test_default_excludes_venv(self, tmp_path: Path):
        from swgoh_comlink.migrate._scanner import scan_directory

        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "lib.py").write_text("import requests\n")

        findings = scan_directory(tmp_path)
        assert all(".venv" not in f.file for f in findings)

    @pytest.mark.parametrize(
        ("rel_path", "exclude_patterns"),
        [
            (".venv/b.py", ["vendor"]),
            ("pkg.egg-info/c.py", None),
            ("src/vendor/d.py", ["vend*"]),
            ("old.py", ["old.py"]),
        ],
        ids=["extra-exclude-keeps-defaults", "egg-info-glob", "user-glob", "file-name"],
    )
    def test_skips_excluded_paths(self, tmp_path: Path, rel_path: str, exclude_patterns: list[str] | None):
        from swgoh_comlink.migrate._scanner import scan_directory

        skipped = tmp_path / rel_path
        skipped.parent.mkdir(parents=True, exist_ok=True)
        skipped.write_text("import requests\n")
        (tmp_path / "main.py").write_text("import requests\n")

        findings = scan_directory(tmp_path, exclude_patterns=exclude_patterns)
        assert {f.file for f in findings} == {str(tmp_path / "main.py")}

    def test_excluded_name_above_the_root_is_ignored(self, tmp_path: Path):
        from swgoh_comlink.migrate._scanner import scan_directory

        project = tmp_path / "build" / "proj"
        project.mkdir(parents=True)
        (project / "a.py").write_text("import requests\n")

        findings = scan_directory(project)
        assert {f.file for f in findings} == {str(project / "a.py")}


# ── format_findings ────────────────────────────────────────────────────


class TestFormatFindings:
    def test_empty_returns_default_message(self):
        from swgoh_comlink.migrate._reporter import format_findings

        assert format_findings([]) == "No migration issues found."

    @pytest.mark.parametrize("use_color", [True, False], ids=["color", "no-color"])
    def test_with_findings(self, tmp_path: Path, use_color: bool):
        from swgoh_comlink.migrate._reporter import format_findings
        from swgoh_comlink.migrate._scanner import scan_file

        f = tmp_path / "test.py"
        f.write_text("import requests\n")
        report = format_findings(scan_file(f), use_color=use_color)

        assert "Found 1 migration issue(s) in 1 file(s):" in report
        assert "DEP002" in report
        # Severity is wrapped in yellow ANSI codes only when color is on.
        assert ("[\033[93mWARNING\033[0m]" in report) is use_color
        assert ("\033[" in report) is use_color
        assert ("[WARNING]" in report) is not use_color


# ── main CLI ───────────────────────────────────────────────────────────


class TestMain:
    def test_scan_file_arg(self, tmp_path: Path):
        from swgoh_comlink.migrate.__main__ import main

        f = tmp_path / "code.py"
        f.write_text("print('clean')\n")
        exit_code = main([str(f)])
        assert exit_code == 0

    def test_scan_directory_arg(self, tmp_path: Path):
        from swgoh_comlink.migrate.__main__ import main

        (tmp_path / "m.py").write_text("print('clean')\n")
        exit_code = main([str(tmp_path)])
        assert exit_code == 0

    def test_invalid_path(self, tmp_path: Path):
        from swgoh_comlink.migrate.__main__ import main

        exit_code = main([str(tmp_path / "nonexistent")])
        assert exit_code == 1

    @pytest.mark.parametrize(
        ("severity", "reported"),
        [("INFO", True), ("WARNING", False), ("ERROR", False)],
    )
    def test_severity_filter(self, tmp_path: Path, capsys: pytest.CaptureFixture[str], severity: str, reported: bool):
        from swgoh_comlink.migrate.__main__ import main

        f = tmp_path / "code.py"
        # DEP005 is INFO severity
        f.write_text("from swgoh_comlink.globals import get_logger\n")

        assert main([str(f), "--severity", severity, "--no-color"]) == 0
        out = capsys.readouterr().out
        assert ("DEP005" in out) is reported
        assert ("No migration issues found." in out) is not reported

    @pytest.mark.parametrize("no_color", [True, False], ids=["no-color", "color"])
    def test_no_color_flag(self, tmp_path: Path, capsys: pytest.CaptureFixture[str], no_color: bool):
        from swgoh_comlink.migrate.__main__ import main

        f = tmp_path / "code.py"
        f.write_text("import requests\n")

        assert main([str(f), *(["--no-color"] if no_color else [])]) == 0
        out = capsys.readouterr().out
        assert "DEP002" in out
        assert ("\033[" in out) is not no_color
