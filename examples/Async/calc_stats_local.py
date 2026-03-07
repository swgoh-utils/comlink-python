"""
calc_stats_local.py
Example usage of async StatCalcAsync support.

Demonstrates two approaches to loading game data:
  1. Default — fetches a static gameData.json from GitHub (async)
  2. GameDataBuilderAsync — fetches data dynamically from a running Comlink service
"""

import asyncio

from swgoh_comlink import SwgohComlinkAsync, StatCalcAsync, GameDataBuilderAsync


# TODO: expand example to include variations with skills and mods as well as actual player roster data
async def main():
    unit = {
        "defId": "BOSSK",
        "rarity": 7,
        "level": 85,
        "gear": 13,
        "equipped": [],
        "skills": [],
    }

    # --- Approach 1: Default (fetch game data from GitHub) ---
    calc = await StatCalcAsync.create()
    stats = calc.calc_char_stats(unit)
    print("From GitHub:", stats)

    # --- Approach 2: Build game data from a running Comlink service ---
    # async with SwgohComlinkAsync() as comlink:
    #     game_data = await GameDataBuilderAsync(comlink).build()
    #     calc = StatCalcAsync(game_data=game_data)
    #     stats = calc.calc_char_stats(unit)
    #     print("From Comlink:", stats)


asyncio.run(main())
