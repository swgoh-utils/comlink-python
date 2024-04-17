# Welcome to the documentation page for the swgoh_comlink python package

---

## What is the swgoh_comlink python package?

`swgoh_comlink` is a python package that provides a collection of interfaces to
the [swgoh-comlink](https://github.com/swgoh-utils/swgoh-comlink) service proxy.

`swgoh-comlink` provides a proxy interface to Electronic
Arts' [Star Wars&trade; : Galaxy of Heroes](https://www.ea.com/games/starwars/galaxy-of-heroes) mobile game servers

### Installation

It is recommended to install the `swgoh_comlink` package into a virtual environment

```shell
# python3 -m venv venv
# source venv/bin/activate
(venv) # python3 -m pip install swgoh-comlink
```

### Available Modules

The `swgoh_comlink` package contains several modules as well as a collection of helper utility functions for commonly
performed tasks when interacting with SWGoH game server data.

| Module                                      | Description                                                                                  |
|---------------------------------------------|----------------------------------------------------------------------------------------------|
| [SwgohComlink](swgoh_comlink.md)            | Synchronous HTTP interface methods for interacting with Comlink                              |
| [SwgohComlinkAsync](swgoh_comlink_async.md) | Asynchronous HTTP interface methods for interacting with Comlink                             |
| [utils](utils.md)                           | Collection of utility functions for common game data interaction and manipulation activities |

