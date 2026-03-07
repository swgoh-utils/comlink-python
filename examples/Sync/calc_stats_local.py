"""
calc_stats_local.py
Example usage of local StatCalc support.

Demonstrates two approaches to loading game data:
  1. Default — fetches a static gameData.json from GitHub
  2. GameDataBuilder — fetches data dynamically from a running Comlink service
"""

from swgoh_comlink import SwgohComlink, StatCalc, GameDataBuilder

# TODO: expand example to include variations with skills and mods as well as actual player roster data

unit = {
    "defId": "BOSSK",
    "rarity": 7,
    "level": 85,
    "gear": 13,
    "equipped": [],
    "skills": [],
}

# --- Approach 1: Default (fetch game data from GitHub) ---
calc = StatCalc()
stats = calc.calc_char_stats(unit)
print("From GitHub:", stats)

# --- Approach 2: Build game data from a running Comlink service ---
# comlink = SwgohComlink()
# game_data = GameDataBuilder(comlink).build()
# calc = StatCalc(game_data=game_data)
# stats = calc.calc_char_stats(unit)
# print("From Comlink:", stats)
