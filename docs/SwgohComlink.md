# SwgohComlink

## Usage

Basic default usage example:

```python
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink()
player_data = comlink.get_player(245866537)
player_name = player_data['name']
guild_id = player_data['guildId']
guild = comlink.get_guild(guild_id)
guild_name = guild['profile']['name']
```

Usage example with non-default settings for a swgoh-comlink service running on the local machine at TCP port 3500:

```python
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(url='http://localhost:3500')
player_data = comlink.get_player(245866537)
player_name = player_data['name']
guild_id = player_data['guildId']
guild = comlink.get_guild(guild_id)
guild_name = guild['profile']['name']
```

Usage example with non-default settings for a swgoh-comlink service running on the local machine at TCP port 3500 and
swgoh-stats service running on the local machine at TCP port 3550:

```python
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(url='http://localhost:3500', stats_url='http://localhost:3550')
player_data = comlink.get_player(245866537)
player_roster = player_data['rosterUnit']
roster_with_stats = comlink.get_unit_stats(player_roster)
```

Usage example with MHAC enabled:

```python
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(
    url='http://localhost:3000',
    access_key='public_key',
    secret_key='this_string_should_be_secret'
)
player_data = comlink.get_player(allycode=245866537)
player_name = player_data['name']
```

## Class Methods

A complete list of available class methods can be found [here](SwgohComlink_class.md)

## Examples

Please see the [Examples](https://github.com/swgoh-utils/swgoh-comlink/examples/SwgohComlink) folder for more detailed
code examples.

## Support

Issues can be reported in [GitHub](https://github.com/swgoh-utils/comlink-python/issues).

Join the [discord server](https://discord.gg/6PBfG5MzR3)
