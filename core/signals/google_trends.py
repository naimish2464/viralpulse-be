"""Live Google Trends via trendspy (primary); pytrends today_searches + cache as fallback."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from core import config
from core.topics import TopicSignal

logger = logging.getLogger(__name__)

_GEO_ALIASES: dict[str, str] = {
    "india": "IN",
    "united_states": "US",
    "united states": "US",
    "usa": "US",
    "us": "US",
    "uk": "GB",
    "united kingdom": "GB",
    "great britain": "GB",
    "canada": "CA",
    "australia": "AU",
    "germany": "DE",
    "japan": "JP",
    "brazil": "BR",
}


def resolve_trends_geo(raw: str | None) -> str:
    if not raw:
        return "IN"
    s = raw.strip()
    if not s:
        return "IN"
    if re.fullmatch(r"[A-Za-z]{2}", s):
        return s.upper()
    key = s.lower().replace("-", "_")
    return _GEO_ALIASES.get(key, "IN")


def _load_cached_topic_signals() -> list[TopicSignal] | None:
    path = config.TOPICS_CACHE_FILE
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("topic_signals")
        if isinstance(items, list) and items:
            out: list[TopicSignal] = []
            for i, obj in enumerate(items, start=1):
                if isinstance(obj, str):
                    out.append(
                        TopicSignal(label=obj, source="google", rank_in_source=i)
                    )
                elif isinstance(obj, dict):
                    label = str(obj.get("label", "")).strip()
                    if not label:
                        continue
                    out.append(
                        TopicSignal(
                            label=label,
                            source=str(obj.get("source", "google")),
                            rank_in_source=int(obj.get("rank_in_source", i)),
                        )
                    )
            if out:
                return out
        topics = data.get("topics")
        if isinstance(topics, list) and all(isinstance(t, str) for t in topics):
            return [
                TopicSignal(label=t, source="google", rank_in_source=i)
                for i, t in enumerate(topics, start=1)
                if len(str(t).strip()) >= config.TOPIC_MIN_LEN
            ]
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return None


def _save_cached_topic_signals(signals: list[TopicSignal]) -> None:
    try:
        config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "topic_signals": [
                {
                    "label": s.label,
                    "source": s.source,
                    "rank_in_source": s.rank_in_source,
                }
                for s in signals
            ],
            "topics": [s.label for s in signals],
        }
        config.TOPICS_CACHE_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as e:
        logger.warning("Could not write topics cache: %s", e)


def _fetch_trendspy(geo_code: str, language: str) -> list[TopicSignal]:
    from trendspy import Trends

    tr = Trends()
    trends = tr.trending_now(geo=geo_code, language=language, hours=24, num_news=0)
    out: list[TopicSignal] = []
    seen: set[str] = set()
    rank = 0
    for item in trends:
        kw = getattr(item, "keyword", None)
        if kw is None:
            continue
        s = str(kw).strip()
        if len(s) < config.TOPIC_MIN_LEN:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        rank += 1
        out.append(TopicSignal(label=s, source="google", rank_in_source=rank))
    return out


def _fetch_pytrends_today(geo_code: str, hl: str) -> list[TopicSignal]:
    from pytrends.request import TrendReq

    pytrends = TrendReq(hl=hl, tz=300, timeout=(10, 25))
    trending: Any = pytrends.today_searches(pn=geo_code)
    if hasattr(trending, "tolist"):
        raw = trending.tolist()
    else:
        raw = list(trending)
    out: list[TopicSignal] = []
    rank = 0
    for k in raw:
        if hasattr(k, "get") and "query" in k:
            s = str(k["query"]).strip()
        else:
            s = str(k).strip()
        if s and len(s) >= config.TOPIC_MIN_LEN:
            rank += 1
            out.append(TopicSignal(label=s, source="google", rank_in_source=rank))
    return out


def fetch_trending_topic_signals(
    pn: str | None = None,
    *,
    geo: str | None = None,
    language: str | None = None,
) -> list[TopicSignal]:
    """Ordered Google trending keywords with 1-based rank within the Google list."""
    raw_geo = geo or pn or config.GOOGLE_TRENDS_PN
    geo_code = resolve_trends_geo(raw_geo)
    lang = (language or config.TREND_ENGINE_LANG).strip() or "en"
    hl = f"{lang}-US" if geo_code == "US" else f"{lang}-{geo_code}"

    last_err: Exception | None = None

    for attempt in range(config.GOOGLE_TRENDS_MAX_RETRIES):
        try:
            signals = _fetch_trendspy(geo_code, lang)
            if signals:
                _save_cached_topic_signals(signals)
                return signals
            logger.warning(
                "trendspy returned no topics (attempt %s/%s); trying pytrends",
                attempt + 1,
                config.GOOGLE_TRENDS_MAX_RETRIES,
            )
        except Exception as e:
            last_err = e
            logger.warning(
                "trendspy failed (attempt %s/%s): %s",
                attempt + 1,
                config.GOOGLE_TRENDS_MAX_RETRIES,
                e,
            )
        if attempt < config.GOOGLE_TRENDS_MAX_RETRIES - 1:
            time.sleep(config.GOOGLE_TRENDS_BACKOFF_SEC * (attempt + 1))

    for attempt in range(max(1, config.GOOGLE_TRENDS_MAX_RETRIES)):
        try:
            signals = _fetch_pytrends_today(geo_code, hl)
            if signals:
                _save_cached_topic_signals(signals)
                return signals
        except Exception as e:
            last_err = e
            logger.debug("pytrends today_searches failed: %s", e)
        if attempt < config.GOOGLE_TRENDS_MAX_RETRIES - 1:
            time.sleep(config.GOOGLE_TRENDS_BACKOFF_SEC)

    cached = _load_cached_topic_signals()
    if cached:
        logger.info("Using cached topics after live fetches failed")
        return cached
    if last_err:
        logger.error("No trending keywords available: %s", last_err)
    return []


def fetch_trending_keywords(
    pn: str | None = None,
    *,
    geo: str | None = None,
    language: str | None = None,
) -> list[str]:
    """Backward-compatible: labels only, order preserved."""
    return [s.label for s in fetch_trending_topic_signals(pn=pn, geo=geo, language=language)]
