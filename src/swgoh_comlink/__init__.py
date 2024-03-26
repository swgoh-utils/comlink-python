from __future__ import annotations

import sys

if sys.version_info[:2] < (3, 9):
    exit("Python 3.9 or higher is required for this version of the swgoh-comlink package.")

from .version import __version__ as version
from .swgoh_comlink import SwgohComlink

__all__ = [
    'SwgohComlink',
    'version'
]
