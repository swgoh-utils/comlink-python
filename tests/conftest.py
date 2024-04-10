# coding=utf-8
"""
Basic pytest configuration elements to be shared across all tests
"""
import os
import sys

import pytest

sys.path.append(os.path.dirname(__file__))

_player_id: str = "cRdX7yGvS-eKfyDxAAgaYw"
_allycode: int = 245866537
_guild_id: str = "8RhppbbqR_ShmjY5S6ZtQg"


@pytest.fixture(autouse=True)
def allycode():
    """Return player allycode to be used in test cases"""
    return _allycode


@pytest.fixture(autouse=True)
def player_id():
    """Return player allycode to be used in test cases"""
    return _player_id


@pytest.fixture(autouse=True)
def guild_id():
    """Return player allycode to be used in test cases"""
    return _guild_id
