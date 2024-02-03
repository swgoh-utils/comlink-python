"""
Wrapper for swgoh-comlink (https://github.com/swgoh-utils/swgoh-comlink)
"""

from __future__ import annotations, print_function, absolute_import

from typing import NamedTuple, Literal

__title__ = 'swgoh-comlink'
__author__ = 'Mar Trepodi'
__license__ = 'MIT'
__copyright__ = 'Copyright 2023-present Mar Trepodi'

__path__ = __import__('pkgutil').extend_path(__path__, __name__)

from .version import __version__
from .SwgohComlink import *


class VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: Literal["alpha", "beta", "candidate", "final"]
    serial: int


version_info: VersionInfo = VersionInfo(major=1, minor=13, micro=0, releaselevel='alpha', serial=0)
