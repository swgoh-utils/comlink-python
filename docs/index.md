# SwgohComlink

This project provides:

- `SwgohComlink` for synchronous network calls to a running `swgoh-comlink` service.
- `SwgohComlinkAsync` for asynchronous (`async`/`await`) network calls to the same service.
- [Typed clients](api/typed.md) in `swgoh_comlink.typed`, which return `msgspec.Struct` models (`Player`, `Guild`, …) instead of dicts, with `raw=True` for the v2 dict on any call.
- `RetryPolicy` for opt-in retries of rate refusals and HTTP 503, and pacing of calls (see [Retries and Pacing](api/comlink.md#retries-and-pacing)).
- `StatCalc` / `StatCalcAsync` for local stat and GP calculation for game units.
- `GameDataBuilder` / `GameDataBuilderAsync` for building StatCalc game data dynamically from Comlink.
- [Helpers](api/helpers.md) — utility functions, constants, localization parsing, and data structures for working with game data.
- [Exceptions](api/exceptions.md) — custom exception hierarchy (`SwgohComlinkException`, `SwgohComlinkValueError`, `SwgohComlinkTypeError`, and the `SwgohComlinkHTTPError` family for HTTP error statuses) for error handling.

Both `SwgohComlink` and `SwgohComlinkAsync` share the same constructor parameters and public methods. The async client uses `await` for all requests and should be used inside an `async with` context manager.

For runnable code samples covering common tasks, see the [Examples](examples.md) page.
Coming from v2? The default import still returns dicts; see
[Migrating from v2 to v3](v3/migration.md) for what changed and the
[v3 alpha install guide](v3/install-alpha.md) for how to install it.

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

async with SwgohComlinkAsync(host="127.0.0.1", port=3000) as comlink:
    calc = await StatCalcAsync.create()
    player = await comlink.get_player(allycode=245866537)
```

## Choosing a Stats Method

`SwgohComlink.get_unit_stats()` and `StatCalc.calc_player_stats()` are similar in outcome but different in execution model:

- `SwgohComlink.get_unit_stats()` calls an external `swgoh-stats` service over HTTP (`stats_url`). This legacy method relies on the use of a separate StatCalc Docker container.
- `StatCalc.calc_player_stats()` runs calculations locally in-process using Python game data. It does not require the separate StatCalc Docker container. This is the recommended method.

Use `get_unit_stats()` when you already operate against hosted comlink/stat services.
Use `StatCalc.calc_player_stats()` when you want local/offline control and no dependency on a separate stats container.

Both methods can be used in parallel, allowing for validation of results while migrating from the legacy approach to the native Python approach.
