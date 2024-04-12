from __future__ import annotations

import os
import platform
import sys

if sys.version_info[:2] < (3, 10):
    exit("Python 3.10 or later is required to use this package version")

sys.path.append(os.path.dirname(__file__))

from swgoh_comlink.swgoh_comlink import SwgohComlink
from swgoh_comlink.swgoh_comlink_async import SwgohComlinkAsync
import swgoh_comlink.utils

__version__ = "1.13.4rc1"

__all__ = [
    __version__,
    SwgohComlink,
    SwgohComlinkAsync,
]

if 'Office-iMac' in platform.node():
    global_logger = utils.get_logger(default_logger=True)
