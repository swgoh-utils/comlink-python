"""
calc_stats_local.py
Example usage of local StatCalc support.

Demonstrates:
  1. Basic character stats (minimal unit definition)
  2. Character with skills and mods (normalized format)
  3. Full player roster stats from Comlink API data
  4. GameDataBuilder — fetches data dynamically from a running Comlink service
"""

from swgoh_comlink import SwgohComlink, StatCalc, GameDataBuilder

# --- Example 1: Basic unit (no skills or mods) ---
basic_unit = {
    "defId": "BOSSK",
    "rarity": 7,
    "level": 85,
    "gear": 13,
    "equipped": [],
    "skills": [],
}

calc = StatCalc()
stats = calc.calc_char_stats(basic_unit)
print("=== Basic unit (no skills/mods) ===")
print(stats)

# --- Example 2: Unit with skills and mods (normalized format) ---
unit_with_skills_and_mods = {
    "defId": "BOSSK",
    "rarity": 7,
    "level": 85,
    "gear": 13,
    "equipped": [],
    "skills": [
        {"id": "basicskill_BOSSK", "tier": 8},
        {"id": "specialskill_BOSSK01", "tier": 8},
        {"id": "specialskill_BOSSK02", "tier": 8},
        {"id": "leaderskill_BOSSK", "tier": 8},
        {"id": "uniqueskill_BOSSK01", "tier": 8},
    ],
    "relic": {"currentTier": 7},
    "mods": [
        {"set": 1, "level": 15, "pips": 6, "tier": 5, "stat": [(48, 8.5), (5, 12), (28, 1198), (41, 113), (49, 116)]},
        {"set": 1, "level": 15, "pips": 6, "tier": 5, "stat": [(55, 24.0), (5, 7), (28, 839), (1, 1260), (41, 100)]},
        {"set": 1, "level": 15, "pips": 6, "tier": 5, "stat": [(48, 8.5), (5, 10), (28, 1500), (53, 18), (1, 980)]},
        {"set": 1, "level": 15, "pips": 6, "tier": 5, "stat": [(48, 8.5), (5, 15), (28, 900), (41, 80), (49, 95)]},
    ],
}

stats = calc.calc_char_stats(unit_with_skills_and_mods)
print("\n=== Unit with skills and mods ===")
print(stats)

# --- Example 3: Player roster stats from Comlink API ---
# Requires a running Comlink service.
# calc_player_stats accepts the raw player payload from get_player().

# comlink = SwgohComlink()
# player = comlink.get_player(allycode=123456789)
# calc.calc_player_stats(player)
# for unit in player["rosterUnit"][:3]:
#     name = unit["definitionId"].split(":")[0]
#     gp = unit.get("gp", "N/A")
#     print(f"{name}: GP={gp}")

# --- Example 4: Build game data from a running Comlink service ---
# comlink = SwgohComlink()
# game_data = GameDataBuilder(comlink).build()
# calc = StatCalc(game_data=game_data)
# stats = calc.calc_char_stats(basic_unit)
# print("From Comlink:", stats)
