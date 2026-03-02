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


def get_logger(logger_name: str = __name__, log_level: str = "INFO") -> logging.Logger:
    """Return the configured logger.

    Guards against adding duplicate handlers when called more than once
    for the same *logger_name*.
    """
    logger = logging.getLogger(logger_name)
    log_lvl = logging.getLevelName(log_level.upper())
    logger.setLevel(log_lvl)
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(LoggingFormatter())
        logger.addHandler(console_handler)
    return logger
