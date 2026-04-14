"""
Celery application for Django.

Run worker:
    celery -A config worker -l info

Run beat (periodic tasks require a beat process):
    celery -A config beat -l info

Redis URLs come from Django settings (``CELERY_BROKER_URL``, ``CELERY_RESULT_BACKEND``).
"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
