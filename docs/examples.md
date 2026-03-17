# Examples

The [`examples/`](https://github.com/swgoh-utils/comlink-python/tree/main/examples) directory contains runnable scripts demonstrating common tasks with both the synchronous and asynchronous clients.

## Synchronous Examples

These examples use `SwgohComlink` — the synchronous client. Simple blocking calls suitable for scripts and quick prototyping.

| Script | Description |
|--------|-------------|
| [`get_player.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Sync/get_player.py) | Get a player's full profile including roster |
| [`get_player_arena_profile.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Sync/get_player_arena_profile.py) | Get a player's arena/PvP profile |
| [`get_guild.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Sync/get_guild.py) | Look up guild info from a player's ally code |
| [`get_events.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Sync/get_events.py) | Retrieve current game events with timestamps and status |
| [`get_game_data.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Sync/get_game_data.py) | Retrieve game data collections (all, by segment, or by name) |
| [`get_gac_leaderboard.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Sync/get_gac_leaderboard.py) | Get GAC bracket or league/division leaderboards |
| [`get_gac_brackets.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Sync/get_gac_brackets.py) | Scan GAC brackets for a league and search for a player |
| [`get_guild_leaderboard.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Sync/get_guild_leaderboard.py) | Get guild-level leaderboards (TW, raids, GP, TB) |
| [`get_language_bundle.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Sync/get_language_bundle.py) | Retrieve and parse a specific language bundle |
| [`get_location_bundle.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Sync/get_location_bundle.py) | Retrieve the full localization bundle (zipped or unzipped) |
| [`get_location_bundle_adv.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Sync/get_location_bundle_adv.py) | Advanced localization bundle retrieval |
| [`get_latest_game_data_version.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Sync/get_latest_game_data_version.py) | Get current game data and language version strings |
| [`search_for_guilds.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Sync/search_for_guilds.py) | Search for guilds by name or criteria |
| [`calc_stats_local.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Sync/calc_stats_local.py) | Calculate character stats locally using `StatCalc` |

### Quick start

```python
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink()
player = comlink.get_player(allycode=245866537)
```

## Asynchronous Examples

These examples use `SwgohComlinkAsync` — the asynchronous client. Supports concurrent requests via `asyncio.gather()` and `asyncio.TaskGroup`.

| Script | Description |
|--------|-------------|
| [`get_player.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Async/get_player.py) | Get a player's full profile including roster |
| [`get_player_arena_profile.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Async/get_player_arena_profile.py) | Get a player's arena/PvP profile |
| [`get_guild.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Async/get_guild.py) | Look up guild info from a player's ally code |
| [`get_events.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Async/get_events.py) | Retrieve current game events with timestamps and status |
| [`get_game_data.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Async/get_game_data.py) | Retrieve game data collections (all, by segment, or by name) |
| [`get_gac_leaderboard.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Async/get_gac_leaderboard.py) | Get GAC bracket or league/division leaderboards |
| [`get_gac_brackets.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Async/get_gac_brackets.py) | Scan GAC brackets for a league and search for a player (parallel batches) |
| [`get_guild_leaderboard.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Async/get_guild_leaderboard.py) | Get guild-level leaderboards (TW, raids, GP, TB) |
| [`get_language_bundle.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Async/get_language_bundle.py) | Retrieve and parse a specific language bundle |
| [`get_location_bundle.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Async/get_location_bundle.py) | Retrieve the full localization bundle (zipped or unzipped) |
| [`get_latest_game_data_version.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Async/get_latest_game_data_version.py) | Get current game data and language version strings |
| [`search_for_guilds.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Async/search_for_guilds.py) | Search for guilds by name or criteria |
| [`calc_stats_local.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Async/calc_stats_local.py) | Calculate character stats locally using `StatCalcAsync` |
| [`concurrent_requests.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Async/concurrent_requests.py) | Fetch multiple players in parallel with `asyncio.gather()` |
| [`streaming_guild_roster.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Async/streaming_guild_roster.py) | Fetch all guild members concurrently with `asyncio.TaskGroup` |
| [`streaming_guild_roster_advanced.py`](https://github.com/swgoh-utils/comlink-python/blob/main/examples/Async/streaming_guild_roster_advanced.py) | Production-quality guild roster fetch with CLI args, retry logic, and debug output |

### Quick start

```python
import asyncio
from swgoh_comlink import SwgohComlinkAsync

async def main():
    async with SwgohComlinkAsync() as comlink:
        player = await comlink.get_player(allycode=245866537)

asyncio.run(main())
```

### Advanced CLI example

The `streaming_guild_roster_advanced.py` script accepts command-line arguments:

```bash
# Fetch by ally code with verbose timing
python streaming_guild_roster_advanced.py 314927874 -v

# Fetch by guild ID with debug output and 5 retries
python streaming_guild_roster_advanced.py <guild_id> -d -r 5

# Specify a remote Comlink host
python streaming_guild_roster_advanced.py 314927874 --host 192.168.1.100 --port 3200
```

!!! note
    Examples using `asyncio.TaskGroup` (`streaming_guild_roster*.py`) require Python 3.11+.
