"""HTML text is escaped while generated markup remains usable."""

import pytest

from swgoh_comlink.helpers import parse_swgoh_string


@pytest.mark.parametrize("text", ["<img src=x onerror=alert(1)>", "<script>alert(1)</script>", "A & B", "&lt;b&gt;"])
def test_web_text_cannot_introduce_html(text):
    from html import escape

    assert parse_swgoh_string(f"[b]{text}[/b]", output="web") == f"<p><b>{escape(text)}</b></p>"


@pytest.mark.parametrize("output", ["bare", "discord", "terminal"])
def test_non_web_text_is_not_html_escaped(output):
    assert parse_swgoh_string("A & <B>", output=output) == "A & <B>"
