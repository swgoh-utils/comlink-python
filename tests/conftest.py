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


@pytest.fixture(autouse=True)
def leaderboard_ids():
    tmp_lb_ids = [[{"leaderboardType": 0, "monthOffset": 1}]]
    for raid in ["sith_raid", "rancor", "rancor_challenge", "aat"]:
        tmp_lb_ids.append([{"leaderboardType": 2, "defId": f"{raid}", "monthOffset": 1}])
    tmp_lb_ids.append([{"leaderboardType": 3, "monthOffset": 1}])
    for i in range(1, 6):
        tmp_lb_ids.append([{"leaderboardType": 4, "defId": f"t{i:02d}D", "monthOffset": 1}])
    tmp_lb_ids.append([{"leaderboardType": 5, "defId": "TERRITORY_WAR_LEADERBOARD", "monthOffset": 1}])
    for raid in [
        "SITH_RAID:HEROIC85",
        "SITH_RAID:DIFF06",
        "AAT:HEROIC80",
        "AAT:DIFF06",
        "RANCOR:DIFF06",
        "RANCOR:DIFF01",
        "KRAYTDRAGON:DIFF01",
        "ROTJ:SPEEDERBIKE"]:
        tmp_lb_ids.append([{"leaderboardType": 6, "defId": "GUILD:RAIDS:NORMAL_DIFF:" + raid, "monthOffset": 1}])
    return tmp_lb_ids
