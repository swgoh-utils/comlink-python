# coding=utf-8
"""Retry / backoff helpers for the unified request path.

Public surface:

* :data:`RETRYABLE_STATUSES` — set of HTTP status codes treated as retryable.
* :func:`should_retry` — classify a status code.
* :func:`parse_retry_after` — read the ``Retry-After`` header.
* :func:`compute_backoff` — exponential backoff with full jitter.
* :class:`RetryableStatusError` — internal exception used to signal a
  retryable response to the retry loop without losing the response object.
* :func:`retrying_sync` / :func:`retrying_async` — small loops that call
  the supplied attempt callable up to *attempts* times, honoring
  ``Retry-After`` and falling back to :func:`compute_backoff`.

Intentionally hand-rolled rather than wrapping stamina: stamina v24's
``retry`` decorator does not let a single attempt's exception influence
the upcoming sleep duration, which is exactly what ``Retry-After``
support requires. ~50 lines of stdlib is honest and fully testable.

This module has zero dependencies on the rest of the SDK so it can be
imported cheaply (the Phase 5 lazy-import work cares about this).
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable, Mapping
from email.utils import parsedate_to_datetime
from typing import TypeVar

T = TypeVar("T")

# ── Status classification ────────────────────────────────────────────────────

#: Status codes the retry loop treats as transient. Aligns with the plan's
#: Phase 2 brief and what most cloud HTTP clients agree on:
#:
#:   408  Request Timeout
#:   425  Too Early
#:   429  Too Many Requests
#:   500  Internal Server Error
#:   502  Bad Gateway
#:   503  Service Unavailable
#:   504  Gateway Timeout
RETRYABLE_STATUSES: frozenset[int] = frozenset({408, 425, 429, 500, 502, 503, 504})


def should_retry(status: int) -> bool:
    """True if *status* is in :data:`RETRYABLE_STATUSES`."""
    return status in RETRYABLE_STATUSES


# ── Retry-After parsing ─────────────────────────────────────────────────────


def parse_retry_after(
    headers: Mapping[str, str],
    *,
    cap_seconds: float = 120.0,
) -> float | None:
    """Read a ``Retry-After`` header. Returns seconds to wait, or ``None``.

    Per RFC 7231 §7.1.3 the header value is either:

    * an HTTP-date (``"Wed, 21 Oct 2015 07:28:00 GMT"``), or
    * a non-negative integer number of seconds.

    A negative or otherwise nonsensical value returns ``None`` (let the
    backoff fallback take over). Values above *cap_seconds* are clamped —
    a comlink that asks us to sleep for an hour is almost certainly
    misconfigured and we shouldn't tie up the calling process.
    """
    raw = headers.get("Retry-After") or headers.get("retry-after")
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    # Numeric seconds path (the common case).
    try:
        seconds = float(raw)
    except ValueError:
        pass  # fall through to HTTP-date path
    else:
        if seconds < 0:
            return None
        return min(seconds, cap_seconds)
    # HTTP-date path.
    try:
        target = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if target is None:
        return None
    # email.utils returns aware datetimes; subtracting another aware
    # datetime gives a timedelta in seconds.
    from datetime import UTC, datetime

    delta = (target - datetime.now(UTC)).total_seconds()
    if delta < 0:
        return 0.0
    return min(delta, cap_seconds)


# ── Backoff ─────────────────────────────────────────────────────────────────


def compute_backoff(
    attempt: int,
    *,
    base: float = 0.5,
    cap: float = 30.0,
    jitter: float = 1.0,
) -> float:
    """Exponential backoff with full jitter, à la AWS Architecture Blog.

    Returns ``random.uniform(0, min(cap, base * 2**attempt)) * jitter``.

    ``attempt`` is zero-indexed: ``attempt=0`` is the wait before the
    *second* try (after the first failure). With ``base=0.5`` the means
    are ~0.25s, 0.5s, 1.0s, 2.0s, 4.0s, ..., capped at *cap*.
    """
    exp = min(cap, base * (2 ** max(0, attempt)))
    return random.uniform(0.0, exp) * jitter


# ── Retryable-status signaling exception ────────────────────────────────────


class RetryableStatusError(Exception):
    """Marker exception: the response carried a retryable HTTP status.

    The retry loop catches this, reads ``Retry-After`` from
    :attr:`response.headers`, sleeps appropriately, and tries again.
    Carrying the response (rather than just the status code) lets the
    loop inspect the headers without round-tripping through httpx again.
    """

    def __init__(self, response: object) -> None:
        # `object` to avoid an import-time httpx dependency in this module.
        status = getattr(response, "status_code", "?")
        super().__init__(f"HTTP {status}")
        self.response = response


# ── Retry loops ─────────────────────────────────────────────────────────────


def retrying_sync(
    attempt: Callable[[], T],
    *,
    attempts: int,
    on: type[BaseException] | tuple[type[BaseException], ...],
) -> T:
    """Call *attempt* up to *attempts* times.

    Retries on exceptions in *on* and on :class:`RetryableStatusError`.
    Between attempts, sleeps for ``Retry-After`` if present on a
    retryable response, otherwise :func:`compute_backoff` with full
    jitter.

    *attempts* is the **total** number of tries: ``attempts=1`` means
    no retry (call once and re-raise), ``attempts=3`` means up to two
    retries.

    Raises the last caught exception when attempts are exhausted.
    """
    if attempts < 1:
        raise ValueError(f"attempts must be >= 1, got {attempts}")

    catchable: tuple[type[BaseException], ...] = (on,) if isinstance(on, type) else on
    catchable = (*catchable, RetryableStatusError)

    last_exc: BaseException | None = None
    for i in range(attempts):
        try:
            return attempt()
        except catchable as exc:
            last_exc = exc
            if i == attempts - 1:
                raise
            wait = _wait_for(exc, attempt_index=i)
            time.sleep(wait)
    assert last_exc is not None  # unreachable; loop either returns or raises
    raise last_exc


async def retrying_async(
    attempt: Callable[[], Awaitable[T]],
    *,
    attempts: int,
    on: type[BaseException] | tuple[type[BaseException], ...],
) -> T:
    """Async analog of :func:`retrying_sync`. Uses :func:`asyncio.sleep`."""
    if attempts < 1:
        raise ValueError(f"attempts must be >= 1, got {attempts}")

    catchable: tuple[type[BaseException], ...] = (on,) if isinstance(on, type) else on
    catchable = (*catchable, RetryableStatusError)

    last_exc: BaseException | None = None
    for i in range(attempts):
        try:
            return await attempt()
        except catchable as exc:
            last_exc = exc
            if i == attempts - 1:
                raise
            wait = _wait_for(exc, attempt_index=i)
            await asyncio.sleep(wait)
    assert last_exc is not None
    raise last_exc


def _wait_for(exc: BaseException, *, attempt_index: int) -> float:
    """Pick a sleep duration for the *attempt_index*-th retry after *exc*.

    Prefers ``Retry-After`` on a :class:`RetryableStatusError` response;
    falls back to :func:`compute_backoff` otherwise.
    """
    if isinstance(exc, RetryableStatusError):
        headers = getattr(exc.response, "headers", None)
        if headers is not None:
            after = parse_retry_after(headers)
            if after is not None:
                return after
    return compute_backoff(attempt_index)
