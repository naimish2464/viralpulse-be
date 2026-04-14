from __future__ import annotations

from django.db import models


class StoryCluster(models.Model):
    title_fingerprint = models.CharField(max_length=64, unique=True, db_index=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.title_fingerprint[:16] + "…"


class Article(models.Model):
    url = models.CharField(max_length=2048, unique=True, db_index=True)
    slug = models.CharField(
        max_length=200,
        unique=True,
        db_index=True,
        help_text="Stable URL slug (title + fingerprint hash).",
    )
    title = models.CharField(max_length=1024)
    domain = models.CharField(max_length=256, default="", db_index=True)
    category = models.CharField(max_length=64, default="general", db_index=True)
    source_rss = models.CharField(max_length=512, default="")
    published_raw = models.CharField(max_length=256, null=True, blank=True)
    title_fingerprint = models.CharField(max_length=64, default="", db_index=True)
    story_cluster = models.ForeignKey(
        StoryCluster,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="articles",
    )
    content = models.TextField(
        default="",
        blank=True,
        help_text="Full raw article body from RSS or scrape.",
    )
    processed_content = models.TextField(
        default="",
        blank=True,
        help_text="Normalized body (whitespace cleanup) for search and reuse.",
    )
    extractive_summary = models.TextField(
        default="",
        blank=True,
        help_text="Newspaper3k NLP extractive summary (when available).",
    )
    authors = models.JSONField(
        default=list,
        blank=True,
        help_text="Normalized author display names from the article page.",
    )
    image_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered image URLs (hero first): og, top, RSS, then inline.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["domain"]),
            models.Index(fields=["title_fingerprint"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self) -> str:
        return self.title[:80]


class ArticleEmbedding(models.Model):
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="embeddings",
    )
    model = models.CharField(max_length=128)
    dimension = models.PositiveIntegerField(default=0)
    vector = models.JSONField(default=list)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["article", "model"],
                name="uq_article_embedding_article_model",
            ),
        ]
        indexes = [
            models.Index(fields=["article"]),
        ]

    def __str__(self) -> str:
        return f"{self.article_id}:{self.model}"


class UserFeedback(models.Model):
    article = models.ForeignKey(
        Article,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="feedback",
    )
    story_cluster = models.ForeignKey(
        StoryCluster,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="feedback",
    )
    label = models.CharField(max_length=64)
    notes = models.TextField(default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.label}:{self.pk}"
