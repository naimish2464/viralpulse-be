"""RSS extract + conditional enrich behavior."""

from __future__ import annotations

from unittest.mock import patch

from core import scrape as scrape_mod
from core.rss_extract import extract_entry_body_plain, extract_entry_images


def test_body_prefers_longest_content_part_by_plain_length() -> None:
    e = {
        "content": [
            {"value": "<p>short</p>", "type": "text/html"},
            {"value": "<p>" + ("x" * 120) + "</p>", "type": "text/html"},
        ],
        "summary": "summary only",
    }
    plain = extract_entry_body_plain(e)
    assert plain.count("x") >= 100


def test_description_only() -> None:
    e = {"description": "<b>Hello</b> world"}
    assert extract_entry_body_plain(e) == "Hello world"


def test_summary_when_no_content() -> None:
    e = {"summary": "<p>Teaser</p>"}
    assert extract_entry_body_plain(e) == "Teaser"


def test_summary_detail_when_summary_missing() -> None:
    e = {"summary_detail": {"type": "text/html", "value": "<p>Atom detail</p>"}}
    assert extract_entry_body_plain(e) == "Atom detail"


def test_description_dict_value() -> None:
    e = {"description": {"value": "<p>Desc block</p>"}}
    assert extract_entry_body_plain(e) == "Desc block"


def test_media_thumbnail() -> None:
    e: dict = {"media_thumbnail": [{"url": "https://a.com/i.jpg"}]}
    assert extract_entry_images(e) == ["https://a.com/i.jpg"]


def test_empty_body() -> None:
    e: dict = {"title": "x"}
    assert extract_entry_body_plain(e) == ""


def test_enrich_skips_scrape_when_long_rss() -> None:
    with patch.object(scrape_mod, "scrape_article") as m:
        long_txt = "w " * 150
        r = scrape_mod.enrich_article_content(
            "https://example.com/x",
            title="T",
            rss_plain=long_txt,
            rss_images=["https://img/x.png"],
            min_chars=200,
        )
        m.assert_not_called()
        assert len(r["content"]) > 200
        assert r["image"] == "https://img/x.png"


def test_enrich_calls_scrape_when_short_rss() -> None:
    fake = {
        "title": "S",
        "content": "full article text here " * 20,
        "image": "",
        "images": [],
        "description": "",
        "extractive_summary": "A short NLP summary.",
        "authors": [],
        "article_publish_date": "",
        "og_image": "",
        "top_image_url": "",
    }
    with patch.object(scrape_mod, "scrape_article", return_value=fake) as m:
        r = scrape_mod.enrich_article_content(
            "https://example.com/y",
            title="T",
            rss_plain="short",
            rss_images=[],
            min_chars=200,
        )
        m.assert_called_once()
        assert r["content"] == fake["content"]


def test_enrich_fallback_on_scrape_fail() -> None:
    with patch.object(scrape_mod, "scrape_article", return_value=None):
        r = scrape_mod.enrich_article_content(
            "https://example.com/z",
            title="T2",
            rss_plain="tiny",
            rss_images=["https://i/a.gif"],
            min_chars=200,
        )
        assert r["content"] == "tiny"
        assert r["image"] == "https://i/a.gif"


def test_feed_row_always_scrapes_when_long_rss() -> None:
    """Ingestion path must hit the article URL even when the RSS body is long."""
    from services import scrape_service

    fake = {
        "title": "From page",
        "content": "page body " * 80,
        "image": "https://cdn.example/hero.jpg",
        "images": ["https://cdn.example/hero.jpg"],
        "description": "meta desc",
        "extractive_summary": "NLP sum",
        "authors": [],
        "article_publish_date": "",
        "og_image": "https://cdn.example/og.jpg",
        "top_image_url": "https://cdn.example/hero.jpg",
    }
    long_rss = "rss fallback " * 200
    with patch.object(scrape_service.te_scrape, "scrape_article", return_value=fake) as m:
        r = scrape_service.enrich_article_from_feed_row(
            "https://example.com/article",
            title="T",
            rss_plain=long_rss,
            rss_images=["https://rss/img.png"],
            min_chars=200,
            allow_newspaper=True,
        )
    m.assert_called_once_with("https://example.com/article")
    assert "page body" in r["content"]
    assert r["extractive_summary"] == "NLP sum"
    assert r["images"][0] == "https://cdn.example/og.jpg"
    assert "https://cdn.example/hero.jpg" in r["images"]
    assert "https://rss/img.png" in r["images"]


def test_skip_ai_pipeline_makes_no_embedding_calls(monkeypatch) -> None:
    calls: list[str] = []

    def _no_embed(*_a, **_k):
        calls.append("embed_texts")
        raise AssertionError("embed_texts should not run when skip_ai")

    def _fake_scrape_article(_url: str):
        return {
            "title": "scraped title",
            "content": "y" * 400,
            "image": "",
            "images": [],
            "description": "meta",
            "extractive_summary": "summary line",
            "authors": ["A Author"],
            "article_publish_date": "",
            "og_image": "",
            "top_image_url": "",
        }

    monkeypatch.setattr("core.config.DATABASE_URL", None)
    monkeypatch.setattr("core.scrape.scrape_article", _fake_scrape_article)
    monkeypatch.setattr("services.cluster_service.embed_texts", _no_embed)
    monkeypatch.setattr(
        "services.trends_service.fetch_trending_topic_signals", lambda **k: []
    )
    monkeypatch.setattr(
        "services.trends_service.fetch_reddit_hot", lambda limit: []
    )

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

    out = run_pipeline(limit=1, skip_ai=True, rss_urls=["https://example.com/feed.xml"])
    assert not calls
    assert len(out) == 1
    assert out[0].get("category") == "technology"
