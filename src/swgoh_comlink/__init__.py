# coding=utf-8
"""
Wrapper package for swgoh-comlink (https://github.com/swgoh-utils/swgoh-comlink)
"""
from __future__ import absolute_import

import sys

if sys.version_info[:2] < (3, 10):
    exit("Python 3.10 or greater is required to use this package version")

from .swgoh_comlink import SwgohComlink
from .swgoh_comlink_async import SwgohComlinkAsync

__version__ = "1.13.0rc1"

__all__ = [
    "__version__",
    "SwgohComlink",
    "SwgohComlinkAsync",
]
