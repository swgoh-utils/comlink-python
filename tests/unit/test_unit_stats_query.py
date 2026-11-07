"""The stats ``language`` query parameter is validated and encoded before it reaches the URL."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any, cast

import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync
from swgoh_comlink._base import SwgohComlinkBase
from swgoh_comlink.exceptions import SwgohComlinkValueError

Client = SwgohComlink | SwgohComlinkAsync
Call = Callable[..., Awaitable[Any]]

STATS_URL = "http://localhost:3223"
BASE_LOGGER = "swgoh_comlink._base"

build = SwgohComlinkBase._build_unit_stats_endpoint


@pytest.mark.parametrize(
    "language",
    [
        "eng_us&flags=onlyGP#x",
        "eng_us#x",
        "eng_us&x=1",
        "eng=us",
        "eng/us",
        "eng_us\n",
        " eng_us",
        "eng us",
        "english",
        "e_us",
        "engl_us",
        "eng_usa",
        "éng_us",
    ],
)
def test_value_that_is_not_a_language_code_raises(language: str) -> None:
    with pytest.raises(SwgohComlinkValueError, match="language"):
        build(flags=["calcGP"], language=language)


def test_non_string_language_raises() -> None:
    with pytest.raises(SwgohComlinkValueError, match="language"):
        build(language=cast(Any, 42))


@pytest.mark.parametrize(
    ("flags", "language", "expected"),
    [
        (["calcGP"], "eng_us", "api?flags=calcGP&language=eng_us"),
        (["calcGP", "onlyGP"], "eng_us", "api?flags=calcGP,onlyGP&language=eng_us"),
        (None, "eng_us", "api?language=eng_us"),
        (["calcGP"], None, "api?flags=calcGP"),
        (None, None, "api"),
    ],
)
def test_valid_input_builds_the_same_endpoint_as_before(
    flags: list[str] | None, language: str | None, expected: str
) -> None:
    assert build(flags=flags, language=language) == expected


@pytest.mark.parametrize("language", ["eng_us", "ENG_US", "Ger_De"])
def test_known_language_is_accepted_without_a_warning(language: str, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger=BASE_LOGGER):
        assert build(language=language) == f"api?language={language}"

    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []


def test_unknown_well_formed_language_warns_once_and_is_still_sent(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger=BASE_LOGGER):
        assert build(flags=["calcGP"], language="eng_uk") == "api?flags=calcGP&language=eng_uk"

    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1
    assert "eng_uk" in warnings[0].getMessage()
    assert "eng_us" in warnings[0].getMessage()


async def test_client_rejects_injection_before_sending(comlink: Client, call: Call, httpx_mock: HTTPXMock) -> None:
    with pytest.raises(SwgohComlinkValueError, match="language"):
        await call(comlink, "get_unit_stats", request_payload=[{"unit": "data"}], language="eng_us&flags=onlyGP#x")

    assert httpx_mock.get_requests() == []


async def test_hmac_signature_matches_a_request_path_with_a_query_string(
    make_comlink: Callable[..., Client], call: Call, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(json=[{"unit": "data"}])

    await call(
        make_comlink(access_key="pub", secret_key="priv"),
        "get_unit_stats",
        request_payload=[{"unit": "data"}],
        flags=["calcGP", "gameStyle"],
        language="eng_us",
    )

    request = httpx_mock.get_request()
    assert request is not None
    assert str(request.url) == f"{STATS_URL}/api?flags=calcGP,gameStyle&language=eng_us"
    # Recompute from the request as it arrived: the signed path must be byte-identical to the
    # path and query on the wire.
    signed_path = request.url.raw_path
    assert signed_path == b"/api?flags=calcGP,gameStyle&language=eng_us"
    body = json.loads(request.content)
    signature = hmac.new(b"priv", digestmod=hashlib.sha256)
    signature.update(request.headers["X-Date"].encode())
    signature.update(request.method.encode())
    signature.update(signed_path)
    signature.update(hashlib.md5(json.dumps(body, separators=(",", ":")).encode()).hexdigest().encode())  # noqa: S324
    assert request.headers["Authorization"] == f"HMAC-SHA256 Credential=pub,Signature={signature.hexdigest()}"
