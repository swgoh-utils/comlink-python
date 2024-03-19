# coding=utf-8
"""
<REPLACE WITH DOCSTRING>
"""
import inspect
import logging

__all__ = [
    "get_function_name",
    "LoggingFormatter"
]


class LoggingFormatter(logging.Formatter):
    """Custom logging formatter class with colored output"""

    # Colors
    black = "\x1b[30m"
    white = "\x1b[37m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    gray = "\x1b[38m"
    # Styles
    reset = "\x1b[0m"
    bold = "\x1b[1m"

    # ANSI color reference https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797

    COLORS = {
        logging.DEBUG: gray + bold,
        logging.INFO: blue + bold,
        logging.WARNING: yellow + bold,
        logging.ERROR: red,
        logging.CRITICAL: "\x1b[1;31;43m",  # Bold (1) Red (31) with Yellow (43) background
    }

    def format(self, record):
        """Method to dynamically color log messages for console output based on message severity"""
        log_color = self.COLORS[record.levelno]
        time_color = "\x1b[1;30;47m"
        format_str = (
                "(black){asctime}(reset) | (lvl_color){levelname:8}(reset) | "
                + "(green){name:<25} | {threadName} | "
                + "(green){module:<14}(reset) | (green){funcName:>20}:{lineno:^4}(reset) | {message}"
        )
        """
        log_message_format = ('{asctime} | [{levelname:^9}] | {name:25} | pid:{process} | {threadName} | ' +
                              '{filename:<15} | {module:<14} : {funcName:>20}()_{lineno:_^4}_ | {message}')
        """
        format_str = format_str.replace("(black)", time_color)
        format_str = format_str.replace("(reset)", self.reset)
        format_str = format_str.replace("(lvl_color)", log_color)
        format_str = format_str.replace("(green)", self.green + self.bold)
        formatter = logging.Formatter(format_str, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


def get_function_name() -> str:
    """Return the name for the calling function"""
    return f"{inspect.stack()[1].function}()"
