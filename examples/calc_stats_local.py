"""Example usage of local StatCalc support."""

from swgoh_comlink import StatCalc

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
