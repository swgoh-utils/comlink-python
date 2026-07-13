"""Tests for the swgoh_comlink exception hierarchy."""

from __future__ import annotations

import logging

import pytest

from swgoh_comlink.exceptions import (
    SwgohComlinkException,
    SwgohComlinkTypeError,
    SwgohComlinkValueError,
)


def test_hierarchy():
    assert issubclass(SwgohComlinkValueError, SwgohComlinkException)
    assert issubclass(SwgohComlinkValueError, ValueError)
    assert issubclass(SwgohComlinkTypeError, SwgohComlinkException)
    assert issubclass(SwgohComlinkTypeError, TypeError)


def test_constructing_exceptions_does_not_log(caplog: pytest.LogCaptureFixture):
    with caplog.at_level(logging.DEBUG):
        SwgohComlinkException("boom")
        try:
            raise SwgohComlinkValueError("bad value")
        except SwgohComlinkValueError:
            pass

    assert caplog.records == []


def test_exception_message_preserved():
    exc = SwgohComlinkException("HTTP 500: oops")
    assert str(exc) == "HTTP 500: oops"
