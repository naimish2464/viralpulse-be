"""RSS ingestion: resolve jobs, fetch feeds, normalize entries (content / summary / description)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import feedparser

from core import config
from core import rss as te_rss
from core.article_url import article_page_url_from_feed_entry
from core.rss_extract import (
    extract_entry_body_html,
    extract_entry_body_plain,
    extract_entry_images,
)


def dedupe_by_url(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for a in articles:
        u = a.get("url") or ""
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(a)
    return out


def append_category_backfill(
    matched: list[dict[str, Any]],
    raw_deduped: list[dict[str, Any]],
    scrape_cap: int,
) -> list[dict[str, Any]]:
    """Round-robin unmatched articles by RSS category so multi-category runs surface all feeds."""
    matched_urls = {a.get("url") for a in matched if a.get("url")}
    unmatched = [a for a in raw_deduped if a.get("url") and a["url"] not in matched_urls]
    if not unmatched:
        return matched
    max_add = max(0, scrape_cap - len(matched))
    if max_add <= 0:
        return matched
    cat_order: list[str] = []
    seen_cat: set[str] = set()
    for a in raw_deduped:
        c = a.get("category") or "general"
        if c not in seen_cat:
            seen_cat.add(c)
            cat_order.append(c)
    pools: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for a in unmatched:
        c = a.get("category") or "general"
        pools[c].append(dict(a))
    backfill: list[dict[str, Any]] = []
    while len(backfill) < max_add:
        progressed = False
        for c in cat_order:
            if len(backfill) >= max_add:
                break
            if pools[c]:
                row = pools[c].pop(0)
                row["matched_topics"] = []
                row["semantic_best"] = 0.0
                row["category_backfill"] = True
                backfill.append(row)
                progressed = True
        if not progressed:
            break
    return matched + backfill


def parse_feed_entry_to_article(
    entry: dict[str, Any],
    *,
    category: str,
    source_label: str,
) -> dict[str, Any] | None:
    """
    Map a feedparser entry to a normalized article dict.
    Body plain/HTML follow ``core.rss_extract`` (content > summary_detail/summary > description).
    """
    title = (entry.get("title") or "").strip()
    if not title:
        return None
    link = (entry.get("link") or "").strip()
    page_url = article_page_url_from_feed_entry(entry, fallback_link=link).strip()
    if not page_url:
        return None
    published = entry.get("published") or entry.get("updated")
    body_html = extract_entry_body_html(entry)
    rss_plain = extract_entry_body_plain(entry)
    rss_images = extract_entry_images(entry, body_html=body_html)
    return {
        "title": title,
        "url": page_url,
        "source_rss": str(source_label),
        "published": published,
        "category": category,
        "rss_plain": rss_plain,
        "rss_html_raw": body_html,
        "rss_images": rss_images,
    }


def fetch_rss_articles(
    urls: list[str] | None = None,
    categories: list[str] | None = None,
    limit_per_feed: int | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch and normalize RSS/Atom entries. Parsing handles ``content``, ``summary``,
    ``summary_detail``, and ``description`` (including dict ``value`` forms).
    """
    import logging

    logger = logging.getLogger(__name__)
    jobs = te_rss.resolve_rss_jobs(urls_override=urls, categories=categories)
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
                row = parse_feed_entry_to_article(
                    entry, category=category, source_label=str(source)
                )
                if row:
                    articles.append(row)
        except Exception as e:
            logger.warning("RSS fetch failed for %s: %s", rss_url, e)
    return articles
