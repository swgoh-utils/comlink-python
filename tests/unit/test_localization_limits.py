"""Bound compressed input, expansion, records, and individual line reads."""

import base64
import io
import threading
import zipfile

import pytest

from swgoh_comlink import SwgohComlinkAsync
from swgoh_comlink.exceptions import SwgohComlinkValueError
from swgoh_comlink.helpers import LocalizationLimits, get_localization_dictionary
from swgoh_comlink.helpers import _game_data as module


def bundle(text, extra=False):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Loc_ENG_US.txt", text)
        if extra:
            archive.writestr("other", "")
    return {"localizationBundle": base64.b64encode(output.getvalue()).decode()}


@pytest.mark.parametrize(
    ("text", "kwargs", "extra", "message"),
    [
        ("A|B", {"max_archive_bytes": 1}, False, "max_archive_bytes"),
        ("A|" + "x" * 10000, {"max_expanded_bytes": 100}, False, "max_expanded_bytes"),
        ("A|" + "x" * 100, {"max_line_bytes": 10}, False, "max_line_bytes"),
        ("A|B\nA|C", {"max_records": 1}, False, "max_records"),
        ("A|B", {"max_entries": 1}, True, "max_entries"),
    ],
)
def test_resource_limits(text, kwargs, extra, message):
    with pytest.raises(SwgohComlinkValueError, match=message):
        module._parse_localization_bundle(bundle(text, extra), "eng_us", LocalizationLimits(**kwargs))


def test_limit_boundaries_and_utf8():
    text = "A|é\r\n"
    limits = LocalizationLimits(max_expanded_bytes=len(text.encode()), max_line_bytes=len(text.encode()), max_records=1)
    assert module._parse_localization_bundle(bundle(text), "eng_us", limits) == {"A": "é"}


def test_expanded_limit_is_enforced_while_reading(monkeypatch):
    # The stream exceeds the entry size declared by the archive.
    payload = bundle("A|B")
    monkeypatch.setattr(zipfile.ZipFile, "open", lambda *args, **kwargs: io.BytesIO(b"A|B\n" * 100))
    with pytest.raises(SwgohComlinkValueError, match="max_expanded_bytes"):
        module._parse_localization_bundle(payload, "eng_us", LocalizationLimits(max_expanded_bytes=10))


@pytest.mark.parametrize("value", [0, -1, True, 1.5, float("inf")])
def test_invalid_limits(value):
    with pytest.raises(SwgohComlinkValueError, match="positive integer"):
        LocalizationLimits(max_line_bytes=value)


async def test_public_helpers_forward_limits(comlink, httpx_mock):
    httpx_mock.add_response(url="http://localhost:3000/metadata", json={"latestLocalizationBundleVersion": "v1"})
    httpx_mock.add_response(url="http://localhost:3000/localization", json=bundle("A|long value"))
    with pytest.raises(SwgohComlinkValueError, match="max_line_bytes"):
        result = get_localization_dictionary(comlink, limits=LocalizationLimits(max_line_bytes=3))
        if isinstance(comlink, SwgohComlinkAsync):
            await result


async def test_async_parsing_runs_off_event_loop(httpx_mock, monkeypatch):
    caller = threading.get_ident()
    worker = []
    httpx_mock.add_response(url="http://localhost:3000/metadata", json={"latestLocalizationBundleVersion": "v1"})
    httpx_mock.add_response(url="http://localhost:3000/localization", json=bundle("A|B"))
    original = module._parse_localization_bundle

    def parse(*args):
        worker.append(threading.get_ident())
        return original(*args)

    monkeypatch.setattr(module, "_parse_localization_bundle", parse)
    async with SwgohComlinkAsync() as client:
        assert await get_localization_dictionary(client) == {"A": "B"}
    assert worker and worker[0] != caller
