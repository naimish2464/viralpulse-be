"""Read-time estimate from plain article text (words / minute)."""

from __future__ import annotations

import re

# Typical editorial reading speed; overridable by callers.
DEFAULT_WORDS_PER_MINUTE = 200


def estimate_read_time_minutes(
    text: str,
    *,
    words_per_minute: int = DEFAULT_WORDS_PER_MINUTE,
) -> int:
    """Return at least 1 minute for any non-empty text; 1 for empty."""
    raw = (text or "").strip()
    if not raw:
        return 1
    words = len(re.findall(r"\b\w+\b", raw, flags=re.UNICODE))
    if words < 1:
        return 1
    wpm = max(1, int(words_per_minute))
    mins = max(1, round(words / wpm))
    return int(mins)
