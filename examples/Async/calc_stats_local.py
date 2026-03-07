"""
calc_stats_local.py
Example usage of async StatCalcAsync support.

StatCalcAsync uses a factory classmethod (create) to fetch game data
asynchronously from GitHub. All calculation methods are inherited from
StatCalc and remain synchronous (they are pure computation).
"""

import asyncio

from swgoh_comlink import StatCalcAsync


# TODO: expand example to include variations with skills and mods as well as actual player roster data
async def main():
    # Create a StatCalcAsync instance — fetches latest game data from GitHub
    calc = await StatCalcAsync.create()

    unit = {
        "defId": "BOSSK",
        "rarity": 7,
        "level": 85,
        "gear": 13,
        "equipped": [],
        "skills": [],
    }

    stats = calc.calc_char_stats(unit)
    print(stats)


asyncio.run(main())
