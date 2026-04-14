"""Viral score breakdown for enriched articles (no I/O)."""

from __future__ import annotations

from typing import Any

from core import score as score_mod
from core.signals.reddit import RedditPost
from core.topics import TopicSignal


def score_article(
    merged: dict[str, Any],
    *,
    topic_signals: list[TopicSignal],
    reddit_posts: list[RedditPost] | None,
    with_reddit: bool,
    semantic_skipped: bool,
) -> tuple[float, dict[str, Any]]:
    """Weighted score and component breakdown (v2)."""
    posts = reddit_posts if with_reddit else None
    return score_mod.trend_score_breakdown(
        merged,
        topic_signals=topic_signals,
        reddit_posts=posts,
        semantic_skipped=semantic_skipped,
    )
