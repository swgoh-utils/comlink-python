# comlink-python

## Description

A python wrapper for the [swgoh-comlink](https://github.com/swgoh-utils/swgoh-comlink) tool.

## Installation
Install from [PyPi package repository](https://pypi.org/project/swgoh-comlink/) using the following shell command.

```buildoutcfg
uv pip install swgoh_comlink
```

## Usage

Basic default usage example:

```python
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink()
player_data = comlink.get_player(allycode=245866537)
player_name = player_data['name']
guild_id = player_data['guildId']
guild = comlink.get_guild(guild_id=guild_id)
guild_name = guild['profile']['name']
```

Usage example with non-default settings for a swgoh-comlink service running on the local machine at TCP port 3500:

```python
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(url='http://localhost:3500')
player_data = comlink.get_player(allycode=245866537)
player_name = player_data['name']
guild_id = player_data['guildId']
guild = comlink.get_guild(guild_id=guild_id)
guild_name = guild['profile']['name']
```

Usage example with non-default settings for a swgoh-comlink service running on the local machine at TCP port 3500 and swgoh-stats service running on the local machine at TCP port 3550:

```python
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(url='http://localhost:3500', stats_url='http://localhost:3550')
player_data = comlink.get_player(allycode=245866537)
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

# Parameters

- **_url_**: the URL where the swgoh-comlink service is running. Defaults to `http://localhost:3000`
- **_access_key_**: The "public" portion of the shared key used in HMAC request signing. Defaults to `None` which disables HMAC signing of requests. Can also be read from the ACCESS_KEY environment variable.
- **_secret_key_**: The "private" portion of the key used in HMAC request signing. Defaults to `None` which disables HMAC signing of requests. Can also be read from the SECRET_KEY environment variable.

# Logging

Logging is handled by the [python logging module](https://docs.python.org/3/library/logging.html). For details on the
logging implementation for this package, go [here](docs/logging.md).

See the online [wiki](https://github.com/swgoh-utils/swgoh-comlink/wiki) for more information.

## Support

Issues can be reported in [GitHub](https://github.com/swgoh-utils/comlink-python/issues).

Join the [discord server](https://discord.gg/6PBfG5MzR3)
