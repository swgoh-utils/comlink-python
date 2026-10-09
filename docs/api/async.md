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

## Retries and Pacing

The `retry` argument takes the same [`RetryPolicy`](comlink.md#retries-and-pacing)
as the synchronous client. Waits use `asyncio.sleep`, so they do not block the
event loop. Pacing and the hold after a rate refusal apply across concurrent
tasks on one client, and the tasks start in the order they asked. A task
cancelled while it waits gives its slot back, so cancelling a batch does not
delay the calls that follow it:

```python
import asyncio

from swgoh_comlink import RetryPolicy, SwgohComlinkAsync

async with SwgohComlinkAsync(retry=RetryPolicy(min_interval=0.4)) as comlink:
    players = await asyncio.gather(*(comlink.get_player(allycode=code) for code in allycodes))
```

Failed calls raise the same [typed HTTP errors](exceptions.md#http-errors) as
the synchronous client.

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
