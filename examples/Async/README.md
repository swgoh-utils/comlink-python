# Asynchronous Examples

These examples use the `SwgohComlinkAsync` async client. All methods must be `await`ed and the client should be used as an async context manager for proper connection cleanup.

## Examples

| File | Description |
|------|-------------|
| `calc_stats_local.py` | Calculate character stats locally using `StatCalcAsync` |
| `get_events.py` | Retrieve current game events with timestamps and status |
| `get_gac_brackets.py` | Scan GAC brackets for a league and search for a player (parallel batches) |
| `get_gac_leaderboard.py` | Get GAC bracket or league/division leaderboards |
| `get_game_data.py` | Retrieve game data collections (all, by segment, or by name) |
| `get_guild.py` | Look up guild info from a player's ally code |
| `get_guild_leaderboard.py` | Get guild-level leaderboards (TW, raids, GP, TB) |
| `get_language_bundle.py` | Retrieve and parse a specific language bundle |
| `get_latest_game_data_version.py` | Get current game data and language version strings |
| `get_location_bundle.py` | Retrieve the full localization bundle (zipped or unzipped) |
| `get_player.py` | Get a player's full profile including roster |
| `get_player_arena_profile.py` | Get a player's arena/PvP profile |
| `search_for_guilds.py` | Search for guilds by name or criteria |
| `concurrent_requests.py` | Fetch multiple players in parallel with `asyncio.gather()` |
| `streaming_guild_roster.py` | Fetch all guild members concurrently with `asyncio.TaskGroup` |
| `streaming_guild_roster_advanced.py` | Production-quality guild roster fetch with CLI args, retry logic, and debug output |

## Requirements

- Python 3.10+ for the basic async examples
- Python 3.11+ for examples using `asyncio.TaskGroup` (`streaming_guild_roster*.py`)

## Usage

```python
import asyncio
from swgoh_comlink import SwgohComlinkAsync

async def main():
    async with SwgohComlinkAsync() as comlink:
        player = await comlink.get_player(allycode=314927874)

asyncio.run(main())
```

## Advanced Example

The `streaming_guild_roster_advanced.py` script accepts command-line arguments:

```bash
# Fetch by ally code with verbose timing
python streaming_guild_roster_advanced.py 314927874 -v

# Fetch by guild ID with debug output and 5 retries
python streaming_guild_roster_advanced.py <guild_id> -d -r 5

# Specify a remote Comlink host
python streaming_guild_roster_advanced.py 314927874 --host 192.168.1.100 --port 3200
```

See each file for detailed comments and sample output.
