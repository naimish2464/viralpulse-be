"""Orchestrate AI enrichment, scoring, and optional SEO for articles."""

from __future__ import annotations

from typing import Any

from core.dedup import title_fingerprint
from core.signals.reddit import RedditPost
from core.topics import TopicSignal

from core.article_text import normalize_article_body_for_storage

from services import ai_service, scoring_service, seo_service


def enrich_chosen_to_results(
    chosen: list[dict[str, Any]],
    *,
    topic_signals: list[TopicSignal],
    reddit_posts: list[RedditPost],
    with_reddit: bool,
    llm_enabled: bool,
    seo_enabled: bool,
) -> tuple[list[dict[str, Any]], int]:
    """
    ``llm_enabled`` gates real LLM calls (maps to ``not skip_ai``).
    ``seo_enabled`` gates the SEO pass (requires LLM path and config caps).
    """
    results: list[dict[str, Any]] = []
    seo_calls = 0
    semantic_skipped = not llm_enabled

    for merged in chosen:
        raw_content = merged.get("content") or ""
        processed_content = normalize_article_body_for_storage(raw_content)

        enr = ai_service.enrich_article(
            merged["title"],
            raw_content,
            merged["matched_topics"],
            llm_enabled=llm_enabled,
        )

        merged["summary"] = enr["summary"]
        merged["main_topic"] = enr["main_topic"]
        merged["why_trending"] = enr["why_trending"]
        merged["why_people_care"] = enr.get("why_people_care", "")
        merged["who_should_care"] = enr.get("who_should_care", "")
        merged["content_angle_ideas"] = enr.get("content_angle_ideas") or []

        total, breakdown = scoring_service.score_article(
            merged,
            topic_signals=topic_signals,
            reddit_posts=reddit_posts,
            with_reddit=with_reddit,
            semantic_skipped=semantic_skipped,
        )
        merged["score"] = total
        merged["score_breakdown"] = breakdown

        seo_payload = seo_service.maybe_generate_seo(
            merged["title"],
            merged["summary"],
            main_topic=merged.get("main_topic") or "",
            url=str(merged.get("url") or ""),
            seo_enabled=seo_enabled,
            llm_enabled=llm_enabled,
            score_total=total,
            seo_calls_so_far=seo_calls,
        )
        if seo_payload:
            seo_calls += 1

        results.append(
            {
                "title": merged["title"],
                "url": merged["url"],
                "summary": merged["summary"],
                "main_topic": merged["main_topic"],
                "why_trending": merged["why_trending"],
                "why_people_care": merged["why_people_care"],
                "who_should_care": merged["who_should_care"],
                "content_angle_ideas": merged["content_angle_ideas"],
                "image": merged["image"],
                "images": merged.get("images") or [],
                "description": merged.get("description") or "",
                "extractive_summary": merged.get("extractive_summary") or "",
                "authors": merged.get("authors") or [],
                "content": raw_content,
                "processed_content": processed_content,
                "category": merged.get("category") or "general",
                "category_backfill": bool(merged.get("category_backfill")),
                "score": merged["score"],
                "score_breakdown": breakdown,
                "matched_topics": merged["matched_topics"],
                "source_rss": merged["source_rss"],
                "semantic_best": merged.get("semantic_best", 0),
                "story_cluster_id": merged.get("story_cluster_id"),
                "title_fingerprint": merged.get("title_fingerprint")
                or title_fingerprint(merged["title"]),
                "published": merged.get("published"),
                "title_embedding": merged.get("title_embedding"),
                "seo": seo_payload,
            }
        )
    return results, seo_calls
