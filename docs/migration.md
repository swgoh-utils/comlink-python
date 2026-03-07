# Migration Guide

This guide covers the changes needed when upgrading from `swgoh_comlink` **v1.x** (the `requests`-based release)
to the new version that introduces async support, `StatCalc`, and `httpx`.

## 1. Update dependencies

The HTTP library changed from `requests` to `httpx`.

```bash
# Remove the old dependency
pip uninstall requests

# Install the new version
pip install --upgrade swgoh_comlink
```

If your project pins dependencies, update your `requirements.txt` or `pyproject.toml`:

```diff
- requests>=2.32.4
+ httpx>=0.28
```

`httpx` is installed automatically as a dependency of `swgoh_comlink`, so in most cases
you only need to upgrade the package itself.

## 2. Update exception handling

The exception raised on HTTP errors changed from `requests.RequestException` to
`httpx.RequestError`. The library still wraps transport errors in its own
`SwgohComlinkException`, so if you catch that you are already covered.

```diff
  from swgoh_comlink import SwgohComlink
- import requests
+ import httpx

  comlink = SwgohComlink()
  try:
      player = comlink.get_player(allycode=245866537)
- except requests.RequestException as e:
+ except httpx.RequestError as e:
      print(f"Network error: {e}")
```

**Recommended:** Catch `SwgohComlinkException` instead of transport-level errors — this
insulates your code from future HTTP library changes:

```python
from swgoh_comlink import SwgohComlink
from swgoh_comlink.exceptions import SwgohComlinkException

comlink = SwgohComlink()
try:
    player = comlink.get_player(allycode=245866537)
except SwgohComlinkException as e:
    print(f"Comlink error: {e}")
```

## 3. Update logging configuration

The `get_logger()` helper no longer accepts a `log_level` parameter and no longer
attaches handlers or sets log levels automatically. The library now follows Python best
practice by attaching only a `NullHandler` to the package root logger.

**Before:**

```python
from swgoh_comlink.globals import get_logger

logger = get_logger(__name__, log_level="DEBUG")  # auto-configured handler + level
```

**After:**

```python
import logging

logging.basicConfig(level=logging.DEBUG)  # configure logging in your application
```

Or target only the `swgoh_comlink` namespace:

```python
import logging

comlink_logger = logging.getLogger("swgoh_comlink")
comlink_logger.setLevel(logging.DEBUG)
comlink_logger.addHandler(logging.StreamHandler())
```

See [Logging](logging.md) for more examples including the built-in `LoggingFormatter`
and rotating file handlers.

## 4. Close the client when done

The new version uses persistent `httpx` connection pools for better performance.
This means the client should be closed when you are finished with it.

**Context manager (recommended):**

```python
with SwgohComlink() as comlink:
    player = comlink.get_player(allycode=245866537)
# connections are closed automatically
```

**Manual close:**

```python
comlink = SwgohComlink()
try:
    player = comlink.get_player(allycode=245866537)
finally:
    comlink.close()
```

Existing code that does not call `close()` will still work — connections are cleaned up
on garbage collection — but explicitly closing is preferred to avoid resource warnings.

## 5. Subclass and internal API changes

These only matter if you subclass `SwgohComlink` or call private methods directly.

### Constructor inheritance

`SwgohComlink` and `SwgohComlinkAsync` now inherit from `SwgohComlinkBase`. The
constructor parameters are unchanged, but the subclass signature uses `**kwargs`:

```python
# Both still work:
comlink = SwgohComlink(url="http://myhost:3000")
comlink = SwgohComlink(host="myhost", port=3000)
```

### `_request()` signature

```diff
  def _request(
      self,
      method: str = "POST",
-     url_base: str | None = None,
      endpoint: str | None = None,
      payload: dict | list | None = None,
+     stats: bool = False,
+     timeout: float | None = None,
  ) -> dict | list:
```

- `url_base` was removed — the method now selects between `self.url_base` and
  `self.stats_url_base` based on the `stats` flag.
- `timeout` allows per-request timeout overrides.

### `_post()` signature

Same changes as `_request()` — `url_base` replaced by `stats` and `timeout`.

## Summary of changes

| Area | Before (v1.x) | After |
|------|---------------|-------|
| HTTP library | `requests` | `httpx` |
| Transport exception | `requests.RequestException` | `httpx.RequestError` |
| `get_logger(log_level=)` | Accepted `log_level`, auto-configured handlers | No `log_level` param, no auto-configuration |
| Default log output | Console output at INFO level | Silent (NullHandler only) |
| Client lifecycle | No close needed | Use `with` or call `close()` |
| Async support | Not available | `SwgohComlinkAsync` |
| Local stat calc | Not available | `StatCalc` (sync) / `StatCalcAsync` (async) |
| `_request(url_base=)` | `url_base` parameter | `stats` bool + `timeout` |
