from __future__ import annotations

from django.db import models


class PipelineRun(models.Model):
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    geo = models.CharField(max_length=16, default="IN")
    lang = models.CharField(max_length=16, default="en")
    status = models.CharField(max_length=32, default="running")
    meta = models.JSONField(null=True, blank=True, default=dict)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["-id"]),
        ]

    def __str__(self) -> str:
        return f"run {self.pk} ({self.status})"


class ArticleEnrichment(models.Model):
    article = models.ForeignKey(
        "articles.Article",
        on_delete=models.CASCADE,
        related_name="enrichments",
    )
    run = models.ForeignKey(
        PipelineRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="enrichments",
    )
    summary = models.TextField(default="")
    main_topic = models.CharField(max_length=512, default="")
    why_trending = models.TextField(default="")
    why_people_care = models.TextField(default="")
    who_should_care = models.TextField(default="")
    content_angle_ideas = models.JSONField(default=list)
    model = models.CharField(max_length=128, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["article"]),
            models.Index(fields=["run"]),
        ]

    def __str__(self) -> str:
        return f"enrichment {self.pk} article={self.article_id}"
