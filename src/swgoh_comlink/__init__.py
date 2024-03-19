# coding=utf-8
"""
Wrapper package for swgoh-comlink (https://github.com/swgoh-utils/swgoh-comlink)
"""
from __future__ import annotations

import sys

if sys.version_info[:2] < (3, 10):
    exit("Python 3.10 or greater is required to use this package version")

from .swgoh_comlink import SwgohComlink
from .swgoh_comlink_async import SwgohComlinkAsync
from .core import *
from .utils import *
from .const import *
from .int.helpers import *

__version__ = "1.13.1"

__all__ = [
    "__version__",
    "SwgohComlink",
    "SwgohComlinkAsync",
]
