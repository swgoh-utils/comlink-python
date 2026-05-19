# coding=utf-8
"""
streaming_guild_roster.py — typed-async-client variant

Sibling of ``examples/Async/streaming_guild_roster.py``. Uses the
typed async client (``swgoh_comlink.typed.SwgohComlinkAsync``) so
each concurrent ``get_player`` returns a typed ``Player`` Struct.

Demonstrates structured-concurrency fan-out with
``asyncio.TaskGroup`` (Python 3.11+): if any single member fetch
fails, the whole group cancels cleanly.

Requires the v3 alpha + Python 3.11+.
"""

from __future__ import annotations

import asyncio
import time

# asyncio.TaskGroup requires Python 3.11+. The project's pyproject.toml
# already pins Python>=3.11, so the version block the v2 examples
# carry is redundant here.
from swgoh_comlink.typed import SwgohComlinkAsync

# CONFIGURATION
ALLY_CODE = 314927874
COMLINK_URL = "http://localhost:3200"


async def fetch_member(
    comlink: SwgohComlinkAsync,
    player_id: str,
    index: int,
    total: int,
) -> tuple[str, int]:
    """Fetch one guild member's typed Player Struct + extract GP."""
    player = await comlink.get_player(player_id=player_id)

    # Profile stats are nested typed Structs. Each ProfileStat
    # exposes `name_key` + `value` as attributes — no dict subscripts.
    gp = 0
    for stat in player.profile_stat or []:
        if stat.name_key == "STAT_GALACTIC_POWER_ACQUIRED_NAME":
            gp = int(stat.value or 0)
            break

    print(f"  [{index:>3}/{total}] {player.name:<28} — GP: {gp:>12,}")
    return player.name, gp


async def main() -> None:
    async with SwgohComlinkAsync(url=COMLINK_URL) as comlink:
        # Step 1 — look up the guild from a single player's profile.
        player = await comlink.get_player(allycode=ALLY_CODE)
        if not player.guild_id:
            print(f"Player {player.name} is not in a guild.")
            return

        print(f"Player: {player.name}")
        print(f"Guild:  {player.guild_name}\n")

        # Step 2 — fetch the guild's typed Struct, extract member IDs.
        guild = await comlink.get_guild(player.guild_id)
        member_ids: list[str] = [m.player_id for m in (guild.member or [])]
        total = len(member_ids)
        print(f"Fetching {total} member profiles concurrently...\n")

        # Step 3 — fan out via asyncio.TaskGroup. If any fetch
        # raises, the group cancels the rest + re-raises the
        # exception cleanly.
        t0 = time.perf_counter()
        results: list[asyncio.Task[tuple[str, int]]] = []
        async with asyncio.TaskGroup() as tg:
            for idx, pid in enumerate(member_ids, start=1):
                results.append(tg.create_task(fetch_member(comlink, pid, idx, total)))
        elapsed = time.perf_counter() - t0

        # Step 4 — summary. Tasks completed in completion order via
        # the print inside fetch_member; here we sort by GP for the
        # final table.
        pairs = [t.result() for t in results]
        pairs.sort(key=lambda p: p[1], reverse=True)
        print(f"\n--- Top 5 by GP (of {total} members; {elapsed:.1f}s total) ---")
        for name, gp in pairs[:5]:
            print(f"  {name:<28} {gp:>12,}")


if __name__ == "__main__":
    asyncio.run(main())
