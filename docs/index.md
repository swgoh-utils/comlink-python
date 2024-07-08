<style>
.center {
    display: flex;
    justify-content: center;
}
</style>

<h1 class="center" style="font-size: 3rem; margin: -15px 0">
SwgohComlink
</h1>
<br>
<div class="center">
<p>
<img src="https://github.com/swgoh-utils/comlink-python/actions/workflows/tests.yml/badge.svg?branch=1.13.0rc1">
<a href="https://badge.fury.io/py/swgoh-comlink"><img src="https://badge.fury.io/py/swgoh-comlink.svg" alt="PyPI version" height="18"></a></p>
</div>

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

