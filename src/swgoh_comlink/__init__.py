from __future__ import annotations

import os
import sys

if sys.version_info[:2] < (3, 10):
    exit("Python 3.10 or later is required to use this package version")

sys.path.append(os.path.dirname(__file__))

from swgoh_comlink.version import __version__
from swgoh_comlink.swgoh_comlink import SwgohComlink
from swgoh_comlink.swgoh_comlink_async import SwgohComlinkAsync

__all__ = [
    '__version__',
    SwgohComlink,
    SwgohComlinkAsync,
]
