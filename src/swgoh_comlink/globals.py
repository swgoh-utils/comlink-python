# coding=utf-8
"""
Global entities
"""

from __future__ import annotations

import logging


class LoggingFormatter(logging.Formatter):
    """Custom logging formatter class"""

    def format(self, record):
        log_message_format = \
            '{asctime} | {levelname:<9} | {name:15} | {module:<14} : {funcName:>30}() [{lineno:_>5}] | {message}'
        formatter = logging.Formatter(log_message_format, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


def get_logger(logger_name: str = __name__, log_level: str = "INFO") -> logging.Logger:
    """Return the configured logger"""
    logger = logging.getLogger(logger_name)
    log_lvl = logging.getLevelName(log_level.upper())
    logger.setLevel(log_lvl)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(LoggingFormatter())
    logger.addHandler(console_handler)
    return logger
