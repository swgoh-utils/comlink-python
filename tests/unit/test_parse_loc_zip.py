"""Tests for parse_loc_zip from examples/Sync/get_location_bundle_adv.py.

Validates zip -> JSON parsing, comment skipping, delimiter handling, directory skipping,
encoding support, and output file creation.
"""

from __future__ import annotations

import importlib.util
import io
import json
import zipfile
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

_EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "Sync" / "get_location_bundle_adv.py"


def _import_parse_loc_zip() -> Any:
    """Import parse_loc_zip without the example script's import-time side effects.

    The script builds a SwgohComlink client and creates its output directory when it is
    imported; both are patched away so only the function is loaded.
    """
    with mock.patch("swgoh_comlink.SwgohComlink"), mock.patch("pathlib.Path.mkdir"):
        spec = importlib.util.spec_from_file_location("get_location_bundle_adv", _EXAMPLE)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module.parse_loc_zip


parse_loc_zip = _import_parse_loc_zip()


def _zip(*entries: tuple[str, str | bytes]) -> zipfile.ZipFile:
    """An in-memory zip of (name, content) entries; a name ending in "/" adds a directory entry."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries:
            zf.writestr(zipfile.ZipInfo(name) if name.endswith("/") else name, content)
    return zipfile.ZipFile(io.BytesIO(buf.getvalue()))


@pytest.mark.parametrize(
    ("content", "kwargs", "expected"),
    [
        pytest.param(
            "UNIT_NAME|Darth Vader\nUNIT_DESC|Sith Lord\n",
            {},
            {"UNIT_NAME": "Darth Vader", "UNIT_DESC": "Sith Lord"},
            id="key-value-lines",
        ),
        pytest.param("# header comment\nKEY|value\n# trailing\n", {}, {"KEY": "value"}, id="comments-skipped"),
        pytest.param(
            "GOOD|yes\nBAD_LINE\nALSO_GOOD|yep\n", {}, {"GOOD": "yes", "ALSO_GOOD": "yep"}, id="no-delimiter-skipped"
        ),
        # Only the first delimiter splits the line.
        pytest.param("KEY|value|with|pipes\n", {}, {"KEY": "value|with|pipes"}, id="pipes-in-value"),
        pytest.param("EMPTY_VAL|\n", {}, {"EMPTY_VAL": ""}, id="empty-value"),
        pytest.param("K1|V1\r\nK2|V2\r\n", {}, {"K1": "V1", "K2": "V2"}, id="crlf"),
        pytest.param("GREETING|こんにちは\nNAME|Ñoño\n", {}, {"GREETING": "こんにちは", "NAME": "Ñoño"}, id="unicode"),
        pytest.param("", {}, {}, id="empty-file"),
        pytest.param("KEY=VALUE\n", {"delimiter": "="}, {"KEY": "VALUE"}, id="custom-delimiter"),
        pytest.param("KEY|héllo".encode("latin-1"), {"encoding": "latin-1"}, {"KEY": "héllo"}, id="custom-encoding"),
    ],
)
def test_parses_each_line_into_json(tmp_path: Path, content: str | bytes, kwargs: dict[str, str], expected: dict):
    parse_loc_zip(_zip(("Loc_ENG_US.txt", content)), output_dir=tmp_path, **kwargs)

    assert json.loads((tmp_path / "Loc_ENG_US.json").read_text("utf-8")) == expected


@pytest.mark.parametrize(
    ("entries", "expected_files"),
    [
        pytest.param(
            [("Loc_ENG_US.txt", "A|1\n"), ("Loc_FRE_FR.txt", "B|2\n"), ("Loc_Key_Mapping.txt", "C|3\n")],
            ["Loc_ENG_US.json", "Loc_FRE_FR.json", "Loc_Key_Mapping.json"],
            id="one-json-per-entry",
        ),
        pytest.param([("subdir/", ""), ("subdir/file.txt", "K|V\n")], ["file.json"], id="directories-skipped"),
        pytest.param([], [], id="empty-zip"),
    ],
)
def test_output_files(tmp_path: Path, entries: list[tuple[str, str]], expected_files: list[str]):
    parse_loc_zip(_zip(*entries), output_dir=tmp_path)

    assert sorted(path.name for path in tmp_path.iterdir()) == expected_files


def test_output_dir_created_if_missing(tmp_path: Path):
    nested = tmp_path / "a" / "b" / "c"

    parse_loc_zip(_zip(("test.txt", "K|V\n")), output_dir=nested)

    assert json.loads((nested / "test.json").read_text("utf-8")) == {"K": "V"}


def test_json_output_keeps_non_ascii_characters(tmp_path: Path):
    parse_loc_zip(_zip(("test.txt", "KEY|café\n")), output_dir=tmp_path)

    raw = (tmp_path / "test.json").read_text("utf-8")
    assert "café" in raw
    assert "\\u" not in raw
