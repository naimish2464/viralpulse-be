"""Heuristic trend score v2 + optional Reddit boost; component breakdown for persistence."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from core import config
from core.dedup import domain_from_url
from core.match import _meaningful_tokens, _tokens
from core.signals.reddit import RedditPost
from core.topics import TopicSignal


def reddit_signal_boost(matched_topics: list[str], reddit_posts: list[RedditPost]) -> float:
    """Up to +3 from Reddit post scores when titles overlap topic tokens."""
    if not reddit_posts or not matched_topics:
        return 0.0
    topic_tokens: set[str] = set()
    for t in matched_topics:
        topic_tokens |= _meaningful_tokens(_tokens(t))
    if not topic_tokens:
        return 0.0
    best = 0
    for p in reddit_posts:
        if _meaningful_tokens(_tokens(p.title)) & topic_tokens:
            best = max(best, p.score)
    return min(3.0, best / 100.0)


def _norm01_trend_rank(rank: int, max_rank: int = 50) -> float:
    """Higher when rank is better (1 is best)."""
    r = max(1, min(rank, max_rank))
    return 1.0 - (r - 1) / max(max_rank, 1)


def _norm01_reddit_score(score: int) -> float:
    return min(1.0, max(0.0, score / 5000.0))


def _recency_score(published_raw: str | None, fetched_at: datetime | None = None) -> float:
    if not published_raw or not str(published_raw).strip():
        return 0.5
    try:
        dt = parsedate_to_datetime(str(published_raw))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return 0.5
    now = fetched_at or datetime.now(timezone.utc)
    age_h = (now - dt).total_seconds() / 3600.0
    if age_h < 0:
        return 1.0
    if age_h < 6:
        return 1.0
    if age_h < 24:
        return 0.85
    if age_h < 72:
        return 0.6
    if age_h < 168:
        return 0.35
    return 0.15


_DEFAULT_DOMAIN_TIERS: dict[str, float] = {
    "techcrunch.com": 0.9,
    "bbc.co.uk": 0.95,
    "theverge.com": 0.88,
}


def _source_quality(url: str) -> float:
    host = domain_from_url(url)
    tiers = {**_DEFAULT_DOMAIN_TIERS, **config.SOURCE_QUALITY_TIERS}
    if not host:
        return float(tiers.get("default", 0.55))
    h = host.lower()
    if h in tiers:
        return float(tiers[h])
    for dom, val in tiers.items():
        if dom != "default" and (h == dom or h.endswith("." + dom)):
            return float(val)
    return float(tiers.get("default", 0.55))


def _signals_by_label(signals: list[TopicSignal]) -> dict[str, TopicSignal]:
    m: dict[str, TopicSignal] = {}
    for s in signals:
        key = s.label_normalized
        if key not in m:
            m[key] = s
    return m


def trend_score_breakdown(
    article: dict[str, Any],
    *,
    topic_signals: list[TopicSignal],
    reddit_posts: list[RedditPost] | None = None,
    fetched_at: datetime | None = None,
    semantic_skipped: bool = False,
) -> tuple[float, dict[str, Any]]:
    """
    Weighted v2 score and a JSON-serializable breakdown.
    """
    by_label = _signals_by_label(topic_signals)
    matched = article.get("matched_topics") or []
    trend_raw = 0.0
    social_raw = 0.0
    for lab in matched:
        key = re.sub(r"\s+", " ", str(lab).strip().lower())
        sig = by_label.get(key)
        if sig is None:
            for s in topic_signals:
                if s.label_normalized == key:
                    sig = s
                    break
        if sig is None:
            continue
        if sig.source == "google":
            trend_raw = max(trend_raw, _norm01_trend_rank(sig.rank_in_source))
        if sig.reddit_score is not None:
            social_raw = max(social_raw, _norm01_reddit_score(sig.reddit_score))

    if reddit_posts and matched:
        social_raw = max(social_raw, reddit_signal_boost(matched, reddit_posts) / 3.0)

    rec_raw = _recency_score(article.get("published"), fetched_at)
    sem_raw = float(article.get("semantic_best") or 0.0)
    src_raw = _source_quality(str(article.get("url") or ""))

    content = article.get("content") or ""
    length_bonus = 0.0
    if len(content) > 500:
        length_bonus = 1.0
    elif len(content) > 100:
        length_bonus = 0.5
    image_bonus = 1.0 if article.get("image") else 0.0

    w = config
    sem_weight = 0.0 if semantic_skipped else w.SCORE_W_SEMANTIC
    total = (
        w.SCORE_W_TREND * trend_raw
        + w.SCORE_W_SOCIAL * social_raw
        + w.SCORE_W_RECENCY * rec_raw
        + w.SCORE_W_SOURCE * src_raw
        + sem_weight * sem_raw
        + w.SCORE_BONUS_LENGTH * length_bonus
        + w.SCORE_BONUS_IMAGE * image_bonus
    )
    breakdown = {
        "trend_signal": round(trend_raw, 4),
        "social_signal": round(social_raw, 4),
        "recency": round(rec_raw, 4),
        "source_quality": round(src_raw, 4),
        "semantic_relevance": round(sem_raw, 4),
        "semantic_skipped": semantic_skipped,
        "length_bonus": round(length_bonus, 4),
        "image_bonus": round(image_bonus, 4),
        "weights": {
            "trend": w.SCORE_W_TREND,
            "social": w.SCORE_W_SOCIAL,
            "recency": w.SCORE_W_RECENCY,
            "source": w.SCORE_W_SOURCE,
            "semantic": w.SCORE_W_SEMANTIC,
        },
    }
    return round(float(total), 3), breakdown


def trend_score(
    article: dict[str, Any],
    reddit_posts: list[RedditPost] | None = None,
    topic_signals: list[TopicSignal] | None = None,
) -> float:
    """
    Composite v2 score when topic_signals provided; else legacy length/image/reddit.
    """
    if topic_signals:
        total, _ = trend_score_breakdown(
            article,
            topic_signals=topic_signals,
            reddit_posts=reddit_posts,
        )
        return total
    score = 0.0
    content = article.get("content") or ""
    if len(content) > 500:
        score += 2.0
    elif len(content) > 100:
        score += 1.0
    if article.get("image"):
        score += 1.0
    matched = article.get("matched_topics") or []
    if reddit_posts and matched:
        score += reddit_signal_boost(matched, reddit_posts)
    return round(score, 2)
