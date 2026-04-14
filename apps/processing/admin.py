from django.contrib import admin

from apps.processing import models as m


@admin.register(m.PipelineRun)
class PipelineRunAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "geo", "lang", "started_at")


@admin.register(m.ArticleEnrichment)
class ArticleEnrichmentAdmin(admin.ModelAdmin):
    list_display = ("id", "article_id", "run_id", "main_topic", "created_at")
