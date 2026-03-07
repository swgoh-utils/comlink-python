# SwgohComlink

This project provides:

- `SwgohComlink` for synchronous network calls to a running `swgoh-comlink` service.
- `SwgohComlinkAsync` for asynchronous (`async`/`await`) network calls to the same service.
- `StatCalc` / `StatCalcAsync` for local stat and GP calculation for game units.

Both `SwgohComlink` and `SwgohComlinkAsync` share the same constructor parameters and public methods. The async client uses `await` for all requests and should be used inside an `async with` context manager.

Similarly, `StatCalcAsync` provides an async factory method for non-blocking game data initialization, while inheriting all calculation methods from `StatCalc`.

## Quick Start

Synchronous:

```python
from swgoh_comlink import SwgohComlink, StatCalc

comlink = SwgohComlink(url="http://localhost:3000")
calc = StatCalc()
```

Asynchronous:

```python
from swgoh_comlink import SwgohComlinkAsync, StatCalcAsync

async with SwgohComlinkAsync() as comlink:
    calc = await StatCalcAsync.create()
    player = await comlink.get_player(allycode=245866537)
```

## Choosing a Stats Method

`SwgohComlink.get_unit_stats()` and `StatCalc.calc_player_stats()` are similar in outcome but different in execution model:

- `SwgohComlink.get_unit_stats()` calls an external `swgoh-stats` service over HTTP (`stats_url`).
- `StatCalc.calc_player_stats()` runs calculations locally in-process using Python game data.

Use `get_unit_stats()` when you already operate against hosted comlink/stat services.
Use `StatCalc.calc_player_stats()` when you want local/offline control and no dependency on a separate stats container.
