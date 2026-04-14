"""SEO module and pipeline gating."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_parse_seo_json_truncates_long_fields() -> None:
    from core.seo import _parse_seo_json

    raw = (
        '{"optimized_title": "' + "x" * 80 + '", '
        '"meta_description": "' + "y" * 200 + '", '
        '"keywords": ["a","b","c","d","e","f"], '
        '"slug": "OK-Slug-Here"}'
    )
    out = _parse_seo_json(raw)
    assert len(out["optimized_title"]) <= 60
    assert len(out["meta_description"]) <= 160
    assert len(out["keywords"]) == 5


def test_generate_seo_uses_mocked_api() -> None:
    from core import seo as seo_mod

    fake = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"optimized_title": "Short AI title", '
                        '"meta_description": "' + "z" * 155 + '", '
                        '"keywords": ["ai", "news", "tech", "trends", "2026"], '
                        '"slug": "short-ai-title"}'
                    )
                }
            }
        ]
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=fake)
    mock_client = MagicMock()
    mock_client.post = MagicMock(return_value=mock_resp)
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_client)
    mock_cm.__exit__ = MagicMock(return_value=False)

    with patch("core.seo.config.OPENAI_API_KEY", "sk-test"):
        with patch("core.seo.httpx.Client", return_value=mock_cm):
            out = seo_mod.generate_seo(
                "Original",
                "Summary line one. Summary line two.",
                main_topic="ai",
                url="https://example.com/a",
            )
    assert out["optimized_title"] == "Short AI title"
    assert len(out["keywords"]) == 5
    assert out["slug"] == "short-ai-title"


def test_pipeline_skips_seo_when_skip_ai(monkeypatch) -> None:
    monkeypatch.setattr("core.config.DATABASE_URL", None)
    monkeypatch.setattr("core.config.TREND_ENGINE_SEO_ENABLED", True)
    monkeypatch.setattr("core.config.TREND_ENGINE_SEO_MIN_SCORE", 0.0)
    monkeypatch.setattr("core.config.TREND_ENGINE_SEO_MAX_PER_RUN", 5)
    monkeypatch.setattr("core.config.OPENAI_API_KEY", "sk-x")

    calls: list[str] = []

    def _boom(*_a, **_k):
        calls.append("seo")
        raise AssertionError("SEO should not run with skip_ai")

    monkeypatch.setattr("services.seo_service.seo_mod.generate_seo", _boom)
    monkeypatch.setattr(
        "services.trends_service.fetch_trending_topic_signals", lambda **k: []
    )
    monkeypatch.setattr("services.trends_service.fetch_reddit_hot", lambda limit: [])

    def _fake_fetch(**_k):
        return [
            {
                "title": "python programming trends",
                "url": "https://example.com/a",
                "source_rss": "test",
                "published": None,
                "category": "technology",
                "rss_plain": "x" * 250,
                "rss_images": [],
            }
        ]

    monkeypatch.setattr("services.rss_service.fetch_rss_articles", _fake_fetch)

    from core.pipeline import run_pipeline

    out = run_pipeline(limit=1, skip_ai=True, rss_urls=["https://x/feed"])
    assert not calls
    assert out[0].get("seo") is None


def test_pipeline_calls_seo_when_enabled_and_high_score(monkeypatch):
    monkeypatch.setattr("core.config.DATABASE_URL", None)
    monkeypatch.setattr("core.config.TREND_ENGINE_SEO_ENABLED", True)
    monkeypatch.setattr("core.config.TREND_ENGINE_SEO_MIN_SCORE", 0.0)
    monkeypatch.setattr("core.config.TREND_ENGINE_SEO_MAX_PER_RUN", 5)
    monkeypatch.setattr("core.config.OPENAI_API_KEY", "sk-x")
    monkeypatch.setattr(
        "services.cluster_service.embed_texts", lambda texts: [[] for _ in texts]
    )

    def _fake_enrich(title: str, content: str):
        return {
            "summary": "S",
            "main_topic": "m",
            "why_trending": "w",
            "why_people_care": "c",
            "who_should_care": "x",
            "content_angle_ideas": [],
        }

    def _fake_seo(*_a, **_k):
        return {
            "optimized_title": "OT",
            "meta_description": "M" * 150,
            "keywords": ["a", "b", "c", "d", "e"],
            "slug": "ot",
        }

    monkeypatch.setattr("services.ai_service.ai_mod.enrich", _fake_enrich)
    monkeypatch.setattr("services.seo_service.seo_mod.generate_seo", _fake_seo)
    monkeypatch.setattr(
        "services.trends_service.fetch_trending_topic_signals", lambda **k: []
    )
    monkeypatch.setattr("services.trends_service.fetch_reddit_hot", lambda limit: [])

    def _fake_fetch(**_k):
        return [
            {
                "title": "python programming trends",
                "url": "https://example.com/a",
                "source_rss": "test",
                "published": None,
                "category": "technology",
                "rss_plain": "x" * 250,
                "rss_images": [],
            }
        ]

    monkeypatch.setattr("services.rss_service.fetch_rss_articles", _fake_fetch)

    from core.pipeline import run_pipeline

    out = run_pipeline(limit=1, skip_ai=False, rss_urls=["https://x/feed"])
    assert out[0].get("seo") is not None
    assert out[0]["seo"]["optimized_title"] == "OT"


def test_pipeline_skips_seo_when_skip_seo_flag(monkeypatch) -> None:
    monkeypatch.setattr("core.config.DATABASE_URL", None)
    monkeypatch.setattr("core.config.TREND_ENGINE_SEO_ENABLED", True)
    monkeypatch.setattr("core.config.TREND_ENGINE_SEO_MIN_SCORE", 0.0)
    monkeypatch.setattr("core.config.TREND_ENGINE_SEO_MAX_PER_RUN", 5)
    monkeypatch.setattr("core.config.OPENAI_API_KEY", "sk-x")
    monkeypatch.setattr(
        "services.cluster_service.embed_texts", lambda texts: [[] for _ in texts]
    )

    calls: list[str] = []

    def _boom(*_a, **_k):
        calls.append("seo")
        raise AssertionError("SEO should not run when skip_seo=True")

    def _fake_enrich(title: str, content: str):
        return {
            "summary": "S",
            "main_topic": "m",
            "why_trending": "w",
            "why_people_care": "c",
            "who_should_care": "x",
            "content_angle_ideas": [],
        }

    monkeypatch.setattr("services.ai_service.ai_mod.enrich", _fake_enrich)
    monkeypatch.setattr("services.seo_service.seo_mod.generate_seo", _boom)
    monkeypatch.setattr(
        "services.trends_service.fetch_trending_topic_signals", lambda **k: []
    )
    monkeypatch.setattr("services.trends_service.fetch_reddit_hot", lambda limit: [])

    def _fake_fetch(**_k):
        return [
            {
                "title": "python programming trends",
                "url": "https://example.com/b",
                "source_rss": "test",
                "published": None,
                "category": "technology",
                "rss_plain": "x" * 250,
                "rss_images": [],
            }
        ]

    monkeypatch.setattr("services.rss_service.fetch_rss_articles", _fake_fetch)

    from core.pipeline import run_pipeline

    out = run_pipeline(limit=1, skip_ai=False, skip_seo=True, rss_urls=["https://x/feed"])
    assert not calls
    assert out[0].get("seo") is None
