# coding=utf-8
"""
Basic pytest configuration elements to be shared across all tests
"""
import pytest
import requests


class MockResponse:
    """Artificial requests.Response object definition"""

    @staticmethod
    def json(*args, **kwargs):
        """Override the response method that SwgohComlink uses to return the responses from _post() calls"""
        mock_test_response_obj = {
            "CombatType": 1,
            "units": 1,
            "localizationBundle": 1,
            "serverVersion": 1,
            "name": 1,
            "gp": 1,
            "rosterUnit": 1,
            "stats": {"gp": 1},
            "guildId": "8RhppbbqR_ShmjY5S6ZtQg",
            "player": {"guildId": "8RhppbbqR_ShmjY5S6ZtQg"},
            "guild": {"member": [{"playerId": 1}]},
        }
        return mock_test_response_obj


"""
class MockResponseList:
    @staticmethod
    def json(*args, **kwargs):
        mock_test_response_obj = [
            {
                "playerId": 1,
            }
        ]
        return mock_test_response_obj
"""


@pytest.fixture(autouse=True)
def mock_response(monkeypatch):
    """Mock the requests.get() response to return a static response"""

    def mock_get(*args, **kwargs):
        """Override requests.get() method"""
        return MockResponse()

    def mock_post(*args, **kwargs):
        """Override requests.get() method"""
        return MockResponse()

    monkeypatch.setattr(requests, "get", mock_get)
    monkeypatch.setattr(requests, "post", mock_post)


"""
@pytest.fixture(autouse=True)
def mock_response_list(monkeypatch):

    def mock_get(*args, **kwargs):
        return MockResponseList()

    def mock_post(*args, **kwargs):
        return MockResponseList()

    monkeypatch.setattr(requests, "get", mock_get)
    monkeypatch.setattr(requests, "post", mock_post)
"""
