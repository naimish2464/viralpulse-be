from django.contrib import admin

from apps.trends import models as m


@admin.register(m.Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("id", "run_id", "label", "source")


@admin.register(m.TrendSnapshot)
class TrendSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "run_id", "article_id", "score_total")
