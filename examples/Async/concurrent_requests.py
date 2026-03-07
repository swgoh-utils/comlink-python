"""
concurrent_requests.py
Sample script demonstrating the primary advantage of async: concurrent requests.
Fetches multiple player profiles simultaneously using asyncio.gather().
"""

import asyncio
import time

from swgoh_comlink import SwgohComlinkAsync


# Example ally codes to fetch concurrently
ALLY_CODES = [
    314927874,
    # Add more ally codes here to see the concurrency benefit
]


async def main():
    async with SwgohComlinkAsync() as comlink:
        # --- Sequential approach (for comparison) ---
        start = time.perf_counter()
        sequential_results = []
        for allycode in ALLY_CODES:
            player = await comlink.get_player(allycode=allycode)
            sequential_results.append(player)
        sequential_time = time.perf_counter() - start
        print(f"Sequential fetch of {len(ALLY_CODES)} player(s): {sequential_time:.2f}s")

        # --- Concurrent approach using asyncio.gather ---
        start = time.perf_counter()
        concurrent_results = await asyncio.gather(
            *[comlink.get_player(allycode=ac) for ac in ALLY_CODES]
        )
        concurrent_time = time.perf_counter() - start
        print(f"Concurrent fetch of {len(ALLY_CODES)} player(s): {concurrent_time:.2f}s")

        # Print player names from concurrent results
        for player in concurrent_results:
            print(f"  Player: {player['name']}, Guild: {player.get('guildName', 'N/A')}")

        if len(ALLY_CODES) > 1:
            speedup = sequential_time / concurrent_time if concurrent_time > 0 else float('inf')
            print(f"\nSpeedup: {speedup:.1f}x faster with concurrent requests")


asyncio.run(main())
