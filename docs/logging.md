# SwgohComlink Logging

The `swgoh_comlink` package has a default logger defined. Normally this logger is disabled. This behavior
can be changed by passing the `default_logger_enabled=True` argument to the SwgohComlink or SwgohComlinkAsync
instance constructor.

For example,

```python
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(default_logger_enabled=True)
```

This will create a `./logs/swgoh_comlink.log` file in the directory where your script is running. The default log level
is set to `DEBUG`. The default logger uses ANSI color coding escape characters in the output format. If you would like
to use the built-in logging but at a lower logging level or specialised output formatting, you can create your own
logging instance with the name 'swgoh_comlink' and implement the custom logging setting appropriate for your program
needs.

For example:

```python
import logging
from swgoh_comlink import SwgohComlink

comlink_logger = logging.getLogger('swgoh_comlink')
comlink_logger.setLevel(logging.CRITICAL)
console_handler = logging.StreamHandler()
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(log_format)
comlink_logger.addHandler(console_handler)

comlink = SwgohComlink()
```

The configuration above would capture all `CRITICAL` events and higher and display them on the console terminal.

If you wanted to capture events to a rotating log file, you could add an additional handler to the logger instance
defined above.

```python
import logging
from logging.handlers import RotatingFileHandler
from swgoh_comlink import SwgohComlink

comlink_logger = logging.getLogger('swgoh_comlink')
comlink_logger.setLevel(logging.CRITICAL)
console_handler = logging.StreamHandler()
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(log_format)
comlink_logger.addHandler(console_handler)

file_handler = RotatingFileHandler(filename="./comlink.log", encoding="utf-8", maxBytes=2500000, backupCount=5)
file_handler.setFormatter(log_format)
file_handler.setLevel(logging.DEBUG)
comlink_logger.addHandler(file_handler)

comlink = SwgohComlink()


```