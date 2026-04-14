"""
Ingestion stage: topics → RSS → match → scrape → cluster.

Produces ``chosen`` article dicts with full ``content`` from feeds/scrape.
No LLM calls; persistence of bodies happens in the final persist step together
with enrichment, but body fields are independent of AI.
"""

from __future__ import annotations

import logging
from typing import Any

from core.rss import resolve_rss_jobs
from core.signals.reddit import RedditPost
from core.topics import TopicSignal

from services.cluster_service import cluster_and_select_top
from services import rss_service
from services.scrape_service import build_scraped_pending
from services.trends_service import collect_topic_signals, match_articles_to_topics

logger = logging.getLogger(__name__)


def run_ingestion(
    *,
    limit: int,
    with_reddit: bool,
    skip_ai: bool,
    rss_urls: list[str] | None = None,
    rss_categories: list[str] | None = None,
    trends_geo: str | None = None,
    trends_lang: str | None = None,
    reddit_limit: int = 20,
    include_unmatched: bool = False,
    allow_newspaper: bool = True,
) -> tuple[str, str, list[TopicSignal], list[RedditPost], list[dict[str, Any]]]:
    """
    Returns ``(resolved_geo, lang, topic_signals, reddit_posts, chosen)``.
    Each item in ``chosen`` includes scraped ``content`` and metadata for enrichment.
    """
    llm_enabled = not skip_ai

    resolved_geo, lang_eff, topic_signals, reddit_posts = collect_topic_signals(
        with_reddit=with_reddit,
        trends_geo=trends_geo,
        trends_lang=trends_lang,
        reddit_limit=reddit_limit,
    )
    logger.info(
        "ingestion: topics geo=%s lang=%s topics=%s reddit_posts=%s",
        resolved_geo,
        lang_eff,
        len(topic_signals),
        len(reddit_posts),
    )

    rss_jobs = resolve_rss_jobs(urls_override=rss_urls, categories=rss_categories)
    categories_assigned = sorted({c for c, _ in rss_jobs})
    logger.info(
        "ingestion: feeds=%s categories=%s",
        len(rss_jobs),
        categories_assigned,
    )

    raw_articles = rss_service.fetch_rss_articles(urls=rss_urls, categories=rss_categories)
    logger.info("ingestion: rss_articles=%s", len(raw_articles))

    n_before = len(raw_articles)
    raw_deduped = rss_service.dedupe_by_url(raw_articles)
    logger.info(
        "ingestion: dedupe before=%s after=%s removed=%s",
        n_before,
        len(raw_deduped),
        n_before - len(raw_deduped),
    )

    matched = match_articles_to_topics(
        raw_deduped=raw_deduped,
        topic_signals=topic_signals,
        limit=limit,
        embeddings_enabled=llm_enabled,
        include_unmatched=include_unmatched,
    )
    logger.info(
        "ingestion: matched=%s embeddings=%s",
        len(matched),
        llm_enabled,
    )

    scrape_cap = max(limit * 3, limit + 8)
    pending = build_scraped_pending(
        matched, scrape_cap, allow_newspaper=allow_newspaper
    )
    logger.info(
        "ingestion: pending=%s scrape_cap=%s allow_newspaper=%s",
        len(pending),
        scrape_cap,
        allow_newspaper,
    )

    if not pending:
        return resolved_geo, lang_eff, topic_signals, reddit_posts, []

    chosen = cluster_and_select_top(pending, limit=limit, skip_ai=skip_ai)
    logger.info(
        "ingestion: chosen=%s limit=%s skip_ai=%s",
        len(chosen),
        limit,
        skip_ai,
    )
    return resolved_geo, lang_eff, topic_signals, reddit_posts, chosen
