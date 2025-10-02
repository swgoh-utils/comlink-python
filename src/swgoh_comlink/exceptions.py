# coding=utf-8
"""
Custom exceptions for logging
"""

from __future__ import annotations

from .globals import get_logger

logger = get_logger(__name__)


class SwgohComlinkException(Exception):
    """Base class for exceptions in this module."""

    def __init__(self, message) -> None:
        super().__init__(message)
        logger.exception(f"SwgohComlinkException: {message}", exc_info=True)


class SwgohComlinkValueError(SwgohComlinkException, ValueError):
    ...
