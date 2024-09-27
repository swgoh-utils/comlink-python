# coding=utf-8
"""
Helper functions for StatCalc module
"""

from __future__ import annotations, absolute_import

from typing import Any

from swgoh_comlink.constants import get_logger

logger = get_logger()


def raise_invalid_object_type_error(obj: Any, type_list: set):
    err_msg = f"Invalid object type {type(obj)} for {obj!r} argument. Expected one of {type_list!r}."
    logger.error(err_msg)
    raise NotImplementedError(err_msg)
