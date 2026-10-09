# coding=utf-8
"""
Custom exceptions for swgoh_comlink
"""

from __future__ import annotations

import functools
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx

__all__ = [
    "SwgohComlinkException",
    "SwgohComlinkValueError",
    "SwgohComlinkTypeError",
    "SwgohComlinkHTTPError",
    "SwgohComlinkRateLimitError",
    "SwgohComlinkUnavailableError",
    "SwgohComlinkClientError",
]

# Error ``code`` values that mean "too many requests". Game error codes of the
# form ``GAME_<n>`` are deliberately absent: the number has been observed to
# differ between calls for the same message, so it identifies nothing.
_RATE_LIMIT_CODES = frozenset({"RATE_LIMITED"})

# The game's own rate refusal, passed through by comlink as an HTTP 502 with a
# body such as ``{"code": "GAME_6", "message": "Rate exceeded!"}``.
_RATE_LIMIT_TEXT = "rate exceeded"


class SwgohComlinkException(Exception):
    """Base class for exceptions in this module."""


class SwgohComlinkValueError(SwgohComlinkException, ValueError):
    """Raised when an argument value is invalid."""


class SwgohComlinkTypeError(SwgohComlinkException, TypeError):
    """Raised when an argument type is invalid."""


class SwgohComlinkHTTPError(SwgohComlinkException):
    """Raised when the comlink service answers with an HTTP error status.

    ``str(exc)`` is always ``"HTTP {status}: {body}"``, and the exception is
    raised from the originating ``httpx.HTTPStatusError``, so code that matched
    on the message or on ``SwgohComlinkException`` keeps working. Use
    :meth:`from_response` to build the most specific subclass for a response.

    Attributes:
        status: The HTTP status code.
        code: The ``code`` field of a JSON error body, when present. comlink
            error bodies have the shape ``{"code": ..., "message": ...}``.
            Codes of the form ``GAME_<n>`` vary between calls for the same
            failure, so match on the exception class rather than on them.
        detail: The ``message`` field of a JSON error body, or the raw body text
            when the body is not a JSON object. ``None`` when the body is empty.
        retry_after: Seconds the server asked the caller to wait, parsed from the
            ``Retry-After`` header (delta-seconds or HTTP-date form). ``None``
            when the header is absent or unreadable. The value is not clamped.
        response: The ``httpx.Response`` that carried the error, if available.
    """

    def __init__(
        self,
        message: str,
        *,
        status: int,
        code: str | None = None,
        detail: str | None = None,
        retry_after: float | None = None,
        response: httpx.Response | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.detail = detail
        self.retry_after = retry_after
        self.response = response

    def __repr__(self) -> str:
        return f"{type(self).__name__}(status={self.status!r}, code={self.code!r}, detail={self.detail!r})"

    def __reduce__(self) -> tuple[Any, ...]:
        # The default reduce rebuilds the exception as ``cls(*self.args)``, which
        # omits the required ``status`` keyword. Pass it explicitly so pickle and
        # copy keep working; the remaining attributes travel in the state dict.
        return functools.partial(type(self), *self.args, status=self.status), (), self.__dict__

    @classmethod
    def from_response(cls, response: httpx.Response) -> SwgohComlinkHTTPError:
        """Build the most specific HTTP error for an error response.

        Classification, first match wins:

        1. :class:`SwgohComlinkRateLimitError`: HTTP 429, a ``RATE_LIMITED``
           code, or a message containing "Rate exceeded" (the game's own refusal,
           which comlink passes through as HTTP 502).
        2. :class:`SwgohComlinkUnavailableError`: HTTP 503.
        3. :class:`SwgohComlinkClientError`: any other 4xx status.
        4. :class:`SwgohComlinkHTTPError`: everything else (5xx).

        Args:
            response: The error response returned by ``httpx``.

        Returns:
            An instance of the matching exception class. It is not raised.

        Examples:
            >>> import httpx
            >>> err = SwgohComlinkHTTPError.from_response(
            ...     httpx.Response(502, json={"code": "GAME_6", "message": "Rate exceeded!"})
            ... )
            >>> type(err).__name__, err.status, err.code, err.detail
            ('SwgohComlinkRateLimitError', 502, 'GAME_6', 'Rate exceeded!')
        """
        status = response.status_code
        body = response.text
        code, detail = _parse_error_body(body)
        error_cls = _classify(status, code, detail)
        return error_cls(
            f"HTTP {status}: {body}",
            status=status,
            code=code,
            detail=detail,
            retry_after=_parse_retry_after(response.headers.get("retry-after")),
            response=response,
        )


class SwgohComlinkRateLimitError(SwgohComlinkHTTPError):
    """Raised when a request was refused for exceeding a rate limit.

    Covers HTTP 429 from comlink and the game's own ``Rate exceeded!`` refusal,
    which arrives as HTTP 502. In both cases the call was not carried out, so
    re-issuing it after a pause is safe.
    """


class SwgohComlinkUnavailableError(SwgohComlinkHTTPError):
    """Raised on HTTP 503: comlink is busy or not ready and asks to be retried.

    comlink usually sends a short ``Retry-After`` with this status.
    """


class SwgohComlinkClientError(SwgohComlinkHTTPError):
    """Raised on a 4xx status other than 429: the request itself was rejected.

    Retrying the same request will not succeed.
    """


def _parse_error_body(body: str) -> tuple[str | None, str | None]:
    """Return ``(code, detail)`` from an error body.

    A JSON object yields its ``code`` and ``message`` fields; any other body
    yields no code and the raw text (or ``None`` when empty) as the detail.
    """
    try:
        parsed: Any = json.loads(body)
    except ValueError:
        return None, body.strip() or None
    if not isinstance(parsed, dict):
        return None, body.strip() or None
    code = parsed.get("code")
    message = parsed.get("message")
    # bool is an int subclass but never a meaningful error code.
    code_str = str(code) if isinstance(code, (str, int)) and not isinstance(code, bool) else None
    return code_str, message if isinstance(message, str) else None


def _classify(status: int, code: str | None, detail: str | None) -> type[SwgohComlinkHTTPError]:
    """Pick the exception class for an error response (see ``from_response``)."""
    if status == 429 or code in _RATE_LIMIT_CODES or _RATE_LIMIT_TEXT in (detail or "").casefold():
        return SwgohComlinkRateLimitError
    if status == 503:
        return SwgohComlinkUnavailableError
    if 400 <= status < 500:
        return SwgohComlinkClientError
    return SwgohComlinkHTTPError


def _parse_retry_after(value: str | None) -> float | None:
    """Seconds to wait from a ``Retry-After`` header value, or ``None`` if unreadable.

    Both forms allowed by RFC 9110 are accepted: delta-seconds and an HTTP-date.
    A date in the past yields ``0.0``.
    """
    if value is None:
        return None
    value = value.strip()
    try:
        seconds = float(value)
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError):
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return max((when - datetime.now(timezone.utc)).total_seconds(), 0.0)
    # NaN fails every comparison, so ``seconds >= 0`` also rejects it.
    return seconds if seconds >= 0 and seconds != float("inf") else None
