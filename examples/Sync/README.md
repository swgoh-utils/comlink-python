# Synchronous Examples

These examples use the `SwgohComlink` synchronous client. They run in a standard blocking fashion and are the simplest way to get started.

## Examples

| File | Description |
|------|-------------|
| `calc_stats_local.py` | Calculate character stats locally using the `StatCalc` module |
| `get_events.py` | Retrieve current game events with timestamps and status |
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

## Usage

```python
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink()
player = comlink.get_player(allycode=314927874)
```

See each file for detailed comments and sample output.
