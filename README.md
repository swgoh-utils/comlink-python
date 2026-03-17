# comlink-python

[![CI](https://github.com/swgoh-utils/comlink-python/actions/workflows/ci.yml/badge.svg)](https://github.com/swgoh-utils/comlink-python/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/swgoh-comlink.svg)](https://pypi.org/project/swgoh-comlink/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen.svg)](https://github.com/swgoh-utils/comlink-python)

## Description

A python wrapper for the [swgoh-comlink](https://github.com/swgoh-utils/swgoh-comlink) tool, plus an in-package local stat calculator (`StatCalc`).

Supports both **synchronous** and **asynchronous** usage via `SwgohComlink` and `SwgohComlinkAsync`.

**Requires Python 3.10 or higher.**

## Installation

Install from [PyPi package repository](https://pypi.org/project/swgoh-comlink/) using the following shell command.

```bash
uv pip install swgoh_comlink
```

## Synchronous Usage

Basic default usage:

```python
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink()
player_data = comlink.get_player(allycode=245866537)
player_name = player_data['name']
guild_id = player_data['guildId']
guild = comlink.get_guild(guild_id=guild_id)
guild_name = guild['profile']['name']
```

With a custom comlink URL:

```python
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(url='http://localhost:3500')
player_data = comlink.get_player(allycode=245866537)
```

With an external swgoh-stats service:

```python
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(url='http://localhost:3500', stats_url='http://localhost:3550')
player_data = comlink.get_player(allycode=245866537)
player_roster = player_data['rosterUnit']
roster_with_stats = comlink.get_unit_stats(player_roster)
```

With HMAC authentication:

```python
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(
    url='http://localhost:3000',
    access_key='public_key',
    secret_key='this_string_should_be_secret'
)
player_data = comlink.get_player(allycode=245866537)
```

As a context manager (auto-closes connections):

```python
from swgoh_comlink import SwgohComlink

with SwgohComlink() as comlink:
    player_data = comlink.get_player(allycode=245866537)
```

## Async Usage

The `SwgohComlinkAsync` class provides the same API with `async`/`await` support. All public methods have identical signatures to the sync client.

```python
from swgoh_comlink import SwgohComlinkAsync

async with SwgohComlinkAsync() as comlink:
    player_data = await comlink.get_player(allycode=245866537)
    player_name = player_data['name']
    guild_id = player_data['guildId']
    guild = await comlink.get_guild(guild_id=guild_id)
    guild_name = guild['profile']['name']
```

Without a context manager, call `aclose()` when done:

```python
comlink = SwgohComlinkAsync()
try:
    player_data = await comlink.get_player(allycode=245866537)
finally:
    await comlink.aclose()
```

Both clients accept the same constructor parameters and support connection pooling via persistent `httpx` clients.

## StatCalc / StatCalcAsync (Local Stat Calculator)

`StatCalc` and `StatCalcAsync` calculate unit stats and Galactic Power locally without requiring an external swgoh-stats service. `StatCalc` fetches game data synchronously on initialization; `StatCalcAsync` provides an async factory method (`await StatCalcAsync.create()`) for non-blocking initialization. Both accept pre-loaded data for offline use.

### Building game data from Comlink

Instead of fetching a static `gameData.json` from GitHub, you can build game data
dynamically from a running Comlink service using `GameDataBuilder` / `GameDataBuilderAsync`:

```python
from swgoh_comlink import SwgohComlink, StatCalc, GameDataBuilder

comlink = SwgohComlink()
game_data = GameDataBuilder(comlink).build()
calc = StatCalc(game_data=game_data)
```

Async:

```python
from swgoh_comlink import SwgohComlinkAsync, StatCalcAsync, GameDataBuilderAsync

async with SwgohComlinkAsync() as comlink:
    game_data = await GameDataBuilderAsync(comlink).build()
    calc = StatCalcAsync(game_data=game_data)
```

The builder fetches only the required game data collections in a single API call
and transforms them into the format `StatCalc` expects.

### Basic usage

```python
from swgoh_comlink import SwgohComlink, StatCalc

comlink = SwgohComlink()
calc = StatCalc()  # fetches latest game data from GitHub on init

# Calculate stats for a full player roster
player = comlink.get_player(allycode=245866537)
calc.calc_roster_stats(player['rosterUnit'])

# Or calculate stats for a single character
unit = {
    "defId": "BOSSK",
    "rarity": 7,
    "level": 85,
    "gear": 13,
    "equipped": [],
    "skills": [],
}
calc.calc_char_stats(unit)
print(unit["stats"])  # final stats, mods, and GP added in-place
print(unit["gp"])     # galactic power
```

### Offline / pre-loaded game data

```python
calc = StatCalc(game_data=my_game_data_dict)
```

### Async usage (`StatCalcAsync`)

`StatCalcAsync` provides an async factory method for fetching game data without blocking the event loop. All calculation methods are inherited from `StatCalc` and remain synchronous (they are pure computation).

```python
from swgoh_comlink import SwgohComlinkAsync, StatCalcAsync

async with SwgohComlinkAsync() as comlink:
    calc = await StatCalcAsync.create()  # fetches game data from GitHub async

    player = await comlink.get_player(allycode=245866537)
    calc.calc_roster_stats(player['rosterUnit'])
```

With pre-loaded game data (no async fetch needed):

```python
calc = StatCalcAsync(game_data=my_game_data_dict)
```

### StatCalc / StatCalcAsync Methods

| Method | Description |
|--------|-------------|
| `calc_char_stats(unit)` | Calculate stats and GP for a single character (modifies in-place) |
| `calc_ship_stats(unit, crew)` | Calculate stats and GP for a ship with its crew |
| `calc_roster_stats(units)` | Calculate stats for all units in a roster (list or dict) |
| `calc_player_stats(players)` | Calculate stats for one or more full player payloads |
| `calc_char_gp(char)` | Calculate GP for a character |
| `calc_ship_gp(ship, crew)` | Calculate GP for a ship |
| `set_game_data(game_data)` | Replace the game data used by the calculator |

## Parameters

Constructor parameters for `SwgohComlink` and `SwgohComlinkAsync`:

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

Methods available on both `SwgohComlink` and `SwgohComlinkAsync` (async methods use `await`):

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
| `get_name_spaces(only_compatible, enums)` | Get available namespaces |
| `get_segmented_content(content_name_space, accept_language, enums)` | Retrieve segmented content |

## Examples

The [`examples/`](examples/) directory contains runnable scripts for common tasks using both the sync and async clients.

### Synchronous ([`examples/Sync/`](examples/Sync/))

| Script | Description |
|--------|-------------|
| [`get_player.py`](examples/Sync/get_player.py) | Get a player's full profile including roster |
| [`get_guild.py`](examples/Sync/get_guild.py) | Look up guild info from a player's ally code |
| [`get_events.py`](examples/Sync/get_events.py) | Retrieve current game events with timestamps |
| [`get_game_data.py`](examples/Sync/get_game_data.py) | Retrieve game data collections |
| [`get_gac_leaderboard.py`](examples/Sync/get_gac_leaderboard.py) | Get GAC leaderboard data |
| [`get_gac_brackets.py`](examples/Sync/get_gac_brackets.py) | Scan GAC brackets and search for a player |
| [`calc_stats_local.py`](examples/Sync/calc_stats_local.py) | Calculate character stats locally with `StatCalc` |
| [`search_for_guilds.py`](examples/Sync/search_for_guilds.py) | Search for guilds by name or criteria |

### Asynchronous ([`examples/Async/`](examples/Async/))

| Script | Description |
|--------|-------------|
| [`get_player.py`](examples/Async/get_player.py) | Get a player's full profile using `await` |
| [`concurrent_requests.py`](examples/Async/concurrent_requests.py) | Fetch multiple players in parallel with `asyncio.gather()` |
| [`streaming_guild_roster.py`](examples/Async/streaming_guild_roster.py) | Fetch all guild members concurrently with `asyncio.TaskGroup` |
| [`streaming_guild_roster_advanced.py`](examples/Async/streaming_guild_roster_advanced.py) | Production-quality guild roster fetch with CLI args and retry logic |
| [`calc_stats_local.py`](examples/Async/calc_stats_local.py) | Calculate character stats locally with `StatCalcAsync` |

See the [full examples listing](examples/README.md) for all available scripts and usage details.

## Logging

Logging is handled by the [python logging module](https://docs.python.org/3/library/logging.html). The library follows Python best practice by attaching only a `NullHandler` — no output is produced unless your application configures logging.

For details on enabling and customizing log output, see [docs/logging.md](docs/logging.md).

## Migrating from v1.x

This release replaces `requests` with `httpx` and changes how logging is configured. If you are upgrading from a previous version, see the [Migration Guide](docs/migration.md) for a walkthrough of required changes:

- Replace `requests` with `httpx` in your dependencies
- Update `except requests.RequestException` to `except httpx.RequestError` (or catch `SwgohComlinkException`)
- Update any `get_logger(log_level=...)` calls — configure logging via the standard `logging` module instead
- Use a context manager (`with SwgohComlink() ...`) or call `close()` to release connections

## Test Configuration

Integration tests are opt-in and require a running comlink service:

```bash
# Run integration tests (requires comlink on localhost:3000)
RUN_INTEGRATION_TESTS=1 uv run pytest tests/integration/ -v

# Run with HMAC tests (requires comlink-hmac on localhost:3001)
HMAC_ACCESS_KEY=your_key HMAC_SECRET_KEY=your_secret \
  RUN_INTEGRATION_TESTS=1 uv run pytest tests/integration/ -v
```

HMAC tests are automatically skipped when `HMAC_ACCESS_KEY` and `HMAC_SECRET_KEY` environment variables are not set.

See the online [wiki](https://github.com/swgoh-utils/swgoh-comlink/wiki) for more information.

## Support

Issues can be reported in [GitHub](https://github.com/swgoh-utils/comlink-python/issues).

Join the [discord server](https://discord.gg/6PBfG5MzR3)
