# Examples for usage of comlink-python

## Description

This folder contains a collection of examples for common uses of the comlink-python interface wrapper for swgoh-comlink.

## Structure

```
examples/
├── README.md                  # This file
├── Sync/                      # Synchronous client examples (SwgohComlink)
│   └── README.md
└── Async/                     # Asynchronous client examples (SwgohComlinkAsync)
    └── README.md
```

### [Sync/](Sync/)
Examples using `SwgohComlink` — the synchronous client. Simple blocking calls suitable for scripts and quick prototyping.

### [Async/](Async/)
Examples using `SwgohComlinkAsync` — the asynchronous client. Supports concurrent requests via `asyncio.gather()` and `asyncio.TaskGroup`. Includes advanced examples with CLI arguments, retry logic, and debug output.

## Usage

Each script contains inline comments and sample responses. See the README in each subdirectory for a full listing.

See the online [wiki](https://github.com/swgoh-utils/swgoh-comlink/wiki) for more information.

## Support

Issues can be reported in [GitHub](https://github.com/swgoh-utils/comlink-python/issues).
