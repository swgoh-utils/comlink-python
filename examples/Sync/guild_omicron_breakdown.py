"""
guild_omicron_breakdown.py
Report omicron adoption across an entire guild, separated by game mode.

This example demonstrates how to:
  1. List a guild's members from one player's ally code with get_guild_members()
  2. Fetch every member's full profile
  3. Pull only the 'skill', 'units' and 'ability' game data collections, by combining
     individual DataItems bits with | rather than requesting whole segments
  4. Resolve unit and omicron names through a localization dictionary
  5. Summarise adoption with helpers.get_omicron_breakdown()

Why the profiles have to be fetched: a guild's 'member' list holds identity stubs (player ID,
name, galactic power) and carries no roster. Whether a member has an omicron applied lives in
player['rosterUnit'][n]['skill'], so every member needs a full get_player() call. Here they are
fetched one after another; see examples/Async/guild_omicron_breakdown.py to fetch them
concurrently.
"""

import time

from swgoh_comlink import SwgohComlink
from swgoh_comlink.helpers import (
    DataItems,
    get_guild_members,
    get_localization_dictionary,
    get_omicron_breakdown,
)

# CONFIGURATION
# Change these to any valid values to look up that player's guild
ALLY_CODE = 314927874
COMLINK_HOST = "localhost"
COMLINK_PORT = 3000
LANGUAGE = "eng_us"

# How many omicrons to list per game mode
TOP_N = 5

comlink = SwgohComlink(host=COMLINK_HOST, port=COMLINK_PORT)

# Step 1: The guild's member list, from any one member's ally code.
members = get_guild_members(comlink, allycode=ALLY_CODE)
print(f"Members: {len(members)}")

# Step 2: Every member profile.
start = time.perf_counter()
profiles = [comlink.get_player(player_id=member["playerId"]) for member in members]
print(f"Fetched {len(profiles)} profiles in {time.perf_counter() - start:.2f}s")

# Step 3: Game data. Request exactly the three collections needed by combining the individual
# DataItems bits; whole segments pull far more than this needs. 'ability' supplies the omicron
# names: a unit often has several omicrons in one game mode, so the unit name alone does not
# identify them. PvE units are left out, since only playable units can be in a roster.
game_data = comlink.get_game_data(
    items=DataItems.SKILL | DataItems.UNITS | DataItems.ABILITY,
    include_pve_units=False,
)
print(
    f"Game data: {len(game_data['skill'])} skills, {len(game_data['units'])} unit rows, "
    f"{len(game_data['ability'])} abilities"
)

# Step 4: Localization, so units and omicrons read as names rather than IDs.
localization = get_localization_dictionary(comlink, language=LANGUAGE)

# Step 5: The breakdown itself.
breakdown = get_omicron_breakdown(
    profiles,
    game_data["skill"],
    game_data["units"],
    ability_list=game_data["ability"],
    localization=localization,
)

# Step 6: Report. Counts first, then the detail behind one of them.
total = breakdown["total_members"]
for mode in breakdown["modes"]:
    print(f"\n=== {mode['mode_name']} (mode {mode['mode']}): {len(mode['skills'])} omicrons ===")
    for row in mode["skills"][:TOP_N]:
        applied = len(row["applied"])
        owners = applied + len(row["owned_not_applied"])
        label = f"{row['unit_name'] or row['unit_base_id'] or '?'}: {row['skill_name'] or row['skill_id']}"
        print(f"  {label:<60} {applied:>3}/{total} guild | {applied:>3}/{owners} owners")

# The member lists are the point of the helper, so show one in full: the omicron with the most
# owners who have not applied it, the guild's largest single opportunity.
rows = [(mode["mode_name"], row) for mode in breakdown["modes"] for row in mode["skills"]]
if rows:
    mode_name, target = max(rows, key=lambda pair: len(pair[1]["owned_not_applied"]))
    if target["owned_not_applied"]:
        unit = target["unit_name"] or target["unit_base_id"] or "?"
        print(f"\n=== Biggest opportunity: {unit}: {target['skill_name'] or target['skill_id']} ({mode_name}) ===")
        print(f"  applied by {len(target['applied'])}, missing on {len(target['owned_not_applied'])} rosters")
        print(f"  {target['not_owned_count']} members do not own the unit\n")
        for member in target["owned_not_applied"]:
            # tier is None when the skill is not in the roster at all: star-gated and not yet
            # unlocked, rather than merely not upgraded.
            position = "not unlocked" if member["tier"] is None else f"tier {member['tier']}/{target['omicron_tier']}"
            print(f"  {member['player_name']:<24} {position}")
