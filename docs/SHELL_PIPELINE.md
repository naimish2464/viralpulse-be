# Running the trend pipeline from Django (real network)

The pipeline hits **live** RSS, Google Trends, and scraping (unless you narrow inputs). Use **`skip_ai=True`** to avoid LLM calls while still exercising the rest of the stack.

## Management command (recommended)

From the project root, with `DJANGO_SETTINGS_MODULE` set (or use `manage.py`, which loads settings):

```bash
set DJANGO_SETTINGS_MODULE=config.settings.development
python manage.py run_trend_pipeline --skip-ai --limit 5
```

Options include `--skip-seo`, `--with-reddit`, `--no-save`, and `--include-unmatched`.

## Django shell

```python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.processing.pipeline_runner import run_pipeline_and_persist

results, run_id = run_pipeline_and_persist(skip_ai=True, limit=5)
len(results), run_id
```

`run_id` is the persisted **`PipelineRun`** primary key when saving succeeded, otherwise `None`.

Celery task **`processing.run_pipeline_task`** calls the same **`run_pipeline_and_persist`** entrypoint.
