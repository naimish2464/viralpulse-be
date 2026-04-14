"""Semantic article ↔ topic matching via embeddings."""

from __future__ import annotations

import logging
from typing import Any

from core import config
from core import match as match_mod
from core.embeddings import cosine_similarity, embed_texts
from core.topics import TopicSignal

logger = logging.getLogger(__name__)


def match_articles(
    articles: list[dict[str, Any]],
    topic_signals: list[TopicSignal],
    *,
    use_semantic: bool | None = None,
) -> list[dict[str, Any]]:
    """
    Match RSS rows to topics using hybrid / semantic / token mode from config.
    Adds matched_topics, semantic_scores (max sim per matched topic optional), semantic_best.
    """
    mode = config.TREND_ENGINE_MATCH_MODE
    if use_semantic is None:
        use_semantic = bool(
            config.TREND_ENGINE_SEMANTIC_ENABLED
            and config.OPENAI_API_KEY
            and mode in ("hybrid", "semantic")
        )

    labels = [t.label for t in topic_signals]
    if not topic_signals:
        return articles

    topic_embeddings: list[list[float]] | None = None
    if use_semantic and mode != "token":
        try:
            topic_embeddings = embed_texts(labels)
        except Exception as e:
            logger.warning("Topic embeddings failed: %s; falling back to token match", e)
            topic_embeddings = None

    out: list[dict[str, Any]] = []
    titles = [(a.get("title") or "").strip() for a in articles]

    title_embeddings: list[list[float]] | None = None
    if topic_embeddings is not None and mode != "token":
        try:
            title_embeddings = embed_texts([t or " " for t in titles])
        except Exception as e:
            logger.warning("Title embeddings failed: %s; token match for batch", e)
            title_embeddings = None

    for i, a in enumerate(articles):
        title = titles[i]
        row = dict(a)
        matched: list[str] = []
        best_sim = 0.0
        token_ok, token_matched = match_mod.match_article_to_topics(title, labels)

        if topic_embeddings and title_embeddings and i < len(title_embeddings):
            te = title_embeddings[i]
            sims: list[tuple[str, float]] = []
            for sig, vec in zip(topic_signals, topic_embeddings, strict=True):
                s = cosine_similarity(te, vec)
                sims.append((sig.label, s))
                best_sim = max(best_sim, s)
            semantic_matched = [lab for lab, s in sims if s >= config.TREND_ENGINE_SEMANTIC_MIN_SIM]

            if mode == "semantic":
                matched = semantic_matched
            else:
                # hybrid
                if semantic_matched:
                    matched = list(dict.fromkeys(semantic_matched + token_matched))
                elif token_ok:
                    matched = token_matched
        else:
            if token_ok:
                matched = token_matched

        if not matched:
            continue
        row["matched_topics"] = matched
        row["semantic_best"] = round(best_sim, 4) if topic_embeddings and title_embeddings else 0.0
        if logger.isEnabledFor(logging.DEBUG) and topic_embeddings and title_embeddings:
            logger.debug(
                "semantic_match title=%r best_sim=%.4f min_sim=%.4f",
                (title or "")[:100],
                best_sim,
                config.TREND_ENGINE_SEMANTIC_MIN_SIM,
            )
        out.append(row)
    return out
