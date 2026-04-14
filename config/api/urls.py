"""
API URLconf (included under ``/api/`` from project ``urls.py``).

Trends & viral:
    GET  /api/trends/              — paginated topics; ``?run_id=&category=``
    GET  /api/topics/              — alias of ``/api/trends/``
    GET  /api/top-viral/           — paginated top scores; ``?run_id=&category=``
    GET  /api/articles/top/        — alias of ``/api/top-viral/``

Meta:
    GET  /api/meta/categories/     — navbar + RSS category metadata

Articles:
    GET  /api/articles/search/     — search (``?q=`` min 2 chars; paginated)
    GET  /api/articles/<id>/related/ — same-category related (scores when run snapshots exist)
    POST /api/articles/<id>/run-seo/ — admin: generate & persist SEO for a run
    GET  /api/articles/<id>/       — article detail; ``?run_id=`` optional
    PATCH /api/articles/<id>/      — admin: partial update (returns full detail)
    DELETE /api/articles/<id>/   — admin

Admin:
    POST /api/admin/articles/generate/ — schedule pipeline (admin auth)
    GET  /api/admin/analytics/leads/   — paginated feedback rows

Other:
    GET  /api/health/
    GET  /api/runs/
    POST /api/runs/trigger/
    POST /api/feedback/
"""

from django.urls import path

from config.api import views

urlpatterns = [
    path("health/", views.health),
    path("meta/categories/", views.meta_categories),
    path("runs/", views.PipelineRunListView.as_view()),
    # Trends (category filter via query string)
    path("trends/", views.TrendTopicListView.as_view()),
    path("topics/", views.TrendTopicListView.as_view()),
    path("top-viral/", views.TopViralListView.as_view()),
    path("articles/top/", views.TopViralListView.as_view()),
    path("articles/search/", views.ArticleSearchListView.as_view()),
    path("admin/articles/generate/", views.admin_articles_generate),
    path("admin/analytics/leads/", views.AdminLeadsListView.as_view()),
    path("articles/<int:pk>/related/", views.ArticleRelatedListView.as_view()),
    path("articles/<int:pk>/run-seo/", views.article_run_seo),
    path("articles/<int:pk>/", views.ArticleDetailView.as_view()),
    path("runs/trigger/", views.trigger_run),
    path("feedback/", views.post_feedback),
]
