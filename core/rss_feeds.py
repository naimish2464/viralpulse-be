"""Category → RSS URL lists (exact URLs from product spec)."""

from __future__ import annotations

RSS_FEEDS_BY_CATEGORY: dict[str, list[str]] = {
    "technology": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
    ],
    "ai": [
        "https://venturebeat.com/category/ai/feed/",
        "https://www.marktechpost.com/feed/",
    ],
    "business": [
        "https://www.forbes.com/business/feed/",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    ],
    "entertainment": [
        "https://www.hollywoodreporter.com/feed/",
        "https://variety.com/feed/",
    ],
    "bollywood": [
        "https://www.bollywoodhungama.com/feed/",
    ],
    "hollywood_tv": [
        "https://feeds.feedburner.com/tvline",
    ],
    "sports": [
        "https://timesofindia.indiatimes.com/sports/rssfeeds/4719148.cms",
    ],
    "current_affairs": [
        "http://rss.cnn.com/rss/edition.rss",
        "https://www.thehindu.com/news/national/?service=rss",
    ],
    "food": [
        "https://www.eater.com/rss/index.xml",
    ],
    "lifestyle": [
        "https://www.theskinnyconfidential.com/feed/",
    ],
    "travel": [
        "https://anywhereweroam.com/feed/",
    ],
    "fashion": [
        "https://www.highsnobiety.com/feeds/rss",
        "https://www.esquire.com/rss/style.xml/",
    ],
    "wellness": [
        "https://www.gq.com/feed/rss",
        "https://tinybuddha.com/feed/",
    ],
    "animals": [
        "https://www.audubon.org/rss.xml",
    ],
}


def normalize_category_key(key: str) -> str:
    return key.strip().lower().replace("-", "_")


def all_category_keys() -> list[str]:
    return list(RSS_FEEDS_BY_CATEGORY.keys())
