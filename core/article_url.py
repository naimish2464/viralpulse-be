"""Resolve a stable HTTP article URL from RSS/Atom feedparser entries."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

logger = logging.getLogger(__name__)

_TRACKING_QUERY_KEYS = frozenset(
    {
        "fbclid",
        "gclid",
        "igshid",
        "mc_cid",
        "mc_eid",
        "_ga",
        "ocid",
        "ncid",
    }
)


def _rel_normalized(rel: Any) -> str:
    if rel is None:
        return ""
    if isinstance(rel, (list, tuple)):
        return " ".join(str(x).lower() for x in rel)
    return str(rel).lower()


def strip_tracking_query_params(url: str) -> str:
    """Remove common tracking query params (utm_*, fbclid, etc.)."""
    s = (url or "").strip()
    if not s or not s.startswith(("http://", "https://")):
        return s
    try:
        parts = urlparse(s)
        if not parts.query:
            return s
        pairs = parse_qsl(parts.query, keep_blank_values=True)
        kept = [
            (k, v)
            for k, v in pairs
            if k.lower() not in _TRACKING_QUERY_KEYS
            and not k.lower().startswith("utm_")
        ]
        new_query = urlencode(kept, doseq=True)
        return urlunparse(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                parts.params,
                new_query,
                parts.fragment,
            )
        )
    except Exception as e:
        logger.debug(
            "strip_tracking_query_params failed for %r: %s",
            s[:120],
            e,
        )
        return s


def article_page_url_from_feed_entry(
    entry: dict[str, Any],
    *,
    fallback_link: str = "",
) -> str:
    """
    Prefer canonical link, then HTML alternate, then entry.link / fallback.

    Does not HTTP-fetch the page; newspaper3k follows redirects when downloading.
    """
    pairs: list[tuple[str, str, str]] = []
    for block in entry.get("links") or []:
        if not isinstance(block, dict):
            continue
        href = (block.get("href") or block.get("url") or "").strip()
        if not href:
            continue
        rel = _rel_normalized(block.get("rel"))
        typ = str(block.get("type") or "").lower()
        pairs.append((href, rel, typ))

    for href, rel, _typ in pairs:
        if href.startswith(("http://", "https://")) and "canonical" in rel:
            return strip_tracking_query_params(href)

    for href, rel, typ in pairs:
        if not href.startswith(("http://", "https://")):
            continue
        if "alternate" in rel and ("text/html" in typ or typ == ""):
            return strip_tracking_query_params(href)

    main = (entry.get("link") or fallback_link or "").strip()
    if main.startswith(("http://", "https://")):
        return strip_tracking_query_params(main)

    for href, _rel, _typ in pairs:
        if href.startswith(("http://", "https://")):
            return strip_tracking_query_params(href)

    if main:
        return strip_tracking_query_params(main)
    return ""
