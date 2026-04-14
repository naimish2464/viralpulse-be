"""Article text, images, meta description, authors via newspaper3k."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

from newspaper import Article
from newspaper.configuration import Configuration

from core import config

logger = logging.getLogger(__name__)

_SKIP_IMG_SUBSTR = (
    "logo",
    "favicon",
    "sprite",
    "pixel",
    "tracking",
    "avatar-default",
    "icon_",
    "/icons/",
    "1x1",
    "blank.",
    "spacer",
    "badge",
    "emoji",
)
_AUTHOR_NOISE_RE = re.compile(
    r"__|--|\.(?:Post|Authors|List|Font|Size|Var)\b|^[.\d\s]+$",
    re.I,
)
_AUTHOR_URLISH_RE = re.compile(r"https?://|www\.\w", re.I)
_AUTHOR_BOILERPLATE = frozenset(
    {
        "staff",
        "staff writer",
        "editorial staff",
        "editor",
        "editors",
        "wire",
        "news desk",
        "breaking news",
        "associated press",
        "reuters",
    }
)


def clean_author_list(authors: list[str] | None, *, max_authors: int = 8) -> list[str]:
    """Public: normalized author names for API / persistence."""
    return _clean_authors(authors, max_authors=max_authors)


def filter_article_image_urls(urls: list[str] | None) -> list[str]:
    """Public: drop tracking/logos/SVG and cap count (uses ``SCRAPE_MAX_IMAGES``)."""
    return _filter_image_urls(urls)


def _clean_authors(authors: list[str] | None, *, max_authors: int = 8) -> list[str]:
    out: list[str] = []
    for raw in authors or []:
        s = str(raw).strip()
        if not s or len(s) > 80 or len(s) < 2:
            continue
        if _AUTHOR_NOISE_RE.search(s):
            continue
        if _AUTHOR_URLISH_RE.search(s):
            continue
        low = s.lower()
        if low in _AUTHOR_BOILERPLATE:
            continue
        if "@" in s and " " not in s:
            continue
        if s.count(".") >= 2 and " " not in s[:30]:
            continue
        if sum(1 for c in s if c.isupper()) > 12 and " " not in s:
            continue
        out.append(s)
        if len(out) >= max_authors:
            break
    return out


def _filter_image_urls(urls: list[str] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for u in urls or []:
        s = str(u).strip()
        if not s:
            continue
        low = s.lower()
        if low.endswith(".svg") or low.endswith(".svgz"):
            continue
        if any(x in low for x in _SKIP_IMG_SUBSTR):
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out[: config.SCRAPE_MAX_IMAGES]


def _article_config() -> Configuration:
    cfg = Configuration()
    # False: accept og:image / first-article img URLs without PIL dimension checks
    # (True often yields empty top_image when CDNs block requests or ratio checks fail).
    cfg.fetch_images = bool(config.SCRAPER_VALIDATE_IMAGES_WITH_PIL)
    ua = (config.SCRAPER_BROWSER_USER_AGENT or "").strip()
    if ua:
        cfg.browser_user_agent = ua
    return cfg


def _serialize_publish_date(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value).strip()


def _first_og_image_url(html: str, base_url: str) -> str:
    """First Open Graph ``og:image`` URL only (not twitter:image or inline ``img``)."""
    if not html or not base_url:
        return ""
    for m in re.finditer(r"<meta\s+[^>]*>", html, re.I):
        tag = m.group(0)
        tl = tag.lower()
        if not re.search(r"property\s*=\s*[\"']og:image[\"']", tag, re.I):
            continue
        if any(
            x in tl
            for x in (
                'property="og:image:width"',
                "property='og:image:width'",
                'property="og:image:height"',
                "property='og:image:height'",
                'property="og:image:type"',
                "property='og:image:type'",
            )
        ):
            continue
        cm = re.search(r'\bcontent\s*=\s*["\']([^"\']+)["\']', tag, re.I)
        if not cm:
            continue
        raw = (cm.group(1) or "").strip()
        if not raw or raw.lower().startswith("data:"):
            continue
        if not urlparse(raw).scheme:
            raw = urljoin(base_url, raw)
        return raw
    return ""


def _extract_image_urls_from_raw_html(html: str, base_url: str) -> list[str]:
    """
    Fallback when newspaper's DOM walk misses lazy-loaded or JSON-LD-only images.
    Pulls og:image, twitter:image, and common lazy ``img`` attributes.
    """
    if not html or not base_url:
        return []
    seen: set[str] = set()
    out: list[str] = []

    def add(raw: str) -> None:
        s = (raw or "").strip()
        if not s or s.lower().startswith("data:"):
            return
        if not urlparse(s).scheme:
            s = urljoin(base_url, s)
        if s in seen:
            return
        seen.add(s)
        out.append(s)

    for m in re.finditer(r"<meta\s+[^>]*>", html, re.I):
        tag = m.group(0)
        tl = tag.lower()
        if "og:image" not in tl and "twitter:image" not in tl:
            continue
        if any(
            x in tl
            for x in (
                'property="og:image:width"',
                "property='og:image:width'",
                'property="og:image:height"',
                "property='og:image:height'",
                'property="og:image:type"',
                "property='og:image:type'",
            )
        ):
            continue
        cm = re.search(r'\bcontent\s*=\s*["\']([^"\']+)["\']', tag, re.I)
        if cm:
            add(cm.group(1))

    for m in re.finditer(r"<img\s+[^>]*>", html, re.I):
        tag = m.group(0)
        for attr in ("data-src", "data-lazy-src", "data-original", "src"):
            sm = re.search(rf'{attr}\s*=\s*["\']([^"\']+)["\']', tag, re.I)
            if sm:
                add(sm.group(1))
                break

    return out


def _collect_image_urls(article: Article, *, max_images: int) -> list[str]:
    """Deduped list: meta/social from HTML, then top_image, then inline imgs."""
    raw = article.images or article.imgs or []
    if isinstance(raw, set):
        raw = list(raw)
    seen: set[str] = set()
    out: list[str] = []

    def push(u: str) -> None:
        s = (str(u) if u is not None else "").strip()
        if not s or s in seen:
            return
        seen.add(s)
        out.append(s)

    html = article.html or ""
    base = article.url or ""
    for u in _extract_image_urls_from_raw_html(html, base):
        push(u)
        if len(out) >= max_images:
            return out

    top = (article.top_image or article.top_img or "").strip()
    if top:
        push(top)
    meta = (getattr(article, "meta_img", None) or "").strip()
    if meta and meta != top:
        push(meta)

    for u in raw:
        push(u)
        if len(out) >= max_images:
            break
    return out[:max_images]


def enrich_article_content(
    url: str,
    *,
    title: str,
    rss_plain: str,
    rss_images: list[str],
    min_chars: int | None = None,
) -> dict[str, Any]:
    """
    Use RSS text when it is long enough; otherwise newspaper3k. On scrape failure,
    fall back to RSS (even if short). Never raises.
    """
    thresh = min_chars if min_chars is not None else config.RSS_MIN_CHARS_FOR_SKIP_SCRAPE
    cap = config.SCRAPE_MAX_CONTENT_CHARS
    rss_clean = (rss_plain or "").strip()
    L = len(rss_clean)

    def _rss_dict() -> dict[str, Any]:
        text = rss_clean
        if cap > 0 and len(text) > cap:
            text = text[:cap]
        imgs = _filter_image_urls(list(rss_images or []))
        primary = imgs[0] if imgs else ""
        return {
            "title": (title or "").strip() or url,
            "content": text,
            "image": primary,
            "images": imgs,
            "description": "",
            "extractive_summary": "",
            "authors": [],
            "article_publish_date": "",
            "og_image": "",
            "top_image_url": "",
        }

    if L > thresh:
        return _rss_dict()
    scraped = scrape_article(url)
    if scraped:
        return scraped
    logger.debug("Scrape failed for %s; using RSS fallback", url)
    return _rss_dict()


def scrape_article(url: str, max_chars: int | None = None) -> dict[str, Any] | None:
    """
    Download and parse URL. Returns None on failure.

    newspaper3k provides:
    - ``image``: primary / OpenGraph image (``top_image``)
    - ``images``: deduped list of image URLs found in the document (often many;
      quality depends on site HTML)
    - ``description``: HTML meta description (not the NLP extractive summary)
    - ``extractive_summary``: newspaper3k NLP summary when ``nlp()`` succeeds
    - ``authors``: list of author strings when detectable
    - ``article_publish_date``: parsed date when the extractor finds one
    """
    try:
        article = Article(url, config=_article_config())
        article.download()
        article.parse()

        extractive_summary = ""
        try:
            article.nlp()
            extractive_summary = (article.summary or "").strip()
        except Exception as e:
            logger.debug("newspaper nlp() skipped for %s: %s", url, e)

        text = (article.text or "").strip()
        limit = max_chars if max_chars is not None else config.SCRAPE_MAX_CONTENT_CHARS
        if limit > 0 and len(text) > limit:
            text = text[:limit]

        title = (article.title or "").strip() or url
        og_image = _first_og_image_url(article.html or "", article.url or "")
        top_image_url = (article.top_image or article.top_img or "").strip()
        images = _filter_image_urls(
            _collect_image_urls(article, max_images=config.SCRAPE_MAX_IMAGES * 2)
        )
        top = top_image_url
        if top and top not in images and not any(top.lower().endswith(x) for x in (".svg", ".svgz")):
            images = _filter_image_urls([top] + images)
        primary = images[0] if images else ""

        authors = clean_author_list(
            [str(a).strip() for a in (article.authors or []) if str(a).strip()]
        )
        description = (article.meta_description or "").strip()

        return {
            "title": title,
            "content": text,
            "image": primary,
            "images": images,
            "description": description,
            "extractive_summary": extractive_summary,
            "authors": authors,
            "article_publish_date": _serialize_publish_date(article.publish_date),
            "og_image": og_image,
            "top_image_url": top_image_url,
        }
    except Exception as e:
        logger.warning("Scrape failed for %s: %s", url, e)
        return None
