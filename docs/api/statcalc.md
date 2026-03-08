# StatCalc / StatCalcAsync API

`StatCalc` and `StatCalcAsync` perform local stat and Galactic Power (GP)
calculations for game units without requiring an external `swgoh-stats` service.

## Quick Start

```python
from swgoh_comlink import SwgohComlink, StatCalc

comlink = SwgohComlink()
calc = StatCalc()  # fetches game data from GitHub on init

player = comlink.get_player(allycode=245866537)
calc.calc_roster_stats(player["rosterUnit"])

# Each unit in rosterUnit now has "stats" and "gp" keys
for unit in player["rosterUnit"]:
    print(unit.get("stats"), unit.get("gp"))
```

## Initialization

```python
# Default — fetches latest game data from GitHub
calc = StatCalc()

# Offline — supply pre-loaded game data
calc = StatCalc(game_data=my_game_data_dict)
```

The `game_data` parameter accepts the JSON payload from the
[swgoh-utils/gamedata](https://github.com/swgoh-utils/gamedata) repository.

## Usage Examples

### Calculate stats for a single character

```python
unit = {
    "defId": "BOSSK",
    "rarity": 7,
    "level": 85,
    "gear": 13,
    "equipped": [],
    "skills": [],
}
calc.calc_char_stats(unit)
print(unit["stats"])  # base, mods, and gear stats
print(unit["gp"])     # galactic power
```

### Calculate stats for a full roster

```python
player = comlink.get_player(allycode=245866537)
calc.calc_roster_stats(player["rosterUnit"])
```

Characters are processed first, then ships (which depend on their crew stats).

### Calculate stats for one or more players

```python
# Single player dict
player = comlink.get_player(allycode=245866537)
calc.calc_player_stats(player)

# List of player dicts
players = [
    comlink.get_player(allycode=245866537),
    comlink.get_player(allycode=123456789),
]
calc.calc_player_stats(players)
```

### Calculate GP only

```python
gp = calc.calc_char_gp(unit)
ship_gp = calc.calc_ship_gp(ship_unit, crew_list)
```

## Async Usage (`StatCalcAsync`)

`StatCalcAsync` inherits all calculation methods from `StatCalc`. The only
difference is initialization: use the async `create()` factory to fetch game
data without blocking the event loop.

```python
from swgoh_comlink import SwgohComlinkAsync, StatCalcAsync

async with SwgohComlinkAsync() as comlink:
    calc = await StatCalcAsync.create()  # async fetch from GitHub

    player = await comlink.get_player(allycode=245866537)
    calc.calc_roster_stats(player["rosterUnit"])
```

With pre-loaded data (no async fetch):

```python
calc = StatCalcAsync(game_data=my_game_data_dict)
```

## GameDataBuilder / GameDataBuilderAsync

Instead of fetching game data from a static GitHub file, you can build it
dynamically from a running Comlink service.

### Sync

```python
from swgoh_comlink import SwgohComlink, StatCalc, GameDataBuilder

comlink = SwgohComlink()
game_data = GameDataBuilder(comlink).build()
calc = StatCalc(game_data=game_data)
```

### Async

```python
from swgoh_comlink import SwgohComlinkAsync, StatCalcAsync, GameDataBuilderAsync

async with SwgohComlinkAsync() as comlink:
    game_data = await GameDataBuilderAsync(comlink).build()
    calc = StatCalcAsync(game_data=game_data)
```

The builder fetches only the collections required for stat calculation
(`units`, `skills`, `equipment`, `tables`, `statProgression`, `statModSets`,
`relicTierDefinitions`, `categories`) in a single `get_game_data()` call and
transforms them into the dict format expected by `StatCalc.set_game_data()`.

## API Reference

### StatCalc

::: swgoh_comlink.StatCalc.calculator.StatCalc
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false
      members:
        - __init__
        - calc_char_stats
        - calc_ship_stats
        - calc_roster_stats
        - calc_player_stats
        - calc_char_gp
        - calc_ship_gp

### StatCalcAsync

::: swgoh_comlink.StatCalc.calculator_async.StatCalcAsync
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false
      members:
        - __init__
        - create

### GameDataBuilder

::: swgoh_comlink.StatCalc.data_builder.builder.GameDataBuilder
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false
      members:
        - __init__
        - build

### GameDataBuilderAsync

::: swgoh_comlink.StatCalc.data_builder.builder_async.GameDataBuilderAsync
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false
      members:
        - __init__
        - build
