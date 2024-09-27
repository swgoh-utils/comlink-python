import pytest

from swgoh_comlink import SwgohComlinkAsync

comlink = SwgohComlinkAsync(default_logger_enabled=True)


@pytest.mark.asyncio
async def test_async_get_guild_raid_leaderboard(leaderboard_ids):
    query_count = 5
    for leaderboard_id in leaderboard_ids:
        comlink.logger.info(f" ** [TEST RUN] ** raid_leaderboard_id: {leaderboard_id}")
        guild_leaderboard_results = await comlink.get_guild_leaderboard(leaderboard_id=leaderboard_id,
                                                                        count=query_count)
        assert "leaderboard" in guild_leaderboard_results
        result_count = len(guild_leaderboard_results['leaderboard'][0]['guild'])
        comlink.logger.info(f" ** [TEST RESULT] ** Query count: {query_count}, Result count: {result_count}")


@pytest.mark.asyncio
async def test_async_get_guild_raid_leaderboard_no_id():
    with pytest.raises(ValueError):
        await comlink.get_guild_leaderboard(count=5)
