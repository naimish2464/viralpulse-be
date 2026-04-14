"""Optional post-enrichment SEO suggestions via OpenAI-compatible Chat Completions."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from core import config

logger = logging.getLogger(__name__)

SYSTEM_SEO = (
    "You are an experienced SEO editor and marketing lead. Respond with valid JSON only, no markdown. "
    "Stay factual and aligned with the source; do not invent events or quotes. Avoid clickbait spam. "
    'Keys: "optimized_title" (string, max 60 characters), '
    '"meta_description" (string, 150–160 characters for search snippets), '
    '"keywords" (array of exactly 5 short keyword strings), '
    '"slug" (string, lowercase, hyphenated, URL-safe, max 72 characters, no leading/trailing hyphens).'
)


def _slugify(raw: str, *, max_len: int = 72) -> str:
    s = raw.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if len(s) > max_len:
        s = s[:max_len].rstrip("-")
    return s


def _parse_seo_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise
        obj = json.loads(m.group(0))
    title = str(obj.get("optimized_title", "")).strip()
    if len(title) > 60:
        title = title[:57].rstrip() + "…"
    meta = str(obj.get("meta_description", "")).strip().replace("\n", " ")
    if len(meta) > 160:
        meta = meta[:157].rstrip() + "…"
    kw = obj.get("keywords", [])
    if isinstance(kw, str):
        kw = [kw]
    if not isinstance(kw, list):
        kw = []
    keywords = [str(x).strip() for x in kw if str(x).strip()][:5]
    slug_raw = str(obj.get("slug", "")).strip()
    slug = _slugify(slug_raw) if slug_raw else ""
    if not slug and title:
        slug = _slugify(title)
    return {
        "optimized_title": title,
        "meta_description": meta,
        "keywords": keywords[:5],
        "slug": slug,
    }


def seo_fields_for_storage(seo: dict[str, Any]) -> dict[str, Any]:
    """
    Map a generate_seo-style dict to ``SEOData`` model kwargs (no heavy imports).
    """
    keywords = seo.get("keywords")
    if keywords is None:
        kw: list[Any] = []
    elif isinstance(keywords, list):
        kw = keywords
    else:
        kw = [keywords]
    known = {"optimized_title", "meta_description", "slug", "keywords"}
    extras = {k: v for k, v in seo.items() if k not in known}
    return {
        "optimized_title": str(seo.get("optimized_title") or "")[:512],
        "meta_description": str(seo.get("meta_description") or ""),
        "slug": str(seo.get("slug") or "")[:256],
        "keywords": kw,
        "extras": extras if extras else {},
    }


def generate_seo(
    title: str,
    summary: str,
    *,
    main_topic: str = "",
    url: str = "",
) -> dict[str, Any]:
    """
    Call OpenAI-compatible API. Returns optimized_title, meta_description, keywords, slug.
    On hard failure returns empty dict (caller sets seo: null).
    """
    api_key = config.OPENAI_API_KEY
    if not api_key:
        logger.warning("generate_seo: OPENAI_API_KEY missing")
        return {}

    model = (config.TREND_ENGINE_SEO_MODEL or config.OPENAI_MODEL).strip()
    body_summary = (summary or "").strip()
    if len(body_summary) > 4000:
        body_summary = body_summary[:4000] + "\n\n[… truncated]"

    user = (
        f"Original page title: {title}\n"
        f"URL (for context only): {url}\n"
        f"Main topic label: {main_topic}\n\n"
        f"Article summary:\n{body_summary}\n\n"
        "Produce the JSON fields. Titles should be compelling but accurate. "
        "Keywords should match real search intent for this story."
    )
    api_url = f"{config.OPENAI_BASE_URL}/chat/completions"
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_SEO},
            {"role": "user", "content": user},
        ],
        "temperature": 0.35,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            try:
                r = client.post(
                    api_url,
                    json={**payload, "response_format": {"type": "json_object"}},
                    headers=headers,
                )
                r.raise_for_status()
            except httpx.HTTPStatusError:
                r = client.post(api_url, json=payload, headers=headers)
                r.raise_for_status()
            data = r.json()
        text = data["choices"][0]["message"]["content"]
        out = _parse_seo_json(text)
        if not out.get("optimized_title") and not out.get("meta_description"):
            logger.warning("generate_seo: model returned empty SEO fields")
            return {}
        return out
    except Exception as e:
        logger.warning("generate_seo failed: %s", e)
        return {}
