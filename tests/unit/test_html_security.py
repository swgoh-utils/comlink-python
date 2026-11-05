"""HTML text is escaped while generated markup remains usable."""

import pytest

from swgoh_comlink.helpers import parse_swgoh_string


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("<img src=x onerror=alert(1)>", "&lt;img src=x onerror=alert(1)&gt;"),
        ("<script>alert(1)</script>", "&lt;script&gt;alert(1)&lt;/script&gt;"),
        ("A & B", "A &amp; B"),
        ("&lt;b&gt;", "&amp;lt;b&amp;gt;"),
    ],
)
def test_web_text_cannot_introduce_html(text, expected):
    assert parse_swgoh_string(f"[b]{text}[/b]", output="web") == f"<p><b>{expected}</b></p>"


def test_web_text_keeps_quotes_readable():
    assert parse_swgoh_string('Vader\'s "Choke"', output="web") == '<p>Vader\'s "Choke"</p>'


@pytest.mark.parametrize("output", ["bare", "discord", "terminal"])
def test_non_web_text_is_not_html_escaped(output):
    assert parse_swgoh_string("A & <B>", output=output) == "A & <B>"
