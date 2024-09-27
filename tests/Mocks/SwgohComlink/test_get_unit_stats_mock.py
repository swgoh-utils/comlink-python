# coding=utf-8
"""
File containing mock tests configurations for the SwgohComlink class methods
"""
from pytest_httpx import HTTPXMock

from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(default_logger_enabled=False)


def test_mock_get_unit_stats(httpx_mock: HTTPXMock, allycode):
    """
    Test that player data can be retrieved from game server correctly
    """
    httpx_mock.add_response(json={"name": 1,
                                  "rosterUnit": [{}, {}],
                                  "stats": {"gp": 1}
                                  }, status_code=200)
    p = comlink.get_player(allycode)
    assert 'name' in p.keys()
    unit_stats = comlink.get_unit_stats(p['rosterUnit'], flags=['calcGP', 'gameStyle'])
    assert 'gp' in unit_stats['stats'].keys()
