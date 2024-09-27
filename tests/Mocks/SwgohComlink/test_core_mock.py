# coding=utf-8
"""
File containing mock tests configurations for the SwgohComlink class methods
"""
import httpx
import pytest
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(default_logger_enabled=False)


def test_mock_post_exception(httpx_mock: HTTPXMock):
    httpx_mock.add_exception(httpx.RequestError("Request error"))
    with pytest.raises(httpx.RequestError):
        comlink._post(endpoint="/enums", payload={"test": True})
