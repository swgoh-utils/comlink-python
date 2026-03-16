# coding=utf-8
"""Utility functions for parsing localization strings."""

from __future__ import annotations

import re
from typing import Literal

__all__ = ["parse_swgoh_string"]

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


def _parse_tokens(text: str) -> list[dict[str, str]]:
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
    TAG_RE = re.compile(r"(\[(?:/c|-c|-|/b|/i|b|i|c|[0-9A-Fa-f]{6})\])", re.IGNORECASE)

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
            elif re.fullmatch(r"[0-9A-Fa-f]{6}", inner):
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


def parse_swgoh_string(text: str, output: OutputFormat = "bare") -> str:
    """
    Parse a SWGOH BBCode-style rich text string and convert it to the
    specified output format.

    Args:
        text:   Raw SWGOH localization string containing BBCode markup.
        output: One of 'terminal', 'discord', 'web', or 'bare'. [Default: 'bare']

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
    state = _FormattingState()
    result = []

    for token in tokens:
        token_type = token["type"]

        if token_type == "text":
            result.append(token["value"])
        elif token_type == "newline":
            result.append("\n")
        elif token_type == "color_block_open":
            state.in_color_block = True
        elif token_type == "color":
            _handle_color(token, output, state, result)
        elif token_type == "color_reset":
            _handle_color_reset(output, state, result)
        elif token_type == "color_end":
            _handle_color_end(output, state, result)
        elif token_type == "bold_open":
            _handle_bold_open(output, state, result)
        elif token_type == "bold_close":
            _handle_bold_close(output, state, result)
        elif token_type == "italic_open":
            _handle_italic_open(output, state, result)
        elif token_type == "italic_close":
            _handle_italic_close(output, state, result)

    return _finalize_output(output, state, result)


class _FormattingState:
    """Tracks the current formatting state during parsing."""

    def __init__(self) -> None:
        self.active_color: str | None = None
        self.in_color_block = False
        self.bold_depth = 0
        self.italic_depth = 0


def _handle_color(token: dict[str, str], output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    """Handle color token."""
    state.active_color = token["hex"]
    if output == "terminal":
        result.append(_hex_to_ansi_truecolor(state.active_color))
    elif output == "web":
        result.append(f'<span style="color:#{state.active_color}">')


def _handle_color_reset(output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    """Handle color reset token [-]."""
    if output == "terminal" and state.in_color_block:
        result.append(ANSI_RESET)
        _reapply_terminal_styles(state, result)
    elif output == "web" and state.active_color:
        result.append("</span>")
    state.active_color = None


def _handle_color_end(output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    """Handle color end token [/c]."""
    state.in_color_block = False
    if output == "terminal":
        result.append(ANSI_RESET)
        _reapply_terminal_styles(state, result)
    elif output == "web" and state.active_color:
        result.append("</span>")
    state.active_color = None


def _handle_bold_open(output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    """Handle bold open token [b]."""
    state.bold_depth += 1
    if output == "terminal":
        result.append(ANSI_BOLD)
    elif output == "discord":
        result.append("**")
    elif output == "web":
        result.append("<b>")


def _handle_bold_close(output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    """Handle bold close token [/b]."""
    state.bold_depth = max(0, state.bold_depth - 1)
    if output == "terminal" and state.bold_depth == 0:
        result.append(ANSI_RESET)
        if state.active_color:
            result.append(_hex_to_ansi_truecolor(state.active_color))
        if state.italic_depth > 0:
            result.append(ANSI_ITALIC)
    elif output == "discord":
        result.append("**")
    elif output == "web":
        result.append("</b>")


def _handle_italic_open(output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    """Handle italic open token [i]."""
    state.italic_depth += 1
    if output == "terminal":
        result.append(ANSI_ITALIC)
    elif output == "discord":
        result.append("*")
    elif output == "web":
        result.append("<em>")


def _handle_italic_close(output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    """Handle italic close token [/i]."""
    state.italic_depth = max(0, state.italic_depth - 1)
    if output == "terminal" and state.italic_depth == 0:
        result.append(ANSI_RESET)
        if state.active_color:
            result.append(_hex_to_ansi_truecolor(state.active_color))
        if state.bold_depth > 0:
            result.append(ANSI_BOLD)
    elif output == "discord":
        result.append("*")
    elif output == "web":
        result.append("</em>")


def _reapply_terminal_styles(state: _FormattingState, result: list[str]) -> None:
    """Re-apply active bold/italic styles after ANSI reset."""
    if state.bold_depth > 0:
        result.append(ANSI_BOLD)
    if state.italic_depth > 0:
        result.append(ANSI_ITALIC)


def _finalize_output(output: OutputFormat, state: _FormattingState, result: list[str]) -> str:
    """Finalize and return the formatted output."""
    if output == "terminal" and (state.active_color or state.bold_depth or state.italic_depth):
        result.append(ANSI_RESET)

    formatted = "".join(result)

    if output == "web":
        return f"<p>{formatted}</p>"

    return formatted
