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

## 5. Helpers module refactoring

The monolithic `helpers.py` file has been refactored into a `helpers/` subpackage.
**All existing import paths continue to work** — a backward-compatible re-export shim
ensures no breaking changes.

### What moved

| Before | After (internal location) |
|--------|--------------------------|
| `helpers.py` (single file) | `helpers/` subpackage with focused modules |
| `Constants.STAT_ENUMS` | `helpers/_stat_data.STAT_ENUMS` (re-exported) |
| `Constants.STATS` | `helpers/_stat_data.STATS` (re-exported) |
| `StatCalc.STATS_NAME_MAP` | Now imports from `helpers/_stat_data.STATS` |

### Constants.get() changes

`Constants.get()` still works for all legacy PascalCase names (e.g., `"UnitDefinitions"`)
as well as the new UPPER_SNAKE_CASE `DataItems` names (e.g., `"UNITS"`):

```python
from swgoh_comlink.helpers import Constants

# All three forms still work:
Constants.get("UnitDefinitions")  # -> '137438953472' (legacy name)
Constants.get("UNITS")            # -> '137438953472' (DataItems name)
Constants.get("Segment1")         # -> '206158430208' (class attribute)
```

**Recommendation:** Prefer using `DataItems` enum values directly for type safety:

```python
from swgoh_comlink.helpers import DataItems

items = DataItems.UNITS | DataItems.CATEGORY
data = comlink.get_game_data(items=items)
```

### Migration checker CLI

A CLI tool is included to scan your codebase for patterns that may need updating:

```bash
# Scan a project directory
python -m swgoh_comlink.migrate /path/to/your/project

# Or use the console script
swgoh-migrate /path/to/your/project

# Filter by severity and exclude directories
swgoh-migrate . --severity=WARNING --exclude .venv dist
```

The tool reports deprecated imports, removed APIs, and suggests replacements.

## 6. Subclass and internal API changes

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

## 7. Removed sentinels

The `OPTIONAL` and `NotSet` sentinel objects have been removed from
`swgoh_comlink.helpers`. If your code imports these, remove the imports.

```diff
  from swgoh_comlink.helpers import (
      REQUIRED,
      MISSING,
      GIVEN,
-     OPTIONAL,
-     NotSet,
  )
```

The remaining sentinels (`REQUIRED`, `MISSING`, `GIVEN`, `MutualExclusiveRequired`)
are unchanged.

## 8. GAC bracket helpers

`get_gac_brackets()` and `async_get_gac_brackets()` have two changes:

1. The `limit` parameter changed from a sentinel default to `int` with default `0`
   (where `0` means "no limit"):

    ```diff
    - get_gac_brackets(comlink, league="KYBER", limit=OPTIONAL)
    + get_gac_brackets(comlink, league="KYBER", limit=0)
    ```

2. Bracket boundary discovery now uses exponential probing with binary search,
   reducing HTTP requests from O(n) to O(log n). The async variant also fetches
   brackets in parallel batches via `asyncio.gather`. No code changes are needed
   on your side — the return format is identical.

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
| `helpers.py` | Single 1,970-line file | `helpers/` subpackage (all imports preserved) |
| `OPTIONAL` / `NotSet` sentinels | Exported from helpers | Removed |
| `get_gac_brackets(limit=)` | Sentinel default | `int` default `0` (0 = no limit) |
| GAC bracket scanning | Linear O(n) | Exponential probe + binary search O(log n) |
| Migration checker | Not available | `swgoh-migrate` CLI / `python -m swgoh_comlink.migrate` |
