"""RSS feeds, region, limits; overridable via env where noted."""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GOOGLE_TRENDS_PN: str = os.environ.get("TREND_ENGINE_GEO", "india")

# Language for trendspy trending_now (e.g. en, hi)
TREND_ENGINE_LANG: str = os.environ.get("TREND_ENGINE_LANG", "en")

# Non-empty → flat URL list with category "general"; overrides category-based feeds entirely.
RSS_ENV_URLS: list[str] = [
    u.strip() for u in os.environ.get("TREND_ENGINE_RSS", "").split(",") if u.strip()
]
# Back-compat name: same as RSS_ENV_URLS (category map is used when this is empty).
RSS_URLS: list[str] = RSS_ENV_URLS

RSS_ENTRIES_PER_FEED: int = int(os.environ.get("TREND_ENGINE_RSS_LIMIT", "30"))

# If RSS body plain text exceeds this length, skip newspaper3k for that item.
RSS_MIN_CHARS_FOR_SKIP_SCRAPE: int = int(
    os.environ.get("TREND_ENGINE_RSS_MIN_CHARS_FOR_SKIP_SCRAPE", "200")
)

# newspaper3k: extra trim after parse; 0 = only newspaper's internal MAX_TEXT (~100k) applies
SCRAPE_MAX_CONTENT_CHARS: int = int(os.environ.get("TREND_ENGINE_SCRAPE_MAX_CHARS", "100000"))
# Max distinct image URLs to return per article (og + inline)
SCRAPE_MAX_IMAGES: int = int(os.environ.get("TREND_ENGINE_SCRAPE_MAX_IMAGES", "30"))
# newspaper3k HTTP User-Agent (many CDNs block the default ``newspaper/…`` string)
SCRAPER_BROWSER_USER_AGENT: str = os.environ.get(
    "TREND_ENGINE_SCRAPER_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
).strip() or (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
# When True, newspaper validates top image via PIL download (often fails on CDNs / WebP).
SCRAPER_VALIDATE_IMAGES_WITH_PIL: bool = os.environ.get(
    "TREND_ENGINE_SCRAPER_VALIDATE_IMAGES", ""
).lower() in ("1", "true", "yes")

GOOGLE_TRENDS_MAX_RETRIES: int = int(os.environ.get("TREND_ENGINE_GT_RETRIES", "3"))
GOOGLE_TRENDS_BACKOFF_SEC: float = float(os.environ.get("TREND_ENGINE_GT_BACKOFF", "2.0"))

TOPIC_MIN_LEN: int = int(os.environ.get("TREND_ENGINE_TOPIC_MIN_LEN", "2"))
# Drop Google/reddit topic labels whose normalized text contains any of these substrings (comma-separated).
TREND_ENGINE_TOPIC_BLOCKLIST: str = os.environ.get("TREND_ENGINE_TOPIC_BLOCKLIST", "").strip()
# 0 = disabled. Drop labels longer than this character count.
TREND_ENGINE_TOPIC_MAX_LABEL_LEN: int = int(os.environ.get("TREND_ENGINE_TOPIC_MAX_LABEL_LEN", "0"))
# 0 = disabled. Require at least this many non-stopword tokens in the label.
TREND_ENGINE_TOPIC_MIN_MEANINGFUL_TOKENS: int = int(
    os.environ.get("TREND_ENGINE_TOPIC_MIN_MEANINGFUL_TOKENS", "0")
)

CACHE_DIR: Path = Path(os.environ.get("TREND_ENGINE_CACHE_DIR", ".trend_engine_cache"))
TOPICS_CACHE_FILE: Path = CACHE_DIR / "last_topics.json"

OPENAI_API_KEY: str | None = os.environ.get("OPENAI_API_KEY")
OPENAI_BASE_URL: str = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
# Max chars of article body sent to the chat model (full body still in scrape / JSON output)
ENRICH_MAX_ARTICLE_CHARS: int = int(os.environ.get("TREND_ENGINE_ENRICH_MAX_CHARS", "20000"))

# Post-enrichment SEO LLM (optional; default off to avoid surprise cost)
TREND_ENGINE_SEO_ENABLED: bool = os.environ.get("TREND_ENGINE_SEO_ENABLED", "0").lower() in (
    "1",
    "true",
    "yes",
)
TREND_ENGINE_SEO_MIN_SCORE: float = float(os.environ.get("TREND_ENGINE_SEO_MIN_SCORE", "5.0"))
TREND_ENGINE_SEO_MAX_PER_RUN: int = int(os.environ.get("TREND_ENGINE_SEO_MAX_PER_RUN", "5"))
TREND_ENGINE_SEO_MODEL: str = os.environ.get("TREND_ENGINE_SEO_MODEL", "").strip()

REDDIT_CLIENT_ID: str | None = os.environ.get("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET: str | None = os.environ.get("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT: str = os.environ.get("REDDIT_USER_AGENT", "trend-engine/1.0")

# --- Phase 2: database & API ---
DATABASE_URL: str | None = os.environ.get("DATABASE_URL") or None

# Embeddings (OpenAI-compatible)
OPENAI_EMBEDDING_MODEL: str = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
TREND_ENGINE_SEMANTIC_MIN_SIM: float = float(os.environ.get("TREND_ENGINE_SEMANTIC_MIN_SIM", "0.28"))
TREND_ENGINE_SEMANTIC_ENABLED: bool = os.environ.get("TREND_ENGINE_SEMANTIC_ENABLED", "1").lower() in (
    "1",
    "true",
    "yes",
)
# hybrid: semantic OR token match; semantic: only cosine; token: legacy
TREND_ENGINE_MATCH_MODE: str = os.environ.get("TREND_ENGINE_MATCH_MODE", "hybrid").strip().lower()

# Dedup: title embedding similarity for story clustering (0..1)
TREND_ENGINE_STORY_SIM_THRESHOLD: float = float(os.environ.get("TREND_ENGINE_STORY_SIM_THRESHOLD", "0.92"))

# Score v2 weights (normalized components are 0..1 before weighting)
SCORE_W_TREND: float = float(os.environ.get("TREND_ENGINE_SCORE_W_TREND", "2.5"))
SCORE_W_SOCIAL: float = float(os.environ.get("TREND_ENGINE_SCORE_W_SOCIAL", "2.0"))
SCORE_W_RECENCY: float = float(os.environ.get("TREND_ENGINE_SCORE_W_RECENCY", "1.5"))
SCORE_W_SOURCE: float = float(os.environ.get("TREND_ENGINE_SCORE_W_SOURCE", "1.0"))
SCORE_W_SEMANTIC: float = float(os.environ.get("TREND_ENGINE_SCORE_W_SEMANTIC", "3.0"))
# Legacy heuristic caps folded into small bonuses
SCORE_BONUS_IMAGE: float = float(os.environ.get("TREND_ENGINE_SCORE_BONUS_IMAGE", "0.5"))
SCORE_BONUS_LENGTH: float = float(os.environ.get("TREND_ENGINE_SCORE_BONUS_LENGTH", "1.0"))

# Source quality: JSON object {"bbc.co.uk": 1.0, "default": 0.5}
_sq_raw = os.environ.get("TREND_ENGINE_SOURCE_QUALITY_JSON", "").strip()
SOURCE_QUALITY_TIERS: dict[str, float] = {}
if _sq_raw:
    try:
        SOURCE_QUALITY_TIERS = {str(k).lower(): float(v) for k, v in json.loads(_sq_raw).items()}
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

API_HOST: str = os.environ.get("TREND_ENGINE_API_HOST", "0.0.0.0")
API_PORT: int = int(os.environ.get("TREND_ENGINE_API_PORT", "8000"))

