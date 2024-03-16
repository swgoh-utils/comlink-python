"""
search_for_guilds.py
Sample script to search for guilds by various criteria using Comlink
"""

import asyncio

# Place module imports below this line
from swgoh_comlink import SwgohComlinkAsync


async def main():
    # Create instance of SwgohComlink
    comlink = SwgohComlinkAsync()

    """
    There are two ways in which guilds can be searched via Comlink. Hence, there are two methods available in the
    SwgohComlink library to call upon. One provides searching for guilds by name. The other provides searching for
    guilds by criteria.

    Searching for guilds by name requires at least one argument, a string to search on. The search is very lazy, so
    the more characters provided, the better the match will be. Searching for the string 'a' will return all guilds
    (up to the maximum value of the 'count' parameter) with the letter 'a' anywhere in the name. The default maximum
    response record count is 10.
    """

    # Search for a guild by name
    guilds_by_name = await comlink.get_guilds_by_name(name="guild")
    # Print the names of the maximum 10 guilds matched
    for guild in guilds_by_name["guild"]:
        print(f'{guild["name"]=}')

    """
    Searching for guilds by criteria offers the ability to find guilds based by characteristics other than name. The
    'search_criteria' argument to get_guilds_by_criteria() method should be a dictionary using the following template:

            search_criteria_template = {
                "minMemberCount": 1,
                "maxMemberCount": 50,
                "includeInviteOnly": True,
                "minGuildGalacticPower": 1,
                "maxGuildGalacticPower": 500000000,
                "recentTbParticipatedIn": []
            }

    """

    # Search for guilds by criteria
    guild_search_criteria = {
        "minMemberCount": 48,
        "maxMemberCount": 50,
        "includeInviteOnly": True,
        "minGuildGalacticPower": 500000000,
        "maxGuildGalacticPower": 600000000,
        "recentTbParticipatedIn": [],
    }

    guilds_by_criteria = await comlink.get_guilds_by_criteria(
        search_criteria=guild_search_criteria, count=1000
    )
    # Check the actual number of guilds over 500m GP with 48 players minimum to compare against the max count of 1000
    print(f'\nTotal number of guilds returned: {len(guilds_by_criteria["guild"])}')

    await comlink.client_session.close()


if __name__ == "__main__":
    asyncio.run(main())
