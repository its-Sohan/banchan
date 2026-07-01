"""Unit tests for pure helpers (no DB needed)."""
from app.util import fmt_time, parse_quotes
from datetime import datetime


def test_parse_quotes_basic():
    html, quoted = parse_quotes(">>5 hello world")
    assert quoted == [5]
    assert 'href="#p5"' in html
    assert ">>5" not in html  # escaped to &gt;&gt;5


def test_parse_quotes_escapes_html():
    html, _ = parse_quotes("<script>x</script>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_parse_greentext():
    html, _ = parse_quotes(">be me\n>>1 nope")
    assert "greentext" in html
    # >>1 should still be a quote, not greentext
    assert 'class="quote"' in html


def test_fmt_time():
    dt = datetime(2026, 7, 2, 13, 5, 1)
    assert fmt_time(dt) == "2026-07-02 13:05:01"


def test_empty_body():
    html, quoted = parse_quotes("")
    assert quoted == []
    assert html == ""
