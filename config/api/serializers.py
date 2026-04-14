"""
DRF serializers — minimal JSON shapes for public API responses.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from apps.articles.models import Article, UserFeedback
from apps.processing.models import ArticleEnrichment, PipelineRun
from apps.seo.models import SEOData
from apps.trends.models import Topic, TrendSnapshot
from core.article_read_time import estimate_read_time_minutes
from core.category_ui import nav_slug_for_rss_key


def _article_read_time_minutes(article: Article) -> int:
    text = (article.processed_content or article.content or "").strip()
    return estimate_read_time_minutes(text)


def _article_authors_list(article: Article) -> list[str]:
    raw = article.authors
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip()]
    return []


def _article_image_urls_list(article: Article) -> list[str]:
    raw = article.image_urls
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip()]
    return []


def _seo_to_dict(sd: SEOData) -> dict[str, Any]:
    out: dict[str, Any] = {
        "optimized_title": sd.optimized_title,
        "meta_description": sd.meta_description,
        "slug": sd.slug,
        "keywords": sd.keywords if isinstance(sd.keywords, list) else [],
    }
    if sd.extras and isinstance(sd.extras, dict):
        for k, v in sd.extras.items():
            if k not in out:
                out[k] = v
    return out


class PipelineRunSerializer(serializers.ModelSerializer):
    """Pipeline run summary (list)."""

    class Meta:
        model = PipelineRun
        fields = ("id", "geo", "lang", "started_at", "finished_at", "status")


class TrendTopicSerializer(serializers.ModelSerializer):
    """
    Trend topic for a pipeline run.

    Query params (on list view): ``run_id``, ``category`` (article RSS category).
    """

    run_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Topic
        fields = ("id", "run_id", "label", "source", "rank_in_source", "reddit_score")


class TopViralSerializer(serializers.ModelSerializer):
    """Top scored articles for a run (ordered by score descending)."""

    article_id = serializers.IntegerField(source="article.id", read_only=True)
    title = serializers.CharField(source="article.title", read_only=True)
    url = serializers.CharField(source="article.url", read_only=True)
    domain = serializers.CharField(source="article.domain", read_only=True)
    category = serializers.CharField(source="article.category", read_only=True)
    published_raw = serializers.CharField(
        source="article.published_raw",
        read_only=True,
        allow_null=True,
    )
    score = serializers.FloatField(source="score_total", read_only=True)
    run_id = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    main_topic = serializers.SerializerMethodField()
    seo = serializers.SerializerMethodField()
    slug = serializers.CharField(
        source="article.slug",
        read_only=True,
        allow_blank=True,
    )
    extractive_summary = serializers.CharField(
        source="article.extractive_summary",
        read_only=True,
        allow_blank=True,
    )
    authors = serializers.SerializerMethodField()
    image_urls = serializers.SerializerMethodField()
    hero_image_url = serializers.SerializerMethodField()
    read_time_minutes = serializers.SerializerMethodField()

    class Meta:
        model = TrendSnapshot
        fields = (
            "article_id",
            "slug",
            "title",
            "url",
            "domain",
            "category",
            "published_raw",
            "score",
            "run_id",
            "summary",
            "extractive_summary",
            "main_topic",
            "authors",
            "image_urls",
            "hero_image_url",
            "read_time_minutes",
            "seo",
        )

    def get_run_id(self, obj: TrendSnapshot) -> int:
        return int(self.context.get("run_id") or obj.run_id)

    def _enrichment(self, obj: TrendSnapshot) -> ArticleEnrichment | None:
        return self.context.get("enrichments", {}).get(obj.article_id)

    def get_summary(self, obj: TrendSnapshot) -> str:
        enr = self._enrichment(obj)
        return enr.summary if enr else ""

    def get_main_topic(self, obj: TrendSnapshot) -> str:
        enr = self._enrichment(obj)
        return enr.main_topic if enr else ""

    def get_seo(self, obj: TrendSnapshot) -> dict[str, Any] | None:
        enr = self._enrichment(obj)
        if not enr:
            return None
        try:
            return _seo_to_dict(enr.seo_data)
        except ObjectDoesNotExist:
            return None

    def get_authors(self, obj: TrendSnapshot) -> list[str]:
        return _article_authors_list(obj.article)

    def get_image_urls(self, obj: TrendSnapshot) -> list[str]:
        return _article_image_urls_list(obj.article)

    def get_hero_image_url(self, obj: TrendSnapshot) -> str:
        urls = _article_image_urls_list(obj.article)
        return urls[0] if urls else ""

    def get_read_time_minutes(self, obj: TrendSnapshot) -> int:
        return _article_read_time_minutes(obj.article)


class ArticleDetailSerializer(serializers.ModelSerializer):
    """
    Single article with enrichment + SEO for an optional ``run_id`` query param.
    """

    enrichment = serializers.SerializerMethodField()
    seo = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    authors = serializers.SerializerMethodField()
    image_urls = serializers.SerializerMethodField()
    hero_image_url = serializers.SerializerMethodField()
    read_time_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            "id",
            "slug",
            "url",
            "title",
            "domain",
            "category",
            "source_rss",
            "published_raw",
            "body",
            "extractive_summary",
            "authors",
            "image_urls",
            "hero_image_url",
            "read_time_minutes",
            "enrichment",
            "seo",
        )
        read_only_fields = fields

    def get_body(self, obj: Article) -> str:
        text = (obj.processed_content or obj.content or "").strip()
        if len(text) > 60000:
            return text[:60000]
        return text

    def get_authors(self, obj: Article) -> list[str]:
        return _article_authors_list(obj)

    def get_image_urls(self, obj: Article) -> list[str]:
        return _article_image_urls_list(obj)

    def get_hero_image_url(self, obj: Article) -> str:
        urls = _article_image_urls_list(obj)
        return urls[0] if urls else ""

    def get_read_time_minutes(self, obj: Article) -> int:
        return _article_read_time_minutes(obj)

    def get_enrichment(self, obj: Article) -> dict[str, Any] | None:
        run_id = self.context.get("run_id")
        if run_id is None:
            return None
        enr = (
            ArticleEnrichment.objects.filter(article=obj, run_id=run_id)
            .order_by("-id")
            .first()
        )
        if not enr:
            return None
        ideas = enr.content_angle_ideas if isinstance(enr.content_angle_ideas, list) else []
        return {
            "summary": enr.summary,
            "main_topic": enr.main_topic,
            "why_trending": enr.why_trending,
            "why_people_care": enr.why_people_care,
            "who_should_care": enr.who_should_care,
            "content_angle_ideas": [str(x) for x in ideas],
        }

    def get_seo(self, obj: Article) -> dict[str, Any] | None:
        run_id = self.context.get("run_id")
        if run_id is None:
            return None
        enr = (
            ArticleEnrichment.objects.filter(article=obj, run_id=run_id)
            .order_by("-id")
            .first()
        )
        if not enr:
            return None
        try:
            return _seo_to_dict(enr.seo_data)
        except ObjectDoesNotExist:
            return None


class ArticleSearchResultSerializer(serializers.ModelSerializer):
    """Compact article row for site search (no run-scoped enrichment)."""

    hero_image_url = serializers.SerializerMethodField()
    read_time_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            "id",
            "slug",
            "title",
            "url",
            "domain",
            "category",
            "published_raw",
            "hero_image_url",
            "read_time_minutes",
        )
        read_only_fields = fields

    def get_hero_image_url(self, obj: Article) -> str:
        urls = _article_image_urls_list(obj)
        return urls[0] if urls else ""

    def get_read_time_minutes(self, obj: Article) -> int:
        return _article_read_time_minutes(obj)


class ArticleRelatedSerializer(ArticleSearchResultSerializer):
    """Search-sized row plus viral score (when run snapshots exist) and UI slug."""

    score = serializers.SerializerMethodField()
    category_slug = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ArticleSearchResultSerializer.Meta.fields + ("score", "category_slug")
        read_only_fields = fields

    def get_score(self, obj: Article) -> float | None:
        v = self.context.get("related_scores", {}).get(obj.pk)
        return float(v) if v is not None else None

    def get_category_slug(self, obj: Article) -> str:
        return nav_slug_for_rss_key(obj.category or "")


class ArticleUpdateSerializer(serializers.ModelSerializer):
    """Partial article edits (admin)."""

    class Meta:
        model = Article
        fields = (
            "slug",
            "title",
            "category",
            "source_rss",
            "published_raw",
            "extractive_summary",
            "content",
            "processed_content",
            "authors",
            "image_urls",
        )

    def validate_slug(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Slug cannot be empty.")
        qs = Article.objects.filter(slug=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Slug already in use.")
        return value[:200]

    def validate_authors(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            raise serializers.ValidationError("authors must be a JSON array of strings.")
        out: list[str] = []
        for x in value:
            s = str(x).strip()
            if s:
                out.append(s[:256])
            if len(out) >= 24:
                break
        return out

    def validate_image_urls(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            raise serializers.ValidationError("image_urls must be a JSON array of strings.")
        from core import config

        max_n = getattr(config, "SCRAPE_MAX_IMAGES", 24)
        out: list[str] = []
        for x in value:
            s = str(x).strip()[:2048]
            if s:
                out.append(s)
            if len(out) >= max_n:
                break
        return out


class AdminLeadSerializer(serializers.ModelSerializer):
    """User feedback rows for admin analytics tables."""

    article_title = serializers.CharField(
        source="article.title",
        read_only=True,
        allow_null=True,
    )
    article_url = serializers.CharField(
        source="article.url",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = UserFeedback
        fields = (
            "id",
            "label",
            "notes",
            "created_at",
            "article_id",
            "article_title",
            "article_url",
            "story_cluster_id",
        )
        read_only_fields = fields


class FeedbackSerializer(serializers.Serializer):
    article_id = serializers.IntegerField(allow_null=True, required=False)
    story_cluster_id = serializers.IntegerField(allow_null=True, required=False)
    label = serializers.CharField(max_length=64)
    notes = serializers.CharField(default="", allow_blank=True)
