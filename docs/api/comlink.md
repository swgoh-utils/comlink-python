# SwgohComlink API

`SwgohComlink` is the synchronous client for a running `swgoh-comlink` service.
Each method sends one request and returns the decoded JSON response. For
`async`/`await` code, use [`SwgohComlinkAsync`](async.md), which has the same
methods and constructor arguments.

## Quick Start

```python
from swgoh_comlink import SwgohComlink

with SwgohComlink() as comlink:
    player = comlink.get_player(allycode=245866537)
    guild = comlink.get_guild(guild_id=player["guildId"])
```

Without a context manager, call `close()` when done:

```python
comlink = SwgohComlink()
try:
    player = comlink.get_player(allycode=245866537)
finally:
    comlink.close()
```

## Connecting to Comlink

The client connects to `http://localhost:3000` by default. Point it at another
service with either a full `url`, or a `host` and `port`:

```python
comlink = SwgohComlink(url="http://comlink.example.com:3000")
comlink = SwgohComlink(host="192.168.1.10", port=3000)
```

When `host` is given, `url` and `stats_url` are ignored.

If your comlink service requires HMAC signing, pass `access_key` and
`secret_key`. When they are not passed, the client reads them from the
`COMLINK_ACCESS_KEY` and `COMLINK_SECRET_KEY` environment variables. Signing is
turned on only when both keys are set; if only one is set, the client logs a
warning. The old `ACCESS_KEY` and `SECRET_KEY` names still work but are
deprecated, and are read only when neither `COMLINK_*` name is set.

See the [API Reference](#swgoh_comlink.swgoh_comlink.SwgohComlink) below for
every constructor argument.

## Handling Errors

When comlink answers with an HTTP error status, the client raises a
[typed HTTP error](exceptions.md#http-errors), such as
`SwgohComlinkRateLimitError` for a rate refusal or `SwgohComlinkClientError`
for a rejected request. All of them subclass `SwgohComlinkException`.

## Limiting Response Size

By default the client reads each response in full, however large it is. On a
host with little memory, such as a Raspberry Pi, two keyword-only arguments
cap how much of a response body the client will read:

- `max_response_bytes`: every endpoint except `/data`, including the stats
  service used by `get_unit_stats`.
- `max_game_data_bytes`: `/data` only (`get_game_data`). It is separate
  because game data is far larger than any other response, for the same reason
  `/data` has its own, longer timeout.

Both default to `None`, which means no limit. Limits count decoded bytes,
after any gzip decompression. When a limit is set:

- A success response whose `Content-Length` is over the limit raises
  `SwgohComlinkValueError` before any of the body is read. `Content-Length` is
  the compressed size, so this check catches only bodies that are too large
  even before decompression.
- Otherwise the client counts bytes as they arrive and raises
  `SwgohComlinkValueError` as soon as the count passes the limit. This also
  stops a small compressed body that would expand to a very large one. The
  count is checked after each decoded chunk, so memory use can pass the limit
  by up to one chunk.
- An HTTP error response is read up to the limit, and the body is cut there.
  The [typed HTTP error](exceptions.md#http-errors) is raised as usual, so
  `retry` still applies.

`SwgohComlinkValueError` from a limit is never retried. Raise the limit, or set
it to `None`, for calls that need more.

Measured decoded sizes in November 2026 (they grow with game updates, so leave
headroom):

| Call | Size |
|------|------|
| `get_game_metadata()` | 43 KB |
| `get_player()` | 1.5 MB |
| `get_localization()` | 46 MB |
| `get_localization(unzip=True)` | 228 MB |
| `get_game_data(request_segment=1)` | 111 MB |
| `get_game_data()`, all collections | 405 MB |

```python
from swgoh_comlink import SwgohComlink

MiB = 1024 * 1024
comlink = SwgohComlink(max_response_bytes=64 * MiB, max_game_data_bytes=512 * MiB)
```

With these values `get_localization(unzip=True)` fails; use `unzip=False` or a
larger `max_response_bytes` for it.

## Retries and Pacing

By default a client makes exactly one attempt per call and raises the
[typed HTTP error](exceptions.md#http-errors) on failure. Pass a `RetryPolicy`
as the keyword-only `retry` argument to retry the failures that mean the call
was not carried out:

- rate refusals (`SwgohComlinkRateLimitError`: HTTP 429, or the game's
  `Rate exceeded!`)
- HTTP 503 (`SwgohComlinkUnavailableError`)

Before each retry the client waits for the `Retry-After` header when the
response has one (capped at `max_retry_after`), otherwise for the next value
of `backoff` (5, 10, 20 and 40 seconds by default), plus a random extra of up
to `jitter` times that wait (20% by default) so that calls refused together do
not all retry at once. Jitter only adds time: no retry starts before the
backoff or `Retry-After` wait. Other errors are raised at once.

A rate refusal also holds back the endpoint it came from. Until the retry wait
has passed, no call to that endpoint starts on the client, whether it is a
retry or a new call, so concurrent callers back off together rather than
adding to the refusal. Endpoints listed in `unpaced_endpoints` are never held.

`min_interval` also spaces calls to the same endpoint. The game refuses calls
with `Rate exceeded!` at roughly 15 calls a second per RPC on one session,
so 0.4 seconds keeps a burst well under that limit.

```python
from swgoh_comlink import RetryPolicy, SwgohComlink

comlink = SwgohComlink(retry=RetryPolicy(attempts=3, min_interval=0.4))
player = comlink.get_player(allycode=245866537)
```

`SwgohComlinkAsync` accepts the same argument; see
[its retries section](async.md#retries-and-pacing) for how waits behave with
concurrent tasks.

::: swgoh_comlink.retry.RetryPolicy
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false

## Stat Calculation

To add stats and Galactic Power to the units in a player profile, pass the
roster to `StatCalc`, which runs the calculation locally:

```python
from swgoh_comlink import StatCalc, SwgohComlink

with SwgohComlink() as comlink:
    calc = StatCalc()
    player = comlink.get_player(allycode=245866537)
    calc.calc_roster_stats(player["rosterUnit"])
```

See the [StatCalc API](statcalc.md) for full details.

## API Reference

::: swgoh_comlink.swgoh_comlink.SwgohComlink
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false
