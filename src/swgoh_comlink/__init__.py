# coding=utf-8
from __future__ import annotations

import logging

from swgoh_comlink.StatCalc import StatCalc
from swgoh_comlink.swgoh_comlink import SwgohComlink
from swgoh_comlink.swgoh_comlink_async import SwgohComlinkAsync
from swgoh_comlink.version import __version__ as version

__all__ = ["StatCalc", "SwgohComlink", "SwgohComlinkAsync", "version"]

# Follow Python best practice for library logging:
# Only add NullHandler so the application controls all logging configuration.
# See: https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger(__name__).addHandler(logging.NullHandler())
