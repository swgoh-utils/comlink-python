# Operator-side concurrency control (in lieu of `[ratelimit]`)

v3.0 does NOT ship `[ratelimit]` — that extra is deferred to v3.1
([ADR-0004](../../adr/0004-defer-ratelimit-circuitbreaker-to-v3-1.md)).
This recipe covers the patterns that get you 80% of the value with
zero v3.0 dependencies.

## When you need it

* Calling comlink from a bot that fans out across many players (e.g.
  guild-wide /player pulls).
* Comlink's documented limits: ~80 req/s on `/player`, ~18 req/s on
  most other endpoints.
* Hitting the limit returns HTTP 429 with `Retry-After` — v3 honors
  the header automatically, but you'd rather not be relying on retry
  for normal traffic.

## Pattern 1: `asyncio.Semaphore`

```python
import asyncio
from swgoh_comlink import SwgohComlinkAsync

async def fetch_many(allies: list[int]) -> list:
    async with SwgohComlinkAsync(url="http://comlink.local:3000") as client:
        # In-flight concurrency cap. 10 is a safe number under the
        # 80/s /player limit at typical latency (~50ms per call).
        sem = asyncio.Semaphore(10)

        async def one(ally: int):
            async with sem:
                return await client.get_player(allycode=ally)

        return await asyncio.gather(*(one(a) for a in allies))
```

## Pattern 2: token-bucket rate limiter (vendored)

If you want strict requests-per-second, hand-roll a small token bucket:

```python
import asyncio
import time

class TokenBucket:
    """Crude async token bucket. Drop-in replacement until v3.1 [ratelimit]."""

    def __init__(self, rate: float, capacity: int | None = None) -> None:
        self.rate = rate                           # tokens / second
        self.capacity = capacity or max(1, int(rate))
        self._tokens = float(self.capacity)
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        async with self._lock:
            now = time.monotonic()
            self._tokens = min(self.capacity, self._tokens + (now - self._last) * self.rate)
            self._last = now
            if self._tokens >= tokens:
                self._tokens -= tokens
                return
            need = tokens - self._tokens
            self._tokens = 0
        # Sleep OUTSIDE the lock so other tasks can refill.
        await asyncio.sleep(need / self.rate)

# Usage
player_bucket = TokenBucket(rate=80)   # 80/s for /player
generic_bucket = TokenBucket(rate=18)  # 18/s for everything else

async def safe_get_player(client, ally):
    await player_bucket.acquire()
    return await client.get_player(allycode=ally)
```

For sync code, swap `asyncio.Lock` → `threading.Lock`, `asyncio.sleep`
→ `time.sleep`.

## Pattern 3: circuit-breaker via failure counter

In lieu of `[circuitbreaker]`:

```python
class FailureCounter:
    """Stop sending requests after N consecutive failures, retry after cool-down."""

    def __init__(self, threshold: int = 5, cooldown_seconds: float = 30) -> None:
        self.threshold = threshold
        self.cooldown = cooldown_seconds
        self._fails = 0
        self._opened_at: float | None = None

    def allow(self) -> bool:
        if self._opened_at is None:
            return True
        if time.monotonic() - self._opened_at > self.cooldown:
            # Half-open: let one call through to probe
            self._opened_at = None
            self._fails = 0
            return True
        return False

    def succeeded(self) -> None:
        self._fails = 0
        self._opened_at = None

    def failed(self) -> None:
        self._fails += 1
        if self._fails >= self.threshold:
            self._opened_at = time.monotonic()


breaker = FailureCounter(threshold=5, cooldown_seconds=60)

def safely_get_player(client, ally):
    if not breaker.allow():
        raise RuntimeError("circuit open; skipping comlink call")
    try:
        p = client.get_player(allycode=ally)
        breaker.succeeded()
        return p
    except SwgohComlinkException:
        breaker.failed()
        raise
```

## When to migrate to `[ratelimit]` / `[circuitbreaker]`

When you have ≥2 production operators independently asking for the same
features, that's the signal to land v3.1's `[ratelimit]` + `[circuitbreaker]`
extras (which would wrap `aiometer`/`aiolimiter` and `purgatory` respectively
behind the same install-hint pattern Phase 6 set up).
