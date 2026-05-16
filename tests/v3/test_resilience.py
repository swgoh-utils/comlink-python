# coding=utf-8
"""Phase 2 resilience-layer tests.

Covers everything the Phase 2 plan added to the client surface:

* ``with_options(**overrides)`` clone semantics.
* ``http_client=`` injection + the SDK leaving caller-owned clients alone.
* ``profile="default"|"bot"|"bulk"`` preset application + bad-name rejection.
* ``max_retries=`` behavior: ``0`` disables; retries succeed on recovery;
  ``Retry-After`` is honored; non-retryable statuses pass through after
  one attempt.

These tests exercise the *new* Phase 2 contract. The Phase 1 golden +
shape tests already cover that *existing* endpoint behavior survived the
refactor — together they form the regression net.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync
from swgoh_comlink._base import (
    BOT_LIMITS,
    BULK_LIMITS,
    DEFAULT_LIMITS,
    NOT_GIVEN,
    NotGiven,
    resolve_profile,
)
from swgoh_comlink._retry import (
    RETRYABLE_STATUSES,
    RetryableStatusError,
    compute_backoff,
    parse_retry_after,
    should_retry,
)
from swgoh_comlink.exceptions import SwgohComlinkException

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
    user_client.get("/anything")  # type: ignore[arg-type]
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
    derived = base.with_options(max_retries=0)
    assert base.max_retries == 3
    assert derived.max_retries == 0
    base.close()


def test_with_options_shares_underlying_client() -> None:
    """Documented contract: clone shares the httpx client with the original."""
    base = SwgohComlink(url="http://comlink.test")
    derived = base.with_options(max_retries=0)
    assert derived.client is base.client
    base.close()


def test_with_options_rejects_unknown_attribute() -> None:
    base = SwgohComlink(url="http://comlink.test")
    try:
        with pytest.raises(AttributeError, match="unknown option"):
            base.with_options(nonsense_option=True)
    finally:
        base.close()


# ── Retry classification & helpers ──────────────────────────────────────────


@pytest.mark.parametrize("status", sorted(RETRYABLE_STATUSES))
def test_should_retry_yes_for_retryable_statuses(status: int) -> None:
    assert should_retry(status)


@pytest.mark.parametrize("status", [200, 201, 204, 301, 400, 401, 403, 404, 422])
def test_should_retry_no_for_other_statuses(status: int) -> None:
    assert not should_retry(status)


def test_parse_retry_after_numeric_seconds() -> None:
    assert parse_retry_after({"Retry-After": "5"}) == 5.0
    assert parse_retry_after({"retry-after": "0"}) == 0.0
    assert parse_retry_after({"Retry-After": "0.5"}) == 0.5


def test_parse_retry_after_negative_returns_none() -> None:
    assert parse_retry_after({"Retry-After": "-1"}) is None


def test_parse_retry_after_capped() -> None:
    """1-hour-from-server-misconfig is clamped to the cap."""
    assert parse_retry_after({"Retry-After": "3600"}, cap_seconds=120.0) == 120.0


def test_parse_retry_after_absent_returns_none() -> None:
    assert parse_retry_after({}) is None
    assert parse_retry_after({"Retry-After": ""}) is None


def test_parse_retry_after_http_date() -> None:
    """HTTP-date form is parsed and returns seconds-from-now (≥ 0)."""
    # 30 seconds from now, in HTTP-date format.
    from email.utils import formatdate

    target = time.time() + 30
    after = parse_retry_after({"Retry-After": formatdate(target, usegmt=True)})
    assert after is not None
    assert 25 <= after <= 31


def test_compute_backoff_monotonic_mean() -> None:
    """Each attempt's *cap* doubles; the mean of the uniform jitter doubles too."""
    # Sample enough to smooth out the jitter.
    means = [sum(compute_backoff(i) for _ in range(200)) / 200 for i in range(5)]
    for a, b in zip(means, means[1:], strict=False):
        # Each subsequent attempt's mean should be roughly 2× the previous
        # (down to ~1.3× given small samples).
        assert b > a * 1.3, f"backoff didn't grow: {means}"


# ── Retry loop end-to-end ───────────────────────────────────────────────────


def _two_503s_then_ok(httpx_mock: HTTPXMock, ok_body: Any) -> None:
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(json=ok_body)


def test_max_retries_zero_disables(httpx_mock: HTTPXMock) -> None:
    """max_retries=0 makes exactly one attempt — and the test mock only
    has one response registered."""
    httpx_mock.add_response(status_code=503)
    client = SwgohComlink(url="http://comlink.test", max_retries=0)
    try:
        with pytest.raises(SwgohComlinkException, match=r"HTTP 503"):
            client.get_enums()
    finally:
        client.close()


def test_retry_succeeds_on_recovery(httpx_mock: HTTPXMock) -> None:
    """503 → 503 → 200 with max_retries=3 returns the OK payload."""
    _two_503s_then_ok(httpx_mock, {"CombatType": 1})
    client = SwgohComlink(url="http://comlink.test", max_retries=3)
    try:
        result = client.get_enums()
    finally:
        client.close()
    assert result == {"CombatType": 1}


def test_retry_exhausted_raises(httpx_mock: HTTPXMock) -> None:
    """503 × 4 attempts (1 + 3 retries) — final raise is HTTP 503."""
    for _ in range(4):
        httpx_mock.add_response(status_code=503)
    client = SwgohComlink(url="http://comlink.test", max_retries=3)
    try:
        with pytest.raises(SwgohComlinkException, match=r"HTTP 503"):
            client.get_enums()
    finally:
        client.close()


def test_non_retryable_4xx_passes_through(httpx_mock: HTTPXMock) -> None:
    """400 is not retried — one attempt, raise."""
    httpx_mock.add_response(status_code=400, json={"detail": "bad request"})
    client = SwgohComlink(url="http://comlink.test", max_retries=3)
    try:
        with pytest.raises(SwgohComlinkException, match=r"HTTP 400"):
            client.get_enums()
    finally:
        client.close()


def test_retry_after_honored_on_429(httpx_mock: HTTPXMock) -> None:
    """429 + Retry-After: 1 → 200 takes at least 1 second wall-clock."""
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "1"})
    httpx_mock.add_response(json={"CombatType": 1})
    client = SwgohComlink(url="http://comlink.test", max_retries=3)
    try:
        start = time.perf_counter()
        result = client.get_enums()
        elapsed = time.perf_counter() - start
    finally:
        client.close()
    assert result == {"CombatType": 1}
    # Allow generous upper bound for CI / scheduler noise; lower bound is the contract.
    assert 0.95 < elapsed < 5.0, f"expected ~1s wait, got {elapsed:.3f}s"


def test_connection_error_is_retryable(httpx_mock: HTTPXMock) -> None:
    """httpx.RequestError (e.g. connection refused) is retried."""
    httpx_mock.add_exception(httpx.ConnectError("refused"))
    httpx_mock.add_exception(httpx.ConnectError("refused"))
    httpx_mock.add_response(json={"CombatType": 1})
    client = SwgohComlink(url="http://comlink.test", max_retries=3)
    try:
        result = client.get_enums()
    finally:
        client.close()
    assert result == {"CombatType": 1}


# ── Async parity ────────────────────────────────────────────────────────────


@pytest.fixture
async def async_recovery_client(httpx_mock: HTTPXMock) -> Iterator[SwgohComlinkAsync]:
    """503 → 503 → 200 setup for the async retry path."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(json={"CombatType": 1})
    c = SwgohComlinkAsync(url="http://comlink.test", max_retries=3)
    yield c
    await c.aclose()


async def test_async_retry_succeeds_on_recovery(async_recovery_client: SwgohComlinkAsync) -> None:
    result = await async_recovery_client.get_enums()
    assert result == {"CombatType": 1}


async def test_async_max_retries_zero_disables(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=503)
    client = SwgohComlinkAsync(url="http://comlink.test", max_retries=0)
    try:
        with pytest.raises(SwgohComlinkException, match=r"HTTP 503"):
            await client.get_enums()
    finally:
        await client.aclose()


async def test_async_http_client_injection_skips_close(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json={"x": 1}, is_reusable=True)
    user_client = httpx.AsyncClient(base_url="http://comlink.test")
    sdk = SwgohComlinkAsync(url="http://comlink.test", http_client=user_client)
    assert sdk._owns_client is False
    await sdk.aclose()
    # Should still be usable.
    await user_client.get("/anything")
    await user_client.aclose()


# ── RetryableStatusError carries the response ───────────────────────────────


def test_retryable_status_error_carries_response() -> None:
    """The retry loop needs ``exc.response`` to read Retry-After."""
    fake_response = type("R", (), {"status_code": 503, "headers": {}, "text": "down"})()
    exc = RetryableStatusError(fake_response)
    assert exc.response is fake_response
    assert "503" in str(exc)
