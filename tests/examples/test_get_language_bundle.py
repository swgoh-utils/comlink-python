"""Tests for examples/{Sync,Async}/get_language_bundle.py.

These test example scripts, not the library, so they live outside tests/unit/.

Each script fetches a localization bundle and decodes it by hand at import time. The client
class is patched to return an in-memory bundle, the script is executed, and the string lookup
it builds is checked. Current bundles contain ``#`` comment lines with no ``|`` delimiter.
"""

from __future__ import annotations

import base64
import importlib.util
import io
import zipfile
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

_EXAMPLES = Path(__file__).resolve().parents[2] / "examples"

# Shaped like a current Loc_GER_DE.txt: category comments, a bare "#", a blank line and a
# value that contains the delimiter.
_BUNDLE_TEXT = (
    "# Start Category: Star_Wars_Strategy_RPG\n"
    "#\n"
    "UNIT_VADER_NAME|Darth Vader\n"
    "\n"
    "UNIT_VADER_DESC|Sith-Lord|Imperium\n"
    "EMPTY_VALUE|\n"
    "# End Category: Star_Wars_Strategy_RPG (3 strings)\n"
)

_EXPECTED = {
    "UNIT_VADER_NAME": "Darth Vader",
    "UNIT_VADER_DESC": "Sith-Lord|Imperium",
    "EMPTY_VALUE": "",
}


def _localization_response() -> dict[str, str]:
    """A get_localization() response whose bundle zips Loc_GER_DE.txt and Loc_Key_Mapping.txt."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Loc_GER_DE.txt", _BUNDLE_TEXT)
        zf.writestr("Loc_Key_Mapping.txt", "")
    return {"localizationBundle": base64.b64encode(buf.getvalue()).decode("ascii")}


def _run_example(variant: str) -> Any:
    """Execute examples/<variant>/get_language_bundle.py against a patched client; return the module."""
    path = _EXAMPLES / variant / "get_language_bundle.py"
    spec = importlib.util.spec_from_file_location(f"get_language_bundle_{variant.lower()}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    if variant == "Sync":
        patcher = mock.patch("swgoh_comlink.SwgohComlink")
        with patcher as client_cls:
            client_cls.return_value.get_localization.return_value = _localization_response()
            spec.loader.exec_module(module)
        client_cls.return_value.get_localization.assert_called_once_with(locale="ger_de")
    else:
        client = mock.MagicMock()
        client.get_localization = mock.AsyncMock(return_value=_localization_response())
        with mock.patch("swgoh_comlink.SwgohComlinkAsync") as client_cls:
            client_cls.return_value.__aenter__.return_value = client
            spec.loader.exec_module(module)
        client.get_localization.assert_awaited_once_with(locale="ger_de")
    return module


@pytest.mark.parametrize("variant", ["Sync", "Async"])
def test_builds_lookup_skipping_comment_lines(variant: str, capsys: pytest.CaptureFixture[str]):
    module = _run_example(variant)

    assert module.der_str_lookup == _EXPECTED
    assert f"{len(_EXPECTED)} German strings" in capsys.readouterr().out
