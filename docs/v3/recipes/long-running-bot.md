# Long-running bot

A bot that lives for the process lifetime, makes many calls per minute,
and needs to survive transient comlink hiccups. The v3 features that
matter here are: `profile="bot"`, an opt-in `RetryPolicy`, `healthcheck`
for startup, and `GameDataCache` for `/data`/`/localization`.

## Setup

```python
from swgoh_comlink import RetryPolicy
from swgoh_comlink._cache import GameDataCache  # requires [cache] extra
from swgoh_comlink.exceptions import SwgohComlinkException
from swgoh_comlink.typed import SwgohComlink  # Struct returns

client = SwgohComlink(
    url="http://comlink.local:3000",
    profile="bot",          # keepalive 120s, larger pool
    # Opt-in (default None = one attempt): retry rate refusals and HTTP 503,
    # honour Retry-After, and space calls to one endpoint at least 0.4 s apart.
    retry=RetryPolicy(attempts=5, min_interval=0.4),
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
            # Rate refusals / 503 were already retried per the RetryPolicy;
            # just log and skip
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
* **Retry policy.** Retries are opt-in. With `RetryPolicy(attempts=5)`
  a rate refusal (HTTP 429 / `Rate exceeded!`) or HTTP 503 is retried,
  waiting for `Retry-After` (capped at `max_retry_after`) or the next
  `backoff` step (5, 10, 20, 40 s) plus jitter. Any other error is
  raised at once as a typed `SwgohComlinkHTTPError`. A rate refusal also
  holds back that endpoint on the whole client, so concurrent tasks back
  off together. Adjust per call site with
  `client.with_options(retry=RetryPolicy(attempts=8))`. See
  [Retries and pacing](../../api/comlink.md#retries-and-pacing).
* **Connection pool.** `profile="bot"` is tuned for low-frequency,
  long-lived patterns: `keepalive_expiry=120s`, `max_connections=200`,
  `max_keepalive_connections=50`. Default would also work; this preset
  is marginally better when you're calling every minute or two and
  TCP/TLS handshakes start to matter.

## Async variant (`SwgohComlinkAsync` + async cache)

Same pattern, different surface. `GameDataCache` exposes `a*` twins of
every client-touching method and an `async with` lifecycle. The disk
store and in-memory memo are shared with the sync surface, so a sync
warmup script can populate the cache an async bot reads.

```python
import asyncio
from swgoh_comlink import RetryPolicy
from swgoh_comlink._cache import GameDataCache
from swgoh_comlink.typed import SwgohComlinkAsync

async def main():
    async with (
        SwgohComlinkAsync(
            url="http://comlink.local:3000",
            profile="bot",
            retry=RetryPolicy(attempts=5, min_interval=0.4),
        ) as client,
        GameDataCache() as cache,
    ):
        if not await client.healthcheck(timeout=5.0):
            raise SystemExit("comlink unreachable")

        while True:
            game_data = await cache.aget_game_data(client)
            loc = await cache.aget_localization(client, locale="ENG_US")

            tasks = [client.get_player(allycode=a) for a in tracked_allies]
            for player in await asyncio.gather(*tasks, return_exceptions=True):
                if isinstance(player, Exception):
                    log.exception("get_player failed: %s", player)
                    continue
                process(player, game_data)

            await asyncio.sleep(60)

asyncio.run(main())
```

Internals: `aget_game_data` / `aget_localization` / `acurrent_version`
/ `aevict_old_versions` / `aclose` wrap the blocking diskcache and
msgpack operations in `asyncio.to_thread`, so the event loop stays
responsive on cold and disk-warm paths. In-memory hits stay
synchronous (nanosecond-scale dict access).

## What's NOT here

* **Rate limiting.** `[ratelimit]` is deferred to v3.1 (ADR-0004). Until
  then, see [operator-side-concurrency.md](operator-side-concurrency.md)
  for the `asyncio.Semaphore` pattern.
* **Circuit breaker.** Same deferral. If you want to stop hammering
  comlink after N consecutive failures, the operator code wraps the
  loop with a simple counter today.
