"""Persist pipeline results using Django ORM (replaces SQLAlchemy path when Django is active)."""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.articles.models import Article, ArticleEmbedding, StoryCluster
from core.article_text import normalize_article_body_for_storage
from apps.processing.models import ArticleEnrichment, PipelineRun
from apps.seo.models import SEOData
from apps.trends.models import Topic, TrendSnapshot
from core import config
from core.article_slug import unique_article_slug
from core.dedup import domain_from_url, title_fingerprint
from core.scrape import clean_author_list
from core.seo import seo_fields_for_storage
from core.topics import TopicSignal

logger = logging.getLogger(__name__)


def _allocate_unique_article_slug(
    *,
    title: str,
    url: str,
    fingerprint: str,
    exclude_pk: int | None,
) -> str:
    base = unique_article_slug(title, url, fingerprint=fingerprint)
    candidate = base
    n = 0
    while Article.objects.filter(slug=candidate).exclude(pk=exclude_pk).exists():
        n += 1
        candidate = f"{base}-{n}"[:200]
    return candidate


def _normalize_authors_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for x in raw:
        s = str(x).strip()
        if s:
            out.append(s[:256])
        if len(out) >= 24:
            break
    return out


def _normalize_image_urls_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for x in raw:
        s = str(x).strip()[:2048]
        if s:
            out.append(s)
        if len(out) >= config.SCRAPE_MAX_IMAGES:
            break
    return out


def _get_or_create_story_cluster(fp: str) -> StoryCluster:
    fingerprint = fp[:64]
    sc, _ = StoryCluster.objects.get_or_create(title_fingerprint=fingerprint)
    return sc


def _pick_topic_row(
    topic_rows: dict[tuple[str, str], Topic],
    matched: list[str],
) -> Topic | None:
    if not matched or not topic_rows:
        return None
    for m in matched:
        ml = m.strip().lower()
        for (label, _src), tr in topic_rows.items():
            if label.lower() == ml:
                return tr
    return None


@transaction.atomic
def persist_pipeline_run_django(
    *,
    geo: str,
    lang: str,
    topic_signals: list[TopicSignal],
    results: list[dict[str, Any]],
    meta: dict[str, Any] | None = None,
) -> int:
    """
    Insert pipeline_run, topics, articles, enrichments, embeddings, snapshots, SEOData.
    Returns run id.
    """
    now = timezone.now()
    run = PipelineRun.objects.create(
        started_at=now,
        finished_at=now,
        geo=geo[:16],
        lang=lang[:16],
        status="completed",
        meta=meta or {},
    )

    topic_rows: dict[tuple[str, str], Topic] = {}
    for sig in topic_signals:
        key = (sig.label.strip()[:512], sig.source[:32])
        if key in topic_rows:
            continue
        tr = Topic.objects.create(
            run=run,
            label=sig.label.strip()[:512],
            source=sig.source[:32],
            rank_in_source=sig.rank_in_source,
            reddit_score=sig.reddit_score,
        )
        topic_rows[key] = tr

    model_name = config.OPENAI_EMBEDDING_MODEL[:128]

    for row in results:
        url = (row.get("url") or "")[:2048]
        if not url:
            continue
        title = (row.get("title") or "")[:1024]
        fp = (row.get("title_fingerprint") or title_fingerprint(title))[:64]
        dom = domain_from_url(url)[:256]
        cat = str(row.get("category") or "general").strip()[:64] or "general"

        raw_body = row.get("content")
        raw_body = raw_body if isinstance(raw_body, str) else ""
        proc_body = row.get("processed_content")
        proc_body = proc_body if isinstance(proc_body, str) else ""
        if not proc_body and raw_body:
            proc_body = normalize_article_body_for_storage(raw_body)

        ext_sum = str(row.get("extractive_summary") or "")[:50000]
        authors_norm = clean_author_list(_normalize_authors_list(row.get("authors")))
        image_urls_norm = _normalize_image_urls_list(row.get("images"))

        sc = _get_or_create_story_cluster(fp)

        art = Article.objects.filter(url=url).first()
        if art is None:
            slug_val = _allocate_unique_article_slug(
                title=title,
                url=url,
                fingerprint=fp,
                exclude_pk=None,
            )
            art = Article.objects.create(
                url=url,
                slug=slug_val,
                title=title,
                domain=dom,
                category=cat,
                source_rss=(row.get("source_rss") or "")[:512],
                published_raw=(str(row.get("published"))[:256] if row.get("published") else None),
                title_fingerprint=fp,
                story_cluster=sc,
                content=raw_body,
                processed_content=proc_body,
                extractive_summary=ext_sum,
                authors=authors_norm,
                image_urls=image_urls_norm,
            )
        else:
            art.title = title
            art.domain = dom
            art.category = cat
            art.source_rss = (row.get("source_rss") or "")[:512]
            if row.get("published"):
                art.published_raw = str(row.get("published"))[:256]
            art.title_fingerprint = fp
            art.story_cluster = sc
            art.content = raw_body
            art.processed_content = proc_body
            art.extractive_summary = ext_sum
            art.authors = authors_norm
            art.image_urls = image_urls_norm
            if not art.slug:
                art.slug = _allocate_unique_article_slug(
                    title=title,
                    url=url,
                    fingerprint=fp,
                    exclude_pk=art.pk,
                )
            art.save(
                update_fields=[
                    "title",
                    "domain",
                    "category",
                    "source_rss",
                    "published_raw",
                    "title_fingerprint",
                    "story_cluster",
                    "content",
                    "processed_content",
                    "extractive_summary",
                    "authors",
                    "image_urls",
                    "slug",
                    "updated_at",
                ]
            )

        vec = row.get("title_embedding")
        if isinstance(vec, list) and vec:
            ArticleEmbedding.objects.update_or_create(
                article=art,
                model=model_name,
                defaults={"dimension": len(vec), "vector": vec},
            )

        ideas = row.get("content_angle_ideas") or []
        if not isinstance(ideas, list):
            ideas = []

        seo_raw = row.get("seo")
        seo_store = seo_raw if isinstance(seo_raw, dict) and seo_raw else None

        enr = ArticleEnrichment.objects.create(
            article=art,
            run=run,
            summary=row.get("summary") or "",
            main_topic=(row.get("main_topic") or "")[:512],
            why_trending=row.get("why_trending") or "",
            why_people_care=row.get("why_people_care") or "",
            who_should_care=row.get("who_should_care") or "",
            content_angle_ideas=ideas,
            model=(config.OPENAI_MODEL or "")[:128],
        )

        if seo_store:
            SEOData.objects.create(article_enrichment=enr, **seo_fields_for_storage(seo_store))

        matched = row.get("matched_topics") or []
        tr = _pick_topic_row(topic_rows, matched)
        breakdown = row.get("score_breakdown") or {}
        TrendSnapshot.objects.create(
            run=run,
            topic=tr,
            article=art,
            score_total=float(row.get("score") or 0.0),
            breakdown=breakdown,
        )

    return run.id


def try_persist_django(
    *,
    geo: str,
    lang: str,
    topic_signals: list[TopicSignal],
    results: list[dict[str, Any]],
    meta: dict[str, Any] | None = None,
) -> int | None:
    try:
        return persist_pipeline_run_django(
            geo=geo,
            lang=lang,
            topic_signals=topic_signals,
            results=results,
            meta=meta,
        )
    except Exception as e:
        logger.warning("Django persistence failed: %s", e)
        return None
