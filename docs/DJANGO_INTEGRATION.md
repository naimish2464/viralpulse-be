# Django integration (service layer)

This project uses **Django + DRF** as the only web/API stack. There is **no FastAPI** in application code.

## Layers

| Layer | Role |
|-------|------|
| **`core/`** | Domain logic: RSS, scrape, AI, SEO, scoring, signals, matching, `config`. Orchestrated by `services.pipeline.run_pipeline` (not Django). |
| **`services/`** | Thin orchestration: wires `core` modules into the pipeline steps (trends → RSS → match → enrich → cluster → score → optional persist hook). |
| **`apps/processing/`** | Django integration: **`pipeline_runner.run_pipeline_and_persist`** calls `services.pipeline.run_pipeline` with persistence; **`persistence.py`** saves to the ORM; Celery **`tasks`** delegates to the runner. |
| **`apps/articles`**, **`apps/trends`**, **`apps/seo`** | Data models and admin. |
| **`config/`** | Django project: settings, URLs, DRF API under `/api/`. |

## Entrypoints

- **HTTP**: `python manage.py runserver` — API at `/api/` (see `docs/DJANGO_JUNIOR_GUIDE.md`).
- **Pipeline + DB**: `python manage.py run_trend_pipeline` or Celery task `processing.run_pipeline_task`.
- **CLI** (optional): `python -m core` — Typer CLI in `core/cli.py` (same pipeline as `services.pipeline`).

## Persistence

When `DJANGO_SETTINGS_MODULE` is set, `services.pipeline.run_pipeline` persists via `core.db.persist.try_persist`, which delegates to `apps.processing.persistence.try_persist_django`.
