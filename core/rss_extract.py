"""Adaptive RSS entry body and image extraction (feedparser entries)."""

from __future__ import annotations

import html as html_lib
import re
from typing import Any

_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)

# Strip before tag removal so <pre>/<code> bodies never become “prose”.
_SCRIPT_STYLE_PRE = re.compile(r"(?is)<(?:script|style|noscript)[^>]*>.*?</(?:script|style|noscript)>")
_PRE_BLOCK = re.compile(r"(?is)<pre[^>]*>.*?</pre>")


def _strip_code_carrying_html(html: str) -> str:
    if not html:
        return ""
    s = _SCRIPT_STYLE_PRE.sub(" ", html)
    s = _PRE_BLOCK.sub(" ", s)

    def _code_tag(m: re.Match[str]) -> str:
        inner = m.group(1) or ""
        if len(inner) > 80 or "\n" in inner or inner.count(";") > 2:
            return " "
        return f" {inner} "

    s = re.sub(r"(?is)<code[^>]*>(.*?)</code>", _code_tag, s)
    return s
_SRC_RE = re.compile(
    r"""<img[^>]+src\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE | re.DOTALL,
)
_MAX_IMG_SRC_FROM_HTML = 3


def html_to_text(s: str) -> str:
    if not s:
        return ""
    s = _strip_code_carrying_html(s)
    t = _TAG_RE.sub(" ", s)
    t = html_lib.unescape(t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _content_parts(entry: dict[str, Any]) -> list[str]:
    raw = entry.get("content")
    if not raw:
        return []
    parts: list[str] = []
    if isinstance(raw, list):
        for block in raw:
            if isinstance(block, dict):
                v = block.get("value") or ""
                if v:
                    parts.append(str(v))
            elif isinstance(block, str):
                parts.append(block)
    elif isinstance(raw, str):
        parts.append(raw)
    return parts


def _best_content_html(entry: dict[str, Any]) -> str:
    parts = _content_parts(entry)
    if not parts:
        return ""
    return max(parts, key=lambda x: len(html_to_text(x)))


def _summary_html(entry: dict[str, Any]) -> str:
    """Atom ``summary_detail`` / RSS ``summary`` (some feeds only populate detail)."""
    sd = entry.get("summary_detail")
    if isinstance(sd, dict) and sd.get("value"):
        return str(sd["value"])
    s = entry.get("summary")
    return str(s) if s else ""


def _description_html(entry: dict[str, Any]) -> str:
    d = entry.get("description")
    if not d:
        return ""
    if isinstance(d, dict) and d.get("value"):
        return str(d["value"])
    return str(d)


def extract_entry_body_html(entry: dict[str, Any]) -> str:
    """Richest ``content`` block, else ``summary``/``summary_detail``, else ``description``."""
    h = _best_content_html(entry)
    if h:
        return h
    sh = _summary_html(entry)
    if sh:
        return sh
    dh = _description_html(entry)
    if dh:
        return dh
    return ""


def extract_entry_body_plain(entry: dict[str, Any]) -> str:
    """
    Plain text: content (largest plain length) > summary (incl. summary_detail) > description.
    """
    h = _best_content_html(entry)
    if h:
        return html_to_text(h)
    sh = _summary_html(entry)
    if sh:
        return html_to_text(sh)
    dh = _description_html(entry)
    if dh:
        return html_to_text(dh)
    return ""


def _media_url(obj: Any) -> str | None:
    if not obj:
        return None
    if isinstance(obj, str):
        return obj.strip() or None
    if isinstance(obj, dict):
        u = obj.get("url") or obj.get("href")
        if u:
            return str(u).strip()
    return None


def extract_entry_images(entry: dict[str, Any], *, body_html: str = "") -> list[str]:
    """Deduped image URLs from media:*, enclosures, and img src in HTML body."""
    seen: set[str] = set()
    out: list[str] = []

    def add(u: str | None) -> None:
        if not u or u in seen:
            return
        seen.add(u)
        out.append(u)

    mt = entry.get("media_thumbnail")
    if isinstance(mt, list):
        for x in mt:
            add(_media_url(x))
    else:
        add(_media_url(mt))

    mc = entry.get("media_content")
    if isinstance(mc, list):
        for block in mc:
            if isinstance(block, dict):
                t = str(block.get("type", "")).lower()
                med = str(block.get("medium", "")).lower()
                if med == "image" or "image" in t:
                    add(_media_url(block.get("url")))
            elif isinstance(block, str):
                add(block.strip())
    elif isinstance(mc, dict):
        t = str(mc.get("type", "")).lower()
        med = str(mc.get("medium", "")).lower()
        if med == "image" or "image" in t:
            add(_media_url(mc.get("url")))

    for enc in entry.get("enclosures") or []:
        if isinstance(enc, dict):
            t = str(enc.get("type", "")).lower()
            if "image" in t:
                add(_media_url(enc.get("href") or enc.get("url")))

    html_src = body_html or extract_entry_body_html(entry)
    n_img = 0
    for m in _SRC_RE.finditer(html_src):
        if n_img >= _MAX_IMG_SRC_FROM_HTML:
            break
        u = m.group(1).strip()
        if u and u not in seen:
            seen.add(u)
            out.append(u)
            n_img += 1

    return out
