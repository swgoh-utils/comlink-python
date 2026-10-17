# Typed clients

`swgoh_comlink.typed` has the same two clients as the top-level package, with
the same constructor arguments, methods and retry behaviour. The difference is
the return type of four endpoints:

| Method | `swgoh_comlink.SwgohComlink` | `swgoh_comlink.typed.SwgohComlink` |
|---|---|---|
| `get_player` | `dict` | `Player` |
| `get_guild` | `dict` | `Guild` |
| `get_game_metadata` | `dict` | `Metadata` |
| `get_leaderboard` | `dict` | `LeaderboardResponse` |

The typed results are [`msgspec.Struct`](https://jcristharif.com/msgspec/structs.html)
objects. Their fields are the wire's camelCase names in snake_case
(`player.guild_id` for `guildId`). Every other endpoint returns a `dict` on both
surfaces.

```python
from swgoh_comlink.typed import SwgohComlink

with SwgohComlink() as comlink:
    player = comlink.get_player(allycode=245866537)
    print(player.name, len(player.roster_unit))
```

## The `raw=True` escape hatch

Pass `raw=True` to any of the four methods to get the v2 dict for that call
instead of a Struct. The dict-default clients accept the same keyword and
ignore it, so code that passes it works with either import.

```python
player = comlink.get_player(allycode=245866537, raw=True)
print(player["name"])
```

StatCalc takes the typed results as they are: `calc_player_stats()` accepts a
`Player`, and `calc_roster_stats()` accepts its `roster_unit` list. See the
[typed StatCalc recipe](../v3/recipes/typed-statcalc.md) and the
[v2 → v3 migration guide](../v3/migration.md) for more.

## API Reference

::: swgoh_comlink.typed.SwgohComlink
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false
      members:
        - get_player
        - get_guild
        - get_game_metadata
        - get_leaderboard

::: swgoh_comlink.typed.SwgohComlinkAsync
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false
      members:
        - get_player
        - get_guild
        - get_game_metadata
        - get_leaderboard
