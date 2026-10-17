# coding=utf-8
"""
Opt-in retry and pacing policy for the SwgohComlink clients.
"""

from __future__ import annotations

import asyncio
import math
import random
import threading
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from .exceptions import (
    SwgohComlinkHTTPError,
    SwgohComlinkRateLimitError,
    SwgohComlinkTypeError,
    SwgohComlinkUnavailableError,
    SwgohComlinkValueError,
)

__all__ = ["RetryPolicy", "DEFAULT_BACKOFF"]

#: Waits, in seconds, before each successive retry when the server gives no
#: ``Retry-After``. Sized for the game's rate refusal, which needs a pause of
#: several seconds before the same call is accepted again.
DEFAULT_BACKOFF: tuple[float, ...] = (5.0, 10.0, 20.0, 40.0)

# Indirections over sleeping, the monotonic clock and the jitter source so tests
# can record waits instead of sitting them out. The clients look these up at call time.
_sleep: Callable[[float], None] = time.sleep
_async_sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
_clock: Callable[[], float] = time.monotonic
_random: Callable[[], float] = random.random


@dataclass(frozen=True)
class RetryPolicy:
    """How a client retries refused calls and paces calls to the same endpoint.

    Pass an instance as the ``retry`` keyword argument of ``SwgohComlink`` or
    ``SwgohComlinkAsync``. Without one (the default) the clients make exactly
    one attempt per call and never wait.

    Only two failures are retried, both of which mean the call was not carried
    out: rate refusals (:class:`~swgoh_comlink.exceptions.SwgohComlinkRateLimitError`)
    and HTTP 503 (:class:`~swgoh_comlink.exceptions.SwgohComlinkUnavailableError`).
    Client errors, other server errors and transport failures are raised at once.

    The game meters calls per session and per RPC, and refuses with
    ``Rate exceeded!`` at roughly 15 calls a second to one RPC. A
    ``min_interval`` of 0.4 s keeps a burst to one endpoint well under that.

    A rate refusal also holds back the endpoint it came from: until the retry wait
    has passed, no call to that endpoint starts on the client, so concurrent
    callers back off together instead of adding to the refusal. Each retry then
    waits a random extra of up to ``jitter`` times its wait, so callers refused
    together do not all retry at the same moment.

    Attributes:
        attempts: Total attempts per call, including the first. ``1`` disables
            retrying while keeping pacing. [Default: 5]
        backoff: Seconds to wait before each retry when the response has no usable
            ``Retry-After``; the last value repeats once the schedule runs out. An
            empty schedule retries at once, without waiting.
            [Default: (5.0, 10.0, 20.0, 40.0)]
        respect_retry_after: Wait for the server's ``Retry-After`` instead of the
            backoff value when the header is present. [Default: True]
        max_retry_after: Upper bound, in seconds, on a ``Retry-After`` wait.
            [Default: 60.0]
        retry_rate_limited: Retry rate refusals. [Default: True]
        retry_unavailable: Retry HTTP 503 responses. [Default: True]
        min_interval: Minimum seconds between the starts of two calls to the same
            endpoint on one client, across threads or tasks. ``0`` disables
            pacing. [Default: 0.0]
        unpaced_endpoints: Endpoint names (such as ``"player"``) exempt from
            ``min_interval`` and from being held back after a rate refusal.
            [Default: empty]
        jitter: Largest random extra added to a retry wait, as a fraction of that
            wait: ``0.2`` turns a 5 s wait into 5 to 6 s. Extra time only, so a retry
            never starts before the backoff or ``Retry-After`` wait. ``0``
            disables it. [Default: 0.2]

    Raises:
        SwgohComlinkValueError: If a numeric field is negative, non-finite, or
            ``attempts`` is less than 1.
        SwgohComlinkTypeError: If ``attempts`` is not an integer, a numeric field is
            not an int or float (``bool`` included), ``backoff`` or
            ``unpaced_endpoints`` is a string or not iterable, or an endpoint name
            is not a string.

    Examples:
        Retry rate refusals and 503s, and space calls to one endpoint 0.4 s apart:

        >>> from swgoh_comlink import SwgohComlink, RetryPolicy
        >>> comlink = SwgohComlink(retry=RetryPolicy(min_interval=0.4))  # doctest: +SKIP
    """

    attempts: int = 5
    backoff: tuple[float, ...] = DEFAULT_BACKOFF
    respect_retry_after: bool = True
    max_retry_after: float = 60.0
    retry_rate_limited: bool = True
    retry_unavailable: bool = True
    min_interval: float = 0.0
    unpaced_endpoints: frozenset[str] = field(default_factory=frozenset)
    jitter: float = 0.2

    def __post_init__(self) -> None:
        if isinstance(self.attempts, bool) or not isinstance(self.attempts, int):
            raise SwgohComlinkTypeError(f"RetryPolicy.attempts must be an int, got {type(self.attempts).__name__}.")
        if self.attempts < 1:
            raise SwgohComlinkValueError("RetryPolicy.attempts must be at least 1.")
        # A str is iterable, so it would otherwise turn into a sequence of characters.
        if isinstance(self.backoff, (str, bytes)):
            raise SwgohComlinkTypeError("RetryPolicy.backoff must be a sequence of numbers, not a string.")
        if isinstance(self.unpaced_endpoints, (str, bytes)):
            raise SwgohComlinkTypeError("RetryPolicy.unpaced_endpoints must be a collection of names, not a string.")
        # Normalise list or set inputs so the frozen policy stays hashable.
        try:
            object.__setattr__(self, "backoff", tuple(self.backoff))
            object.__setattr__(self, "unpaced_endpoints", frozenset(self.unpaced_endpoints))
        except TypeError as exc:
            raise SwgohComlinkTypeError(
                "RetryPolicy.backoff and RetryPolicy.unpaced_endpoints must be iterable."
            ) from exc
        if not all(isinstance(name, str) for name in self.unpaced_endpoints):
            raise SwgohComlinkTypeError("RetryPolicy.unpaced_endpoints must contain only str endpoint names.")
        for name, value in (
            *(("backoff", wait) for wait in self.backoff),
            ("max_retry_after", self.max_retry_after),
            ("min_interval", self.min_interval),
            ("jitter", self.jitter),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise SwgohComlinkTypeError(f"RetryPolicy.{name} must be an int or float, got {type(value).__name__}.")
            if not (math.isfinite(value) and value >= 0):
                raise SwgohComlinkValueError(f"RetryPolicy.{name} must be a finite, non-negative number of seconds.")

    def retry_delay(self, error: SwgohComlinkHTTPError, attempt: int) -> float | None:
        """Return how long to wait before retrying a failed attempt, or ``None`` to give up.

        Args:
            error: The exception raised by the attempt that failed.
            attempt: The 1-based number of the attempt that failed.

        Returns:
            Seconds to wait before the next attempt, or ``None`` when the error is
            not retryable or no attempts remain.

        Examples:
            >>> import httpx
            >>> from swgoh_comlink.exceptions import SwgohComlinkHTTPError
            >>> error = SwgohComlinkHTTPError.from_response(httpx.Response(429))
            >>> RetryPolicy().retry_delay(error, attempt=1)
            5.0
            >>> RetryPolicy(attempts=1).retry_delay(error, attempt=1) is None
            True
        """
        if attempt >= self.attempts:
            return None
        retryable = (self.retry_rate_limited and isinstance(error, SwgohComlinkRateLimitError)) or (
            self.retry_unavailable and isinstance(error, SwgohComlinkUnavailableError)
        )
        if not retryable:
            return None
        if self.respect_retry_after and error.retry_after is not None:
            return min(error.retry_after, self.max_retry_after)
        if not self.backoff:
            return 0.0
        return self.backoff[min(attempt, len(self.backoff)) - 1]

    def jitter_extra(self, delay: float) -> float:
        """Return a random extra, from 0 up to ``jitter * delay`` seconds, to add to a retry wait."""
        return delay * self.jitter * _random()


class _Pacer:
    """Reserves start times so calls to one endpoint begin ``interval`` seconds apart.

    The slot is reserved under a lock before the caller waits, so concurrent
    callers queue behind one another rather than beside. No await happens while
    the lock is held, which makes the same pacer safe for threads and tasks.

    Each key keeps the start times still spacing out the next call, so a caller
    that abandons its slot removes exactly that slot, wherever it sits in the
    queue. A key can also be held back until a given time, after a rate refusal.
    """

    def __init__(self, interval: float, unpaced: frozenset[str]) -> None:
        self._interval = interval
        self._unpaced = unpaced
        self._slots: dict[str, list[float]] = {}
        self._held: dict[str, float] = {}
        self._lock = threading.Lock()

    def reserve(self, key: str, endpoint: str) -> float:
        """Take the next slot for *key* and return how long to wait for it."""
        return self.reserve_slot(key, endpoint)[0]

    def reserve_slot(self, key: str, endpoint: str) -> tuple[float, Callable[[], None]]:
        """Take the next slot for *key*; return the wait and a callable that gives the slot back.

        The slot starts after any hold on *key* and ``interval`` after the latest
        slot still taken. Call the returned callable when the caller abandons the
        slot before using it, such as a task cancelled while it waits: the slot is
        removed, and later callers queue after the slots that remain. Callers
        already waiting keep their start times.
        """
        if endpoint in self._unpaced:
            return 0.0, _no_release
        with self._lock:
            now = _clock()
            due = now
            held = self._held.get(key)
            if held is not None:
                if held > now:
                    due = held
                else:
                    del self._held[key]
            if self._interval <= 0:
                return due - now, _no_release
            # Slots that no longer delay anyone are dropped as the queue is read.
            slots = [start for start in self._slots.get(key, []) if start + self._interval > now]
            if slots:
                due = max(due, max(slots) + self._interval)
            slots.append(due)
            self._slots[key] = slots
            wait = due - now

        def release() -> None:
            with self._lock:
                taken = self._slots.get(key)
                if taken and due in taken:
                    taken.remove(due)

        return wait, release

    def hold(self, key: str, endpoint: str, seconds: float) -> bool:
        """Hold back calls to *key* for *seconds* from now; return whether a hold applies.

        An existing hold that ends later is kept. Unpaced endpoints are never held,
        and ``False`` tells the caller to wait out the delay itself.
        """
        if endpoint in self._unpaced:
            return False
        if seconds > 0:
            with self._lock:
                until = _clock() + seconds
                if until > self._held.get(key, until - 1):
                    self._held[key] = until
        return True


def _no_release() -> None:
    """Release callable for a call that reserved no slot."""
