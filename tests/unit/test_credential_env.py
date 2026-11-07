"""HMAC credentials come from the namespaced COMLINK_* environment variables, with the old names deprecated."""

from __future__ import annotations

import logging
import os
import warnings
from collections.abc import Callable

import pytest

import swgoh_comlink
from swgoh_comlink import SwgohComlink, SwgohComlinkAsync

Client = SwgohComlink | SwgohComlinkAsync

BASE_LOGGER = "swgoh_comlink._base"
ENV_NAMES = ("COMLINK_ACCESS_KEY", "COMLINK_SECRET_KEY", "ACCESS_KEY", "SECRET_KEY")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test with none of the credential variables set, whatever the outer shell exports."""
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def _build(make_comlink: Callable[..., Client], **kwargs: str) -> tuple[Client, list[warnings.WarningMessage]]:
    """Build a client and return it with the DeprecationWarnings raised while constructing it."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        client = make_comlink(**kwargs)
    return client, [w for w in caught if issubclass(w.category, DeprecationWarning)]


def test_new_names_enable_hmac(make_comlink: Callable[..., Client], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMLINK_ACCESS_KEY", "new_pub")
    monkeypatch.setenv("COMLINK_SECRET_KEY", "new_priv")
    client, deprecations = _build(make_comlink)
    assert (client.hmac, client.access_key, client.secret_key) == (True, "new_pub", "new_priv")
    assert deprecations == []


def test_new_names_take_precedence_over_old(
    make_comlink: Callable[..., Client], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COMLINK_ACCESS_KEY", "new_pub")
    monkeypatch.setenv("COMLINK_SECRET_KEY", "new_priv")
    monkeypatch.setenv("ACCESS_KEY", "old_pub")
    monkeypatch.setenv("SECRET_KEY", "old_priv")
    client, deprecations = _build(make_comlink)
    assert (client.hmac, client.access_key, client.secret_key) == (True, "new_pub", "new_priv")
    assert deprecations == []


def test_old_names_still_work_with_one_deprecation_warning(
    make_comlink: Callable[..., Client], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ACCESS_KEY", "old_pub")
    monkeypatch.setenv("SECRET_KEY", "old_priv")
    client, deprecations = _build(make_comlink)
    assert (client.hmac, client.access_key, client.secret_key) == (True, "old_pub", "old_priv")
    assert len(deprecations) == 1
    message = str(deprecations[0].message)
    assert "COMLINK_ACCESS_KEY" in message
    assert "COMLINK_SECRET_KEY" in message
    assert "old_pub" not in message
    assert "old_priv" not in message


def test_each_client_warns_once(make_comlink: Callable[..., Client], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACCESS_KEY", "old_pub")
    monkeypatch.setenv("SECRET_KEY", "old_priv")
    assert len(_build(make_comlink)[1]) == 1
    assert len(_build(make_comlink)[1]) == 1


def test_deprecation_points_at_the_caller(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACCESS_KEY", "old_pub")
    monkeypatch.setenv("SECRET_KEY", "old_priv")
    with pytest.warns(DeprecationWarning) as record:
        client = SwgohComlink()
    client.close()
    assert record[0].filename == __file__


async def test_async_deprecation_points_at_the_caller(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACCESS_KEY", "old_pub")
    monkeypatch.setenv("SECRET_KEY", "old_priv")
    with pytest.warns(DeprecationWarning) as record:
        client = SwgohComlinkAsync()
    await client.aclose()
    assert record[0].filename == __file__


@pytest.mark.parametrize("parent", [SwgohComlink, SwgohComlinkAsync])
async def test_deprecation_skips_a_subclass_inside_the_package(
    parent: type[Client], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A subclass in the package adds a frame; the warning must still blame the code that built the client.

    The subclass is compiled under a file name inside the package, as a module there would be, so nothing is written.
    """
    in_package = os.path.join(os.path.dirname(swgoh_comlink.__file__), "_subclass_under_test.py")
    source = "class Child(Parent):\n    def __init__(self, **kwargs):\n        super().__init__(**kwargs)\n"
    namespace: dict[str, object] = {"Parent": parent}
    exec(compile(source, in_package, "exec"), namespace)
    child = namespace["Child"]
    assert isinstance(child, type)
    monkeypatch.setenv("ACCESS_KEY", "old_pub")
    monkeypatch.setenv("SECRET_KEY", "old_priv")
    with pytest.warns(DeprecationWarning) as record:
        client = child()
    if isinstance(client, SwgohComlinkAsync):
        await client.aclose()
    else:
        client.close()
    assert record[0].filename == __file__


def test_constructor_arguments_beat_all_env_vars(
    make_comlink: Callable[..., Client], monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ENV_NAMES:
        monkeypatch.setenv(name, f"env_{name}")
    client, deprecations = _build(make_comlink, access_key="arg_pub", secret_key="arg_priv")
    assert (client.hmac, client.access_key, client.secret_key) == (True, "arg_pub", "arg_priv")
    assert deprecations == []


def test_constructor_argument_overrides_one_env_var(
    make_comlink: Callable[..., Client], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COMLINK_ACCESS_KEY", "new_pub")
    monkeypatch.setenv("COMLINK_SECRET_KEY", "new_priv")
    client, _ = _build(make_comlink, secret_key="arg_priv")
    assert (client.access_key, client.secret_key) == ("new_pub", "arg_priv")


def test_old_names_ignored_once_a_new_name_is_set(
    make_comlink: Callable[..., Client], monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The two namespaces are never mixed: one new name stops both old names from being read."""
    monkeypatch.setenv("COMLINK_ACCESS_KEY", "new_pub")
    monkeypatch.setenv("SECRET_KEY", "old_priv")
    with caplog.at_level(logging.WARNING, logger=BASE_LOGGER):
        client, deprecations = _build(make_comlink)
    assert (client.hmac, client.access_key, client.secret_key) == (False, "new_pub", None)
    assert deprecations == []
    assert "COMLINK_SECRET_KEY" in caplog.text


@pytest.mark.parametrize(
    ("env", "missing"),
    [
        ({"COMLINK_ACCESS_KEY": "new_pub"}, "secret_key"),
        ({"COMLINK_SECRET_KEY": "new_priv"}, "access_key"),
        ({"ACCESS_KEY": "old_pub"}, "secret_key"),
        ({"SECRET_KEY": "old_priv"}, "access_key"),
    ],
)
def test_half_a_pair_logs_a_warning(
    make_comlink: Callable[..., Client],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    env: dict[str, str],
    missing: str,
) -> None:
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    with caplog.at_level(logging.WARNING, logger=BASE_LOGGER):
        client, _ = _build(make_comlink)
    assert client.hmac is False
    warnings_logged = [r for r in caplog.records if r.levelno == logging.WARNING and r.name == BASE_LOGGER]
    assert len(warnings_logged) == 1
    text = warnings_logged[0].getMessage()
    assert "HMAC" in text
    assert missing in text
    assert all(value not in text for value in env.values())


def test_half_a_pair_from_arguments_logs_a_warning(
    make_comlink: Callable[..., Client], caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger=BASE_LOGGER):
        client, _ = _build(make_comlink, access_key="arg_pub")
    assert client.hmac is False
    assert "secret_key" in caplog.text


def test_no_credentials_is_silent(make_comlink: Callable[..., Client], caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger=BASE_LOGGER):
        client, deprecations = _build(make_comlink)
    assert client.hmac is False
    assert deprecations == []
    assert caplog.records == []
