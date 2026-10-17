"""Tests for RetryPolicy and the per-endpoint pacer (no HTTP involved)."""

from __future__ import annotations

import math
from typing import Any

import httpx
import pytest

from swgoh_comlink import RetryPolicy, SwgohComlink, SwgohComlinkAsync
from swgoh_comlink import retry as retry_module
from swgoh_comlink.exceptions import (
    SwgohComlinkHTTPError,
    SwgohComlinkTypeError,
    SwgohComlinkValueError,
)
from swgoh_comlink.retry import DEFAULT_BACKOFF, _Pacer


def _error(status: int, retry_after: str | None = None, **json: str) -> SwgohComlinkHTTPError:
    headers = {"Retry-After": retry_after} if retry_after is not None else {}
    return SwgohComlinkHTTPError.from_response(httpx.Response(status, headers=headers, json=json or None))


# ── RetryPolicy construction ─────────────────────────────────────────────


def test_defaults() -> None:
    policy = RetryPolicy()

    assert policy.attempts == 5
    assert policy.backoff == DEFAULT_BACKOFF == (5.0, 10.0, 20.0, 40.0)
    assert policy.respect_retry_after is True
    assert policy.min_interval == 0.0
    assert policy.unpaced_endpoints == frozenset()
    assert policy.jitter == 0.2


def test_sequences_are_normalised() -> None:
    backoff: Any = [1, 2]
    unpaced: Any = {"player"}
    policy = RetryPolicy(backoff=backoff, unpaced_endpoints=unpaced)

    assert policy.backoff == (1, 2)
    assert policy.unpaced_endpoints == frozenset({"player"})
    assert hash(policy) == hash(RetryPolicy(backoff=(1, 2), unpaced_endpoints=frozenset({"player"})))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"attempts": 0},
        {"backoff": (1.0, -1.0)},
        {"backoff": (math.inf,)},
        {"max_retry_after": -0.1},
        {"min_interval": math.nan},
        {"jitter": -0.2},
        {"jitter": math.inf},
    ],
)
def test_invalid_values_raise(kwargs: dict[str, Any]) -> None:
    with pytest.raises(SwgohComlinkValueError):
        RetryPolicy(**kwargs)


@pytest.mark.parametrize("attempts", [2.0, True, "3"])
def test_non_int_attempts_raise(attempts: Any) -> None:
    with pytest.raises(SwgohComlinkTypeError):
        RetryPolicy(attempts=attempts)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"unpaced_endpoints": "player"},
        {"unpaced_endpoints": 5},
        {"unpaced_endpoints": frozenset({1})},
        {"backoff": "5"},
        {"backoff": 5},
        {"backoff": ("5",)},
        {"backoff": (True,)},
        {"max_retry_after": None},
        {"max_retry_after": "60"},
        {"min_interval": True},
    ],
)
def test_wrong_types_raise(kwargs: dict[str, Any]) -> None:
    with pytest.raises(SwgohComlinkTypeError):
        RetryPolicy(**kwargs)


@pytest.mark.parametrize("client_cls", [SwgohComlink, SwgohComlinkAsync])
def test_client_rejects_non_policy_retry(client_cls: type[SwgohComlink] | type[SwgohComlinkAsync]) -> None:
    with pytest.raises(SwgohComlinkTypeError):
        client_cls(retry={"attempts": 3})


@pytest.mark.parametrize("client_cls", [SwgohComlink, SwgohComlinkAsync])
def test_client_retry_defaults_to_none(client_cls: type[SwgohComlink] | type[SwgohComlinkAsync]) -> None:
    client = client_cls()

    assert client.retry_policy is None
    assert client._pace_delay("player", stats=False) == 0.0


# ── RetryPolicy.retry_delay ──────────────────────────────────────────────


def test_backoff_schedule_then_give_up() -> None:
    policy = RetryPolicy()
    rate = _error(502, code="GAME_6", message="Rate exceeded!")

    assert [policy.retry_delay(rate, attempt) for attempt in range(1, 6)] == [5.0, 10.0, 20.0, 40.0, None]


def test_last_backoff_value_repeats() -> None:
    policy = RetryPolicy(attempts=5, backoff=(1.0, 2.0))

    assert [policy.retry_delay(_error(429), attempt) for attempt in range(1, 5)] == [1.0, 2.0, 2.0, 2.0]


def test_empty_backoff_retries_immediately() -> None:
    assert RetryPolicy(backoff=()).retry_delay(_error(503), 1) == 0.0


def test_retry_after_is_used_and_clamped() -> None:
    policy = RetryPolicy(max_retry_after=30.0)

    assert policy.retry_delay(_error(503, retry_after="1"), 1) == 1.0
    assert policy.retry_delay(_error(429, retry_after="600"), 1) == 30.0
    # An unreadable header falls back to the backoff schedule.
    assert policy.retry_delay(_error(503, retry_after="later"), 2) == 10.0


def test_retry_after_can_be_ignored() -> None:
    policy = RetryPolicy(respect_retry_after=False)

    assert policy.retry_delay(_error(503, retry_after="1"), 1) == 5.0


@pytest.mark.parametrize("status", [400, 401, 404, 500, 502])
def test_non_retryable_statuses(status: int) -> None:
    assert RetryPolicy().retry_delay(_error(status), 1) is None


def test_retry_kinds_can_be_switched_off() -> None:
    no_rate = RetryPolicy(retry_rate_limited=False)
    no_unavailable = RetryPolicy(retry_unavailable=False)

    assert no_rate.retry_delay(_error(429), 1) is None
    assert no_rate.retry_delay(_error(503), 1) == 5.0
    assert no_unavailable.retry_delay(_error(503), 1) is None
    assert no_unavailable.retry_delay(_error(429), 1) == 5.0


# ── Pacing ───────────────────────────────────────────────────────────────


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """A settable monotonic clock: ``clock[0]`` is the current time."""
    now = [100.0]
    monkeypatch.setattr(retry_module, "_clock", lambda: now[0])
    return now


def test_pacer_spaces_calls_per_key(clock: list[float]) -> None:
    pacer = _Pacer(0.4, frozenset())

    assert [pacer.reserve("comlink:data", "data") for _ in range(3)] == [0.0, pytest.approx(0.4), pytest.approx(0.8)]
    assert pacer.reserve("comlink:guild", "guild") == 0.0

    clock[0] += 5.0
    assert pacer.reserve("comlink:data", "data") == 0.0


def test_pacer_skips_unpaced_and_disabled(clock: list[float]) -> None:
    pacer = _Pacer(0.4, frozenset({"player"}))

    assert [pacer.reserve("comlink:player", "player") for _ in range(3)] == [0.0, 0.0, 0.0]
    assert [_Pacer(0.0, frozenset()).reserve("comlink:data", "data") for _ in range(3)] == [0.0, 0.0, 0.0]


def test_client_pace_keys_ignore_query_and_split_services(clock: list[float]) -> None:
    client = SwgohComlink(retry=RetryPolicy(min_interval=0.4))

    assert client._pace_delay("api?flags=gameStyle", stats=True) == 0.0
    assert client._pace_delay("api?flags=calcGP", stats=True) == pytest.approx(0.4)
    assert client._pace_delay("api", stats=False) == 0.0


def test_pacer_release_returns_the_last_slot(clock: list[float]) -> None:
    pacer = _Pacer(0.4, frozenset())
    pacer.reserve("comlink:data", "data")
    wait, release = pacer.reserve_slot("comlink:data", "data")

    release()

    assert wait == pytest.approx(0.4)
    # The abandoned slot is free again, so the next caller takes it.
    assert pacer.reserve("comlink:data", "data") == pytest.approx(0.4)


def test_pacer_release_keeps_the_queue_once_someone_is_behind(clock: list[float]) -> None:
    pacer = _Pacer(0.4, frozenset())
    pacer.reserve("comlink:data", "data")
    _, release = pacer.reserve_slot("comlink:data", "data")
    pacer.reserve("comlink:data", "data")

    release()

    assert pacer.reserve("comlink:data", "data") == pytest.approx(1.2)


def test_pacer_releasing_every_slot_frees_the_queue(clock: list[float]) -> None:
    pacer = _Pacer(0.4, frozenset())
    releases = [pacer.reserve_slot("comlink:data", "data")[1] for _ in range(10)]

    for release in releases:  # the order a cancelled gather unwinds in: first reserved, first released
        release()

    assert pacer.reserve("comlink:data", "data") == 0.0


def test_pacer_released_slot_in_the_middle_keeps_later_slots(clock: list[float]) -> None:
    pacer = _Pacer(0.4, frozenset())
    slots = [pacer.reserve_slot("comlink:data", "data") for _ in range(4)]

    slots[1][1]()
    slots[3][1]()

    # 100.0 and 100.8 are still taken, so the next caller follows 100.8.
    assert pacer.reserve("comlink:data", "data") == pytest.approx(1.2)


def test_pacer_hold_delays_every_caller_until_it_ends(clock: list[float]) -> None:
    pacer = _Pacer(0.4, frozenset())

    assert pacer.hold("comlink:data", "data", 5.0) is True
    assert [pacer.reserve("comlink:data", "data") for _ in range(2)] == [pytest.approx(5.0), pytest.approx(5.4)]
    assert pacer.reserve("comlink:guild", "guild") == 0.0

    clock[0] += 10.0
    assert pacer.reserve("comlink:data", "data") == 0.0


def test_pacer_hold_applies_without_min_interval(clock: list[float]) -> None:
    pacer = _Pacer(0.0, frozenset())
    pacer.hold("comlink:data", "data", 5.0)

    assert [pacer.reserve("comlink:data", "data") for _ in range(2)] == [5.0, 5.0]


def test_pacer_hold_keeps_the_later_end(clock: list[float]) -> None:
    pacer = _Pacer(0.0, frozenset())
    pacer.hold("comlink:data", "data", 5.0)
    pacer.hold("comlink:data", "data", 1.0)

    assert pacer.reserve("comlink:data", "data") == 5.0


def test_pacer_never_holds_unpaced_endpoints(clock: list[float]) -> None:
    pacer = _Pacer(0.4, frozenset({"player"}))

    assert pacer.hold("comlink:player", "player", 5.0) is False
    assert pacer.reserve("comlink:player", "player") == 0.0


@pytest.mark.parametrize(("draw", "expected"), [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0)])
def test_jitter_extra_scales_with_the_wait(monkeypatch: pytest.MonkeyPatch, draw: float, expected: float) -> None:
    monkeypatch.setattr(retry_module, "_random", lambda: draw)

    assert RetryPolicy(jitter=0.2).jitter_extra(5.0) == pytest.approx(expected)
    assert RetryPolicy(jitter=0.0).jitter_extra(5.0) == 0.0
