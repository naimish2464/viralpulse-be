"""Canonical article URL selection from feedparser-style entries."""

from __future__ import annotations

from core.article_url import article_page_url_from_feed_entry, strip_tracking_query_params


def test_strip_utm_params() -> None:
    u = "https://example.com/path?utm_source=x&utm_medium=y&id=1"
    assert "utm_" not in strip_tracking_query_params(u)
    assert strip_tracking_query_params(u).endswith("id=1")


def test_prefers_canonical_link() -> None:
    entry = {
        "link": "https://example.com/amp/story",
        "links": [
            {"rel": "canonical", "href": "https://example.com/story"},
        ],
    }
    assert article_page_url_from_feed_entry(entry) == "https://example.com/story"


def test_fallback_to_entry_link() -> None:
    entry = {"link": "https://news.site/item?utm_campaign=z"}
    out = article_page_url_from_feed_entry(entry)
    assert out.startswith("https://news.site/item")
    assert "utm_campaign" not in out
