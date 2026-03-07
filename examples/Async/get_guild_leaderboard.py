"""
get_guild_leaderboard.py
Sample script to get the various guild level leaderboards using the async Comlink client
"""

import asyncio

# Place module imports below this line
from swgoh_comlink import SwgohComlinkAsync


def get_max_guild_name_length(guild_list: list) -> int:
    max_length = max(len(leader_guild['name']) for leader_guild in guild_list)
    return max_length


def print_table(leaderboard: list,
                table_title: str,
                guild_name_col_title: str,
                score_col_title: str,
                rank_col_title: str) -> None:
    guild_name_col_width = get_max_guild_name_length(leaderboard)
    total_width = guild_name_col_width + len(score_col_title) + len(rank_col_title) + 7
    print()
    print(f"{table_title: ^{total_width}}")
    print('=' * total_width)
    print(f"{guild_name_col_title:^{guild_name_col_width}} | {score_col_title} | Rank")
    print('-' * total_width)
    for leaderboard_entry in leaderboard:
        score = f"{int(leaderboard_entry['leaderboardScore']):,}"
        print(
            f"{leaderboard_entry['name']:{guild_name_col_width}} | {score:^{len(score_col_title)}} | " +
            f"{leaderboard_entry['rank']:^{len(rank_col_title)}}")


async def main():
    # Create instance of SwgohComlinkAsync
    async with SwgohComlinkAsync() as comlink:
        """
        The get_guild_leaderboard() method takes three arguments, 'leaderboard_id', 'count', and the usual 'enums'
        boolean flag. The leaderboard_id parameter must be a list containing a single dictionary. The dictionary
        elements define which leaderboard (Total Raid Points, Specific Raid Points, Galactic Power, Territory Battle,
        Territory War) to get as well as narrowing details for the query depending on the type of leaderboard.
        The 'monthOffset' element may only be 0 or 1 to indicate the current month or previous month respectively.

        See the Sync version of this example for the full list of leaderboard_id variations.
        """

        # Get the top 5 Territory War leaderboard for the current month
        tw_leaderboard_id = [{"leaderboardType": 5, "defId": "TERRITORY_WAR_LEADERBOARD", "monthOffset": 0}]
        tw_top_5 = await comlink.get_guild_leaderboard(leaderboard_id=tw_leaderboard_id, count=5)

        # Print the top 5 TW leaderboard information
        print_table(leaderboard=tw_top_5['leaderboard'][0]['guild'],
                    table_title="Top 5 TW Leaderboard for current month",
                    guild_name_col_title="Guild Name",
                    score_col_title="Total GP Defeated",
                    rank_col_title="Rank")

        # Get the top 5 Speeder Bike raid leaderboard for the past month
        speederbike_raid_leaderboard_id = [
            {
                "leaderboardType": 6,
                "defId": "GUILD:RAIDS:NORMAL_DIFF:ROTJ:SPEEDERBIKE",
                "monthOffset": 1
            }
        ]
        speederbike_raid_top_5 = await comlink.get_guild_leaderboard(
            leaderboard_id=speederbike_raid_leaderboard_id, count=5
        )

        # Print the top 5 raid information
        print_table(leaderboard=speederbike_raid_top_5['leaderboard'][0]['guild'],
                    table_title="Top 5 Speeder bike raid Leaderboard for past month",
                    guild_name_col_title="Guild Name",
                    score_col_title="Total Raid points achieved",
                    rank_col_title="Rank")


asyncio.run(main())
