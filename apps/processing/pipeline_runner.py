"""
Django-facing entrypoint for the trend pipeline: same orchestration as
``services.pipeline.run_pipeline`` with persistence and optional ``run_id``.
"""

from __future__ import annotations

from typing import Any

from services.pipeline import run_pipeline


def run_pipeline_and_persist(
    *,
    save_to_db: bool = True,
    **kwargs: Any,
) -> tuple[list[dict[str, Any]], int | None]:
    """
    Run the full pipeline and persist when ``save_to_db`` is True (default).

    Returns ``(results, run_id)`` where ``run_id`` is the Django ``PipelineRun`` id
    when persistence succeeded, else ``None``.
    """
    return run_pipeline(save_to_db=save_to_db, return_run_id=True, **kwargs)
