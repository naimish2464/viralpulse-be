"""Smoke tests for DRF list/detail endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from apps.articles.models import Article, UserFeedback
from apps.processing.models import PipelineRun
from apps.trends.models import Topic, TrendSnapshot


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def admin_user(db) -> User:
    return User.objects.create_user(
        username="admin",
        password="secret",
        is_staff=True,
        is_superuser=True,
    )


@pytest.mark.django_db
def test_trends_empty_without_runs(api_client: APIClient) -> None:
    r = api_client.get("/api/trends/")
    assert r.status_code == 200
    body = r.json()
    assert body["results"] == []


@pytest.mark.django_db
def test_runs_list_and_trends_category_filter(api_client: APIClient) -> None:
    now = timezone.now()
    run = PipelineRun.objects.create(
        started_at=now,
        finished_at=now,
        geo="IN",
        lang="en",
        status="completed",
        meta={},
    )
    art = Article.objects.create(
        slug="article-example-com-x-a1b2c3d4e5f6",
        url="https://example.com/x",
        title="Article",
        domain="example.com",
        category="technology",
    )
    topic = Topic.objects.create(
        run=run,
        label="python",
        source="google",
        rank_in_source=1,
        reddit_score=None,
    )
    TrendSnapshot.objects.create(
        run=run,
        topic=topic,
        article=art,
        score_total=8.5,
        breakdown={"x": 1},
    )

    r_runs = api_client.get("/api/runs/")
    assert r_runs.status_code == 200
    assert r_runs.json()["results"][0]["id"] == run.id

    r_all = api_client.get(f"/api/trends/?run_id={run.id}")
    assert r_all.status_code == 200
    assert len(r_all.json()["results"]) == 1

    r_cat = api_client.get(f"/api/trends/?run_id={run.id}&category=technology")
    assert r_cat.status_code == 200
    assert len(r_cat.json()["results"]) == 1

    r_miss = api_client.get(f"/api/trends/?run_id={run.id}&category=business")
    assert r_miss.status_code == 200
    assert r_miss.json()["results"] == []

    r_slug = api_client.get(f"/api/trends/?run_id={run.id}&category_slug=tech")
    assert r_slug.status_code == 200
    assert len(r_slug.json()["results"]) == 1


@pytest.mark.django_db
def test_top_viral_and_article_detail(api_client: APIClient) -> None:
    now = timezone.now()
    run = PipelineRun.objects.create(
        started_at=now,
        finished_at=now,
        geo="US",
        lang="en",
        status="completed",
        meta={},
    )
    art = Article.objects.create(
        slug="story-news-example-y-9f8e7d6c5b4a",
        url="https://news.example/y",
        title="Story",
        domain="news.example",
        category="general",
    )
    TrendSnapshot.objects.create(
        run=run,
        topic=None,
        article=art,
        score_total=9.0,
        breakdown={},
    )

    r_top = api_client.get(f"/api/top-viral/?run_id={run.id}")
    assert r_top.status_code == 200
    res = r_top.json()["results"]
    assert len(res) == 1
    assert res[0]["article_id"] == art.id
    assert res[0]["score"] == 9.0
    assert res[0]["category"] == "general"
    assert res[0]["slug"] == art.slug
    assert res[0]["read_time_minutes"] >= 1
    assert res[0]["authors"] == []
    assert res[0]["image_urls"] == []
    assert res[0]["extractive_summary"] == ""

    r_art = api_client.get(f"/api/articles/{art.id}/?run_id={run.id}")
    assert r_art.status_code == 200
    body = r_art.json()
    assert body["id"] == art.id
    assert body["url"] == art.url
    assert body["slug"] == art.slug
    assert body["read_time_minutes"] >= 1
    assert body["authors"] == []
    assert body["image_urls"] == []
    assert body["extractive_summary"] == ""


@pytest.mark.django_db
def test_article_search_and_category_slug_top_viral(api_client: APIClient) -> None:
    now = timezone.now()
    run = PipelineRun.objects.create(
        started_at=now,
        finished_at=now,
        geo="US",
        lang="en",
        status="completed",
        meta={},
    )
    art = Article.objects.create(
        slug="unique-widget-search-abc123def456",
        url="https://search.example/widget",
        title="Widget breakthrough",
        domain="search.example",
        category="technology",
        processed_content="The quantum widget solves everything.",
    )
    TrendSnapshot.objects.create(
        run=run,
        topic=None,
        article=art,
        score_total=7.0,
        breakdown={},
    )

    r_search = api_client.get("/api/articles/search/?q=widget")
    assert r_search.status_code == 200
    hits = r_search.json()["results"]
    assert len(hits) >= 1
    assert any(h["id"] == art.id for h in hits)
    assert hits[0]["read_time_minutes"] >= 1

    r_short = api_client.get("/api/articles/search/?q=x")
    assert r_short.status_code == 400

    r_tv_slug = api_client.get(f"/api/top-viral/?run_id={run.id}&category_slug=tech")
    assert r_tv_slug.status_code == 200
    assert len(r_tv_slug.json()["results"]) == 1


@pytest.mark.django_db
def test_meta_categories(api_client: APIClient) -> None:
    r = api_client.get("/api/meta/categories/")
    assert r.status_code == 200
    cats = r.json()["categories"]
    assert any(c.get("slug") == "trending" and c.get("virtual") for c in cats)
    assert any(c.get("slug") == "tech" and not c.get("virtual") for c in cats)


@pytest.mark.django_db
def test_article_related_order_by_score(api_client: APIClient) -> None:
    now = timezone.now()
    run = PipelineRun.objects.create(
        started_at=now,
        finished_at=now,
        geo="US",
        lang="en",
        status="completed",
        meta={},
    )
    a1 = Article.objects.create(
        slug="rel-a-one-aaaaaaaaaaaa",
        url="https://rel.example/a1",
        title="A1",
        domain="rel.example",
        category="technology",
    )
    a2 = Article.objects.create(
        slug="rel-a-two-bbbbbbbbbbbb",
        url="https://rel.example/a2",
        title="A2",
        domain="rel.example",
        category="technology",
    )
    Article.objects.create(
        slug="rel-other-cat-cccccccccccc",
        url="https://rel.example/other",
        title="Other",
        domain="rel.example",
        category="sports",
    )
    TrendSnapshot.objects.create(
        run=run, topic=None, article=a1, score_total=3.0, breakdown={}
    )
    TrendSnapshot.objects.create(
        run=run, topic=None, article=a2, score_total=9.0, breakdown={}
    )

    r = api_client.get(f"/api/articles/{a1.id}/related/?run_id={run.id}")
    assert r.status_code == 200
    ids = [row["id"] for row in r.json()["results"]]
    assert ids[0] == a2.id
    assert r.json()["results"][0]["score"] == 9.0
    assert r.json()["results"][0]["category_slug"] == "tech"


@pytest.mark.django_db
def test_article_patch_delete_requires_admin(
    api_client: APIClient, admin_user: User
) -> None:
    now = timezone.now()
    PipelineRun.objects.create(
        started_at=now,
        finished_at=now,
        geo="US",
        lang="en",
        status="completed",
        meta={},
    )
    art = Article.objects.create(
        slug="patch-me-dddddddddddd",
        url="https://patch.example/p",
        title="Before",
        domain="patch.example",
        category="general",
    )
    r_denied = api_client.patch(
        f"/api/articles/{art.id}/",
        {"title": "Nope"},
        format="json",
    )
    assert r_denied.status_code == 401

    api_client.force_authenticate(user=admin_user)
    r_ok = api_client.patch(
        f"/api/articles/{art.id}/",
        {"title": "After"},
        format="json",
    )
    assert r_ok.status_code == 200
    assert r_ok.json()["title"] == "After"

    r_del = api_client.delete(f"/api/articles/{art.id}/")
    assert r_del.status_code == 204
    assert not Article.objects.filter(pk=art.pk).exists()


@pytest.mark.django_db
def test_article_run_seo_admin_persists(
    api_client: APIClient, admin_user: User
) -> None:
    now = timezone.now()
    run = PipelineRun.objects.create(
        started_at=now,
        finished_at=now,
        geo="US",
        lang="en",
        status="completed",
        meta={},
    )
    art = Article.objects.create(
        slug="seo-target-eeeeeeeeeeee",
        url="https://seo.example/s",
        title="SEO Target",
        domain="seo.example",
        category="general",
        extractive_summary="Short summary for SEO.",
    )
    fake_seo = {
        "optimized_title": "T",
        "meta_description": "M" * 20,
        "keywords": ["a", "b", "c", "d", "e"],
        "slug": "seo-slug",
    }
    api_client.force_authenticate(user=admin_user)
    with patch("config.api.views.generate_seo", return_value=fake_seo):
        r = api_client.post(f"/api/articles/{art.id}/run-seo/?run_id={run.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["article_id"] == art.id
    assert body["seo"]["optimized_title"] == "T"


@pytest.mark.django_db
def test_admin_generate_and_leads(
    api_client: APIClient, admin_user: User
) -> None:
    art = Article.objects.create(
        slug="lead-article-ffffffffffff",
        url="https://lead.example/l",
        title="Lead Article",
        domain="lead.example",
        category="general",
    )
    UserFeedback.objects.create(article=art, label="hot", notes="call back")

    api_client.force_authenticate(user=admin_user)
    with patch("config.api.views.run_pipeline_task.delay") as m_delay:
        m_delay.return_value = MagicMock(id="task-test")
        r_gen = api_client.post("/api/admin/articles/generate/", {"limit": 3}, format="json")
    assert r_gen.status_code == 202
    assert r_gen.json()["task_id"] == "task-test"

    r_leads = api_client.get("/api/admin/analytics/leads/")
    assert r_leads.status_code == 200
    row = r_leads.json()["results"][0]
    assert row["label"] == "hot"
    assert row["article_title"] == "Lead Article"
    assert row["article_id"] == art.id
