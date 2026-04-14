"""Match article titles to trend topics (token-aware)."""

from __future__ import annotations

import re
from typing import Any

# Tokens ignored when counting multi-word topic overlap (avoids "of"/"the" false positives).
_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "from",
        "with",
        "by",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "we",
        "our",
        "you",
        "your",
        "they",
        "their",
        "them",
        "he",
        "she",
        "his",
        "her",
        "vs",
        "v",
        "into",
        "over",
        "after",
        "before",
        "between",
        "through",
        "during",
        "about",
        "against",
        "without",
        "within",
        "than",
        "then",
        "so",
        "if",
        "how",
        "what",
        "when",
        "where",
        "who",
        "why",
        "all",
        "any",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "too",
        "very",
        "just",
        "can",
        "will",
        "may",
        "might",
        "must",
        "shall",
        "should",
        "could",
        "would",
        "new",
        "now",
        "also",
        "here",
        "there",
        "out",
        "up",
        "down",
    }
)


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def _meaningful_tokens(tokens: set[str]) -> set[str]:
    return {t for t in tokens if t not in _STOPWORDS and len(t) >= 2}


def _multiword_overlap_ok(topic_lower: str, art_tokens: set[str]) -> bool:
    """Require overlap on meaningful tokens only; stricter when few content words."""
    tt = _tokens(topic_lower)
    tt_m = _meaningful_tokens(tt)
    art_m = _meaningful_tokens(art_tokens)
    if not tt_m:
        return False
    overlap_m = tt_m & art_m
    n = len(tt_m)
    if n == 1:
        w = next(iter(tt_m))
        return len(w) >= 4 and w in art_m
    # At least 2 meaningful topic tokens must appear in the title (meaningful side).
    need = min(n, max(2, (n + 1) // 2))
    return len(overlap_m) >= need


def match_article_to_topics(article_title: str, topics: list[str]) -> tuple[bool, list[str]]:
    """
    True if relevant; also returns which topics matched.
    - Full phrase substring (case-insensitive), or
    - Multi-word topic: overlap on **meaningful** (non-stopword) tokens; at least two
      content words for phrases with 2+ meaningful tokens, or one token of length >= 4.
    - Single token topic: token length >= 3 and appears in title tokens
    """
    title_lower = article_title.lower()
    art_tokens = _tokens(article_title)
    matched: list[str] = []
    for t in topics:
        t_strip = t.strip().lower()
        if not t_strip:
            continue
        if t_strip in title_lower:
            matched.append(t)
            continue
        tt = _tokens(t)
        if not tt:
            continue
        if len(tt) == 1:
            w = next(iter(tt))
            if len(w) >= 3 and w in art_tokens:
                matched.append(t)
            continue
        if _multiword_overlap_ok(t_strip, art_tokens):
            matched.append(t)
    return (len(matched) > 0, matched)


def filter_articles_by_topics(
    articles: list[dict[str, Any]],
    topics: list[str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for a in articles:
        title = a.get("title") or ""
        ok, matched = match_article_to_topics(title, topics)
        if ok:
            row = dict(a)
            row["matched_topics"] = matched
            out.append(row)
    return out
