"""
Pipeline orchestration — trend → RSS → ingest → enrich → persist.

**Ingestion** (``services.ingestion_service.run_ingestion``): topics, RSS fetch/dedupe,
topic match, scrape/body enrichment, clustering. Each chosen row carries full
``content`` from the feed or scraper; nothing here depends on the LLM.

**Enrichment** (``services.enrichment_service.enrich_chosen_to_results``): optional
LLM fields, scoring, optional SEO. Summary without AI uses a truncated body
(see ``core.ai.enrich_placeholder``). Persisted article bodies are written from
the pipeline row and do not require AI.

**Persistence**: when enabled, stores ``Article.content`` / ``processed_content``
along with per-run enrichments and snapshots.

``skip_ai`` disables LLM enrichment and embedding-based match/cluster paths.
``skip_seo`` disables the SEO LLM pass (and SEO also requires AI + env gates).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Literal, overload

from core import config
from core.db.persist import try_persist

from services.enrichment_service import enrich_chosen_to_results
from services.ingestion_service import run_ingestion

logger = logging.getLogger(__name__)


@overload
def run_pipeline(
    limit: int = 10,
    with_reddit: bool = False,
    skip_ai: bool = False,
    skip_seo: bool = False,
    rss_urls: list[str] | None = None,
    rss_categories: list[str] | None = None,
    trends_geo: str | None = None,
    trends_lang: str | None = None,
    reddit_limit: int = 20,
    save_to_db: bool | None = None,
    include_unmatched: bool = False,
    seo_cli_on: bool = False,
    seo_cli_off: bool = False,
    allow_newspaper: bool = True,
    *,
    return_run_id: Literal[False] = False,
) -> list[dict[str, Any]]: ...


@overload
def run_pipeline(
    limit: int = 10,
    with_reddit: bool = False,
    skip_ai: bool = False,
    skip_seo: bool = False,
    rss_urls: list[str] | None = None,
    rss_categories: list[str] | None = None,
    trends_geo: str | None = None,
    trends_lang: str | None = None,
    reddit_limit: int = 20,
    save_to_db: bool | None = None,
    include_unmatched: bool = False,
    seo_cli_on: bool = False,
    seo_cli_off: bool = False,
    allow_newspaper: bool = True,
    *,
    return_run_id: Literal[True],
) -> tuple[list[dict[str, Any]], int | None]: ...


def _resolve_seo_enabled(
    *,
    skip_seo: bool,
    seo_cli_off: bool,
    seo_cli_on: bool,
) -> bool:
    if skip_seo or seo_cli_off:
        return False
    if seo_cli_on:
        return True
    return bool(config.TREND_ENGINE_SEO_ENABLED)


def run_pipeline(
    limit: int = 10,
    with_reddit: bool = False,
    skip_ai: bool = False,
    skip_seo: bool = False,
    rss_urls: list[str] | None = None,
    rss_categories: list[str] | None = None,
    trends_geo: str | None = None,
    trends_lang: str | None = None,
    reddit_limit: int = 20,
    save_to_db: bool | None = None,
    include_unmatched: bool = False,
    seo_cli_on: bool = False,
    seo_cli_off: bool = False,
    allow_newspaper: bool = True,
    *,
    return_run_id: bool = False,
) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], int | None]:
    llm_enabled = not skip_ai
    seo_enabled = _resolve_seo_enabled(
        skip_seo=skip_seo,
        seo_cli_off=seo_cli_off,
        seo_cli_on=seo_cli_on,
    )

    logger.info(
        "pipeline: start limit=%s llm_enabled=%s (skip_ai=%s) seo_enabled=%s (skip_seo=%s) with_reddit=%s",
        limit,
        llm_enabled,
        skip_ai,
        seo_enabled,
        skip_seo,
        with_reddit,
    )

    resolved_geo, lang_eff, topic_signals, reddit_posts, chosen = run_ingestion(
        limit=limit,
        with_reddit=with_reddit,
        skip_ai=skip_ai,
        rss_urls=rss_urls,
        rss_categories=rss_categories,
        trends_geo=trends_geo,
        trends_lang=trends_lang,
        reddit_limit=reddit_limit,
        include_unmatched=include_unmatched,
        allow_newspaper=allow_newspaper,
    )
    logger.info(
        "pipeline: step=ingestion geo=%s lang=%s chosen=%s",
        resolved_geo,
        lang_eff,
        len(chosen),
    )

    if not chosen:
        logger.info("pipeline: step=early_exit reason=no_chosen_after_ingestion")
        if return_run_id:
            return [], None
        return []

    # Enrichment — AI (optional), score, SEO (optional); scoring always runs inside service
    results, seo_calls = enrich_chosen_to_results(
        chosen,
        topic_signals=topic_signals,
        reddit_posts=reddit_posts,
        with_reddit=with_reddit,
        llm_enabled=llm_enabled,
        seo_enabled=seo_enabled,
    )
    logger.info(
        "pipeline: step=enrichment rows=%s llm_enabled=%s seo_enabled=%s seo_llm_calls=%s",
        len(results),
        llm_enabled,
        seo_enabled,
        seo_calls,
    )

    if save_to_db is not None:
        do_persist = save_to_db
    else:
        do_persist = bool(config.DATABASE_URL) or bool(os.environ.get("DJANGO_SETTINGS_MODULE"))

    run_id: int | None = None
    if do_persist:
        run_id = try_persist(
            geo=resolved_geo,
            lang=lang_eff,
            topic_signals=topic_signals,
            results=results,
            meta={
                "limit": limit,
                "with_reddit": with_reddit,
                "include_unmatched": include_unmatched,
                "seo_enabled": seo_enabled,
                "seo_calls": seo_calls,
                "skip_ai": skip_ai,
                "skip_seo": skip_seo,
            },
        )
        if run_id is not None:
            logger.info("pipeline: step=11_persist run_id=%s", run_id)
        else:
            logger.warning("pipeline: step=11_persist skipped_or_failed run_id=None")
    else:
        logger.info("pipeline: step=11_persist disabled")

    for r in results:
        r.pop("title_embedding", None)

    logger.info("pipeline: complete rows=%s", len(results))
    if return_run_id:
        return results, run_id
    return results
