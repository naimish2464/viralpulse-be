"""Normalize article body text for storage and downstream use."""

from __future__ import annotations

import re


def normalize_article_body_for_storage(raw: str) -> str:
    """Strip edges, collapse horizontal whitespace, trim excessive blank lines."""
    s = (raw or "").strip()
    if not s:
        return ""
    s = re.sub(r"[ \t\f\v]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()
