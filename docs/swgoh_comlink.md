# SwgohComlink

## Basic usage

```python
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(url="http://localhost:3000")
player = comlink.get_player(allycode=123456789)
```

## Advanced usage

```python
from swgoh_comlink import SwgohComlink

# Create a SwgohComlink instance with links to both the swgoh-comlink and swgoh-stats proxy services
# Also include access key and secret key assignments to prevent unwanted usage
comlink = SwgohComlink(url="http://localhost:3000", stats_url="http://localhost:3223", access_key="someRandomString",
                       secret_key="AnotherSecretRandomString")

# Get player details for a specific allycode. Note the example below is fictitious. Replace with a real
# allycode if trying for real.
player = comlink.get_player(allycode=123456789)

# If the player is a member of a guild, get a list of all the guild members
guild_members = comlink.get_guild(guild_id=player['guildId'])['member']

# The guild member list contains player objects, but there is only a 'playerId' element, no 'allyCode'
guild_member_player_ids = [p['playerId'] for p in guild_members]

# To get the individual guild member allycodes, we need to call either the get_player() or get_player_arena() methods.
# The get_player() method returns the entire character and ship roster for a player, which can be quite large.
# Since we are collecting information for up to 50 players in a guild, it is quicker to use the get_player_arena() method.
# The get_player_arena() method also contains an optional flag that can be used to request just the bare minimum
# information for a player. Setting the 'player_details_only' parameter to 'True' will reduce bandwidth on the network
# and speed up the response time overall

# While we could write a dedicated function to make call to get_player_arena() with a passed in 'player_id' argument,
# leveraging the Python map() function and lambda expression makes a one line example easy to produce.
guild_member_allycodes = list(
    map(lambda x: comlink.get_player_arena(player_id=x, player_details_only=True)['allyCode'], guild_member_player_ids))

```

## Module Details

::: swgoh_comlink._base.SwgohComlinkBase
options:
show_object_full_path: false
show_root_full_path: false
members:
- __init__
::: swgoh_comlink.swgoh_comlink.SwgohComlink
options:
show_object_full_path: false
show_root_full_path: false

#### Examples

More examples of how to use this module can be found in
the [GitHub repository](https://github.com/swgoh-utils/comlink-python/tree/1.13.0rc1/examples/SwgohComlink).