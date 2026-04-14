"""OpenAI-compatible text embeddings (batch)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from core import config

logger = logging.getLogger(__name__)


def embed_texts(texts: list[str], model: str | None = None) -> list[list[float]]:
    """
    Return one embedding vector per input string. Empty strings get zero vectors
    of the same dimension as the first successful response (caller should skip empties).
    """
    if not config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set")
    model = model or config.OPENAI_EMBEDDING_MODEL
    url = f"{config.OPENAI_BASE_URL}/embeddings"
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    # OpenAI allows multiple inputs per request
    payload: dict[str, Any] = {"model": model, "input": texts}
    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
    items = data.get("data") or []
    # API returns unsorted by index sometimes
    by_idx = {int(x["index"]): list(map(float, x["embedding"])) for x in items if "embedding" in x}
    return [by_idx[i] for i in range(len(texts))]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def max_sim_to_topics(embedding: list[float], topic_embeddings: list[list[float]]) -> float:
    if not topic_embeddings:
        return 0.0
    return max(cosine_similarity(embedding, te) for te in topic_embeddings)
