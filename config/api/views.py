"""
DRF API views.

Public list/detail endpoints (paginated, ``page`` / ``page_size``):

- ``GET /api/trends/`` — topics for a run; optional ``run_id``, ``category``.
- ``GET /api/articles/<id>/`` — article detail; optional ``run_id`` for enrichment/SEO.
- ``GET /api/top-viral/`` — snapshots by score; optional ``run_id``, ``category``.

``/api/topics/`` is an alias of ``/api/trends/``.
"""

from __future__ import annotations

from typing import Any

from django.db import connection
from django.db.models import Case, Q, When
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from apps.articles.models import Article, UserFeedback
from apps.processing.models import ArticleEnrichment, PipelineRun
from apps.processing.tasks import run_pipeline_task
from apps.seo.models import SEOData
from apps.trends.models import Topic, TrendSnapshot
from config.api.pagination import StandardResultsPagination
from config.api.serializers import (
    AdminLeadSerializer,
    ArticleDetailSerializer,
    ArticleRelatedSerializer,
    ArticleSearchResultSerializer,
    ArticleUpdateSerializer,
    FeedbackSerializer,
    PipelineRunSerializer,
    TopViralSerializer,
    TrendTopicSerializer,
    _seo_to_dict,
)
from core import config
from core.category_ui import categories_meta_payload, resolved_rss_category_for_filter
from core.seo import generate_seo, seo_fields_for_storage


def _latest_run() -> PipelineRun | None:
    return PipelineRun.objects.order_by("-id").first()


def _db_unavailable() -> bool:
    try:
        connection.ensure_connection()
    except Exception:
        return True
    return False


def _effective_run_id(request) -> int | None:
    raw = request.query_params.get("run_id")
    if raw is None:
        lr = _latest_run()
        return lr.id if lr else None
    try:
        return int(raw)
    except ValueError:
        raise ValidationError({"run_id": "Must be a valid integer."})


def _category_filter(request) -> str:
    """Legacy ``category`` string or ``category_slug`` (navbar / route slug)."""
    return resolved_rss_category_for_filter(
        category=(request.query_params.get("category") or "").strip(),
        category_slug=(request.query_params.get("category_slug") or "").strip(),
    )


class DatabaseRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if _db_unavailable():
            return Response(
                {"detail": "Database unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return super().dispatch(request, *args, **kwargs)


class PipelineRunListView(DatabaseRequiredMixin, ListAPIView):
    queryset = PipelineRun.objects.all().order_by("-id")
    serializer_class = PipelineRunSerializer
    pagination_class = StandardResultsPagination


class TrendTopicListView(DatabaseRequiredMixin, ListAPIView):
    """
    List trend topics for one pipeline run.

    Query parameters:
        run_id (optional) — defaults to latest run.
        category (optional) — filter by article RSS category (``iexact``).
        category_slug (optional) — UI slug (e.g. ``tech`` → ``technology``); ignored if ``category`` is set.
    """

    serializer_class = TrendTopicSerializer
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        rid = _effective_run_id(self.request)
        if rid is None:
            return Topic.objects.none()
        qs = Topic.objects.filter(run_id=rid).order_by("id")
        cat = _category_filter(self.request)
        if cat:
            qs = qs.filter(snapshots__article__category__iexact=cat).distinct()
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        rid = _effective_run_id(request)
        page = self.paginate_queryset(queryset)
        ctx = {**self.get_serializer_context(), "run_id": rid}
        ser = self.get_serializer(page, many=True, context=ctx)
        return self.get_paginated_response(ser.data)


class TopViralListView(DatabaseRequiredMixin, ListAPIView):
    """
    Top viral articles (by ``score_total``) for one pipeline run.

    Query parameters:
        run_id (optional) — defaults to latest run.
        category (optional) — filter by article ``category`` (``iexact``).
        category_slug (optional) — UI slug; ignored if ``category`` is set.
    """

    serializer_class = TopViralSerializer
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        rid = _effective_run_id(self.request)
        if rid is None:
            return TrendSnapshot.objects.none()
        qs = (
            TrendSnapshot.objects.filter(run_id=rid)
            .select_related("article")
            .order_by("-score_total")
        )
        cat = _category_filter(self.request)
        if cat:
            qs = qs.filter(article__category__iexact=cat)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        rid = _effective_run_id(request)
        article_ids = list(queryset.values_list("article_id", flat=True))
        enrichments: dict[int, ArticleEnrichment] = {}
        if article_ids and rid is not None:
            rows = (
                ArticleEnrichment.objects.filter(run_id=rid, article_id__in=article_ids)
                .select_related("seo_data")
                .order_by("article_id", "-id")
            )
            for e in rows:
                if e.article_id not in enrichments:
                    enrichments[e.article_id] = e
        page = self.paginate_queryset(queryset)
        ctx = {
            **self.get_serializer_context(),
            "run_id": rid,
            "enrichments": enrichments,
        }
        ser = self.get_serializer(page, many=True, context=ctx)
        return self.get_paginated_response(ser.data)


class ArticleDetailView(DatabaseRequiredMixin, RetrieveUpdateDestroyAPIView):
    """
    Single article.

    GET — public. PATCH / DELETE — staff (Session or Basic auth).

    Query parameters:
        run_id (optional) — enrichment + SEO for that run; defaults to latest run when omitted.
    """

    queryset = Article.objects.all()
    serializer_class = ArticleDetailSerializer
    lookup_field = "pk"

    def get_authenticators(self):
        if self.request.method in ("PATCH", "PUT", "DELETE"):
            return [BasicAuthentication(), SessionAuthentication()]
        return []

    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT", "DELETE"):
            return [IsAdminUser()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return ArticleUpdateSerializer
        return ArticleDetailSerializer

    def get_serializer_context(self) -> dict[str, Any]:
        ctx = super().get_serializer_context()
        raw = self.request.query_params.get("run_id")
        if raw is not None:
            try:
                ctx["run_id"] = int(raw)
            except ValueError:
                raise ValidationError({"run_id": "Must be a valid integer."})
        else:
            lr = _latest_run()
            ctx["run_id"] = lr.id if lr else None
        return ctx

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance.refresh_from_db()
        detail = ArticleDetailSerializer(instance, context=self.get_serializer_context())
        return Response(detail.data)


class ArticleRelatedListView(DatabaseRequiredMixin, ListAPIView):
    """
    Related articles in the same category.

    When ``run_id`` resolves (default: latest run), order follows viral scores for that run;
    otherwise falls back to ``-updated_at``. Optional ``?run_id=`` overrides.
    """

    serializer_class = ArticleRelatedSerializer
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        base = get_object_or_404(Article, pk=self.kwargs["pk"])
        rid = _effective_run_id(self.request)
        ids: list[int] = []
        scores: dict[int, float] = {}
        if rid is not None:
            seen: set[int] = set()
            for row in (
                TrendSnapshot.objects.filter(
                    run_id=rid,
                    article__category__iexact=base.category,
                )
                .order_by("-score_total")
                .values("article_id", "score_total")
            ):
                aid = int(row["article_id"])
                if aid == base.pk or aid in seen:
                    continue
                seen.add(aid)
                scores[aid] = float(row["score_total"])
                ids.append(aid)
                if len(ids) >= 200:
                    break
            if ids:
                self._related_scores = scores
                preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ids)])
                return Article.objects.filter(pk__in=ids).order_by(preserved)
        self._related_scores = {}
        return (
            Article.objects.filter(category__iexact=base.category)
            .exclude(pk=base.pk)
            .order_by("-updated_at")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        score_map = getattr(self, "_related_scores", {})
        page = self.paginate_queryset(queryset)
        context = {**self.get_serializer_context(), "related_scores": score_map}
        serializer = self.get_serializer(page, many=True, context=context)
        return self.get_paginated_response(serializer.data)


class AdminLeadsListView(DatabaseRequiredMixin, ListAPIView):
    """Paginated feedback / leads for admin dashboards."""

    serializer_class = AdminLeadSerializer
    pagination_class = StandardResultsPagination

    def get_authenticators(self):
        return [BasicAuthentication(), SessionAuthentication()]

    def get_permissions(self):
        return [IsAdminUser()]

    def get_queryset(self):
        return UserFeedback.objects.select_related("article").order_by("-created_at")


class ArticleSearchListView(DatabaseRequiredMixin, ListAPIView):
    """
    Full-text-ish search over stored articles (title + body fields).

    Query: ``q`` (required, min length 2), ``page``, ``page_size``.
    """

    serializer_class = ArticleSearchResultSerializer
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        q = (self.request.query_params.get("q") or "").strip()
        if len(q) < 2:
            return Article.objects.none()
        return (
            Article.objects.filter(
                Q(title__icontains=q)
                | Q(processed_content__icontains=q)
                | Q(content__icontains=q)
                | Q(extractive_summary__icontains=q)
            )
            .order_by("-updated_at")
            .only(
                "id",
                "slug",
                "title",
                "url",
                "domain",
                "category",
                "published_raw",
                "image_urls",
                "processed_content",
                "content",
            )
        )

    def list(self, request, *args, **kwargs):
        q = (request.query_params.get("q") or "").strip()
        if len(q) < 2:
            raise ValidationError({"q": "Must be at least 2 characters."})
        return super().list(request, *args, **kwargs)


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


@api_view(["GET"])
def meta_categories(request):
    return Response({"categories": categories_meta_payload()})


def _truthy(val) -> bool:
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("1", "true", "yes", "on")


def _schedule_pipeline_response(request) -> Response:
    if _db_unavailable():
        return Response({"detail": "Database unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    data = getattr(request, "data", {}) or {}
    qp = request.query_params
    try:
        raw_lim = data.get("limit", qp.get("limit", 10))
        limit = int(raw_lim)
    except (TypeError, ValueError):
        limit = 10
    with_reddit = _truthy(data.get("with_reddit", qp.get("with_reddit")))
    skip_ai = _truthy(data.get("skip_ai", qp.get("skip_ai")))
    include_unmatched = _truthy(data.get("include_unmatched", qp.get("include_unmatched")))
    seo_cli_on = _truthy(data.get("seo_cli_on", qp.get("seo_cli_on")))
    seo_cli_off = _truthy(data.get("seo_cli_off", qp.get("seo_cli_off")))
    skip_seo = _truthy(data.get("skip_seo", qp.get("skip_seo"))) or seo_cli_off

    async_result = run_pipeline_task.delay(
        limit=limit,
        with_reddit=with_reddit,
        skip_ai=skip_ai,
        skip_seo=skip_seo,
        include_unmatched=include_unmatched,
        seo_cli_on=seo_cli_on,
        seo_cli_off=seo_cli_off,
    )
    return Response(
        {"status": "scheduled", "task_id": async_result.id},
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(["POST"])
def trigger_run(request):
    return _schedule_pipeline_response(request)


@api_view(["POST"])
@authentication_classes([BasicAuthentication, SessionAuthentication])
@permission_classes([IsAdminUser])
def admin_articles_generate(request):
    return _schedule_pipeline_response(request)


@api_view(["POST"])
@authentication_classes([BasicAuthentication, SessionAuthentication])
@permission_classes([IsAdminUser])
def article_run_seo(request, pk: int):
    if _db_unavailable():
        return Response({"detail": "Database unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    article = get_object_or_404(Article, pk=pk)
    rid = _effective_run_id(request)
    if rid is None:
        return Response(
            {"detail": "No pipeline run found; create a run or pass run_id."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    run = get_object_or_404(PipelineRun, pk=rid)
    enr = (
        ArticleEnrichment.objects.filter(article=article, run_id=rid)
        .order_by("-id")
        .first()
    )
    summary = ""
    main_topic = ""
    if enr:
        summary = (enr.summary or "").strip()
        main_topic = (enr.main_topic or "").strip()
    if not summary:
        summary = (article.extractive_summary or "").strip()
    if not summary:
        summary = ((article.processed_content or article.content or "").strip())[:12000]
    seo = generate_seo(
        article.title,
        summary,
        main_topic=main_topic,
        url=article.url,
    )
    if not seo:
        return Response(
            {"detail": "SEO generation failed (missing API key or upstream error)."},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    if not enr:
        enr = ArticleEnrichment.objects.create(
            article=article,
            run=run,
            summary=summary[:20000],
            main_topic=main_topic[:512],
            model=(getattr(config, "OPENAI_MODEL", None) or "")[:128],
        )
    fields = seo_fields_for_storage(seo)
    sd, created = SEOData.objects.get_or_create(
        article_enrichment=enr,
        defaults=fields,
    )
    if not created:
        for k, v in fields.items():
            setattr(sd, k, v)
        sd.save()
    return Response(
        {
            "article_id": article.id,
            "run_id": rid,
            "seo": _seo_to_dict(sd),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def post_feedback(request):
    if _db_unavailable():
        return Response({"detail": "Database unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    ser = FeedbackSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    body = ser.validated_data
    row = UserFeedback.objects.create(
        article_id=body.get("article_id"),
        story_cluster_id=body.get("story_cluster_id"),
        label=body["label"][:64],
        notes=body.get("notes") or "",
    )
    return Response({"id": row.id}, status=status.HTTP_201_CREATED)
