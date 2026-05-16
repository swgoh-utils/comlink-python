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
from swgoh_comlink import SwgohComlink  # ← 7 ms total to import the SDK

def main() -> int:
    allycode = int(sys.argv[1])
    with SwgohComlink(url="http://comlink.local:3000", max_retries=0) as client:
        # max_retries=0: fail fast for one-shot scripts (don't burn
        # 30 seconds on a transient failure)
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
  fast (with `max_retries=0`). A separate probe just doubles your
  latency.

## What v3 gives you for free

* `~7 ms` cold import (vs `~65 ms` in v2). Anything else in your script
  dominates the wall time.
* Typed return — `player.name`, `len(player.roster_unit)` work without
  type-narrowing dance.
* `max_retries=0` is one kwarg; v2 had no equivalent.

## When to add complexity back

* You start making `/data` calls (one cache call across the per-invoke
  lifetime gives you nothing; `/data` over the wire is ~3-7s). Switch
  to a long-running pattern.
* Your script runs as part of a deployment with strict timeouts. Add
  `healthcheck(timeout=1.0)` if you'd rather fail before the
  comlink call than during it.
