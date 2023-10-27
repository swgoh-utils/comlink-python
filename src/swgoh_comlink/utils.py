"""
Helper utilities for the swgoh-python-async package and related modules
"""
import os
import logging
from logging.handlers import RotatingFileHandler


def get_logger(name: str = None, logging_level: str = 'INFO', terminal: bool = False) -> logging.Logger:
    """Create logger instance for writing messages to log files.

    :param name: Name of the log file to create. [Default: swgoh-comlink-async.log]
    :type name: str
    :param logging_level: Level of messages to log. [Default: INFO]
    :type logging_level: str
    :param terminal: Flag to determine if messages should be logged to terminal in addition to log file. [Default: False]
    :type terminal: bool
    :return: Logger instance
    :rtype: Logger
    """
    if name is None:
        name = __name__
    logger = logging.getLogger(name)
    logger.setLevel(logging.getLevelName(logging_level.upper()))
    # Create message formatting to include module and function naming for easier debugging
    formatter = logging.Formatter('{asctime} [ {levelname:^9}] {module:25} : {funcName:20}({lineno}) - {message}',
                                  style='{')
    log_base_name = os.path.join(os.getcwd(),  'swgoh-comlink-async.log')
    # Create a log file handler to write logs to disk
    log_file_handler = RotatingFileHandler(
        log_base_name,
        maxBytes=25000000,
        backupCount=5
    )
    log_file_handler.setFormatter(formatter)
    logger.addHandler(log_file_handler)
    # Create a second handler for output to terminal
    if terminal is True:
        log_console_handler = logging.StreamHandler()
        log_console_handler.setFormatter(formatter)
        logger.addHandler(log_console_handler)
    if logging_level == 'DEBUG':
        logger.debug("Logger created with 'DEBUG' level set.")
    return logger
