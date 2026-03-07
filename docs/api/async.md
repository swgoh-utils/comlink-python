# SwgohComlinkAsync API

`SwgohComlinkAsync` provides the same API as `SwgohComlink` with `async`/`await` support.
All public methods have identical signatures — just add `await` to each call.

## Quick Start

```python
from swgoh_comlink import SwgohComlinkAsync

async with SwgohComlinkAsync() as comlink:
    player = await comlink.get_player(allycode=245866537)
    guild = await comlink.get_guild(guild_id=player["guildId"])
```

Without a context manager, call `aclose()` when done:

```python
comlink = SwgohComlinkAsync()
try:
    player = await comlink.get_player(allycode=245866537)
finally:
    await comlink.aclose()
```

## Async Stat Calculation

For local stat calculation in async code, use `StatCalcAsync` which fetches
game data without blocking the event loop:

```python
from swgoh_comlink import SwgohComlinkAsync, StatCalcAsync

async with SwgohComlinkAsync() as comlink:
    calc = await StatCalcAsync.create()
    player = await comlink.get_player(allycode=245866537)
    calc.calc_roster_stats(player["rosterUnit"])
```

See the [StatCalc API](statcalc.md) for full details.

## API Reference

::: swgoh_comlink.swgoh_comlink_async.SwgohComlinkAsync
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false
