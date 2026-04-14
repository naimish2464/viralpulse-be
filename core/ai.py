"""LLM enrichment via OpenAI-compatible Chat Completions API."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from core import config

logger = logging.getLogger(__name__)

SYSTEM = (
    "You are a news analyst. Respond with valid JSON only, no markdown. "
    'Keys: "summary" (2-3 lines), "main_topic" (short phrase), "why_trending" (1-2 lines), '
    '"why_people_care" (1-2 lines), "who_should_care" (1 line, audience), '
    '"content_angle_ideas" (array of 3-5 short strings, creative angles for creators).'
)


def enrich(title: str, content: str) -> dict[str, Any]:
    """
    Call OpenAI-compatible API. Requires OPENAI_API_KEY.
    Returns summary, main_topic, why_trending, why_people_care, who_should_care, content_angle_ideas.
    """
    api_key = config.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    body = (content or "").strip()
    cap = max(1000, config.ENRICH_MAX_ARTICLE_CHARS)
    if len(body) > cap:
        body = body[:cap] + "\n\n[… truncated for API]"

    user = (
        f"Title: {title}\n\nArticle text:\n{body}\n\n"
        "Summarize this news in 2-3 lines. Give main topic, why it's trending, why people care, "
        "who should care (one line), and 3-5 content angle ideas for creators."
    )
    url = f"{config.OPENAI_BASE_URL}/chat/completions"
    payload: dict[str, Any] = {
        "model": config.OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        "temperature": 0.4,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=120.0) as client:
        try:
            r = client.post(
                url,
                json={**payload, "response_format": {"type": "json_object"}},
                headers=headers,
            )
            r.raise_for_status()
        except httpx.HTTPStatusError:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
        data = r.json()

    text = data["choices"][0]["message"]["content"]
    return _parse_enrichment_json(text)


def _parse_enrichment_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise
        obj = json.loads(m.group(0))
    ideas = obj.get("content_angle_ideas", [])
    if isinstance(ideas, str):
        ideas = [ideas]
    if not isinstance(ideas, list):
        ideas = []
    ideas = [str(x).strip() for x in ideas if str(x).strip()]
    return {
        "summary": str(obj.get("summary", "")).strip(),
        "main_topic": str(obj.get("main_topic", "")).strip(),
        "why_trending": str(obj.get("why_trending", "")).strip(),
        "why_people_care": str(obj.get("why_people_care", "")).strip(),
        "who_should_care": str(obj.get("who_should_care", "")).strip(),
        "content_angle_ideas": ideas,
    }


def enrich_placeholder(title: str, content: str, matched_topics: list[str]) -> dict[str, Any]:
    """When AI is skipped: shallow fields for JSON shape."""
    cap = 200
    body = content or ""
    snippet = body[:cap].replace("\n", " ").strip()
    if len(body) > cap:
        snippet += "…"
    main = matched_topics[0] if matched_topics else "general"
    if main.lower() != "general":
        why_t = f"Surfacing because it aligns with the trending topic: {main}."
        why_care = f"Useful for audiences tracking news and discussion around “{main}”."
        who_care = f"Readers and creators interested in {main}."
    else:
        why_t = "Included from monitored RSS sources as timely news."
        why_care = "Provides context on a current story from the feed."
        who_care = "General news readers and trend monitors."
    return {
        "summary": snippet or title,
        "main_topic": main,
        "why_trending": why_t,
        "why_people_care": why_care,
        "who_should_care": who_care,
        "content_angle_ideas": [],
    }
