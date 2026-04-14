"""Title fingerprinting and semantic story clustering helpers."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urlparse

from core.embeddings import cosine_similarity


def normalize_title(title: str) -> str:
    s = (title or "").lower()
    s = re.sub(r"^[\s\-–—:]+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def title_fingerprint(title: str) -> str:
    n = normalize_title(title)
    return hashlib.sha256(n.encode("utf-8")).hexdigest()[:32]


def domain_from_url(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def assign_story_clusters(
    articles: list[dict[str, Any]],
    embedding_key: str = "title_embedding",
    threshold: float = 0.92,
) -> list[dict[str, Any]]:
    """
    Greedy clustering: each item gets story_cluster_id (int). Same fingerprint
    gets same cluster. Else merge if cosine sim >= threshold to existing rep embedding.
    """
    clusters: list[dict[str, Any]] = []  # {"id", "embedding", "fingerprint"}
    fp_to_cluster: dict[str, int] = {}
    next_id = 0

    out: list[dict[str, Any]] = []
    for a in articles:
        row = dict(a)
        fp = title_fingerprint(str(row.get("title") or ""))
        emb = row.get(embedding_key)

        cid: int | None = None
        if fp in fp_to_cluster:
            cid = fp_to_cluster[fp]
        elif isinstance(emb, list) and emb:
            for c in clusters:
                ce = c.get("embedding")
                if isinstance(ce, list) and cosine_similarity(emb, ce) >= threshold:
                    cid = c["id"]
                    break
            if cid is None:
                cid = next_id
                clusters.append({"id": cid, "embedding": emb, "fingerprint": fp})
                next_id += 1
            fp_to_cluster[fp] = cid
        else:
            cid = next_id
            clusters.append({"id": cid, "embedding": emb, "fingerprint": fp})
            fp_to_cluster[fp] = cid
            next_id += 1

        row["title_fingerprint"] = fp
        row["story_cluster_id"] = cid
        out.append(row)
    return out


def dedupe_by_fingerprint_keep_order(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep first article per title_fingerprint (must be precomputed)."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for a in articles:
        fp = a.get("title_fingerprint") or title_fingerprint(str(a.get("title") or ""))
        if fp in seen:
            continue
        seen.add(fp)
        out.append(a)
    return out
