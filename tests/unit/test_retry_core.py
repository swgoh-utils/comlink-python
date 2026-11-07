"""The sans-I/O request core shared by both clients: preparation, interpretation, admission and retry steps."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable

import httpx
import pytest

from swgoh_comlink import RetryPolicy, SwgohComlink
from swgoh_comlink import retry as retry_module
from swgoh_comlink.exceptions import (
    SwgohComlinkClientError,
    SwgohComlinkDecodeError,
    SwgohComlinkHTTPError,
    SwgohComlinkRateLimitError,
    SwgohComlinkUnavailableError,
)
from swgoh_comlink.retry import _Admission, _retry_step, _RetryStep

LOG = logging.getLogger("tests.retry_core")
REQUEST = httpx.Request("POST", "http://localhost:3000/player")


def _error(status: int, body: dict[str, str] | None = None) -> SwgohComlinkHTTPError:
    return SwgohComlinkHTTPError.from_response(httpx.Response(status, json=body or {}, request=REQUEST))


@pytest.fixture
def now(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    clock = [100.0]
    monkeypatch.setattr(retry_module, "_clock", lambda: clock[0])
    return clock


# ── Retry step ───────────────────────────────────────────────────────────


def test_retry_step_holds_the_endpoint_after_a_rate_refusal() -> None:
    assert _retry_step(RetryPolicy(), _error(429), attempt=1) == _RetryStep(delay=5.0, hold=True)


def test_retry_step_waits_without_a_hold_after_unavailable() -> None:
    error = _error(503)
    assert isinstance(error, SwgohComlinkUnavailableError)
    assert _retry_step(RetryPolicy(), error, attempt=2) == _RetryStep(delay=10.0, hold=False)


@pytest.mark.parametrize(("status", "attempt"), [(400, 1), (500, 1), (429, 3)])
def test_retry_step_gives_up(status: int, attempt: int) -> None:
    assert _retry_step(RetryPolicy(attempts=3), _error(status), attempt=attempt) is None


# ── Admission ────────────────────────────────────────────────────────────


class FakeSlots:
    """Hands out a scripted wait per reservation and records which slots were given back."""

    def __init__(self, waits: list[float], holds: list[bool]) -> None:
        self.waits = waits
        self.holds = holds
        self.deadlines: list[float] = []
        self.released: list[int] = []
        self.taken = 0

    def reserve(self) -> tuple[float, Callable[[], None]]:
        slot = self.taken
        self.taken += 1
        return self.waits.pop(0), lambda: self.released.append(slot)

    def held_after(self, deadline: float) -> bool:
        self.deadlines.append(deadline)
        return self.holds.pop(0)

    def admission(self, extra: float = 0.0) -> _Admission:
        return _Admission("player", extra, self.reserve, self.held_after, LOG)


def test_admission_with_no_wait_admits_at_once(now: list[float]) -> None:
    slots = FakeSlots(waits=[0.0], holds=[False])
    assert slots.admission().next_wait() is None
    assert slots.deadlines == [100.0]
    assert slots.released == []


def test_admission_adds_the_carried_retry_wait_to_the_first_slot(now: list[float]) -> None:
    slots = FakeSlots(waits=[1.0], holds=[False])
    admission = slots.admission(extra=5.0)
    assert admission.next_wait() == 6.0
    now[0] += 6.0
    assert admission.next_wait() is None
    assert slots.deadlines == [106.0]


def test_admission_requeues_behind_a_hold_set_while_waiting(now: list[float]) -> None:
    slots = FakeSlots(waits=[1.0, 5.0], holds=[True, False])
    admission = slots.admission(extra=2.0)
    assert admission.next_wait() == 3.0
    now[0] += 3.0
    # The carried retry wait is not added again to the new slot.
    assert admission.next_wait() == 5.0
    assert slots.released == [0]
    now[0] += 5.0
    assert admission.next_wait() is None
    assert slots.deadlines == [103.0, 108.0]


def test_abandon_gives_back_the_current_slot(now: list[float]) -> None:
    slots = FakeSlots(waits=[1.0, 5.0], holds=[True])
    admission = slots.admission()
    admission.next_wait()
    admission.next_wait()
    admission.abandon()
    assert slots.released == [0, 1]


def test_admission_logs_each_wait(now: list[float], caplog: pytest.LogCaptureFixture) -> None:
    slots = FakeSlots(waits=[0.25], holds=[False])
    with caplog.at_level(logging.DEBUG, logger=LOG.name):
        slots.admission().next_wait()
    assert caplog.messages == ["Pacing player for 0.25s"]


# ── Request preparation ──────────────────────────────────────────────────


def test_prepare_post_serializes_the_payload_once() -> None:
    with SwgohComlink() as client:
        request = client._prepare_request("post", "player", {"payload": {"allyCode": "é"}}, stats=False, timeout=None)
    assert request.method == "POST"
    assert request.url == "/player"
    assert request.kwargs == {"headers": {}, "content": '{"payload":{"allyCode":"é"}}'.encode()}
    assert request.stats is False
    assert (request.limit_name, request.limit) == ("max_response_bytes", None)


def test_prepare_get_sends_no_body_and_keeps_the_timeout() -> None:
    with SwgohComlink(access_key="a", secret_key="s", max_response_bytes=10) as client:
        request = client._prepare_request("GET", "enums", None, stats=True, timeout=7.0)
    assert request.method == "GET"
    assert "content" not in request.kwargs
    assert request.kwargs["timeout"] == 7.0
    assert set(request.kwargs["headers"]) == {"X-Date", "Authorization"}
    assert request.stats is True
    assert (request.limit_name, request.limit) == ("max_response_bytes", 10)


def test_prepare_game_data_uses_its_own_limit() -> None:
    with SwgohComlink(max_response_bytes=10, max_game_data_bytes=20) as client:
        request = client._prepare_request("POST", "data", {}, stats=False, timeout=None)
    assert (request.limit_name, request.limit) == ("max_game_data_bytes", 20)


# ── Response interpretation ──────────────────────────────────────────────


def test_interpret_decodes_a_json_object() -> None:
    response = httpx.Response(200, json={"a": 1}, request=REQUEST)
    assert SwgohComlink._interpret_response(response, response.content) == {"a": 1}


def test_interpret_raises_the_typed_http_error() -> None:
    response = httpx.Response(400, json={"code": "BAD", "message": "no"}, request=REQUEST)
    with pytest.raises(SwgohComlinkClientError) as caught:
        SwgohComlink._interpret_response(response, response.content)
    assert isinstance(caught.value.__cause__, httpx.HTTPStatusError)


@pytest.mark.parametrize(("body", "cause"), [(b"nope", json.JSONDecodeError), (b"\xff", UnicodeDecodeError)])
def test_interpret_raises_a_decode_error(body: bytes, cause: type[Exception]) -> None:
    response = httpx.Response(200, content=body, request=REQUEST)
    with pytest.raises(SwgohComlinkDecodeError) as caught:
        SwgohComlink._interpret_response(response, response.content)
    assert isinstance(caught.value.__cause__, cause)


# ── Retry wait ───────────────────────────────────────────────────────────


def test_retry_wait_without_a_policy_gives_up() -> None:
    with SwgohComlink() as client:
        assert client._retry_wait(_error(429), 1, "player", False) is None


def test_retry_wait_holds_a_paced_endpoint_instead_of_waiting(now: list[float], monkeypatch) -> None:
    monkeypatch.setattr(retry_module, "_random", lambda: 0.5)
    with SwgohComlink(retry=RetryPolicy(min_interval=0.4, jitter=0.2)) as client:
        error = _error(429)
        assert isinstance(error, SwgohComlinkRateLimitError)
        # Only the jitter is carried; the hold makes every caller, this one included, wait out the delay.
        assert client._retry_wait(error, 1, "player", False) == pytest.approx(0.5)
        assert client._pace_delay("player", False) == pytest.approx(5.0)


def test_retry_wait_carries_the_delay_for_an_unpaced_endpoint(now: list[float], monkeypatch) -> None:
    monkeypatch.setattr(retry_module, "_random", lambda: 0.0)
    with SwgohComlink(retry=RetryPolicy(unpaced_endpoints=frozenset({"metadata"}))) as client:
        assert client._retry_wait(_error(429), 1, "metadata", False) == 5.0
        assert client._retry_wait(_error(503), 1, "player", False) == 5.0


def test_retry_wait_logs_under_the_client_module(caplog: pytest.LogCaptureFixture, monkeypatch) -> None:
    monkeypatch.setattr(retry_module, "_random", lambda: 0.0)
    with SwgohComlink(retry=RetryPolicy(attempts=2)) as client, caplog.at_level(logging.INFO, logger="swgoh_comlink"):
        client._retry_wait(_error(503), 1, "player", False)
        client._retry_wait(_error(503), 2, "player", False)
    assert [record.name for record in caplog.records] == ["swgoh_comlink.swgoh_comlink"] * 2
    assert caplog.messages == [
        "SwgohComlinkUnavailableError on player (attempt 1 of 2); retrying in 5.0s",
        "SwgohComlinkUnavailableError on player; giving up after 2 attempts",
    ]


# ── Runtime cancellation ─────────────────────────────────────────────────


def test_sync_interrupt_while_pacing_gives_the_slot_back(now: list[float], monkeypatch) -> None:
    """The sync client releases its slot on any exception while sleeping, KeyboardInterrupt included."""

    def interrupted(seconds: float) -> None:
        raise KeyboardInterrupt

    with SwgohComlink(retry=RetryPolicy(min_interval=1)) as client:
        client._pace_delay("metadata", False)
        monkeypatch.setattr(retry_module, "_sleep", interrupted)
        with pytest.raises(KeyboardInterrupt):
            client.get_game_metadata()
        assert client._pace_delay("metadata", False) == 1
