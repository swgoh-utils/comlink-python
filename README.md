# comlink-python

[![CI](https://github.com/swgoh-utils/comlink-python/actions/workflows/ci.yml/badge.svg)](https://github.com/swgoh-utils/comlink-python/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/swgoh-comlink.svg)](https://pypi.org/project/swgoh-comlink/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Description

A python wrapper for the [swgoh-comlink](https://github.com/swgoh-utils/swgoh-comlink) tool.

**Requires Python 3.10 or higher.**

## Installation

Install from [PyPi package repository](https://pypi.org/project/swgoh-comlink/) using the following shell command.

```bash
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

Usage example with HMAC enabled:

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

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | `http://localhost:3000` | URL where swgoh-comlink is running |
| `stats_url` | `str` | `http://localhost:3223` | URL where swgoh-stats service is running |
| `access_key` | `str` | `None` | HMAC public key. Also reads from `ACCESS_KEY` env var |
| `secret_key` | `str` | `None` | HMAC private key. Also reads from `SECRET_KEY` env var |
| `host` | `str` | `None` | Server hostname (overrides `url` and `stats_url`) |
| `port` | `int` | `3000` | Comlink TCP port (used with `host`) |
| `stats_port` | `int` | `3223` | Stats service TCP port (used with `host`) |
| `verify_ssl` | `bool` | `True` | Enable TLS certificate verification |

## Available Methods

| Method | Description |
|--------|-------------|
| `get_player(allycode, player_id, enums)` | Get player data by allycode or player ID |
| `get_player_arena(allycode, player_id, player_details_only, enums)` | Get player arena profile |
| `get_guild(guild_id, include_recent_guild_activity_info, enums)` | Get guild data by guild ID |
| `get_guilds_by_name(name, start_index, count, enums)` | Search guilds by name |
| `get_guilds_by_criteria(search_criteria, start_index, count, enums)` | Search guilds by criteria |
| `get_game_data(version, include_pve_units, request_segment, enums)` | Get game data collections |
| `get_game_metadata(client_specs, enums)` | Get current game and localization versions |
| `get_localization(localization_id, locale, unzip, enums)` | Get localization bundles |
| `get_enums()` | Get game data enums |
| `get_events(enums)` | Get current game events |
| `get_leaderboard(leaderboard_type, league, division, ...)` | Get GAC leaderboard data |
| `get_guild_leaderboard(leaderboard_id, count, enums)` | Get guild leaderboard data |
| `get_unit_stats(request_payload, flags, language)` | Calculate unit stats via swgoh-stats |
| `get_latest_game_data_version()` | Get latest game data and language versions |

## Logging

Logging is handled by the [python logging module](https://docs.python.org/3/library/logging.html). For details on the
logging implementation for this package, go [here](docs/logging.md).

See the online [wiki](https://github.com/swgoh-utils/swgoh-comlink/wiki) for more information.

## Support

Issues can be reported in [GitHub](https://github.com/swgoh-utils/comlink-python/issues).

Join the [discord server](https://discord.gg/6PBfG5MzR3)
