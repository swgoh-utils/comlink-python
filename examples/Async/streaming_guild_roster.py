"""
streaming_guild_roster.py
Fetch all guild member profiles concurrently using asyncio.TaskGroup.

This example demonstrates how to:
  1. Look up a guild from a player's ally code
  2. Extract all member player IDs from the guild roster
  3. Fetch every member's full profile concurrently using asyncio.TaskGroup
  4. Process results as each task completes (streaming-style output)

asyncio.TaskGroup (Python 3.11+) is preferred over asyncio.gather() when you want
structured concurrency — if any single fetch fails, the entire group is cancelled
and the exception is raised cleanly.
"""

import sys

if sys.version_info < (3, 11):
    sys.exit("This example requires Python 3.11+ (asyncio.TaskGroup support).")

import asyncio
import time

from swgoh_comlink import SwgohComlinkAsync

# Change this to any valid ally code to look up that player's guild
ALLY_CODE = 314927874


async def fetch_member(comlink: SwgohComlinkAsync, player_id: str, index: int, total: int) -> dict:
    """Fetch a single guild member's profile and print progress."""
    player = await comlink.get_player(player_id=player_id)
    gp = 0
    for stat in player.get('profileStat', []):
        if stat.get('nameKey') == 'STAT_GALACTIC_POWER_ACQUIRED_NAME':
            gp = int(stat.get('value', 0))
            break
    print(f"  [{index}/{total}] {player['name']} — GP: {gp:,}")
    return player


async def main():
    async with SwgohComlinkAsync(host="192.168.68.74", port=3200) as comlink:
        # Step 1: Get the guild ID from a player's profile
        player = await comlink.get_player(allycode=ALLY_CODE)
        guild_id = player.get('guildId')
        if not guild_id:
            print(f"Player {player['name']} is not in a guild.")
            return

        print(f"Player: {player['name']}")
        print(f"Guild:  {player.get('guildName', 'Unknown')}\n")

        # Step 2: Get guild data to extract member IDs
        guild = await comlink.get_guild(guild_id)
        members = guild.get('member', [])
        member_ids = [m['playerId'] for m in members]
        total = len(member_ids)
        print(f"Fetching {total} guild member profiles concurrently...\n")

        # Step 3: Fetch all members concurrently using TaskGroup
        start = time.perf_counter()
        results = []

        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(fetch_member(comlink, pid, i + 1, total))
                for i, pid in enumerate(member_ids)
            ]

        # TaskGroup ensures all tasks have completed (or all are cancelled on error)
        results = [task.result() for task in tasks]
        elapsed = time.perf_counter() - start

        # Step 4: Summary
        print(f"\nFetched {len(results)} member profiles in {elapsed:.2f}s")
        total_gp = 0
        for p in results:
            for stat in p.get('profileStat', []):
                if stat.get('nameKey') == 'STAT_GALACTIC_POWER_ACQUIRED_NAME':
                    total_gp += int(stat.get('value', 0))
                    break
        print(f"Combined Guild GP: {total_gp:,}")


asyncio.run(main())
