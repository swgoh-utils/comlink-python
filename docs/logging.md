# SwgohComlink Logging

The `swgoh_comlink` package follows Python's recommended best practice for library logging: it attaches only a
[`NullHandler`](https://docs.python.org/3/library/logging.handlers.html#logging.NullHandler) to the root package
logger and never configures handlers, formatters, or log levels on its own.

This means:

- **By default the library is silent** — no log output unless your application configures logging.
- **You have full control** over formatting, log levels, and destinations.
- **No duplicate handlers** or forced formatting from the library.

All loggers in the package use the `swgoh_comlink` namespace (e.g. `swgoh_comlink.helpers`,
`swgoh_comlink.exceptions`), so you can target them by name.

## Quick Start

The simplest way to see log output is with `logging.basicConfig()`:

```python
import logging

logging.basicConfig(level=logging.DEBUG)

from swgoh_comlink import SwgohComlink

comlink = SwgohComlink()
player = comlink.get_player(allycode=245866537)
```

This sends all DEBUG-and-above messages from every logger (including `swgoh_comlink`) to the console.

## Custom Console Handler

To control only `swgoh_comlink` output without affecting other loggers:

```python
import logging
from swgoh_comlink import SwgohComlink

comlink_logger = logging.getLogger("swgoh_comlink")
comlink_logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
comlink_logger.addHandler(handler)

comlink = SwgohComlink()
```

## Using the Package's Built-in Formatter

The package ships a `LoggingFormatter` class in `swgoh_comlink.globals` that you can use as an
opt-in convenience:

```python
import logging
from swgoh_comlink import SwgohComlink
from swgoh_comlink.globals import LoggingFormatter

comlink_logger = logging.getLogger("swgoh_comlink")
comlink_logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setFormatter(LoggingFormatter())
comlink_logger.addHandler(handler)

comlink = SwgohComlink()
```

## Rotating File Handler

To capture logs to a rotating file:

```python
import logging
from logging.handlers import RotatingFileHandler
from swgoh_comlink import SwgohComlink

comlink_logger = logging.getLogger("swgoh_comlink")
comlink_logger.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(
    filename="./comlink.log",
    encoding="utf-8",
    maxBytes=2_500_000,
    backupCount=5,
)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
comlink_logger.addHandler(file_handler)

comlink = SwgohComlink()
```
