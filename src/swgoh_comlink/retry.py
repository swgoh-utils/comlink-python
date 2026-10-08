# coding=utf-8
"""
Opt-in retry and pacing policy for the SwgohComlink clients.
"""

from __future__ import annotations

import asyncio
import math
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

# Indirections over sleeping and the monotonic clock so tests can record waits
# instead of sitting them out. The clients look these up at call time.
_sleep: Callable[[float], None] = time.sleep
_async_sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
_clock: Callable[[], float] = time.monotonic


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

    Attributes:
        attempts: Total attempts per call, including the first. ``1`` disables
            retrying while keeping pacing. [Default: 5]
        backoff: Seconds to wait before each retry when the response has no usable
            ``Retry-After``; the last value repeats once the schedule runs out.
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
            ``min_interval``. [Default: empty]

    Raises:
        SwgohComlinkValueError: If a numeric field is negative, non-finite, or
            ``attempts`` is less than 1.
        SwgohComlinkTypeError: If ``attempts`` is not an integer.

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

    def __post_init__(self) -> None:
        if isinstance(self.attempts, bool) or not isinstance(self.attempts, int):
            raise SwgohComlinkTypeError(f"RetryPolicy.attempts must be an int, got {type(self.attempts).__name__}.")
        if self.attempts < 1:
            raise SwgohComlinkValueError("RetryPolicy.attempts must be at least 1.")
        # Normalise list or set inputs so the frozen policy stays hashable.
        object.__setattr__(self, "backoff", tuple(self.backoff))
        object.__setattr__(self, "unpaced_endpoints", frozenset(self.unpaced_endpoints))
        for name, value in (
            *(("backoff", wait) for wait in self.backoff),
            ("max_retry_after", self.max_retry_after),
            ("min_interval", self.min_interval),
        ):
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


class _Pacer:
    """Reserves start times so calls to one endpoint begin ``interval`` seconds apart.

    The slot is reserved under a lock before the caller waits, so concurrent
    callers queue behind one another rather than beside. No await happens while
    the lock is held, which makes the same pacer safe for threads and tasks.
    """

    def __init__(self, interval: float, unpaced: frozenset[str]) -> None:
        self._interval = interval
        self._unpaced = unpaced
        self._next: dict[str, float] = {}
        self._lock = threading.Lock()

    def reserve(self, key: str, endpoint: str) -> float:
        """Take the next slot for *key* and return how long to wait for it."""
        if self._interval <= 0 or endpoint in self._unpaced:
            return 0.0
        with self._lock:
            now = _clock()
            due = max(self._next.get(key, now), now)
            self._next[key] = due + self._interval
            return due - now
