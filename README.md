# comlink_python

## Description

A python wrapper for the [swgoh-comlink](https://github.com/swgoh-utils/swgoh-comlink) tool.

There are two modules within the `comlink_python` package. They are:

| Module Name                                      | Purpose                                                       |
|--------------------------------------------------|---------------------------------------------------------------|
| [SwgohComlink](README_SwgohComlink.md)           | Used for traditional HTTP requests to the `comlink` instance  |
| [SwgohComlinkAsync](README_SwgohComlinkAsync.md) | Used for asynchronous HTTP requests to the `comlink` instance |

The SwgohComlink module is built upon the Python `requests` module. It provides traditional HTTP access to the comlink
utility provided in the instance creation parameters.

The SwgohComlinkAsync module is built upon the `aiohttp` module. It provides a more modern multi-threaded
access to the comlink utility provided in the instance creation parameters.
