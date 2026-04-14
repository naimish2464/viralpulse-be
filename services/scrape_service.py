"""Article enrichment: visit article URL with newspaper3k; RSS body/images only as fallback."""

from __future__ import annotations

import logging
from typing import Any

from core import config
from core.article_content_sanitize import sanitize_extracted_article_body
from core import scrape as te_scrape

logger = logging.getLogger(__name__)


def normalize_article_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Apply shared author/image cleanup to any enrichment result (RSS-only or scraped)."""
    p = dict(payload)
    authors_raw = p.get("authors")
    if isinstance(authors_raw, list):
        authors = [str(a).strip() for a in authors_raw if str(a).strip()]
    else:
        authors = []
    p["authors"] = te_scrape.clean_author_list(authors)
    imgs = te_scrape.filter_article_image_urls(list(p.get("images") or []))
    p["images"] = imgs
    primary = str(p.get("image") or "").strip()
    if primary and primary not in imgs:
        filtered = te_scrape.filter_article_image_urls([primary])
        primary = filtered[0] if filtered else ""
    if not primary and imgs:
        primary = imgs[0]
    p["image"] = primary
    raw = p.get("content")
    if isinstance(raw, str) and raw.strip():
        p["content"] = sanitize_extracted_article_body(raw)
    p.pop("og_image", None)
    p.pop("top_image_url", None)
    es = p.get("extractive_summary")
    if isinstance(es, str) and es.strip():
        t = es.strip()
        if len(t) > 8000:
            t = t[:8000]
        p["extractive_summary"] = t
    else:
        p["extractive_summary"] = ""
    return p


def _prioritize_and_merge_rss_images(scraped: dict[str, Any], rss_images: list[str]) -> dict[str, Any]:
    """
    Image order: og:image, newspaper top image, RSS media, then remaining page images.
    """
    out = dict(scraped)
    og = str(out.pop("og_image", "") or "").strip()
    top = str(out.pop("top_image_url", "") or "").strip()
    paper = list(out.get("images") or [])
    rss_filtered = te_scrape.filter_article_image_urls(list(rss_images or []))
    skip = {u for u in (og, top) if u}
    rest_paper = [u for u in paper if u not in skip]
    ordered: list[str] = []
    seen: set[str] = set()

    def add(u: str) -> None:
        u = u.strip()
        if not u or u in seen:
            return
        seen.add(u)
        ordered.append(u)

    for u in te_scrape.filter_article_image_urls([og, top, *rss_filtered, *rest_paper]):
        add(u)
    capped = te_scrape.filter_article_image_urls(ordered)
    out["images"] = capped
    out["image"] = capped[0] if capped else ""
    return out


def _supplement_scrape_with_rss_body(
    scraped: dict[str, Any],
    rss_plain: str,
    *,
    min_len: int = 200,
) -> dict[str, Any]:
    """If the downloaded page has almost no text, fill body from RSS (scrape still drove the fetch)."""
    text = (scraped.get("content") or "").strip()
    rss = (rss_plain or "").strip()
    if len(text) >= min_len or not rss:
        return scraped
    out = dict(scraped)
    out["content"] = sanitize_extracted_article_body(rss)
    return out


def enrich_article_from_feed_row(
    url: str,
    *,
    title: str,
    rss_plain: str,
    rss_images: list[str],
    min_chars: int | None = None,
    allow_newspaper: bool = True,
) -> dict[str, Any]:
    """
    When ``allow_newspaper`` is True, always download the article URL with newspaper3k
    (title, body, NLP summary, authors, dates, images). RSS snippet is used only if the
    page body is nearly empty or scrape fails. ``allow_newspaper=False`` keeps RSS-only text.
    """
    if not allow_newspaper:
        rss_clean = (rss_plain or "").strip()
        text = rss_clean
        cap = config.SCRAPE_MAX_CONTENT_CHARS
        if cap > 0 and len(text) > cap:
            text = text[:cap]
        imgs = te_scrape.filter_article_image_urls(list(rss_images or []))
        primary = imgs[0] if imgs else ""
        return normalize_article_payload(
            {
                "title": (title or "").strip() or url,
                "content": text,
                "image": primary,
                "images": imgs,
                "description": "",
                "extractive_summary": "",
                "authors": [],
                "article_publish_date": "",
            }
        )

    scraped = te_scrape.scrape_article(url)
    if scraped:
        body_min = min_chars if min_chars is not None else config.RSS_MIN_CHARS_FOR_SKIP_SCRAPE
        scraped = _supplement_scrape_with_rss_body(scraped, rss_plain, min_len=body_min)
        scraped = _prioritize_and_merge_rss_images(scraped, rss_images)
        return normalize_article_payload(scraped)

    logger.debug("Scrape failed for %s; using RSS fallback", url)
    out = te_scrape.enrich_article_content(
        url,
        title=title,
        rss_plain=rss_plain,
        rss_images=rss_images,
        min_chars=0,
    )
    return normalize_article_payload(out)


def build_scraped_pending(
    matched: list[dict[str, Any]],
    scrape_cap: int,
    *,
    allow_newspaper: bool = True,
    min_chars: int | None = None,
) -> list[dict[str, Any]]:
    """Turn matched RSS rows into scraped/enriched pending items for clustering."""
    pending: list[dict[str, Any]] = []
    for item in matched:
        if len(pending) >= scrape_cap:
            break
        url = item["url"]
        rss_plain = str(item.get("rss_plain") or "")
        rss_images = list(item.get("rss_images") or [])
        enriched = enrich_article_from_feed_row(
            url,
            title=str(item.get("title") or ""),
            rss_plain=rss_plain,
            rss_images=rss_images,
            min_chars=min_chars,
            allow_newspaper=allow_newspaper,
        )
        pub = item.get("published") or enriched.get("article_publish_date") or ""
        pending.append(
            {
                "url": url,
                "title": enriched["title"],
                "content": enriched["content"],
                "image": enriched.get("image") or "",
                "images": enriched.get("images") or [],
                "description": enriched.get("description") or "",
                "extractive_summary": enriched.get("extractive_summary") or "",
                "authors": enriched.get("authors") or [],
                "matched_topics": item.get("matched_topics") or [],
                "source_rss": item.get("source_rss") or "",
                "category": item.get("category") or "general",
                "published": pub,
                "semantic_best": float(item.get("semantic_best") or 0),
                "category_backfill": bool(item.get("category_backfill")),
            }
        )
    return pending
