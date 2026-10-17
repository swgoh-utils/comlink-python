# coding=utf-8
"""
get_player.py — typed async-client variant

Sibling of ``examples/Async/get_player.py``. Uses the typed async
client (``swgoh_comlink.typed.SwgohComlinkAsync``) so awaited
endpoint methods return ``msgspec.Struct`` instances.

Requires the v3 alpha — install via the v3.0.0a1 GitHub Release.
"""

import asyncio

# Typed async client — same SwgohComlinkAsync name as the dict
# variant, but at the `.typed` import path. Endpoint methods are
# async + return msgspec.Struct.
from swgoh_comlink.typed import SwgohComlinkAsync


async def main() -> None:
    # Construct once, reuse across awaits. Same kwargs as sync
    # (`url`, `profile`, `retry`, …).
    async with SwgohComlinkAsync() as comlink:
        # await returns a typed `Player` Struct.
        player = await comlink.get_player(allycode=314927874)

        # Attribute access — same as sync.
        print(f"Name:         {player.name}")
        print(f"Level:        {player.level}")
        print(f"Ally code:    {player.ally_code}")
        print(f"Guild:        {player.guild_name} ({player.guild_id})")
        print(f"Roster units: {len(player.roster_unit)}")

        # Fetch the guild concurrently with another player call.
        # asyncio.gather() works the same on the typed client — both
        # awaitables return typed Structs.
        if player.guild_id:
            guild_task = comlink.get_guild(guild_id=player.guild_id)
            second_player_task = comlink.get_player(allycode=379454819)
            guild, second_player = await asyncio.gather(guild_task, second_player_task)
            print(f"\nGuild member count: {len(guild.member or [])}")
            print(f"Second player:      {second_player.name}")


if __name__ == "__main__":
    asyncio.run(main())
