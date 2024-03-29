# SwgohComlinkAsync

## Basic usage

```python
import asyncio
from swgoh_comlink import SwgohComlinkAsync


async def main():
    comlink = SwgohComlinkAsync(url="http://192.168.1.167:3200")
    player = await comlink.get_player(allycode=314927874)
    print(f"{player['name']=}")


if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced usage

```python
import asyncio
from swgoh_comlink import SwgohComlinkAsync

# Create a SwgohComlink instance with links to both the swgoh-comlink and swgoh-stats proxy services
# Also include access key and secret key assignments to prevent unwanted usage
comlink = SwgohComlinkAsync(url="http://localhost:3000", stats_url="http://localhost:3223",
                            access_key="someRandomString", secret_key="AnotherSecretRandomString")


async def exchange_player_id_for_allycode(player_id: str) -> str:
    return await comlink.get_player_arena(player_id=player_id, player_details_only=True)['allyCode']


async def main():
    # Get player details for a specific allycode. Note the example below is fictitious. Replace with a real
    # allycode if trying for real.
    player: dict = await comlink.get_player(allycode=123456789)

    # If the player is a member of a guild, get a list of all the guild members
    guild_members: list = await comlink.get_guild(guild_id=player['guildId'])['member']

    # The guild member list contains player objects, but there is only a 'playerId' element, no 'allyCode'
    guild_member_player_ids: list = [p['playerId'] for p in guild_members]

    # To get the individual guild member allycodes, we need to call either the get_player() or get_player_arena() methods.
    # The get_player() method returns the entire character and ship roster for a player, which can be quite large.
    # Since we are collecting information for up to 50 players in a guild, it is quicker to use the get_player_arena() method.
    # The get_player_arena() method also contains an optional flag that can be used to request just the bare minimum
    # information for a player. Setting the 'player_details_only' parameter to 'True' will reduce bandwidth on the network
    # and speed up the response time overall

    guild_member_allycodes: list = []
    for member_player_id in guild_member_player_ids:
        guild_member_allycodes.append(await exchange_player_id_for_allycode(member_player_id))

    for member_allycode in guild_member_allycodes:
        print(member_allycode)


if __name__ == '__main__':
    asyncio.run(main())
```

## Module Details

### SwgohComlinkAsync

::: swgoh_comlink.swgoh_comlink.SwgohComlinkBase
options:
members: [ThisClass]
filters: ["^__"]
::: swgoh_comlink.swgoh_comlink.SwgohComlinkAsync

#### Examples

More examples of how to use this module can be found in
the [GitHub repository](https://github.com/swgoh-utils/comlink-python/tree/1.13.0rc1/examples/SwgohComlinkAsync).