"""Image URL extraction fallbacks for newspaper scrape path."""

from __future__ import annotations

from core.scrape import _extract_image_urls_from_raw_html


def test_html_fallback_og_twitter_lazy_img() -> None:
    html = """
    <head>
    <meta property="og:image" content="https://cdn.example/og.jpg" />
    <meta name="twitter:image" content="/pic/twitter.png" />
    </head>
    <body><img data-src="https://img.site/lazy.webp" alt="x" /></body>
    """
    base = "https://news.example/2024/story/"
    urls = _extract_image_urls_from_raw_html(html, base)
    assert "https://cdn.example/og.jpg" in urls
    assert "https://news.example/pic/twitter.png" in urls
    assert "https://img.site/lazy.webp" in urls


def test_skips_og_image_dimension_meta_tags() -> None:
    html = """
    <meta property="og:image:width" content="1200" />
    <meta property="og:image" content="https://ok/only.jpg" />
    """
    urls = _extract_image_urls_from_raw_html(html, "https://x.com/a")
    assert urls == ["https://ok/only.jpg"]
