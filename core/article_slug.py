"""URL-safe unique slugs for persisted articles (no UI coupling)."""

from __future__ import annotations

import hashlib
import re

from django.utils.text import slugify


def unique_article_slug(title: str, url: str, *, fingerprint: str = "") -> str:
    """
    Stable slug from title plus a short hash so different URLs stay distinct.

    ``fingerprint`` should be the existing title fingerprint (hex) when available.
    """
    t = (title or "").strip() or "article"
    base = slugify(t)[:72] or "article"
    fp = (fingerprint or "").strip()[:32]
    if len(fp) < 8:
        fp = hashlib.sha256((url or "").encode("utf-8")).hexdigest()[:12]
    else:
        fp = fp[:12]
    combined = f"{base}-{fp}"
    combined = re.sub(r"-{2,}", "-", combined).strip("-")
    return combined[:200]
