# Examples for usage of comlink-python

## Description

This folder contains a collection of examples for common uses of the `comlink-python` interface wrapper for the `swgoh-comlink` API service.

## Structure

```
examples/
├── README.md                  # This file
├── Sync/                      # Synchronous dict client (SwgohComlink) — v2-stable
│   └── README.md
├── Async/                     # Asynchronous dict client (SwgohComlinkAsync) — v2-stable
│   └── README.md
└── typed/                     # Typed client (swgoh_comlink.typed) — v3 alpha
    ├── README.md
    ├── Sync/
    └── Async/
```

### [typed/](typed/) — v3 alpha

Examples using the **typed client** at `from swgoh_comlink.typed import …`.
Endpoint methods return `msgspec.Struct` instances with typed
attributes instead of `dict` values; v3-only ergonomics
(`healthcheck()`, `raw_request()`, bimorphic StatCalc,
`get_statcalc_game_data`) are demonstrated here.

Requires the v3.0.0a1 alpha — see the project [README "Alpha (v3)
install" section](../README.md#alpha-v3-install).

### [Sync/](Sync/) — v2 stable
Examples using `SwgohComlink` — the synchronous dict client. Simple blocking calls suitable for scripts and quick prototyping.

### [Async/](Async/) — v2 stable
Examples using `SwgohComlinkAsync` — the asynchronous dict client. Supports concurrent requests via `asyncio.gather()` and `asyncio.TaskGroup`. Includes advanced examples with CLI arguments, retry logic, and debug output.

## Usage

Each script contains inline comments and sample responses. See the README in each subdirectory for a full listing.


## Support

Issues can be reported in [GitHub](https://github.com/swgoh-utils/comlink-python/issues).
