# SwgohComlink API

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
of `backoff` (5, 10, 20 and 40 seconds by default). Other errors are raised at
once.

`min_interval` also spaces calls to the same endpoint. The game refuses calls
with `Rate exceeded!` at roughly 15 calls a second per RPC on one session,
so 0.4 seconds keeps a burst well under that limit.

```python
from swgoh_comlink import RetryPolicy, SwgohComlink

comlink = SwgohComlink(retry=RetryPolicy(attempts=3, min_interval=0.4))
player = comlink.get_player(allycode=123456789)
```

`SwgohComlinkAsync` accepts the same argument.

::: swgoh_comlink.retry.RetryPolicy
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false

## API Reference

::: swgoh_comlink.swgoh_comlink.SwgohComlink
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false
