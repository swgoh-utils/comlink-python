# coding=utf-8
from __future__ import absolute_import, annotations

import sys

if sys.version_info[:2] < (3, 10):
    exit("Python 3.10 or higher is required for this version of the swgoh-comlink package.")

from swgoh_comlink.version import __version__ as version
from swgoh_comlink.swgoh_comlink import SwgohComlink

__all__ = [
        'SwgohComlink',
        'version'
        ]
