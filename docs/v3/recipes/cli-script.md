# Short-lived CLI script

A one-shot script invoked from a shell pipeline or `argparse` CLI. Cold
import time matters; nothing else.

## The numbers that justify this recipe

* **v2 `import swgoh_comlink`**: ~65 ms (drags httpx, msgspec, StatCalc, helpers).
* **v3 `import swgoh_comlink`**: ~7 ms (PEP 562 lazy `__getattr__`).

For a script that runs in 100 ms total, a 60 ms import cost was a
non-trivial fraction. v3 makes the import effectively free for scripts
that don't use the full SDK surface.

## Setup

```python
#!/usr/bin/env python3
"""Print a player's roster size from the command line."""
from __future__ import annotations
import sys
from swgoh_comlink.typed import SwgohComlink  # typed surface: get_player returns a Player Struct

def main() -> int:
    allycode = int(sys.argv[1])
    with SwgohComlink(url="http://comlink.local:3000") as client:
        # No retry= argument: the default is one attempt and no waiting, so a
        # one-shot script fails fast (don't burn 30 seconds on a transient failure)
        try:
            player = client.get_player(allycode=allycode)
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        print(f"{player.name}: {len(player.roster_unit)} units")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## What you can skip

* **No `[cache]`** — the cache is only valuable across calls; a
  single-shot script doesn't benefit.
* **No `profile="bot"` / `"bulk"`** — default pool is fine for one call.
* **No `healthcheck()`** — if comlink is down, the actual call fails
  fast (the default is one attempt, no retries). A separate probe just doubles your
  latency.

## What v3 gives you for free

* `~7 ms` cold import (vs `~65 ms` in v2). Anything else in your script
  dominates the wall time.
* Typed return — `player.name`, `len(player.roster_unit)` work without
  type-narrowing dance.
* Retries are opt-in (`retry=RetryPolicy(...)`), so this script fails fast by
  default. Add a policy only if you expect to hit rate refusals.

## When to add complexity back

* You start making `/data` calls (one cache call across the per-invoke
  lifetime gives you nothing; `/data` over the wire is ~3-7s). Switch
  to a long-running pattern.
* Your script runs as part of a deployment with strict timeouts. Add
  `healthcheck(timeout=1.0)` if you'd rather fail before the
  comlink call than during it.
