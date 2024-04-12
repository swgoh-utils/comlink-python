# coding=utf-8
"""
Test swgoh_comlink.utils functions
"""
import pytest

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync
from swgoh_comlink.utils import (
    get_current_gac_event,
    get_function_name,
)

async_comlink = SwgohComlinkAsync(default_logger_enabled=True)
comlink = SwgohComlink(default_logger_enabled=True)


def test_get_current_gac_event():
    comlink.logger.debug(f"** Starting {get_function_name()}")
    try:
        current_gac_event = get_current_gac_event(comlink=comlink)
        assert "id" in current_gac_event
    except NameError:
        pass


def test_get_current_gac_event_async():
    comlink.logger.debug(f"** Starting {get_function_name()}")
    try:
        current_gac_event = get_current_gac_event(comlink=async_comlink)
        assert "id" in current_gac_event
    except NameError:
        pass


def test_get_current_gac_event_no_comlink():
    comlink.logger.debug(f"** Starting {get_function_name()}")
    try:
        with pytest.raises(ValueError):
            current_gac_event = get_current_gac_event()
            assert "id" in current_gac_event
    except NameError:
        pass
