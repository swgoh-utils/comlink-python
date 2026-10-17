"""Tests for .github/scripts/docs_version.py (docs version/alias decisions)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / ".github" / "scripts" / "docs_version.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("docs_version", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered first: @dataclass resolves string annotations via sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


docs_version = _load()


def _mike(*versions: str) -> str:
    """Return ``mike list --json`` output listing *versions*."""
    return json.dumps([{"version": v, "title": v, "aliases": [], "properties": None} for v in versions])


def _row(ref: str, *deployed: str) -> tuple[str, str, str, bool]:
    d = docs_version.decide(ref, _mike(*deployed))
    return d.version, d.alias, d.title, d.set_default


# ── stable ──────────────────────────────────────────────────────────────


def test_first_stable_takes_latest_with_empty_gh_pages() -> None:
    assert _row("release/v2.5.0") == ("2.5.0", "latest", "2.5.0", True)


def test_missing_gh_pages_output_counts_as_nothing_deployed() -> None:
    d = docs_version.decide("release/v2.5.0", "")
    assert (d.alias, d.set_default) == ("latest", True)


def test_older_patch_after_newer_stable_gets_no_alias() -> None:
    assert _row("release/v2.4.2", "2.5.0") == ("2.4.2", "", "2.4.2", False)


def test_newer_stable_takes_latest() -> None:
    assert _row("release/v2.6.0", "2.5.0", "2.4.2") == ("2.6.0", "latest", "2.6.0", True)


def test_redeploying_the_newest_stable_keeps_latest() -> None:
    assert _row("release/v2.5.0", "2.5.0", "2.4.2")[1] == "latest"


def test_prereleases_do_not_hold_back_a_stable_latest() -> None:
    assert _row("release/v2.6.0", "2.5.0", "3.0.0a2", "3.0.0.dev1")[1] == "latest"


def test_branch_name_without_v() -> None:
    assert _row("release/2.5.0") == ("2.5.0", "latest", "2.5.0", True)


# ── pre-releases ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("ref", "expected"),
    [
        ("release/v3.0.0a2", ("3.0.0a2", "alpha", "3.0.0a2 (alpha)", False)),
        ("release/v3.0.0a3", ("3.0.0a3", "alpha", "3.0.0a3 (alpha)", False)),
        ("release/v3.0.0b1", ("3.0.0b1", "beta", "3.0.0b1 (beta)", False)),
        ("release/v3.0.0rc1", ("3.0.0rc1", "rc", "3.0.0rc1 (rc)", False)),
        ("release/v3.0.0.dev1", ("3.0.0.dev1", "dev", "3.0.0.dev1 (dev)", False)),
        ("release/v3.0.0a2.dev1", ("3.0.0a2.dev1", "dev", "3.0.0a2.dev1 (dev)", False)),
    ],
)
def test_prerelease_takes_the_alias_for_its_kind(ref: str, expected: tuple[str, str, str, bool]) -> None:
    assert _row(ref, "2.5.0") == expected


def test_prerelease_is_flagged_and_never_sets_default() -> None:
    d = docs_version.decide("release/v3.0.0a2", _mike())
    assert (d.prerelease, d.set_default) == (True, False)
    assert docs_version.decide("release/v2.5.0", _mike()).prerelease is False


def test_newer_alpha_moves_the_alpha_alias() -> None:
    assert _row("release/v3.0.0a3", "2.5.0", "3.0.0a2")[1] == "alpha"


def test_older_alpha_after_newer_alpha_gets_no_alias() -> None:
    assert _row("release/v3.0.0a2", "2.5.0", "3.0.0a3") == ("3.0.0a2", "", "3.0.0a2 (alpha)", False)


def test_only_same_kind_versions_compete_for_an_alias() -> None:
    # A newer beta or rc does not stop an alpha from taking `alpha`.
    assert _row("release/v3.0.0a3", "3.0.0b1", "3.0.0rc1")[1] == "alpha"


def test_prerelease_name_is_normalized() -> None:
    assert _row("release/v3.0.0-alpha2")[:2] == ("3.0.0a2", "alpha")


# ── errors and output ───────────────────────────────────────────────────


@pytest.mark.parametrize("ref", ["release/next", "release/v3.0.0-foo", "release/", "main", "release/v2.5.0+local"])
def test_invalid_branch_names_are_rejected(ref: str) -> None:
    with pytest.raises(ValueError, match="release/|PEP 440|local version"):
        docs_version.decide(ref, _mike())


def test_unparseable_deployed_entries_are_ignored() -> None:
    assert _row("release/v2.5.0", "latest-preview")[1] == "latest"


def test_main_writes_github_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    assert docs_version.main(["docs_version.py", "release/v2.4.2", _mike("2.5.0")]) == 0
    assert out.read_text().splitlines() == [
        "version=2.4.2",
        "alias=",
        "title=2.4.2",
        "set_default=false",
        "prerelease=false",
    ]


def test_main_reports_invalid_name_as_github_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert docs_version.main(["docs_version.py", "release/vNext", ""]) == 1
    assert capsys.readouterr().out.startswith("::error::branch 'release/vNext' does not name a PEP 440 version")
