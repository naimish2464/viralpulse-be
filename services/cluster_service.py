"""Story clustering via title embeddings."""

from __future__ import annotations

import logging
from typing import Any

from core import config
from core.dedup import assign_story_clusters
from core.embeddings import embed_texts

logger = logging.getLogger(__name__)


def cluster_and_select_top(
    pending: list[dict[str, Any]],
    *,
    limit: int,
    skip_ai: bool,
) -> list[dict[str, Any]]:
    use_title_embeddings = (
        not skip_ai
        and bool(config.OPENAI_API_KEY)
        and config.TREND_ENGINE_SEMANTIC_ENABLED
    )
    if use_title_embeddings:
        try:
            titles = [(p["title"] or " ").strip() or " " for p in pending]
            vecs = embed_texts(titles)
            for i, p in enumerate(pending):
                p["title_embedding"] = vecs[i] if i < len(vecs) else []
        except Exception as e:
            logger.warning("Title embedding batch for clustering failed: %s", e)
            for p in pending:
                p["title_embedding"] = []
    else:
        for p in pending:
            p["title_embedding"] = []

    pending = assign_story_clusters(
        pending,
        embedding_key="title_embedding",
        threshold=config.TREND_ENGINE_STORY_SIM_THRESHOLD,
    )

    pending.sort(key=lambda x: float(x.get("semantic_best") or 0), reverse=True)
    chosen: list[dict[str, Any]] = []
    seen_cluster: set[int] = set()
    for p in pending:
        cid = p.get("story_cluster_id")
        if cid is not None and cid in seen_cluster:
            continue
        if cid is not None:
            seen_cluster.add(cid)
        chosen.append(p)
        if len(chosen) >= limit:
            break
    return chosen
