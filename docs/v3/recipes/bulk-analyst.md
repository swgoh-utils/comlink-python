# Bulk analyst

A short-lived script that pulls a lot of players, runs analysis, writes
a report, exits. Different needs from a long-running bot: pool sized
for concurrency, no need for a persistent cache (the data is consumed
once), `[pydantic]` for the report's typed model.

## Setup

```python
import asyncio
from swgoh_comlink import RetryPolicy
from swgoh_comlink.typed import SwgohComlinkAsync  # Struct returns

async def main():
    async with SwgohComlinkAsync(
        url="http://comlink.local:3000",
        profile="bulk",          # max_connections=500, keepalive 60s
        # min_interval spaces calls to one endpoint; retries cover rate
        # refusals and HTTP 503 (opt-in; default is a single attempt).
        retry=RetryPolicy(attempts=5, min_interval=0.1),
    ) as client:
        if not await client.healthcheck(timeout=5.0):
            return 2
        await run_analysis(client)
    return 0
```

## Fan-out with `asyncio.Semaphore`

```python
async def run_analysis(client):
    allies = load_ally_codes_from_csv("input.csv")  # ~1000 entries

    # 10 in-flight at once — past this comlink starts rate-limiting
    # (the official limit is ~80/s on /player + 18/s on others, so 10
    # concurrent calls is a comfortable headroom)
    sem = asyncio.Semaphore(10)

    async def one(ally: int):  # returns a Player Struct
        async with sem:
            return await client.get_player(allycode=ally)

    players = await asyncio.gather(*(one(a) for a in allies))

    # Attribute access throughout; no dict indexing
    for p in players:
        print(p.name, p.guild_name, len(p.roster_unit))
```

## Optional: typed pydantic models for the report

```python
# pip install swgoh-comlink[pydantic]
from pydantic import BaseModel, Field
from swgoh_comlink import compat

class PlayerSummary(BaseModel):
    name: str
    ally_code: str = Field(alias="allyCode")
    guild_name: str = Field(alias="guildName")
    roster_size: int
    model_config = {"populate_by_name": True}

def summarize(player) -> PlayerSummary:
    raw = compat.to_dict(player)  # camelCase dict
    raw["roster_size"] = len(raw["rosterUnit"])
    return PlayerSummary.model_validate(raw)
```

(For deeper integration, define a richer BaseModel covering all the
fields you need and validate the whole player at once.)

## Operational notes

* **Profile.** `"bulk"` is the right preset: `max_connections=500`
  handles a bigger fan-out before httpx queues.
* **Cache.** Skip `GameDataCache` here — you're not making repeat
  `/data` calls. If you DO need `/data` once, just call
  `client.get_game_data()` directly.
* **Memory.** With `gc=False` Struct leaves (Phase 3.5), a fully-loaded
  Player Struct is ~30% smaller than the v2 dict. For 1000 players in
  memory simultaneously the win is real (5-10 MiB).

## What's NOT here

* **aiometer-based rate limiting.** v3.1 candidate. For now, the
  `Semaphore` + `gather` pattern above is what you'd write anyway.
* **Resume-on-failure for partial runs.** Add your own checkpoint file
  if a single bad input shouldn't tank the whole script.
