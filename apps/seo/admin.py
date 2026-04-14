from django.contrib import admin

from apps.seo import models as m


@admin.register(m.SEOData)
class SEODataAdmin(admin.ModelAdmin):
    list_display = ("id", "article_enrichment_id", "slug", "optimized_title")
