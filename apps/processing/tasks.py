"""Celery tasks for pipeline execution (manual + periodic)."""

from __future__ import annotations

import logging
import os
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)

# Retry transient / unknown failures with exponential backoff (max ~10 min cap in Celery)
_PIPELINE_RETRY_KWARGS: dict[str, Any] = {
    "max_retries": 3,
    "countdown": 60,
}


def _ensure_django() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    import django

    django.setup()


def _log_task_boundary(
    task_self: Any,
    *,
    phase: str,
    extra: dict[str, Any] | None = None,
) -> None:
    req = getattr(task_self, "request", None)
    tid = getattr(req, "id", None) if req else None
    retries = getattr(req, "retries", 0) if req else 0
    name = getattr(req, "task", None) if req else getattr(task_self, "name", "task")
    payload = {
        "celery_task_id": tid,
        "celery_task_name": name,
        "celery_retries": retries,
        "phase": phase,
    }
    if extra:
        payload.update(extra)
    logger.info("celery pipeline %s", payload)


@shared_task(
    bind=True,
    name="processing.run_pipeline_task",
    ignore_result=False,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    retry_kwargs=_PIPELINE_RETRY_KWARGS,
)
def run_pipeline_task(
    self,
    limit: int = 10,
    with_reddit: bool = False,
    skip_ai: bool = False,
    skip_seo: bool = False,
    include_unmatched: bool = False,
    seo_cli_on: bool = False,
    seo_cli_off: bool = False,
) -> dict[str, Any]:
    """
    On-demand pipeline run (e.g. from ``POST /api/runs/trigger/``).
    Retries up to 3 times with exponential backoff on failure.
    """
    _log_task_boundary(
        self,
        phase="start",
        extra={
            "limit": limit,
            "with_reddit": with_reddit,
            "skip_ai": skip_ai,
            "skip_seo": skip_seo,
        },
    )
    _ensure_django()

    from apps.processing.pipeline_runner import run_pipeline_and_persist

    try:
        out, run_id = run_pipeline_and_persist(
            limit=limit,
            with_reddit=with_reddit,
            skip_ai=skip_ai,
            skip_seo=skip_seo,
            save_to_db=True,
            include_unmatched=include_unmatched,
            seo_cli_on=seo_cli_on,
            seo_cli_off=seo_cli_off,
        )
        result = {
            "status": "ok",
            "count": len(out),
            "run_id": run_id,
            "task_id": self.request.id,
        }
        _log_task_boundary(self, phase="success", extra={"run_id": run_id, "count": len(out)})
        return result
    except Exception as e:
        _log_task_boundary(
            self,
            phase="error",
            extra={"error": str(e), "will_retry": self.request.retries < _PIPELINE_RETRY_KWARGS["max_retries"]},
        )
        logger.exception("Pipeline task failed: %s", e)
        raise


@shared_task(
    bind=True,
    name="processing.run_scheduled_pipeline",
    ignore_result=False,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    retry_kwargs=_PIPELINE_RETRY_KWARGS,
)
def run_scheduled_pipeline(self) -> dict[str, Any]:
    """
    Periodic pipeline run (Celery Beat, every 30 minutes by default).

    Uses conservative defaults to limit API spend; adjust in ``CELERY_BEAT_SCHEDULE``
    or switch to calling ``run_pipeline_task`` with different kwargs via a custom task.
    """
    _log_task_boundary(self, phase="scheduled_start", extra={"schedule": "every_30_min"})
    _ensure_django()

    from apps.processing.pipeline_runner import run_pipeline_and_persist

    try:
        out, run_id = run_pipeline_and_persist(
            limit=10,
            with_reddit=False,
            skip_ai=True,
            skip_seo=True,
            save_to_db=True,
            include_unmatched=False,
        )
        result = {
            "status": "ok",
            "count": len(out),
            "run_id": run_id,
            "task_id": self.request.id,
            "scheduled": True,
        }
        _log_task_boundary(
            self,
            phase="scheduled_success",
            extra={"run_id": run_id, "count": len(out)},
        )
        return result
    except Exception as e:
        _log_task_boundary(
            self,
            phase="scheduled_error",
            extra={"error": str(e), "will_retry": self.request.retries < _PIPELINE_RETRY_KWARGS["max_retries"]},
        )
        logger.exception("Scheduled pipeline task failed: %s", e)
        raise
