"""Example usage of local StatCalc support."""

from swgoh_comlink import StatCalc

# TODO: expand example to include variations with skills and mods as well as actual player roster data

calc = StatCalc()
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
