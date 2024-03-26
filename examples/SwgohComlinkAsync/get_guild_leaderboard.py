"""
get_guild_leaderboard.py
Sample script to get the various guild level leaderboards using Comlink
"""

import asyncio

# Place module imports below this line
from swgoh_comlink import SwgohComlinkAsync


async def main():
    # Create instance of SwgohComlink
    comlink = SwgohComlinkAsync()

    """
    The get_guild_leaderboard() method takes three arguments, 'leaderboard_id', 'count', and the usual 'enums' boolean flag.
    The leaderboard_id parameter must be a list containing a single dictionary. The dictionary elements define which
    leaderboard (Total Raid Points, Specific Raid Points, Galactic Power, Territory Battle, Territory War) to get as well
    as narrowing details for the query depending on the type of leaderboard. The 'monthOffset' element may only be 0 or 1 to
    indicate the current month or previous month respectively. The possible variations for the 'leaderboard_id' list
    object are:

    [{"leaderboardType": 0, "monthOffset": 0}] # Total raid points for current month
    [{"leaderboardType": 0, "monthOffset": 1}] # Total raid points for the previous month

    [{"leaderboardType": 2, "defId": <str>, "monthOffset": 0}] # Raid points for specific raid (indicated by the <str>
                                                                  value for the current month. <str> can be one of:
                                                                  "sith_raid", "rancor", "rancor_challenge", or "aat"

    [{"leaderboardType": 3, "monthOffset": 0}] # Total Galactic Power for current month
    [{"leaderboardType": 3, "monthOffset": 1}] # Total Galactic Power for the previous month

    [{"leaderboardType": 4, "defId": <str>, "monthOffset": 0}] # Territory Battle Stars for specific TB (indicated by the
                                                                  <str> value for the current month. <str> can be one of:
                                                                  "t01D", "t02D", "t03D", "t04D", or "t05D"

                                                                  Note:
                                                                    t01D = Rebel Assault
                                                                    t02D = Imperial Retaliation
                                                                    t03D = Separatist Might
                                                                    t04D = Republic Offensive
                                                                    t05D = Rise of the Empire

    [{"leaderboardType": 5, "defId": "TERRITORY_WAR_LEADERBOARD", "monthOffset": 0}] # Territory War accumulated defeated GP for the current month
    [{"leaderboardType": 5, "defId": "TERRITORY_WAR_LEADERBOARD", "monthOffset": 1}] # Territory War accumulated defeated GP for the previous month

    """

    # Get the top 5 Territory War leaderboard for the current month
    tw_leaderboard_id = [
        {"leaderboardType": 5, "defId": "TERRITORY_WAR_LEADERBOARD", "monthOffset": 0}
    ]
    tw_top_5 = await comlink.get_guild_leaderboard(
        leaderboard_id=tw_leaderboard_id, count=5
    )
    await comlink.client.aclose()

    # Print the top 5 information
    for guild in tw_top_5["leaderboard"][0]["guild"]:
        total_gp = f"{int(guild['leaderboardScore']):,}"
        print(
            f"Guild: {guild['name']:20} Total GP defeated: {total_gp:15} (Rank: {guild['rank']})"
        )


if __name__ == "__main__":
    asyncio.run(main())
