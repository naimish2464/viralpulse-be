from __future__ import annotations

from django.db import models


class SEOData(models.Model):
    article_enrichment = models.OneToOneField(
        "processing.ArticleEnrichment",
        on_delete=models.CASCADE,
        related_name="seo_data",
    )
    optimized_title = models.CharField(max_length=512, default="")
    meta_description = models.TextField(default="")
    slug = models.CharField(max_length=256, default="", db_index=True)
    keywords = models.JSONField(default=list)
    extras = models.JSONField(null=True, blank=True, default=dict)

    class Meta:
        verbose_name = "SEO data"
        verbose_name_plural = "SEO data"

    def __str__(self) -> str:
        return f"seo:{self.article_enrichment_id}"
