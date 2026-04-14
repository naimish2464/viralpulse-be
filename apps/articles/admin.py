from django.contrib import admin

from apps.articles import models as m


@admin.register(m.StoryCluster)
class StoryClusterAdmin(admin.ModelAdmin):
    list_display = ("id", "title_fingerprint")


@admin.register(m.Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("id", "slug", "title", "domain", "url")
    search_fields = ("title", "url", "slug")


@admin.register(m.ArticleEmbedding)
class ArticleEmbeddingAdmin(admin.ModelAdmin):
    list_display = ("id", "article_id", "model", "dimension")


@admin.register(m.UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "label", "article_id", "created_at")
