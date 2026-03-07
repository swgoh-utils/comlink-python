# coding=utf-8
"""Sentinel objects used for parameter validation throughout swgoh_comlink."""

from __future__ import annotations

from sentinels import Sentinel

# Define sentinels used in parameter checking.
# Each sentinel has a unique label matching its primary name for clear debugging output.
OPTIONAL = Sentinel("OPTIONAL")
NotSet = Sentinel("NotSet")
EMPTY = Sentinel("EMPTY")
NotGiven = Sentinel("NotGiven")
REQUIRED = Sentinel("REQUIRED")
GIVEN = Sentinel("GIVEN")
MISSING = Sentinel("MISSING")
SET = Sentinel("SET")
MutualExclusiveRequired = Sentinel("MutualExclusiveRequired")
MutualRequiredNotSet = Sentinel("MutualRequiredNotSet")
