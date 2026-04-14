"""Persist pipeline results via Django ORM when configured."""

from __future__ import annotations

import logging
import os
from typing import Any

from core.topics import TopicSignal

logger = logging.getLogger(__name__)


def try_persist(
    *,
    geo: str,
    lang: str,
    topic_signals: list[TopicSignal],
    results: list[dict[str, Any]],
    meta: dict[str, Any] | None = None,
) -> int | None:
    """
    Persist via Django ORM when ``DJANGO_SETTINGS_MODULE`` is set.
    Otherwise log and return ``None`` (legacy SQLAlchemy path removed).
    """
    if os.environ.get("DJANGO_SETTINGS_MODULE"):
        import django

        django.setup()
        from apps.processing.persistence import try_persist_django

        return try_persist_django(
            geo=geo,
            lang=lang,
            topic_signals=topic_signals,
            results=results,
            meta=meta,
        )

    logger.debug(
        "Persistence skipped: set DJANGO_SETTINGS_MODULE and use Django migrations "
        "(SQLAlchemy/Alembic path removed)."
    )
    return None
