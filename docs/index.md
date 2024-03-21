# swgoh_comlink

## Description

`swgoh_comlink` is a python language wrapper for the [swgoh-comlink](https://github.com/swgoh-utils/swgoh-comlink) tool.

There are several modules within the `swgoh_comlink` package. They are:

| Module Name                               | Purpose                                                                           |
|-------------------------------------------|-----------------------------------------------------------------------------------|
| [SwgohComlink](SwgohComlink.md)           | Used for traditional synchronous HTTP requests to the `swgoh-comlink` application |
| [SwgohComlinkAsync](SwgohComlinkAsync.md) | Used for asynchronous HTTP requests to the `swgoh-comlink` application            |
| [utils](/comlink-python/References/utils) | Helper functions to assist with typical tasks while working with game data        |

The underlying HTTP framework used by both the `SwgohComlink` and `SwgohComlinkAsync` modules
is [httpx](https://www.python-httpx.org/).

## Installation

`pip install swgoh-comlink`

## Basic Usage

```python
from swgoh_comlink import SwgohComlink

comlink = SwgohComlink(
    url='http://localhost:3000',
    stats_url='http://localhost:3223'
)

game_data = comlink.get_gamedata()

```

