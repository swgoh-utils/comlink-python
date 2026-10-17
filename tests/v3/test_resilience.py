# coding=utf-8
"""Phase 2 resilience-layer tests.

Covers everything the Phase 2 plan added to the client surface:

* ``with_options(**overrides)`` clone semantics.
* ``http_client=`` injection + the SDK leaving caller-owned clients alone.
* ``profile="default"|"bot"|"bulk"`` preset application + bad-name rejection.
* ``retry=`` integration with the v3 client surface: off by default (one
  attempt); a :class:`~swgoh_comlink.retry.RetryPolicy` retries 503 / rate
  refusals and honors ``Retry-After``; other statuses and transport errors
  pass through after one attempt; ``with_options(retry=...)`` and
  ``healthcheck()`` never retrying. The policy itself is unit-tested in
  ``tests/unit/test_retry.py`` / ``test_retry_mocked.py``.

These tests exercise the *new* Phase 2 contract. The Phase 1 golden +
shape tests already cover that *existing* endpoint behavior survived the
refactor — together they form the regression net.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, cast

import httpx
import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import RetryPolicy, SwgohComlink, SwgohComlinkAsync
from swgoh_comlink import retry as retry_module
from swgoh_comlink._base import (
    BOT_LIMITS,
    BULK_LIMITS,
    DEFAULT_LIMITS,
    NOT_GIVEN,
    NotGiven,
    resolve_profile,
)
from swgoh_comlink.exceptions import (
    SwgohComlinkClientError,
    SwgohComlinkException,
    SwgohComlinkHTTPError,
    SwgohComlinkTypeError,
    SwgohComlinkUnavailableError,
)

#: Retry quickly in tests: no backoff schedule, no jitter.
FAST_RETRY = RetryPolicy(attempts=4, backoff=(), jitter=0.0)


@pytest.fixture
def waits(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Record every sleep the clients ask for instead of sleeping, on a frozen clock and without jitter."""
    recorded: list[float] = []

    async def async_sleep(seconds: float) -> None:
        recorded.append(seconds)

    monkeypatch.setattr(retry_module, "_sleep", recorded.append)
    monkeypatch.setattr(retry_module, "_async_sleep", async_sleep)
    monkeypatch.setattr(retry_module, "_clock", lambda: 1000.0)
    monkeypatch.setattr(retry_module, "_random", lambda: 0.0)
    return recorded


# ── NOT_GIVEN sentinel ──────────────────────────────────────────────────────


def test_not_given_is_singleton() -> None:
    """``NOT_GIVEN`` returns the same instance every construction."""
    assert NotGiven() is NOT_GIVEN
    assert NotGiven() is NotGiven()


def test_not_given_is_falsy() -> None:
    """Convenient for ``if x is NOT_GIVEN`` *and* ``if x`` semantics."""
    assert not NOT_GIVEN
    assert bool(NOT_GIVEN) is False


def test_not_given_repr() -> None:
    assert repr(NOT_GIVEN) == "NOT_GIVEN"


# ── Pool presets ────────────────────────────────────────────────────────────


def test_pool_presets_have_distinct_keepalive() -> None:
    """Documented contract: default has 30s keepalive (up from httpx's 5s)."""
    assert DEFAULT_LIMITS.keepalive_expiry == 30.0
    assert BOT_LIMITS.keepalive_expiry == 120.0
    assert BULK_LIMITS.keepalive_expiry == 60.0


def test_resolve_profile_known_names() -> None:
    assert resolve_profile("default") is DEFAULT_LIMITS
    assert resolve_profile("bot") is BOT_LIMITS
    assert resolve_profile("bulk") is BULK_LIMITS


def test_resolve_profile_unknown_raises() -> None:
    with pytest.raises(ValueError, match=r"unknown profile 'turbo'"):
        resolve_profile("turbo")


def test_client_accepts_profile_kwarg() -> None:
    """Passing a known profile constructs + closes without error."""
    for name in ("default", "bot", "bulk"):
        c = SwgohComlink(url="http://comlink.test", profile=name)
        c.close()


def test_client_rejects_unknown_profile() -> None:
    with pytest.raises(ValueError, match="unknown profile"):
        SwgohComlink(url="http://comlink.test", profile="turbo")


# ── http_client injection + ownership ───────────────────────────────────────


def test_http_client_injection_skips_close(httpx_mock: HTTPXMock) -> None:
    """Injected ``http_client`` is NOT closed by ``client.close()``."""
    httpx_mock.add_response(json={"x": 1}, is_reusable=True)
    user_client = httpx.Client(base_url="http://comlink.test")
    sdk = SwgohComlink(url="http://comlink.test", http_client=user_client)
    assert sdk._owns_client is False
    sdk.close()
    # If close() had closed it, this next call would fail.
    user_client.get("/anything")
    user_client.close()


def test_auto_constructed_client_is_owned() -> None:
    """Without ``http_client`` the SDK constructs its own and owns it."""
    sdk = SwgohComlink(url="http://comlink.test")
    assert sdk._owns_client is True
    sdk.close()
    # Internal client is now closed; making a request would raise.
    with pytest.raises(RuntimeError):
        sdk.client.get("/anything")


# ── with_options ────────────────────────────────────────────────────────────


def test_with_options_overrides_attribute() -> None:
    base = SwgohComlink(url="http://comlink.test")
    derived = base.with_options(verify_ssl=False)
    assert base.verify_ssl is True
    assert derived.verify_ssl is False
    base.close()


def test_with_options_shares_underlying_client() -> None:
    """Documented contract: clone shares the httpx client with the original."""
    base = SwgohComlink(url="http://comlink.test")
    derived = base.with_options(retry=None)
    assert derived.client is base.client
    base.close()


def test_with_options_rejects_unknown_attribute() -> None:
    base = SwgohComlink(url="http://comlink.test")
    try:
        with pytest.raises(AttributeError, match="unknown option"):
            base.with_options(nonsense_option=True)
    finally:
        base.close()


def test_with_options_max_retries_removed() -> None:
    """``max_retries`` (v3.0.0a1) is gone; ``retry=`` replaces it."""
    base = SwgohComlink(url="http://comlink.test")
    try:
        with pytest.raises(AttributeError, match="unknown option 'max_retries'"):
            base.with_options(max_retries=0)
        with pytest.raises(TypeError):
            SwgohComlink(url="http://comlink.test", max_retries=0)
    finally:
        base.close()


def test_with_options_retry_sets_policy_and_pacer() -> None:
    base = SwgohComlink(url="http://comlink.test")
    try:
        assert base.retry_policy is None
        policy = RetryPolicy(min_interval=0.4)
        derived = base.with_options(retry=policy)
        assert derived.retry_policy is policy
        assert derived._pacer is not None
        assert base.retry_policy is None
        assert base._pacer is None
    finally:
        base.close()


def test_with_options_retry_none_disables_and_not_given_keeps() -> None:
    base = SwgohComlink(url="http://comlink.test", retry=RetryPolicy(min_interval=0.4))
    try:
        disabled = base.with_options(retry=None)
        assert disabled.retry_policy is None
        assert disabled._pacer is None
        kept = base.with_options()
        assert kept.retry_policy is base.retry_policy
        # A kept policy shares the pacing state (and endpoint holds) with the original.
        assert kept._pacer is base._pacer
    finally:
        base.close()


@pytest.mark.parametrize("bad", [3, "fast", object()])
def test_with_options_rejects_non_policy_retry(bad: object) -> None:
    base = SwgohComlink(url="http://comlink.test")
    try:
        with pytest.raises(SwgohComlinkTypeError, match="retry must be a RetryPolicy or None"):
            base.with_options(retry=cast(Any, bad))
    finally:
        base.close()


def test_with_options_rejects_internal_retry_attributes() -> None:
    base = SwgohComlink(url="http://comlink.test")
    try:
        with pytest.raises(AttributeError, match="with_options\\(retry="):
            base.with_options(retry_policy=RetryPolicy())
    finally:
        base.close()


# ── Retry loop end-to-end ───────────────────────────────────────────────────
#
# ``get_events`` is the probe: a single POST with no version lookup, so the
# registered mock responses map 1:1 onto attempts.


def _two_503s_then_ok(httpx_mock: HTTPXMock, ok_body: Any) -> None:
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(json=ok_body)


def test_default_makes_one_attempt(httpx_mock: HTTPXMock) -> None:
    """Retries are opt-in: without ``retry=`` a 503 raises after exactly one attempt."""
    httpx_mock.add_response(status_code=503)
    client = SwgohComlink(url="http://comlink.test")
    try:
        with pytest.raises(SwgohComlinkUnavailableError, match=r"HTTP 503"):
            client.get_events()
    finally:
        client.close()
    assert len(httpx_mock.get_requests()) == 1


def test_retry_succeeds_on_recovery(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    """503 → 503 → 200 with a RetryPolicy returns the OK payload."""
    _two_503s_then_ok(httpx_mock, {"events": []})
    client = SwgohComlink(url="http://comlink.test", retry=FAST_RETRY)
    try:
        result = client.get_events()
    finally:
        client.close()
    assert result == {"events": []}
    assert len(httpx_mock.get_requests()) == 3


def test_retry_exhausted_raises(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    """503 × 4 attempts — final raise is the typed 503 error."""
    for _ in range(4):
        httpx_mock.add_response(status_code=503)
    client = SwgohComlink(url="http://comlink.test", retry=FAST_RETRY)
    try:
        with pytest.raises(SwgohComlinkUnavailableError, match=r"HTTP 503"):
            client.get_events()
    finally:
        client.close()
    assert len(httpx_mock.get_requests()) == 4


@pytest.mark.parametrize(("status", "expected"), [(400, SwgohComlinkClientError), (500, SwgohComlinkHTTPError)])
def test_non_retryable_status_passes_through(
    httpx_mock: HTTPXMock, waits: list[float], status: int, expected: type[SwgohComlinkHTTPError]
) -> None:
    """4xx and non-503 5xx are not retried — one attempt, typed raise."""
    httpx_mock.add_response(status_code=status, json={"code": "X", "message": "nope"})
    client = SwgohComlink(url="http://comlink.test", retry=FAST_RETRY)
    try:
        with pytest.raises(expected, match=rf"HTTP {status}"):
            client.get_events()
    finally:
        client.close()
    assert len(httpx_mock.get_requests()) == 1
    assert waits == []


def test_retry_after_honored_on_429(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    """429 + Retry-After: 1 → 200 waits the server's Retry-After before retrying."""
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "1"})
    httpx_mock.add_response(json={"events": []})
    client = SwgohComlink(url="http://comlink.test", retry=RetryPolicy(jitter=0.0))
    try:
        result = client.get_events()
    finally:
        client.close()
    assert result == {"events": []}
    assert waits == [1.0]


def test_connection_error_is_not_retried(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    """Transport failures are raised at once, even with a policy (only 429/503 are retried)."""
    httpx_mock.add_exception(httpx.ConnectError("refused"))
    client = SwgohComlink(url="http://comlink.test", retry=FAST_RETRY)
    try:
        with pytest.raises(SwgohComlinkException, match="refused"):
            client.get_events()
    finally:
        client.close()
    assert len(httpx_mock.get_requests()) == 1


def test_typed_client_retries(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    """The typed client shares the retry pipeline."""
    from swgoh_comlink.typed import SwgohComlink as TypedSwgohComlink

    _two_503s_then_ok(httpx_mock, {"events": []})
    client = TypedSwgohComlink(url="http://comlink.test", retry=FAST_RETRY)
    try:
        assert client.get_events() == {"events": []}
    finally:
        client.close()


def test_healthcheck_never_retries(httpx_mock: HTTPXMock, waits: list[float]) -> None:
    """``healthcheck`` reports False on a 503 after one probe, whatever the policy."""
    httpx_mock.add_response(status_code=503)
    client = SwgohComlink(url="http://comlink.test", retry=FAST_RETRY)
    try:
        assert client.healthcheck() is False
    finally:
        client.close()
    assert len(httpx_mock.get_requests()) == 1
    assert waits == []


# ── Async parity ────────────────────────────────────────────────────────────


@pytest.fixture
async def async_recovery_client(httpx_mock: HTTPXMock, waits: list[float]) -> AsyncIterator[SwgohComlinkAsync]:
    """503 → 503 → 200 setup for the async retry path."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(json={"events": []})
    c = SwgohComlinkAsync(url="http://comlink.test", retry=FAST_RETRY)
    yield c
    await c.aclose()


async def test_async_retry_succeeds_on_recovery(async_recovery_client: SwgohComlinkAsync) -> None:
    result = await async_recovery_client.get_events()
    assert result == {"events": []}


async def test_async_default_makes_one_attempt(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=503)
    client = SwgohComlinkAsync(url="http://comlink.test")
    try:
        with pytest.raises(SwgohComlinkUnavailableError, match=r"HTTP 503"):
            await client.get_events()
    finally:
        await client.aclose()
    assert len(httpx_mock.get_requests()) == 1


async def test_async_http_client_injection_skips_close(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"x": 1}, is_reusable=True)
    user_client = httpx.AsyncClient(base_url="http://comlink.test")
    sdk = SwgohComlinkAsync(url="http://comlink.test", http_client=user_client)
    assert sdk._owns_client is False
    await sdk.aclose()
    # Should still be usable.
    await user_client.get("/anything")
    await user_client.aclose()
