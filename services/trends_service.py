"""Trend signals (Google Trends + optional Reddit) and article–topic matching."""

from __future__ import annotations

import logging
from typing import Any

from core import config
from core.dedup import dedupe_by_fingerprint_keep_order, title_fingerprint
from core.signals.google_trends import fetch_trending_topic_signals, resolve_trends_geo
from core.signals.reddit import RedditPost, fetch_reddit_hot
from core.topics import TopicSignal, filter_topic_signals, merge_topic_signals

from services.rss_service import append_category_backfill, dedupe_by_url

logger = logging.getLogger(__name__)


def collect_topic_signals(
    *,
    with_reddit: bool,
    trends_geo: str | None,
    trends_lang: str | None,
    reddit_limit: int,
) -> tuple[str, str, list[TopicSignal], list[RedditPost]]:
    resolved_geo = resolve_trends_geo(trends_geo or config.GOOGLE_TRENDS_PN)
    lang_eff = (trends_lang or config.TREND_ENGINE_LANG).strip() or "en"
    google_signals = fetch_trending_topic_signals(geo=trends_geo, language=trends_lang)
    reddit_posts: list[RedditPost] = fetch_reddit_hot(limit=reddit_limit) if with_reddit else []
    topic_signals = filter_topic_signals(merge_topic_signals(google_signals, reddit_posts))
    return resolved_geo, lang_eff, topic_signals, reddit_posts


def match_articles_to_topics(
    *,
    raw_deduped: list[dict[str, Any]],
    topic_signals: list[TopicSignal],
    limit: int,
    embeddings_enabled: bool,
    include_unmatched: bool,
) -> list[dict[str, Any]]:
    """
    Match RSS rows to trend topics (token / semantic). ``embeddings_enabled`` mirrors
    pipeline ``not skip_ai`` plus API key and config for hybrid/semantic match.
    """
    from core import semantic

    use_semantic_match = (
        embeddings_enabled
        and bool(config.OPENAI_API_KEY)
        and config.TREND_ENGINE_SEMANTIC_ENABLED
        and config.TREND_ENGINE_MATCH_MODE in ("hybrid", "semantic")
    )
    scrape_cap = max(limit * 3, limit + 8)
    if not topic_signals:
        logger.warning(
            "No topics from signals; using RSS-only fallback (no trend keyword match)"
        )
        matched = list(raw_deduped)
        for a in matched:
            a.setdefault("matched_topics", [])
            a.setdefault("semantic_best", 0.0)
    else:
        matched = semantic.match_articles(
            raw_deduped, topic_signals, use_semantic=use_semantic_match
        )
        matched = dedupe_by_url(matched)

    if include_unmatched and topic_signals:
        matched = append_category_backfill(matched, raw_deduped, scrape_cap)

    for a in matched:
        a["title_fingerprint"] = title_fingerprint(str(a.get("title") or ""))
    matched = dedupe_by_fingerprint_keep_order(matched)
    return matched
