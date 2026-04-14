"""Merge and normalize topic strings from multiple signals."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from core import config
from core.match import _meaningful_tokens, _tokens
from core.signals.reddit import RedditPost


@dataclass
class TopicSignal:
    """A trending topic with source-specific rank for scoring."""

    label: str
    source: str  # "google" | "reddit"
    rank_in_source: int  # 1-based position within that source's list
    reddit_score: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def label_normalized(self) -> str:
        return re.sub(r"\s+", " ", str(self.label).strip().lower())


def normalize_topics(
    *lists: list[str],
    min_len: int | None = None,
) -> list[str]:
    """
    Lowercase, strip, drop duplicates (order preserved), filter short noise.
    """
    min_len = min_len if min_len is not None else config.TOPIC_MIN_LEN
    seen: set[str] = set()
    out: list[str] = []
    for raw in lists:
        for item in raw:
            s = re.sub(r"\s+", " ", str(item).strip().lower())
            if len(s) < min_len:
                continue
            if s not in seen:
                seen.add(s)
                out.append(s)
    return out


def topics_from_reddit(posts: list[RedditPost]) -> list[str]:
    """Use post titles as topic strings (normalized later)."""
    return [p.title for p in posts]


def merge_topic_signals(
    google: list[TopicSignal],
    reddit_posts: list[RedditPost],
    min_len: int | None = None,
) -> list[TopicSignal]:
    """
    Google signals first (preserve order/rank). Append Reddit titles not already
    covered by normalized label match to a google topic.
    """
    min_len = min_len if min_len is not None else config.TOPIC_MIN_LEN
    out: list[TopicSignal] = []
    seen_labels: set[str] = set()

    for g in google:
        ln = g.label_normalized
        if len(ln) < min_len:
            continue
        if ln in seen_labels:
            continue
        seen_labels.add(ln)
        out.append(g)

    for idx, p in enumerate(reddit_posts, start=1):
        title = (p.title or "").strip()
        s = re.sub(r"\s+", " ", title.lower())
        if len(s) < min_len:
            continue
        if s in seen_labels:
            continue
        seen_labels.add(s)
        out.append(
            TopicSignal(
                label=title,
                source="reddit",
                rank_in_source=idx,
                reddit_score=p.score,
            )
        )
    return out


def filter_topic_signals(signals: list[TopicSignal]) -> list[TopicSignal]:
    """
    Optional env-driven hygiene after merge: blocklist substrings, max label length,
    minimum meaningful token count. Defaults are no-ops.
    """
    max_len = config.TREND_ENGINE_TOPIC_MAX_LABEL_LEN
    min_mean = config.TREND_ENGINE_TOPIC_MIN_MEANINGFUL_TOKENS
    block_parts = [
        b.strip().lower()
        for b in config.TREND_ENGINE_TOPIC_BLOCKLIST.split(",")
        if b.strip()
    ]
    out: list[TopicSignal] = []
    for s in signals:
        lab = str(s.label).strip()
        if not lab:
            continue
        low = lab.lower()
        if max_len > 0 and len(lab) > max_len:
            continue
        if any(b and b in low for b in block_parts):
            continue
        if min_mean > 0 and len(_meaningful_tokens(_tokens(lab))) < min_mean:
            continue
        out.append(s)
    return out


def topic_labels(signals: list[TopicSignal]) -> list[str]:
    """Plain labels for backward-compatible matching APIs."""
    return [t.label for t in signals]


def rank_map_for_labels(signals: list[TopicSignal]) -> dict[str, tuple[str, int]]:
    """
    Map normalized label -> (source, rank_in_source) for first occurrence.
    """
    m: dict[str, tuple[str, int]] = {}
    for t in signals:
        key = t.label_normalized
        if key not in m:
            m[key] = (t.source, t.rank_in_source)
    return m
