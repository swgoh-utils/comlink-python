# coding=utf-8
"""Decorators for timing and debug logging."""

from __future__ import annotations

import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def func_timer(func):
    """Decorator to record total execution time of a function to the configured logger using level DEBUG."""

    @wraps(func)
    def wrap(*args, **kw):
        """Wrapper function"""
        start = time.perf_counter()
        result = func(*args, **kw)
        elapsed = time.perf_counter() - start
        logger.debug(f"{func.__name__} executed in {elapsed:.4f}s")
        return result

    return wrap


def func_debug_logger(func):
    """Decorator for applying DEBUG logging to a function.

    Sensitive keyword arguments (``secret_key``, ``access_key``) are
    automatically masked before being written to the log.
    """
    from .._base import _SENSITIVE_KEYS

    def _sanitize_kwargs(kw: dict) -> dict:
        """Return a shallow copy with sensitive values masked."""
        return {k: ("***" if k in _SENSITIVE_KEYS else v) for k, v in kw.items()}

    @wraps(func)
    def wrap(*args, **kw):
        """Wrapper function"""
        safe_kw = _sanitize_kwargs(kw)
        logger.debug(f"{func.__name__} called with args: {args} and kwargs: {safe_kw}")
        result = func(*args, **kw)
        logger.debug(f"{func.__name__} Result: {result}")
        return result

    return wrap
