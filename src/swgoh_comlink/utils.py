"""
Helper utilities for the swgoh-python-async package and related modules
"""
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

logger_name = 'swgoh_comlink'


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
        name = logger_name
    logger = logging.getLogger(name)
    logger.setLevel(logging.getLevelName(logging_level.upper()))
    # Create message formatting to include module and function naming for easier debugging
    formatter = logging.Formatter('{asctime} [ {levelname:^9}] {module:25} : {funcName:20}({lineno}) - {message}',
                                  style='{')
    log_base = os.path.join(os.getcwd(), 'logs')
    try:
        os.mkdir(log_base)
    except FileExistsError:
        pass
    log_base_name = os.path.join(log_base, f'{logger_name}.log')
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
    logger.info(f"Logger created with level set to {logging_level.upper()!r}.")
    return logger


def human_time(time: int or float) -> str:
    """Convert unix time to human readable string"""
    if isinstance(time, float):
        time = int(time)
    if isinstance(time, str):
        try:
            time = int(time)
        except Exception as exc:
            logging.getLogger(logger_name).exception(f"Exception caught: [{exc}]")
            raise
    return datetime.fromtimestamp(time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%s')
