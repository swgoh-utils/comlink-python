# Long-running bot

A bot that lives for the process lifetime, makes many calls per minute,
and needs to survive transient comlink hiccups. The v3 features that
matter here are: `profile="bot"`, retries on by default, `healthcheck`
for startup, and `GameDataCache` for `/data`/`/localization`.

## Setup

```python
from swgoh_comlink import SwgohComlink
from swgoh_comlink._cache import GameDataCache  # requires [cache] extra

client = SwgohComlink(
    url="http://comlink.local:3000",
    profile="bot",          # keepalive 120s, larger pool
    max_retries=3,           # default; 1 + 3 retries on transient errors
)

# Startup probe — fail fast if comlink is down
if not client.healthcheck(timeout=5.0):
    raise SystemExit("comlink unreachable; check the service")

cache = GameDataCache()  # XDG default: ~/Library/Caches/swgoh-comlink/ (macOS)
```

## Per-tick loop

```python
while True:
    # /data + /localization come from the cache; first call per process
    # hits the wire, every later call within the same process is a
    # microsecond-scale dict lookup.
    game_data = cache.get_game_data(client)
    loc = cache.get_localization(client, locale="ENG_US")

    # /player is uncached (the data changes per call by design)
    for ally in tracked_allies:
        try:
            player = client.get_player(allycode=ally)
        except SwgohComlinkException:
            # Already retried 3 times under the hood; just log and skip
            log.exception("get_player failed for %s", ally)
            continue
        process(player, game_data)  # attribute access throughout

    time.sleep(60)
```

## Operational notes

* **Cache instance lifetime.** Keep ONE `GameDataCache` for the process
  lifetime. The in-memory memo only benefits same-instance calls.
* **Cache eviction.** Call `cache.evict_old_versions(cache.current_version(client))`
  on a schedule (e.g. daily) to clean up stale game-data versions.
  Diskcache won't grow unbounded — the `_inmem` dict resets after each
  evict.
* **Retry envelopes.** Default 3 retries with full-jitter exponential
  backoff. `Retry-After` headers are honored on 429. A 4-attempt total
  failure raises `SwgohComlinkException` after ~30s in the worst case.
  Adjust with `client.with_options(max_retries=5)` if your operator
  network is flaky.
* **Connection pool.** `profile="bot"` is tuned for low-frequency,
  long-lived patterns: `keepalive_expiry=120s`, `max_connections=200`,
  `max_keepalive_connections=50`. Default would also work; this preset
  is marginally better when you're calling every minute or two and
  TCP/TLS handshakes start to matter.

## What's NOT here

* **Rate limiting.** `[ratelimit]` is deferred to v3.1 (ADR-0004). Until
  then, see [operator-side-concurrency.md](operator-side-concurrency.md)
  for the `asyncio.Semaphore` pattern.
* **Circuit breaker.** Same deferral. If you want to stop hammering
  comlink after N consecutive failures, the operator code wraps the
  loop with a simple counter today.
