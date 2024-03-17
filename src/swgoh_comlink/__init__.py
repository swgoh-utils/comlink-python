# coding=utf-8
"""
Wrapper package for swgoh-comlink (https://github.com/swgoh-utils/swgoh-comlink)
"""
from __future__ import absolute_import

from .swgoh_comlink import SwgohComlink
from .swgoh_comlink_async import SwgohComlinkAsync

__version__ = "1.13.0rc1"

__all__ = [
    "__version__",
    "SwgohComlink",
    "SwgohComlinkAsync",
]
