"""Tests for the swgoh_comlink exception hierarchy."""

from __future__ import annotations

import copy
import logging
import pickle
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from typing import Any

import httpx
import pytest

from swgoh_comlink.exceptions import (
    SwgohComlinkClientError,
    SwgohComlinkException,
    SwgohComlinkHTTPError,
    SwgohComlinkRateLimitError,
    SwgohComlinkTypeError,
    SwgohComlinkUnavailableError,
    SwgohComlinkValueError,
)


def test_hierarchy():
    assert issubclass(SwgohComlinkValueError, SwgohComlinkException)
    assert issubclass(SwgohComlinkValueError, ValueError)
    assert issubclass(SwgohComlinkTypeError, SwgohComlinkException)
    assert issubclass(SwgohComlinkTypeError, TypeError)
    assert issubclass(SwgohComlinkHTTPError, SwgohComlinkException)
    for subclass in (SwgohComlinkRateLimitError, SwgohComlinkUnavailableError, SwgohComlinkClientError):
        assert issubclass(subclass, SwgohComlinkHTTPError)


def test_constructing_exceptions_does_not_log(caplog: pytest.LogCaptureFixture):
    with caplog.at_level(logging.DEBUG):
        SwgohComlinkException("boom")
        SwgohComlinkHTTPError.from_response(httpx.Response(429, headers={"Retry-After": "1"}))
        try:
            raise SwgohComlinkValueError("bad value")
        except SwgohComlinkValueError:
            pass

    assert caplog.records == []


def test_exception_message_preserved():
    exc = SwgohComlinkException("HTTP 500: oops")
    assert str(exc) == "HTTP 500: oops"


# ── HTTP error classification ────────────────────────────────────────────


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (429, {"code": "RATE_LIMITED", "message": "slow down"}, SwgohComlinkRateLimitError),
        (429, None, SwgohComlinkRateLimitError),
        # The game's rate refusal arrives as a 502; the GAME_<n> number varies.
        (502, {"code": "GAME_6", "message": "Rate exceeded!"}, SwgohComlinkRateLimitError),
        (502, {"code": "GAME_11", "message": "Rate exceeded!"}, SwgohComlinkRateLimitError),
        (502, "GAME_6 Rate exceeded!", SwgohComlinkRateLimitError),
        (503, {"code": "UNAVAILABLE", "message": "server is at capacity"}, SwgohComlinkUnavailableError),
        (503, None, SwgohComlinkUnavailableError),
        (400, {"code": "BAD_REQUEST", "message": "missing allyCode"}, SwgohComlinkClientError),
        (401, {"code": "UNAUTHORIZED", "message": "bad signature"}, SwgohComlinkClientError),
        (404, "Not Found", SwgohComlinkClientError),
        (500, {"code": "INTERNAL", "message": "boom"}, SwgohComlinkHTTPError),
        # A GAME_<n> code alone says nothing about rate limiting.
        (502, {"code": "GAME_6", "message": "Player not found"}, SwgohComlinkHTTPError),
    ],
)
def test_from_response_classifies(status: int, body: dict[str, str] | str | None, expected: type) -> None:
    if isinstance(body, dict):
        response = httpx.Response(status, json=body)
    else:
        response = httpx.Response(status, text=body or "")

    error = SwgohComlinkHTTPError.from_response(response)

    assert type(error) is expected
    assert error.status == status
    assert error.response is response


def test_from_response_keeps_legacy_message_and_parses_body() -> None:
    response = httpx.Response(502, json={"code": "GAME_6", "message": "Rate exceeded!"}, headers={"Retry-After": "3"})

    error = SwgohComlinkHTTPError.from_response(response)

    assert str(error) == f"HTTP 502: {response.text}"
    assert error.code == "GAME_6"
    assert error.detail == "Rate exceeded!"
    assert error.retry_after == 3.0


def test_from_response_non_json_body() -> None:
    error = SwgohComlinkHTTPError.from_response(httpx.Response(500, text="  upstream exploded \n"))

    assert str(error) == "HTTP 500:   upstream exploded \n"
    assert error.code is None
    assert error.detail == "upstream exploded"
    assert error.retry_after is None


def test_from_response_json_non_object_body() -> None:
    error = SwgohComlinkHTTPError.from_response(httpx.Response(500, json=["a", "b"]))

    assert error.code is None
    assert error.detail == '["a","b"]'


def test_from_response_numeric_code_and_empty_body() -> None:
    assert SwgohComlinkHTTPError.from_response(httpx.Response(500, json={"code": 13})).code == "13"
    assert SwgohComlinkHTTPError.from_response(httpx.Response(500, json={"code": True})).code is None
    assert SwgohComlinkHTTPError.from_response(httpx.Response(500)).detail is None


@pytest.mark.parametrize(
    ("header", "expected"),
    [("1", 1.0), (" 2.5 ", 2.5), ("0", 0.0), ("-1", None), ("nan", None), ("inf", None), ("soon", None)],
)
def test_retry_after_delta_seconds(header: str, expected: float | None) -> None:
    response = httpx.Response(503, headers={"Retry-After": header})

    assert SwgohComlinkHTTPError.from_response(response).retry_after == expected


def test_retry_after_http_date() -> None:
    now = datetime.now(timezone.utc)
    future = format_datetime(now + timedelta(seconds=30), usegmt=True)
    past = format_datetime(now - timedelta(seconds=30), usegmt=True)

    later = SwgohComlinkHTTPError.from_response(httpx.Response(503, headers={"Retry-After": future}))
    earlier = SwgohComlinkHTTPError.from_response(httpx.Response(503, headers={"Retry-After": past}))

    assert later.retry_after is not None
    assert 25 < later.retry_after <= 30
    assert earlier.retry_after == 0.0


def test_http_error_repr_and_direct_construction() -> None:
    error = SwgohComlinkClientError("HTTP 400: nope", status=400, code="BAD_REQUEST", detail="nope")

    assert str(error) == "HTTP 400: nope"
    assert repr(error) == "SwgohComlinkClientError(status=400, code='BAD_REQUEST', detail='nope')"
    assert error.retry_after is None
    assert error.response is None


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (500, {"code": "INTERNAL", "message": "boom"}),
        (502, {"code": "GAME_6", "message": "Rate exceeded!"}),
        (503, {"code": "UNAVAILABLE", "message": "busy"}),
        (400, {"code": "BAD_REQUEST", "message": "nope"}),
    ],
)
@pytest.mark.parametrize("duplicate", [lambda e: pickle.loads(pickle.dumps(e)), copy.copy, copy.deepcopy])
def test_http_errors_pickle_and_copy(status: int, body: dict[str, str], duplicate: Any) -> None:
    original = SwgohComlinkHTTPError.from_response(httpx.Response(status, json=body, headers={"Retry-After": "3"}))

    clone = duplicate(original)

    assert type(clone) is type(original)
    assert str(clone) == str(original)
    assert str(clone).startswith(f"HTTP {status}: ")
    assert (clone.status, clone.code, clone.detail, clone.retry_after) == (
        original.status,
        original.code,
        original.detail,
        3.0,
    )
    assert clone.response is not None
    assert clone.response.status_code == status
