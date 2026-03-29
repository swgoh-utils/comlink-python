# coding=utf-8
"""
Global entities
"""

from __future__ import annotations

import logging

_LOG_FORMAT = "{asctime} | {levelname:<9} | {name:15} | {module:<14} : {funcName:>30}() [{lineno:_>5}] | {message}"


class LoggingFormatter(logging.Formatter):
    """Custom logging formatter class."""

    def __init__(self) -> None:
        super().__init__(_LOG_FORMAT, "%Y-%m-%d %H:%M:%S", style="{")

    def format(self, record: logging.LogRecord) -> str:
        return super().format(record)


def get_logger(logger_name: str = __name__) -> logging.Logger:
    """Return a logger for the given name.

    This is a thin wrapper around :func:`logging.getLogger`.  No handlers
    or levels are configured — the application is responsible for that.
    """
    return logging.getLogger(logger_name)
