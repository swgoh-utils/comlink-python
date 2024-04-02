from __future__ import annotations

import os
import sys

if sys.version_info[:2] < (3, 10):
    exit("Python 3.10 or later is required to use this package version")

sys.path.append(os.path.dirname(__file__))

from .Base.swgoh_comlink_base import SwgohComlinkBase
from .SwgohComlink import SwgohComlink
from .SwgohComlinkAsync import SwgohComlinkAsync
import swgoh_comlink.utils

__version__ = "1.13.3rc2"

__all__ = [
    __version__,
    SwgohComlinkBase,
    SwgohComlink,
    SwgohComlinkAsync,
    utils
]


@property
def version() -> str:
    return __version__
