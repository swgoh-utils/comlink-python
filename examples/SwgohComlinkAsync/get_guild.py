"""
get_guild.py
Sample script to get guild information from Comlink
"""

import asyncio

from swgoh_comlink import SwgohComlinkAsync


def display_tw_data(tw_list: list) -> None:
    print(f'{"Territory War ID":18} {"Score":^10} {"GP Defeated":^15}')
    print("=" * 45)
    for tw in tw_list:
        print(
            f'{tw["territoryWarId"]:^18} {int(tw["score"]):^10,} {int(tw["power"]):15,}'
        )


async def main():
    # Create instance of SwgohComlink
    comlink = SwgohComlinkAsync()

    """
    The get_guild() call requires a positional parameter 'guild_id'. The guild_id can be found in a guild member
    player profile. In the example below, we'll make a call to the get_player() method first and then use the guild_id
    from the response to call the get_guild() method.
    """
    player = await comlink.get_player(314927874)
    guild = await comlink.get_guild(player["guildId"])
    print(f"{guild['profile']['name']=}")

    """
    The get_guild() method returns a dictionary containing information about the guild, its members and event
    participation. By default, there is no actual statistic data returned. If the desire is to include information
    such as recent raid or event result, then the 'include_recent_guild_activity_info' argument in the method should
    be set to True.
    """

    guild_with_stats = await comlink.get_guild(
        player["guildId"], include_recent_guild_activity_info=True
    )
    # Closing the aiohttp session is only needed for this example script. Normally, the client session would be
    # managed in a different method depending on the application needs
    await comlink.client.aclose()
    display_tw_data(guild_with_stats["recentTerritoryWarResult"])

    """
    >>> pprint(guild['recentTerritoryWarResult'])
    []

    >>> pprint(guild_with_stats['recentTerritoryWarResult'])
    [{'endTimeSeconds': '1684083602',
      'opponentScore': '5993',
      'power': 420466841,
      'score': '25660',
      'territoryWarId': 'tw01A'},
     {'endTimeSeconds': '1680112801',
      'opponentScore': '31708',
      'power': 441637947,
      'score': '28226',
      'territoryWarId': 'tw01D'},
      <...>
    """


if __name__ == "__main__":
    asyncio.run(main())
