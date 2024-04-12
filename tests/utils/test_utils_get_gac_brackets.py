# coding=utf-8
"""
Test swgoh_comlink.utils functions
"""
import pytest

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync
from swgoh_comlink.utils import (
    get_gac_brackets,
    get_function_name,
)

async_comlink = SwgohComlinkAsync(default_logger_enabled=True)
comlink = SwgohComlink(default_logger_enabled=True)


def test_get_gac_brackets():
    league = "KYBER"
    limit = 5
    comlink.logger.debug(f"** Starting {get_function_name()} with {comlink=} {league=} and {limit=}")
    brackets = get_gac_brackets(comlink=comlink, league=league, limit=limit)
    assert brackets is not None
    assert isinstance(brackets, dict)
    assert len(brackets) == limit


def test_get_gac_brackets_no_comlink():
    comlink.logger.debug(f"** Starting {get_function_name()}")
    with pytest.raises(ValueError):
        get_gac_brackets(league="KYBER", limit=5)


def test_get_gac_brackets_wrong_comlink():
    comlink.logger.debug(f"** Starting {get_function_name()}")
    with pytest.raises(ValueError):
        get_gac_brackets(comlink=async_comlink, league="KYBER", limit=5)


def test_get_gac_brackets_no_league():
    comlink.logger.debug(f"** Starting {get_function_name()}")
    with pytest.raises(ValueError):
        get_gac_brackets(comlink=comlink, limit=5)


def test_get_gac_brackets_wrong_league():
    comlink.logger.debug(f"** Starting {get_function_name()}")
    with pytest.raises(ValueError):
        get_gac_brackets(comlink=comlink, league=10, limit=5)
