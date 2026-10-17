# Exceptions

All custom exceptions raised by `swgoh_comlink` inherit from
`SwgohComlinkException`. Catching this base class is sufficient to handle any
error from the library.

```python
from swgoh_comlink import SwgohComlink
from swgoh_comlink.exceptions import SwgohComlinkException, SwgohComlinkValueError, SwgohComlinkTypeError

comlink = SwgohComlink()

try:
    player = comlink.get_player(allycode=123)
except SwgohComlinkValueError:
    print("Invalid allycode format")
except SwgohComlinkTypeError:
    print("Invalid argument type")
except SwgohComlinkException:
    print("Comlink request failed")
```

## HTTP errors

When comlink answers with an HTTP error status, the clients raise a
`SwgohComlinkHTTPError` (or one of its subclasses) from the original
`httpx.HTTPStatusError`. `str(exc)` is `"HTTP {status}: {body}"`, as it has
always been, so existing handlers that catch `SwgohComlinkException` keep
working.

| Exception | Raised for |
|---|---|
| `SwgohComlinkRateLimitError` | HTTP 429, or the game's `Rate exceeded!` refusal (sent as HTTP 502) |
| `SwgohComlinkUnavailableError` | HTTP 503, comlink busy or not ready |
| `SwgohComlinkClientError` | Any other 4xx, the request was rejected |
| `SwgohComlinkHTTPError` | Any other error status (5xx) |

Each one has these attributes:

- `status`: the HTTP status code.
- `code` and `detail`: the `code` and `message` fields of comlink's JSON error
  body (`detail` is the raw body text when the body is not JSON).
- `retry_after`: the `Retry-After` header in seconds, or `None`.
- `response`: the `httpx.Response`.

Game error codes look like `GAME_<n>`, and the number can differ between calls
that fail for the same reason. Match on the exception class, not on `code`.

```python
from swgoh_comlink import SwgohComlink
from swgoh_comlink.exceptions import (
    SwgohComlinkClientError,
    SwgohComlinkHTTPError,
    SwgohComlinkRateLimitError,
)

comlink = SwgohComlink()

try:
    player = comlink.get_player(allycode=123456789)
except SwgohComlinkRateLimitError as exc:
    print(f"Rate limited, retry in {exc.retry_after or 5} s")
except SwgohComlinkClientError as exc:
    print(f"Rejected ({exc.status} {exc.code}): {exc.detail}")
except SwgohComlinkHTTPError as exc:
    print(f"Comlink error {exc.status}")
```

To have the client retry rate refusals and 503 responses for you, pass a
[`RetryPolicy`](comlink.md#retries-and-pacing).

## API Reference

### SwgohComlinkException

::: swgoh_comlink.exceptions.SwgohComlinkException
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false

### SwgohComlinkValueError

::: swgoh_comlink.exceptions.SwgohComlinkValueError
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false

### SwgohComlinkTypeError

::: swgoh_comlink.exceptions.SwgohComlinkTypeError
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false

### SwgohComlinkHTTPError

::: swgoh_comlink.exceptions.SwgohComlinkHTTPError
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false

### SwgohComlinkRateLimitError

::: swgoh_comlink.exceptions.SwgohComlinkRateLimitError
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false

### SwgohComlinkUnavailableError

::: swgoh_comlink.exceptions.SwgohComlinkUnavailableError
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false

### SwgohComlinkClientError

::: swgoh_comlink.exceptions.SwgohComlinkClientError
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false
