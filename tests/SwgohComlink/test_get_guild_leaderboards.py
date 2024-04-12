import pytest

from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(default_logger_enabled=True)


def test_get_guild_raid_leaderboard(leaderboard_ids):
    query_count = 5
    for leaderboard_id in leaderboard_ids:
        comlink.logger.info(f" ** [TEST RUN] ** raid_leaderboard_id: {leaderboard_id}")
        guild_leaderboard_results = comlink.get_guild_leaderboard(leaderboard_id=leaderboard_id, count=query_count)
        assert "leaderboard" in guild_leaderboard_results
        result_count = len(guild_leaderboard_results['leaderboard'][0]['guild'])
        comlink.logger.info(f" ** [TEST RESULT] ** Query count: {query_count}, Result count: {result_count}")


def test_get_guild_raid_leaderboard_no_id():
    with pytest.raises(ValueError):
        comlink.get_guild_leaderboard(count=5)
