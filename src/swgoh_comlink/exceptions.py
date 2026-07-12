# coding=utf-8
"""
Custom exceptions for swgoh_comlink
"""

from __future__ import annotations


class SwgohComlinkException(Exception):
    """Base class for exceptions in this module."""


class SwgohComlinkValueError(SwgohComlinkException, ValueError):
    """Raised when an argument value is invalid."""


class SwgohComlinkTypeError(SwgohComlinkException, TypeError):
    """Raised when an argument type is invalid."""
