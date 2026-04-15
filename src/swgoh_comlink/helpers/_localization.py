# coding=utf-8
"""Utility functions for parsing localization strings."""

from __future__ import annotations

import re
from typing import Any, Literal

__all__ = ["parse_swgoh_string"]

OutputFormat = Literal["terminal", "discord", "web", "bare"]
ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_ITALIC = "\033[3m"
ANSI_UNDERLINE = "\033[4m"
ANSI_STRIKE = "\033[9m"


# ANSI color support: convert hex to nearest 256-color or use truecolor if available
def _hex_to_ansi_truecolor(hex_color: str) -> str:
    """Convert a hex color string (RRGGBB) to an ANSI truecolor escape sequence."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"\033[38;2;{r};{g};{b}m"


def _expand_color_hex(raw: str) -> tuple[int, int, int, int]:
    """
    Expand a SWGOH/NGUI color literal into an (r, g, b, a) tuple.

    Accepted lengths (matching NGUIText.ParseSymbol):
      - 3 digits: RGB,    each nibble duplicated -> RRGGBB, alpha = FF
      - 4 digits: RGBA,   each nibble duplicated -> RRGGBBAA
      - 6 digits: RRGGBB, alpha = FF
      - 8 digits: RRGGBBAA
    """
    raw = raw.lower()
    if len(raw) == 3:
        r = int(raw[0] * 2, 16)
        g = int(raw[1] * 2, 16)
        b = int(raw[2] * 2, 16)
        a = 255
    elif len(raw) == 4:
        r = int(raw[0] * 2, 16)
        g = int(raw[1] * 2, 16)
        b = int(raw[2] * 2, 16)
        a = int(raw[3] * 2, 16)
    elif len(raw) == 6:
        r = int(raw[0:2], 16)
        g = int(raw[2:4], 16)
        b = int(raw[4:6], 16)
        a = 255
    elif len(raw) == 8:
        r = int(raw[0:2], 16)
        g = int(raw[2:4], 16)
        b = int(raw[4:6], 16)
        a = int(raw[6:8], 16)
    else:  # pragma: no cover - regex prevents other lengths
        raise ValueError(f"Unsupported color hex length: {raw!r}")
    return r, g, b, a


def _expand_alpha_hex(raw: str) -> int:
    """Expand a 1-digit alpha hex literal (e.g. 'F') to an int 0-255."""
    return int(raw * 2, 16)


# Tag grammar - order matters. Named tags and parameterized tags are tried
# before bare hex literals because tag names (b, c, f, ...) are also valid
# hex digits.
_TAG_RE = re.compile(
    r"""
    \[ (?:
          /?sub(?:=\d+(?:\.\d+)?)?      # [sub], [/sub], [sub=1.5]
        | /?sup(?:=\d+(?:\.\d+)?)?      # [sup], [/sup], [sup=0.8]
        | /?y(?:=\d+(?:\.\d+)?)?        # [y=1.2], [/y]
        | /c | -c | /b | /i | /u | /s | /t
        | b | i | u | s | c | t | -
        | [0-9A-Fa-f]{8}                # RRGGBBAA
        | [0-9A-Fa-f]{6}                # RRGGBB
        | [0-9A-Fa-f]{4}                # RGBA short
        | [0-9A-Fa-f]{3}                # RGB short
        | [0-9A-Fa-f]                   # single-hex alpha
    ) \]
    """,
    re.IGNORECASE | re.VERBOSE,
)
_HEX_COLOR_RE = re.compile(r"^[0-9A-Fa-f]+$")
_PARAM_RE = re.compile(r"^(/?)(sub|sup|y)(?:=(\d+(?:\.\d+)?))?$", re.IGNORECASE)


def _parse_tokens(text: str) -> list[dict[str, Any]]:
    """
    Tokenize a SWGOH BBCode string into a list of tokens.
    Each token is a dict with a 'type' and relevant fields.

    Token types:
      - 'text':            plain text content                {'value': str}
      - 'color':           set foreground color (any length) {'r','g','b','a','hex6','hex8'}
      - 'alpha':           set alpha only (1-digit hex)      {'a': int}
      - 'color_block_open':      [c]
      - 'color_reset':           [-]
      - 'color_end':             [/c] or [-c]
      - 'bold_open' / 'bold_close'
      - 'italic_open' / 'italic_close'
      - 'underline_open' / 'underline_close'
      - 'strike_open' / 'strike_close'
      - 'sprite_open' / 'sprite_close':  [t] / [/t] (no-op in text outputs)
      - 'sub_open' / 'sub_close':         [sub], [sub=X], [/sub]   {'scale': float|None}
      - 'sup_open' / 'sup_close':         [sup], [sup=X], [/sup]   {'scale': float|None}
      - 'scale_open' / 'scale_close':     [y=X], [/y]              {'scale': float|None}
      - 'newline':         \\n literal escape in the source string
    """
    tokens: list[dict[str, Any]] = []
    last_end = 0

    for match in _TAG_RE.finditer(text):
        # Emit any text between the prior match and this tag.
        if match.start() > last_end:
            _emit_text_segment(tokens, text[last_end : match.start()])
        last_end = match.end()

        inner = match.group(0)[1:-1]
        lower = inner.lower()

        # Parameterized / named tags -------------------------------------------------
        if lower in ("/c", "-c"):
            tokens.append({"type": "color_end"})
            continue
        if lower == "c":
            tokens.append({"type": "color_block_open"})
            continue
        if lower == "-":
            tokens.append({"type": "color_reset"})
            continue
        if lower == "b":
            tokens.append({"type": "bold_open"})
            continue
        if lower == "/b":
            tokens.append({"type": "bold_close"})
            continue
        if lower == "i":
            tokens.append({"type": "italic_open"})
            continue
        if lower == "/i":
            tokens.append({"type": "italic_close"})
            continue
        if lower == "u":
            tokens.append({"type": "underline_open"})
            continue
        if lower == "/u":
            tokens.append({"type": "underline_close"})
            continue
        if lower == "s":
            tokens.append({"type": "strike_open"})
            continue
        if lower == "/s":
            tokens.append({"type": "strike_close"})
            continue
        if lower == "t":
            tokens.append({"type": "sprite_open"})
            continue
        if lower == "/t":
            tokens.append({"type": "sprite_close"})
            continue

        param_match = _PARAM_RE.match(inner)
        if param_match:
            closing, name, scale_raw = param_match.groups()
            name = name.lower()
            scale = float(scale_raw) if scale_raw is not None else None
            if name == "sub":
                token_type = "sub_close" if closing else "sub_open"
            elif name == "sup":
                token_type = "sup_close" if closing else "sup_open"
            else:  # y
                token_type = "scale_close" if closing else "scale_open"
            entry: dict[str, Any] = {"type": token_type}
            if not closing:
                entry["scale"] = scale
            tokens.append(entry)
            continue

        # Hex color literal ----------------------------------------------------------
        if _HEX_COLOR_RE.match(inner):
            if len(inner) == 1:
                tokens.append({"type": "alpha", "a": _expand_alpha_hex(inner)})
            else:
                r, g, b, a = _expand_color_hex(inner)
                tokens.append(
                    {
                        "type": "color",
                        "r": r,
                        "g": g,
                        "b": b,
                        "a": a,
                        "hex6": f"{r:02X}{g:02X}{b:02X}",
                        "hex8": f"{r:02X}{g:02X}{b:02X}{a:02X}",
                    }
                )
            continue

    # Remaining trailing text
    if last_end < len(text):
        _emit_text_segment(tokens, text[last_end:])

    return tokens


def _emit_text_segment(tokens: list[dict[str, Any]], segment: str) -> None:
    """Emit text segment(s), splitting on literal '\\n' escapes into newline tokens."""
    if not segment:
        return
    parts = segment.split("\\n")
    for idx, part in enumerate(parts):
        if part:
            tokens.append({"type": "text", "value": part})
        if idx < len(parts) - 1:
            tokens.append({"type": "newline"})


def parse_swgoh_string(text: str, output: OutputFormat = "bare") -> str:
    """
    Parse a SWGOH BBCode-style rich text string and convert it to the
    specified output format.

    Args:
        text:   Raw SWGOH localization string containing BBCode markup.
        output: One of 'terminal', 'discord', 'web', or 'bare'. [Default: 'bare']

    Returns:
        A formatted string in the target format.

    Supported tags (parity with NGUIText.ParseSymbol):
        ``[c]`` ``[/c]`` ``[-c]``        - Optional color block wrapper
        ``[-]``                          - Reset the active color
        ``[RGB]`` ``[RGBA]``             - Short-form hex color (each nibble duplicated)
        ``[RRGGBB]`` ``[RRGGBBAA]``      - Hex color (alpha defaults to FF when omitted)
        ``[A]``                          - 1-digit hex alpha (reuses previous RGB or white)
        ``[b]`` ``[/b]``                 - Bold
        ``[i]`` ``[/i]``                 - Italic
        ``[u]`` ``[/u]``                 - Underline
        ``[s]`` ``[/s]``                 - Strikethrough
        ``[t]`` ``[/t]``                 - Sprite color forcing (stripped in text output)
        ``[sub]`` ``[sub=X]`` ``[/sub]`` - Subscript (optional font-size scale)
        ``[sup]`` ``[sup=X]`` ``[/sup]`` - Superscript (optional font-size scale)
        ``[y=X]`` ``[/y]``               - Font scaling
        ``\\n``                          - Newline (literal backslash-n in source)

    Notes:
        The `[c]...[/c]` wrapper is optional; bare color codes such as `[FF0000]`
        take effect on their own. A `[-]` anywhere clears the active color.

    Output formats:
        terminal  - ANSI truecolor escape codes + SGR styles
        discord   - Discord markdown (**bold**, *italic*, __underline__, ~~strike~~)
        web       - HTML (<b>, <em>, <u>, <s>, <sub>, <sup>, <span style="...">)
        bare      - Plain text, all markup stripped
    """
    tokens = _parse_tokens(text)
    state = _FormattingState()
    result: list[str] = []

    for token in tokens:
        token_type = token["type"]

        if token_type == "text":
            result.append(str(token["value"]))
        elif token_type == "newline":
            result.append("\n")
        elif token_type == "color_block_open":
            state.in_color_block = True
        elif token_type == "color":
            _handle_color(token, output, state, result)
        elif token_type == "alpha":
            _handle_alpha(token, output, state, result)
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
        elif token_type == "underline_open":
            _handle_underline_open(output, state, result)
        elif token_type == "underline_close":
            _handle_underline_close(output, state, result)
        elif token_type == "strike_open":
            _handle_strike_open(output, state, result)
        elif token_type == "strike_close":
            _handle_strike_close(output, state, result)
        elif token_type == "sub_open":
            _handle_sub_open(token, output, result)
        elif token_type == "sub_close":
            _handle_sub_close(output, result)
        elif token_type == "sup_open":
            _handle_sup_open(token, output, result)
        elif token_type == "sup_close":
            _handle_sup_close(output, result)
        elif token_type == "scale_open":
            _handle_scale_open(token, output, result)
        elif token_type == "scale_close":
            _handle_scale_close(output, result)
        # sprite_open / sprite_close are intentional no-ops in text outputs

    return _finalize_output(output, state, result)


class _FormattingState:
    """Tracks the current formatting state during parsing."""

    def __init__(self) -> None:
        # Active color kept as RGBA tuple + cached hex for renderers.
        self.active_color: tuple[int, int, int, int] | None = None
        self.in_color_block = False
        self.bold_depth = 0
        self.italic_depth = 0
        self.underline_depth = 0
        self.strike_depth = 0

    def any_style_active(self) -> bool:
        return bool(self.bold_depth or self.italic_depth or self.underline_depth or self.strike_depth)


def _web_color_style(color: tuple[int, int, int, int]) -> str:
    """Render an RGBA tuple as a CSS ``color:`` value, preferring ``#HEX`` when opaque."""
    r, g, b, a = color
    if a == 255:
        return f"color:#{r:02X}{g:02X}{b:02X}"
    alpha = round(a / 255, 3)
    return f"color:rgba({r},{g},{b},{alpha})"


def _handle_color(token: dict[str, Any], output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    """Handle color token (set foreground color)."""
    new_color: tuple[int, int, int, int] = (
        int(token["r"]),
        int(token["g"]),
        int(token["b"]),
        int(token["a"]),
    )
    if output == "web" and state.active_color is not None:
        # Close the previous span before opening a new one.
        result.append("</span>")
    state.active_color = new_color
    if output == "terminal":
        result.append(_hex_to_ansi_truecolor(f"{new_color[0]:02X}{new_color[1]:02X}{new_color[2]:02X}"))
    elif output == "web":
        result.append(f'<span style="{_web_color_style(new_color)}">')


def _handle_alpha(token: dict[str, Any], output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    """Handle 1-digit alpha token."""
    alpha = int(token["a"])
    if state.active_color is None:
        new_color = (255, 255, 255, alpha)
    else:
        r, g, b, _ = state.active_color
        new_color = (r, g, b, alpha)
    if output == "web" and state.active_color is not None:
        result.append("</span>")
    state.active_color = new_color
    if output == "terminal":
        # ANSI truecolor foreground has no alpha channel; the RGB stays the same,
        # so only re-emit the sequence if the RGB actually changed.
        result.append(_hex_to_ansi_truecolor(f"{new_color[0]:02X}{new_color[1]:02X}{new_color[2]:02X}"))
    elif output == "web":
        result.append(f'<span style="{_web_color_style(new_color)}">')


def _handle_color_reset(output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    """Handle color reset token [-]."""
    if output == "terminal":
        # Reset covers both active color and all SGR styles; reapply the styles after.
        result.append(ANSI_RESET)
        _reapply_terminal_styles(state, result)
    elif output == "web" and state.active_color is not None:
        result.append("</span>")
    state.active_color = None


def _handle_color_end(output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    """Handle color end token [/c]."""
    state.in_color_block = False
    if output == "terminal":
        result.append(ANSI_RESET)
        _reapply_terminal_styles(state, result)
    elif output == "web" and state.active_color is not None:
        result.append("</span>")
    state.active_color = None


def _handle_bold_open(output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    state.bold_depth += 1
    if output == "terminal":
        result.append(ANSI_BOLD)
    elif output == "discord":
        result.append("**")
    elif output == "web":
        result.append("<b>")


def _handle_bold_close(output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    state.bold_depth = max(0, state.bold_depth - 1)
    if output == "terminal" and state.bold_depth == 0:
        _reset_and_reapply_terminal(state, result, drop_bold=True)
    elif output == "discord":
        result.append("**")
    elif output == "web":
        result.append("</b>")


def _handle_italic_open(output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    state.italic_depth += 1
    if output == "terminal":
        result.append(ANSI_ITALIC)
    elif output == "discord":
        result.append("*")
    elif output == "web":
        result.append("<em>")


def _handle_italic_close(output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    state.italic_depth = max(0, state.italic_depth - 1)
    if output == "terminal" and state.italic_depth == 0:
        _reset_and_reapply_terminal(state, result, drop_italic=True)
    elif output == "discord":
        result.append("*")
    elif output == "web":
        result.append("</em>")


def _handle_underline_open(output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    state.underline_depth += 1
    if output == "terminal":
        result.append(ANSI_UNDERLINE)
    elif output == "discord":
        result.append("__")
    elif output == "web":
        result.append("<u>")


def _handle_underline_close(output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    state.underline_depth = max(0, state.underline_depth - 1)
    if output == "terminal" and state.underline_depth == 0:
        _reset_and_reapply_terminal(state, result, drop_underline=True)
    elif output == "discord":
        result.append("__")
    elif output == "web":
        result.append("</u>")


def _handle_strike_open(output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    state.strike_depth += 1
    if output == "terminal":
        result.append(ANSI_STRIKE)
    elif output == "discord":
        result.append("~~")
    elif output == "web":
        result.append("<s>")


def _handle_strike_close(output: OutputFormat, state: _FormattingState, result: list[str]) -> None:
    state.strike_depth = max(0, state.strike_depth - 1)
    if output == "terminal" and state.strike_depth == 0:
        _reset_and_reapply_terminal(state, result, drop_strike=True)
    elif output == "discord":
        result.append("~~")
    elif output == "web":
        result.append("</s>")


def _handle_sub_open(token: dict[str, Any], output: OutputFormat, result: list[str]) -> None:
    if output != "web":
        return
    scale = token.get("scale")
    if scale is None:
        result.append("<sub>")
    else:
        result.append(f'<sub style="font-size:{_fmt_scale(float(scale))}em">')


def _handle_sub_close(output: OutputFormat, result: list[str]) -> None:
    if output == "web":
        result.append("</sub>")


def _handle_sup_open(token: dict[str, Any], output: OutputFormat, result: list[str]) -> None:
    if output != "web":
        return
    scale = token.get("scale")
    if scale is None:
        result.append("<sup>")
    else:
        result.append(f'<sup style="font-size:{_fmt_scale(float(scale))}em">')


def _handle_sup_close(output: OutputFormat, result: list[str]) -> None:
    if output == "web":
        result.append("</sup>")


def _handle_scale_open(token: dict[str, Any], output: OutputFormat, result: list[str]) -> None:
    if output != "web":
        return
    scale = token.get("scale")
    if scale is None:
        result.append("<span>")
    else:
        result.append(f'<span style="font-size:{_fmt_scale(float(scale))}em">')


def _handle_scale_close(output: OutputFormat, result: list[str]) -> None:
    if output == "web":
        result.append("</span>")


def _fmt_scale(value: float) -> str:
    """Format a float scale without trailing zeros (1.5 stays 1.5, 2.0 becomes 2)."""
    if value == int(value):
        return str(int(value))
    return f"{value:g}"


def _reset_and_reapply_terminal(
    state: _FormattingState,
    result: list[str],
    *,
    drop_bold: bool = False,
    drop_italic: bool = False,
    drop_underline: bool = False,
    drop_strike: bool = False,
) -> None:
    """Emit ANSI_RESET and reapply remaining active color/styles (minus any dropped ones)."""
    if not (
        state.active_color or state.any_style_active() or drop_bold or drop_italic or drop_underline or drop_strike
    ):
        return
    result.append(ANSI_RESET)
    if state.active_color is not None:
        r, g, b, _ = state.active_color
        result.append(_hex_to_ansi_truecolor(f"{r:02X}{g:02X}{b:02X}"))
    if not drop_bold and state.bold_depth > 0:
        result.append(ANSI_BOLD)
    if not drop_italic and state.italic_depth > 0:
        result.append(ANSI_ITALIC)
    if not drop_underline and state.underline_depth > 0:
        result.append(ANSI_UNDERLINE)
    if not drop_strike and state.strike_depth > 0:
        result.append(ANSI_STRIKE)


def _reapply_terminal_styles(state: _FormattingState, result: list[str]) -> None:
    """Re-apply active bold/italic/underline/strike styles after ANSI reset."""
    if state.bold_depth > 0:
        result.append(ANSI_BOLD)
    if state.italic_depth > 0:
        result.append(ANSI_ITALIC)
    if state.underline_depth > 0:
        result.append(ANSI_UNDERLINE)
    if state.strike_depth > 0:
        result.append(ANSI_STRIKE)


def _finalize_output(output: OutputFormat, state: _FormattingState, result: list[str]) -> str:
    """Finalize and return the formatted output, balancing any unclosed markup."""
    if output == "terminal" and (state.active_color or state.any_style_active()):
        result.append(ANSI_RESET)
    elif output == "web":
        # Close any tags the source string left dangling so the HTML stays well-formed.
        # Inner-most first: styles, then color span.
        for _ in range(state.strike_depth):
            result.append("</s>")
        for _ in range(state.underline_depth):
            result.append("</u>")
        for _ in range(state.italic_depth):
            result.append("</em>")
        for _ in range(state.bold_depth):
            result.append("</b>")
        if state.active_color is not None:
            result.append("</span>")

    formatted = "".join(result)

    if output == "web":
        return f"<p>{formatted}</p>"

    return formatted
