# coding=utf-8
"""General utility functions: validation, sanitization, conversion."""

from __future__ import annotations

import inspect
import logging
import os
import re
from enum import Enum
from os import PathLike
from pathlib import Path
from typing import Any, Literal

from ..exceptions import SwgohComlinkValueError
from ._constants import Constants
from ._sentinels import MISSING, REQUIRED

logger = logging.getLogger(__name__)

OutputFormat = Literal["terminal", "discord", "web", "bare"]

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_ITALIC = "\033[3m"

# ANSI color support: convert hex to nearest 256-color or use truecolor if available
def _hex_to_ansi_truecolor(hex_color: str) -> str:
    """Convert a hex color string to an ANSI truecolor escape sequence."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"\033[38;2;{r};{g};{b}m"

def _parse_tokens(text: str) -> list[dict]:
    """
    Tokenize a SWGOH BBCode string into a list of tokens.
    Each token is a dict with a 'type' and relevant fields.

    Token types:
      - 'text':    plain text content
      - 'color':   opens a color scope  {'hex': 'F0FF23'}
      - 'color_reset':  [-] inside a color scope
      - 'color_end':    [/c] closes color scope
      - 'bold_open':    [b]
      - 'bold_close':   [/b]
      - 'italic_open':  [i]
      - 'italic_close': [/i]
      - 'newline':      \\n literal escape in the source string
    """
    # Tag pattern: [TAG] where TAG is /c, -c, -, b, /b, i, /i, or a hex color
    TAG_RE = re.compile(
        r'(\[(?:/c|-c|-|/b|/i|b|i|c|[0-9A-Fa-f]{6})\])',
        re.IGNORECASE
    )

    tokens = []
    parts = TAG_RE.split(text)

    for part in parts:
        if not part:
            continue

        if TAG_RE.fullmatch(part):
            inner = part[1:-1]  # strip [ ]
            lower = inner.lower()

            if lower in ("/c", "-c"):
                tokens.append({"type": "color_end"})
            elif lower == "c":
                tokens.append({"type": "color_block_open"})
            elif lower == "-":
                tokens.append({"type": "color_reset"})
            elif lower == "b":
                tokens.append({"type": "bold_open"})
            elif lower == "/b":
                tokens.append({"type": "bold_close"})
            elif lower == "i":
                tokens.append({"type": "italic_open"})
            elif lower == "/i":
                tokens.append({"type": "italic_close"})
            elif re.fullmatch(r'[0-9A-Fa-f]{6}', inner):
                tokens.append({"type": "color", "hex": inner.upper()})
        else:
            # Split on literal \n sequences in the source
            segments = part.split("\\n")
            for idx, segment in enumerate(segments):
                if segment:
                    tokens.append({"type": "text", "value": segment})
                if idx < len(segments) - 1:
                    tokens.append({"type": "newline"})

    return tokens


def get_function_name() -> str:
    """Return the name of the calling function"""
    return f"{inspect.stack()[1].function}()"


def get_enum_key_by_value(enum_dict: dict[str, Any], category: Any, enum_value: Any, default_return: Any = None) -> Any:
    """
    Return the key from enum_dict for the given enum_value.
    """
    enum_values: dict[str, Any] | None = enum_dict.get(category)
    if enum_values:
        enum_value_match: list[Any] | None = [key for key, value in enum_values.items() if value == enum_value]
        return enum_value_match[0] if enum_value_match else default_return
    else:
        return default_return


def validate_file_path(path: str | Path | PathLike[Any]) -> bool:
    """Test whether provided path exists or not

    Args:
        path: path of file to validate

    Returns:
        True if exists, False otherwise.

    """
    if not path:
        err_msg = f"{get_function_name()}: 'path' argument is required."
        raise SwgohComlinkValueError(err_msg)
    return os.path.exists(path) and os.path.isfile(path)


def sanitize_allycode(allycode: str | int | Any = REQUIRED) -> str:
    """Sanitize a player allycode

    Ensure that allycode does not:
        - contain dashes
        - is the proper length
        - contains only digits

    Args:
        allycode: Player allycode to sanitize

    Returns:
        Player allycode in the proper format

    """
    from ._sentinels import GIVEN

    _orig_ac = allycode
    if not allycode and allycode is not GIVEN:
        return ""
    if isinstance(allycode, int):
        allycode = str(allycode)
    if "-" in str(allycode):
        allycode = allycode.replace("-", "")
    if not allycode.isdigit() or len(allycode) != 9:
        err_msg = f"{get_function_name()}: Invalid ally code: {allycode}"
        raise SwgohComlinkValueError(err_msg)
    return allycode


def human_time(unix_time: int | float | Any = REQUIRED) -> str:
    """Convert unix time to human-readable string

    Args:
        unix_time (int|float): standard unix time in seconds or milliseconds

    Returns:
        str: human-readable time string

    Notes:
        If the provided unix time is invalid or an error occurs, the default time string returned
        is 1970-01-01 00:00:00

    """
    logger.debug(f"unix_time: {unix_time}")
    if unix_time is MISSING or not str(unix_time):
        err_msg = f"{get_function_name()}: The 'unix_time' argument is required."
        raise SwgohComlinkValueError(err_msg)
    from datetime import datetime, timezone

    if isinstance(unix_time, float):
        unix_time = int(unix_time)
    if isinstance(unix_time, str):
        try:
            unix_time = int(unix_time)
        except (ValueError, TypeError) as e:
            err_msg = f"{get_function_name()}: Unable to convert unix time from {type(unix_time)} to type <int>"
            raise SwgohComlinkValueError(err_msg) from e
    if len(str(unix_time)) >= 13:
        unix_time /= 1000
    return datetime.fromtimestamp(unix_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def convert_relic_tier(relic_tier: str | int | Any = REQUIRED) -> str | None:
    """Convert character relic tier to offset string in-game value.

    Conversion is done based on a zero based table indicating both the relic tier status and achieved level.

    Args:
        relic_tier (str | int): The relic tier from character game data to convert to in-game equivalent.

    Returns:
        String representing the relic status and tier

    Raises:
        TypeError: If the provided 'relic_tier' cannot be converted to a string using the Python
                    built-in str() method.

    Examples:
        Relic tier is '0' indicates the character has not yet achieved a level where access to relics have been
            unlocked.
        Relic tier of '1', indicates that the character has achieved the required level to access relics,
            but has not yet upgraded to the first level.
    """
    if not isinstance(relic_tier, str) and not isinstance(relic_tier, int):
        err_msg = f"{get_function_name()}: 'relic_tier' argument is required for conversion."
        raise SwgohComlinkValueError(err_msg)
    relic_value = None
    if isinstance(relic_tier, int):
        relic_tier = str(relic_tier)
    if relic_tier in Constants.RELIC_TIERS:
        relic_value = Constants.RELIC_TIERS[relic_tier]
    return relic_value

def parse_swgoh_string(text: str, output: OutputFormat) -> str:
    """
    Parse a SWGOH BBCode-style rich text string and convert it to the
    specified output format.

    Args:
        text:   Raw SWGOH localization string containing BBCode markup.
        output: One of 'terminal', 'discord', 'web', or 'bare'.

    Returns:
        A formatted string in the target format.

    Supported tags:
        [c]          - Open color block
        [RRGGBB]     - Set hex color (must follow [c])
        [-]          - Reset color within a color block
        [/c] [-c]    - Close color block
        [b] [/b]     - Bold
        [i] [/i]     - Italic
        \\n           - Newline (literal backslash-n in source)

    Output formats:
        terminal  - ANSI truecolor escape codes
        discord   - Discord markdown (**bold**, *italic*, no color support)
        web       - HTML with <span style="color:...">, <b>, <em>
        bare      - Plain text, all markup stripped
    """
    tokens = _parse_tokens(text)
    result = []

    # Track state for formats that need open/close pairs
    active_color: str | None = None   # current hex color
    in_color_block = False            # are we inside a [c]...[/c]?
    bold_depth = 0
    italic_depth = 0

    for token in tokens:
        t = token["type"]

        if t == "text":
            result.append(token["value"])

        elif t == "newline":
            result.append("\n")

        elif t == "color":
            active_color = token["hex"]
            if output == "terminal":
                result.append(_hex_to_ansi_truecolor(active_color))
            elif output == "web":
                result.append(f'<span style="color:#{active_color}">')

        elif t == "color_block_open":
            in_color_block = True

        elif t == "color_reset":
            # [-] resets color but stays in the color block
            if output == "terminal" and in_color_block:
                result.append(ANSI_RESET)
                # Re-apply any active bold/italic after reset
                if bold_depth > 0:
                    result.append(ANSI_BOLD)
                if italic_depth > 0:
                    result.append(ANSI_ITALIC)
            elif output == "web" and active_color:
                result.append("</span>")
            active_color = None

        elif t == "color_end":
            in_color_block = False
            if output == "terminal":
                result.append(ANSI_RESET)
                if bold_depth > 0:
                    result.append(ANSI_BOLD)
                if italic_depth > 0:
                    result.append(ANSI_ITALIC)
            elif output == "web" and active_color:
                result.append("</span>")
            active_color = None

        # [c] just marks the start of a color scope — the hex tag sets the actual color
        elif t == "bold_open":
            bold_depth += 1
            if output == "terminal":
                result.append(ANSI_BOLD)
            elif output == "discord":
                result.append("**")
            elif output == "web":
                result.append("<b>")

        elif t == "bold_close":
            bold_depth = max(0, bold_depth - 1)
            if output == "terminal" and bold_depth == 0:
                result.append(ANSI_RESET)
                if active_color:
                    result.append(_hex_to_ansi_truecolor(active_color))
                if italic_depth > 0:
                    result.append(ANSI_ITALIC)
            elif output == "discord":
                result.append("**")
            elif output == "web":
                result.append("</b>")

        elif t == "italic_open":
            italic_depth += 1
            if output == "terminal":
                result.append(ANSI_ITALIC)
            elif output == "discord":
                result.append("*")
            elif output == "web":
                result.append("<em>")

        elif t == "italic_close":
            italic_depth = max(0, italic_depth - 1)
            if output == "terminal" and italic_depth == 0:
                result.append(ANSI_RESET)
                if active_color:
                    result.append(_hex_to_ansi_truecolor(active_color))
                if bold_depth > 0:
                    result.append(ANSI_BOLD)
            elif output == "discord":
                result.append("*")
            elif output == "web":
                result.append("</em>")

    # Close any dangling ANSI sequences
    if output == "terminal" and (active_color or bold_depth or italic_depth):
        result.append(ANSI_RESET)

    # Wrap HTML output in a container
    if output == "web":
        inner = "".join(result)
        return f"<p>{inner}</p>"

    return "".join(result)
