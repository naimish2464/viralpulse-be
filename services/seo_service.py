"""SEO package generation (optional via flags and score caps)."""

from __future__ import annotations

from typing import Any

from core import config
from core import seo as seo_mod


def maybe_generate_seo(
    title: str,
    summary: str,
    *,
    main_topic: str,
    url: str,
    seo_enabled: bool,
    llm_enabled: bool,
    score_total: float,
    seo_calls_so_far: int,
) -> dict[str, Any] | None:
    """
    Returns a SEO dict only when all gates pass: ``seo_enabled``, ``llm_enabled``,
    API key, score floor, and per-run cap.
    """
    if not (
        seo_enabled
        and llm_enabled
        and config.OPENAI_API_KEY
        and score_total >= config.TREND_ENGINE_SEO_MIN_SCORE
        and seo_calls_so_far < config.TREND_ENGINE_SEO_MAX_PER_RUN
    ):
        return None
    got = seo_mod.generate_seo(
        title,
        summary,
        main_topic=main_topic,
        url=url,
    )
    return got if got else None
