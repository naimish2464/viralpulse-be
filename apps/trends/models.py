from __future__ import annotations

from django.db import models


class Topic(models.Model):
    run = models.ForeignKey(
        "processing.PipelineRun",
        on_delete=models.CASCADE,
        related_name="topics",
    )
    label = models.CharField(max_length=512)
    source = models.CharField(max_length=32)
    rank_in_source = models.IntegerField(null=True, blank=True)
    reddit_score = models.IntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["run", "label", "source"],
                name="uq_topic_run_label_source",
            ),
        ]
        indexes = [
            models.Index(fields=["run"]),
        ]

    def __str__(self) -> str:
        return self.label[:60]


class TrendSnapshot(models.Model):
    run = models.ForeignKey(
        "processing.PipelineRun",
        on_delete=models.CASCADE,
        related_name="snapshots",
    )
    topic = models.ForeignKey(
        Topic,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="snapshots",
    )
    article = models.ForeignKey(
        "articles.Article",
        on_delete=models.CASCADE,
        related_name="trend_snapshots",
    )
    score_total = models.FloatField()
    breakdown = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["run", "-score_total"]),
            models.Index(fields=["run"]),
            models.Index(fields=["article"]),
            models.Index(fields=["topic"]),
        ]

    def __str__(self) -> str:
        return f"snapshot {self.pk} score={self.score_total}"
