"""Map UI/nav category slugs to persisted RSS ``Article.category`` keys."""

from __future__ import annotations

from typing import Any

from core.rss_feeds import RSS_FEEDS_BY_CATEGORY, normalize_category_key

# Navbar slugs that differ from RSS keys (e.g. tech → technology).
_SLUG_TO_RSS: dict[str, str] = {
    "tech": "technology",
    "current-affairs": "current_affairs",
    "hollywood-tv": "hollywood_tv",
}


def resolved_rss_category_for_filter(
    *,
    category: str,
    category_slug: str,
) -> str:
    """
    Effective category for ``iexact`` filters.

    Non-empty ``category`` wins. Else ``category_slug`` maps to an RSS key.
    Unknown slug → ``""`` (no filter, like home trending).
    """
    c = (category or "").strip()
    if c:
        return c
    raw = (category_slug or "").strip()
    if not raw:
        return ""
    key = normalize_category_key(raw)
    if key in ("trending", "quiz", "general"):
        return ""
    key = _SLUG_TO_RSS.get(key, key)
    if key in RSS_FEEDS_BY_CATEGORY:
        return key
    return ""


def nav_slug_for_rss_key(rss_key: str) -> str:
    """Navbar / route slug for a stored ``Article.category`` value."""
    key = normalize_category_key(rss_key)
    for slug, mapped in _SLUG_TO_RSS.items():
        if mapped == key:
            return slug
    return key.replace("_", "-")


def categories_meta_payload() -> list[dict[str, Any]]:
    """
    Categories for nav, filters, and admin (virtual feeds + RSS-backed keys).
    """
    virtual: list[dict[str, Any]] = [
        {
            "key": "trending",
            "slug": "trending",
            "label": "Trending",
            "rss_key": None,
            "feed_count": 0,
            "virtual": True,
        },
        {
            "key": "quiz",
            "slug": "quiz",
            "label": "Quiz",
            "rss_key": None,
            "feed_count": 0,
            "virtual": True,
        },
    ]
    rows: list[dict[str, Any]] = []
    for rss_key in sorted(RSS_FEEDS_BY_CATEGORY.keys()):
        feeds = RSS_FEEDS_BY_CATEGORY[rss_key]
        rows.append(
            {
                "key": rss_key,
                "slug": nav_slug_for_rss_key(rss_key),
                "label": rss_key.replace("_", " ").title(),
                "rss_key": rss_key,
                "feed_count": len(feeds),
                "virtual": False,
            }
        )
    return virtual + rows
