# coding=utf-8
"""
Custom exceptions for swgoh_comlink
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SwgohComlinkException(Exception):
    """Base class for exceptions in this module."""

    def __init__(self, message: str | Exception) -> None:
        super().__init__(message)
        # Log at error level; callers are responsible for traceback context
        logger.exception(f"SwgohComlinkException: {message}")


class SwgohComlinkValueError(SwgohComlinkException, ValueError):
    """Raised when an argument value is invalid."""


class SwgohComlinkTypeError(SwgohComlinkException, TypeError):
    """Raised when an argument type is invalid."""
