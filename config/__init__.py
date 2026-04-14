"""Django project package — load Celery app when Django starts."""

from __future__ import annotations

from config.celery import app as celery_app

__all__ = ("celery_app",)
