"""LLM article enrichment (optional via ``llm_enabled``)."""

from __future__ import annotations

import logging
from typing import Any

from core import ai as ai_mod
from core import config

logger = logging.getLogger(__name__)


def enrich_article(
    title: str,
    content: str,
    matched_topics: list[str],
    *,
    llm_enabled: bool,
) -> dict[str, Any]:
    """
    When ``llm_enabled`` is False or no API key, returns placeholder enrichment.
    When True, calls the configured chat model; failures fall back to placeholder.
    """
    if not llm_enabled or not config.OPENAI_API_KEY:
        if llm_enabled and not config.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY missing; using placeholder enrichment")
        return ai_mod.enrich_placeholder(title, content, matched_topics)
    try:
        return ai_mod.enrich(title, content)
    except Exception as e:
        logger.warning("AI enrich failed: %s; using placeholder", e)
        return ai_mod.enrich_placeholder(title, content, matched_topics)
