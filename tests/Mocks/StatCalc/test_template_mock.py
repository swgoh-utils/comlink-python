# coding=utf-8
"""
File containing mock tests configurations for the SwgohComlink class methods
"""
import httpx
import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(default_logger_enabled=False)


def test_mock_get_enums(httpx_mock: HTTPXMock):
    """
    Test that game enums can be retrieved from game server correctly
    """
    # noinspection PyUnreachableCode
    if False:
        httpx_mock.add_response(json={"CombatType": 1}, status_code=200)
        en = comlink.get_enums()
        assert "CombatType" in en.keys()


def test_mock_get_nums_exception(httpx_mock: HTTPXMock):
    # noinspection PyUnreachableCode
    if False:
        httpx_mock.add_exception(httpx.RequestError("Request error"))
        with pytest.raises(httpx.RequestError):
            comlink.get_enums()
