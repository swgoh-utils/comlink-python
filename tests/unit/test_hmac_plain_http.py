"""A client that signs requests over plain HTTP to a non-loopback host logs one warning."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import pytest

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync

Client = SwgohComlink | SwgohComlinkAsync

BASE_LOGGER = "swgoh_comlink._base"
KEYS = {"access_key": "pub_key", "secret_key": "priv_key"}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep credential variables from the outer shell from switching HMAC on."""
    for name in ("COMLINK_ACCESS_KEY", "COMLINK_SECRET_KEY", "ACCESS_KEY", "SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)


def _plain_http_warnings(
    make_comlink: Callable[..., Client], caplog: pytest.LogCaptureFixture, **kwargs: Any
) -> list[logging.LogRecord]:
    with caplog.at_level(logging.WARNING, logger=BASE_LOGGER):
        make_comlink(**kwargs)
    return [r for r in caplog.records if r.name == BASE_LOGGER and "plain HTTP" in r.getMessage()]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"url": "http://comlink.example.com:3000"},
        {"url": "http://comlink.example.com"},
        {"url": "HTTP://comlink.example.com:3000"},
        {"url": "http://192.168.1.10:3000"},
        {"url": "http://[2001:db8::1]:3000"},
        {"url": "http://128.0.0.1:3000"},
        {"url": "http://localhost.example.com:3000"},
        {"host": "comlink.lab"},
        {"url": "https://comlink.example.com", "stats_url": "http://stats.example.com:3223"},
    ],
    ids=lambda kwargs: next(iter(kwargs.values())),
)
def test_warns_for_plain_http_to_a_remote_host(
    make_comlink: Callable[..., Client], caplog: pytest.LogCaptureFixture, kwargs: dict[str, str]
) -> None:
    records = _plain_http_warnings(make_comlink, caplog, **KEYS, **kwargs)
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING
    text = records[0].getMessage()
    assert "HMAC" in text
    assert "priv_key" not in text
    assert "pub_key" not in text


def test_one_warning_when_both_urls_are_remote(
    make_comlink: Callable[..., Client], caplog: pytest.LogCaptureFixture
) -> None:
    records = _plain_http_warnings(
        make_comlink, caplog, url="http://comlink.example.com:3000", stats_url="http://stats.example.com:3223", **KEYS
    )
    assert len(records) == 1
    assert "comlink.example.com" in records[0].getMessage()
    assert "stats.example.com" in records[0].getMessage()


def test_each_client_warns_once(make_comlink: Callable[..., Client], caplog: pytest.LogCaptureFixture) -> None:
    assert len(_plain_http_warnings(make_comlink, caplog, url="http://comlink.example.com:3000", **KEYS)) == 1
    caplog.clear()
    assert len(_plain_http_warnings(make_comlink, caplog, url="http://comlink.example.com:3000", **KEYS)) == 1


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:3000",
        "http://LOCALHOST:3000",
        "http://localhost",
        "http://127.0.0.1:3000",
        "http://127.0.0.1",
        "http://127.10.20.30:3000",
        "http://[::1]:3000",
        "https://comlink.example.com",
        "https://comlink.example.com:8443",
        "https://192.168.1.10:3000",
    ],
)
def test_no_warning_for_loopback_or_https(
    make_comlink: Callable[..., Client], caplog: pytest.LogCaptureFixture, url: str
) -> None:
    assert _plain_http_warnings(make_comlink, caplog, url=url, **KEYS) == []


def test_no_warning_without_keys(make_comlink: Callable[..., Client], caplog: pytest.LogCaptureFixture) -> None:
    assert _plain_http_warnings(make_comlink, caplog, url="http://comlink.example.com:3000") == []


def test_warns_for_env_keys(
    make_comlink: Callable[..., Client], caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COMLINK_ACCESS_KEY", "pub_key")
    monkeypatch.setenv("COMLINK_SECRET_KEY", "priv_key")
    assert len(_plain_http_warnings(make_comlink, caplog, url="http://comlink.example.com:3000")) == 1


def test_the_connection_is_not_blocked(make_comlink: Callable[..., Client]) -> None:
    client = make_comlink(url="http://comlink.example.com:3000", **KEYS)
    assert client.hmac is True
    assert client.url_base == "http://comlink.example.com:3000"
