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
