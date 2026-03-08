"""
get_gac_brackets.py
Scan GAC brackets for a league and optionally search for a player by name.

Uses the helper functions from swgoh_comlink.helpers:
  - get_gac_brackets()       — scans all brackets for a given league
  - search_gac_brackets()    — finds a player within the bracket data
  - convert_league_to_int()  — converts league name to integer ID
"""

from swgoh_comlink import SwgohComlink
from swgoh_comlink.helpers import get_gac_brackets, search_gac_brackets

# Create instance of SwgohComlink
comlink = SwgohComlink()

# Scan all Kyber league brackets
# Supported league names: "kyber", "aurodium", "chromium", "bronzium", "carbonite"
print("Scanning Kyber brackets (this may take a moment)...")
brackets = get_gac_brackets(comlink, league="kyber")

if brackets is None:
    print("No active GAC event found.")
else:
    print(f"Found {len(brackets)} brackets")

    # Show a summary of players per bracket
    total_players = sum(len(players) for players in brackets.values())
    print(f"Total players across all brackets: {total_players}")

    # Print first bracket as a sample
    if 0 in brackets:
        print(f"\nBracket 0 ({len(brackets[0])} players):")
        for player in brackets[0]:
            print(f"  {player.get('name', 'Unknown')}")

    # Search for a specific player across all brackets
    player_name = "target_player_name"  # Replace with the player name to search
    result = search_gac_brackets(brackets, player_name)
    if result:
        print(f"\nFound '{result['player']['name']}' in bracket {result['bracket']}")
    else:
        print(f"\nPlayer '{player_name}' not found in any bracket")

    # You can also limit the number of brackets scanned
    # limited_brackets = get_gac_brackets(comlink, league="kyber", limit=10)
