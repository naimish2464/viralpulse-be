"""Fetch and normalize RSS entries."""

from __future__ import annotations

import logging
import os
from typing import Any

import feedparser

from core import config
from core.article_url import article_page_url_from_feed_entry
from core.rss_extract import (
    extract_entry_body_html,
    extract_entry_body_plain,
    extract_entry_images,
)
from core.rss_feeds import RSS_FEEDS_BY_CATEGORY, normalize_category_key

logger = logging.getLogger(__name__)


def resolve_rss_jobs(
    urls_override: list[str] | None = None,
    categories: list[str] | None = None,
) -> list[tuple[str, str]]:
    """
    Return (category, feed_url) jobs.
    Precedence: explicit urls_override → TREND_ENGINE_RSS env → category map.
    """
    if urls_override:
        return [("general", u.strip()) for u in urls_override if u.strip()]

    if config.RSS_ENV_URLS:
        return [("general", u) for u in config.RSS_ENV_URLS]

    keys: list[str]
    if categories is not None:
        keys = []
        for c in categories:
            k = normalize_category_key(c)
            if k in RSS_FEEDS_BY_CATEGORY:
                keys.append(k)
            else:
                logger.warning("Unknown RSS category %r; skipping", c)
    else:
        raw = os.environ.get("TREND_ENGINE_RSS_CATEGORIES", "").strip()
        if raw:
            keys = []
            for part in raw.split(","):
                k = normalize_category_key(part)
                if not k:
                    continue
                if k in RSS_FEEDS_BY_CATEGORY:
                    keys.append(k)
                else:
                    logger.warning("Unknown RSS category %r in TREND_ENGINE_RSS_CATEGORIES", k)
        else:
            keys = list(RSS_FEEDS_BY_CATEGORY.keys())

    out: list[tuple[str, str]] = []
    for k in keys:
        for url in RSS_FEEDS_BY_CATEGORY.get(k, []):
            out.append((k, url))
    return out


def fetch_rss_entries(
    urls: list[str] | None = None,
    categories: list[str] | None = None,
    limit_per_feed: int | None = None,
) -> list[dict[str, Any]]:
    jobs = resolve_rss_jobs(urls_override=urls, categories=categories)
    limit = limit_per_feed if limit_per_feed is not None else config.RSS_ENTRIES_PER_FEED
    articles: list[dict[str, Any]] = []
    for category, rss_url in jobs:
        try:
            feed = feedparser.parse(rss_url)
            if feed.bozo and getattr(feed, "bozo_exception", None):
                logger.warning("RSS parse issues for %s: %s", rss_url, feed.bozo_exception)
            source = (feed.feed.get("title") or rss_url) if hasattr(feed, "feed") else rss_url
            entries = getattr(feed, "entries", [])[:limit]
            for entry in entries:
                title = (entry.get("title") or "").strip()
                if not title:
                    continue
                link = (entry.get("link") or "").strip()
                page_url = article_page_url_from_feed_entry(entry, fallback_link=link).strip()
                if not page_url:
                    continue
                published = entry.get("published") or entry.get("updated")
                body_html = extract_entry_body_html(entry)
                rss_plain = extract_entry_body_plain(entry)
                rss_images = extract_entry_images(entry, body_html=body_html)
                articles.append(
                    {
                        "title": title,
                        "url": page_url,
                        "source_rss": str(source),
                        "published": published,
                        "category": category,
                        "rss_plain": rss_plain,
                        "rss_html_raw": body_html,
                        "rss_images": rss_images,
                    }
                )
        except Exception as e:
            logger.warning("RSS fetch failed for %s: %s", rss_url, e)
    return articles
