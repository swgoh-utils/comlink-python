# coding=utf-8
"""Sentinel objects used for parameter validation throughout swgoh_comlink."""

from __future__ import annotations


class Sentinel:
    """Lightweight sentinel object for distinguishing 'not provided' from None."""

    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        self._name = name

    def __repr__(self) -> str:
        return self._name

    def __bool__(self) -> bool:
        return False


# Define sentinels used in parameter checking.
REQUIRED = Sentinel("REQUIRED")
GIVEN = Sentinel("GIVEN")
MISSING = Sentinel("MISSING")
MutualExclusiveRequired = Sentinel("MutualExclusiveRequired")
