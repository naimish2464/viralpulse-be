
# Viral Trend Engine

Python **trend intelligence** stack: live **Google Trends** (and optional **Reddit**), **RSS** headlines, **semantic + token** matching via embeddings, **scraping**, **LLM enrichment**, **scoring v2**, and **Django** + **DRF** for persistence and the HTTP API. Domain logic lives in the **`core`** package; orchestration is in **`services/pipeline.py`**; Django calls it via **`apps/processing/pipeline_runner.py`**. Optional CLI: `python -m core`.

## Features

- **Signals** — trendspy primary, pytrends fallback, file cache; topics carry **source** and **rank** (Google list order).
- **RSS** — category-based feed lists ([`core/rss_feeds.py`](core/rss_feeds.py)); adaptive body/image extraction from feed items; long RSS text skips per-article scraping.
- **Matching** — `hybrid` (embeddings + token overlap on **meaningful** words; stopwords like “of/the” ignored for multi-word topics), `semantic`, or `token` via `TREND_ENGINE_MATCH_MODE`.
- **Dedup** — URL dedup, normalized **title fingerprint**, **story clusters** from title-embedding similarity.
- **Scoring v2** — Weighted blend of trend rank, social/Reddit, recency, source quality, semantic relevance, plus small length/image bonuses; **breakdown** stored per snapshot.
- **AI** — OpenAI-compatible chat JSON: `summary`, `main_topic`, `why_trending`, plus `why_people_care`, `who_should_care`, `content_angle_ideas`.
- **SEO (optional)** — After enrichment and scoring, an extra LLM pass can add `seo`: `optimized_title`, `meta_description`, `keywords`, `slug` (gated by score and caps; not run on raw RSS; skipped with `--skip-ai`).
- **Storage** — **Django ORM** (`apps/articles`, `apps/processing`, `apps/trends`, `apps/seo`); vectors in `ArticleEmbedding` as JSON (no pgvector extension required). Use `python manage.py migrate` for schema changes.
- **API** — **Django REST Framework** under `/api/`.

## Setup

```bash
cd d:\bhg
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Copy [`.env.example`](.env.example) to `.env` and set at least `OPENAI_API_KEY` if you want embeddings, LLM enrichment, and hybrid matching. For persistence and the HTTP API, configure **PostgreSQL** (or use SQLite by leaving `DATABASE_URL` unset for local dev) and set `DJANGO_SETTINGS_MODULE`.

### Database (Django)

Use a PostgreSQL URL with the **psycopg3** driver, for example:

```text
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/trend_engine
```

Create the database, set `DATABASE_URL`, then apply migrations from the repo root:

```bash
set DJANGO_SETTINGS_MODULE=config.settings.development
set DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/trend_engine
python manage.py migrate
```

On Linux or macOS, use `export` instead of `set`.

### Testing locally (step-by-step for beginners)

See **[TESTING.md](TESTING.md)** for ordered test cases, example commands, what output to expect, and how to **cross-check trends and articles in Google and your browser** without technical guesswork.

## Commands reference

Run the CLI as a module from the project directory (venv activated):

```bash
python -m core <subcommand> [options]
```

### Built-in help

| Command                          | Use case                                             |
| -------------------------------- | ---------------------------------------------------- |
| `python -m core --help`        | List subcommands (`run`, `topics`, `version`). |
| `python -m core run --help`    | Full pipeline options.                               |
| `python -m core topics --help` | Trend signals JSON dump.                             |

### `run` — full pipeline

Runs trends → RSS → match → scrape → cluster → enrich → score → JSON on stdout (or `--out`). If `DATABASE_URL` is set, results are **persisted** unless you pass `--no-persist`.

| Option                  | Short  | Default                   | Use case                                                                                                                                                 |
| ----------------------- | ------ | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--out PATH`          | `-o` | stdout                    | Write JSON array to a file.                                                                                                                              |
| `--limit N`           | `-n` | `10`                    | Max**distinct stories** returned (after clustering).                                                                                               |
| `--geo REGION`        | `-g` | env `TREND_ENGINE_GEO`  | Trends region:`IN`, `US`, `GB`, or aliases (`india`, `united_states`, …).                                                                     |
| `--lang CODE`         | `-l` | env `TREND_ENGINE_LANG` | trendspy language (e.g.`en`, `hi`).                                                                                                                  |
| `--skip-ai`           | —     | off                       | No OpenAI HTTP (no chat**or** embeddings); token-only topic match; placeholder summary (200-char clip); story clustering without title embeddings. |
| `--categories`        | —     | (see env)                 | Comma-separated keys:`technology`, `ai`, `business`, … — **ignored** if `TREND_ENGINE_RSS` is set.                                       |
| `--include-unmatched` | —     | off                       | After trend match, add unmatched RSS rows**round-robin by category** (up to scrape buffer); needs non-empty topics.                                |
| `--seo`               | —     | off                       | Enable SEO LLM for this run (in addition to `TREND_ENGINE_SEO_ENABLED`; needs API key; not with `--skip-ai`).                                        |
| `--no-seo`            | —     | off                       | Disable SEO for this run even if `TREND_ENGINE_SEO_ENABLED=1`.                                                                                         |
| `--with-reddit`       | —     | off                       | Merge r/all hot titles; needs `REDDIT_*` in `.env`.                                                                                                  |
| `--no-persist`        | —     | off                       | Skip DB writes when persistence would run (`DJANGO_SETTINGS_MODULE` or `DATABASE_URL` / Django default DB).                                          |
| `--verbose`           | `-v` | off                       | DEBUG on stderr.                                                                                                                                         |

Examples:

```bash
python -m core run --skip-ai --geo IN --limit 2
python -m core run --skip-ai --categories technology,current_affairs --include-unmatched --limit 8
python -m core run --geo US --limit 5 --out data\latest.json
python -m core run --no-persist --limit 5
```

### `topics` — trend signals (debug)

Prints one JSON object: `geo_resolved`, `count`, and **`signals`** — a list of `{ "label", "source", "rank_in_source" }` (Google ranks are 1-based within the fetched list).

| Option        | Short  | Default |
| ------------- | ------ | ------- |
| `--geo`     | `-g` | env     |
| `--lang`    | `-l` | env     |
| `--max`     | `-n` | `30`  |
| `--verbose` | `-v` | off     |

### `version`

Prints package version (e.g. `0.2.0`).

### HTTP API server (Django — recommended)

With dependencies installed, from the repo root:

```bash
set DJANGO_SETTINGS_MODULE=config.settings.development
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Full **directory layout**, **every `/api/...` endpoint**, **query parameters**, and **example JSON responses** for junior developers: **[docs/DJANGO_JUNIOR_GUIDE.md](docs/DJANGO_JUNIOR_GUIDE.md)**.

Summary (all paths are prefixed with `/api/`):

| Method | Path                                | Description                                                          |
| ------ | ----------------------------------- | -------------------------------------------------------------------- |
| GET    | `/health/`                        | Liveness (no DB).                                                    |
| GET    | `/runs/`                          | Paginated pipeline runs.                                             |
| GET    | `/trends/`, `/topics/`          | Paginated trend topics for a run; optional `run_id`, `category`. |
| GET    | `/top-viral/`, `/articles/top/` | Paginated top scores; optional `run_id`, `category`.             |
| GET    | `/articles/<id>/`                 | Article detail; optional `run_id` for enrichment/SEO.              |
| POST   | `/runs/trigger/`                  | Schedule pipeline via Celery (`202` + `task_id`).                |
| POST   | `/feedback/`                      | User feedback JSON.                                                  |

List endpoints use **pagination** (`page`, `page_size`; default page size 20, max 100).

### Dev script: `print_trends.py`

```bash
python print_trends.py
```

Prints the first 15 trending **keyword strings** (legacy helper using `fetch_trending_keywords()`).

Do **not** name a project file `pytrends.py` — it shadows the **pytrends** package.

## Architecture (pipeline)

1. **Google trends** — [`core/signals/google_trends.py`](core/signals/google_trends.py): `fetch_trending_topic_signals()` with rank; cache in `.trend_engine_cache/last_topics.json` (includes `topic_signals`).
2. **Topic merge** — [`core/topics.py`](core/topics.py): `TopicSignal`, `merge_topic_signals()` (Google first, then Reddit titles not already seen).
3. **RSS** — [`core/rss.py`](core/rss.py) resolves feeds from **`TREND_ENGINE_RSS`** (flat list, category `general`) **or** [`core/rss_feeds.py`](core/rss_feeds.py) + optional `TREND_ENGINE_RSS_CATEGORIES` / `--categories`. Each item gets plain text and images via [`core/rss_extract.py`](core/rss_extract.py) (`content` → `summary` → `description`; `media:*` and `<img src>`).
4. **Match** — [`core/semantic.py`](core/semantic.py) uses [`core/embeddings.py`](core/embeddings.py) + [`core/match.py`](core/match.py) for hybrid/token paths. With **`--skip-ai`**, embeddings are not used for matching or clustering (token path only).
5. **Dedup** — URL, title fingerprint [`core/dedup.py`](core/dedup.py), then story clustering (title-embedding similarity when embeddings exist; otherwise fingerprint-only buckets).
6. **Enrich body** — [`core/scrape.py`](core/scrape.py): `enrich_article_content()` uses RSS text when longer than `TREND_ENGINE_RSS_MIN_CHARS_FOR_SKIP_SCRAPE` (default 200); otherwise **newspaper3k**, with RSS fallback on failure.
7. **AI** — [`core/ai.py`](core/ai.py) (OpenAI-compatible chat + JSON).
8. **Score** — [`core/score.py`](core/score.py): `trend_score_breakdown()`.
9. **SEO (optional)** — [`core/seo.py`](core/seo.py): second LLM pass after scoring (title/summary in, `seo` JSON out); gated by env / CLI and min score; skipped with `--skip-ai`.
10. **Orchestration** — [`services/pipeline.py`](services/pipeline.py); Django persist [`core/db/persist.py`](core/db/persist.py) → [`apps/processing/persistence.py`](apps/processing/persistence.py). See [docs/DJANGO_INTEGRATION.md](docs/DJANGO_INTEGRATION.md).

If there are **no** topics from signals, the pipeline falls back to **RSS-only** (empty `matched_topics`).

## Package layout

| Path                              | Role                                                             |
| --------------------------------- | ---------------------------------------------------------------- |
| `core/config.py`                | Environment-driven settings                                      |
| `core/signals/google_trends.py` | Trends + geo + cache                                             |
| `core/signals/reddit.py`        | Optional PRAW hot posts                                          |
| `core/topics.py`                | `TopicSignal`, merge/normalize                                 |
| `core/rss.py`                   | feedparser + job resolution                                      |
| `core/rss_feeds.py`             | Category → feed URL map                                         |
| `core/rss_extract.py`           | Body / image extraction from entries                             |
| `core/match.py`                 | Token/phrase headline matching                                   |
| `core/semantic.py`              | Embedding-based match                                            |
| `core/embeddings.py`            | OpenAI-compatible `/embeddings`                                |
| `core/dedup.py`                 | Fingerprints + story clusters                                    |
| `core/scrape.py`                | newspaper3k                                                      |
| `core/ai.py`                    | LLM enrichment                                                   |
| `core/seo.py`                   | Optional SEO metadata LLM                                        |
| `core/score.py`                 | Scoring v2 + breakdown                                           |
| `services/pipeline.py`          | End-to-end orchestration                                         |
| `core/cli.py`                   | Typer CLI implementation                                         |
| `core/db/persist.py`            | `try_persist` → Django when `DJANGO_SETTINGS_MODULE` is set |
| `apps/*`                        | Django models, API, Celery,`pipeline_runner`                   |
| `config/`                       | Django project, DRF routes, Celery                               |

## JSON output shape (`run` each item)

Scraping uses **newspaper3k**: `image` is the primary/OG image; **`images`** is a deduped list of URLs found in the page (how many are found depends on HTML; not every inline image is always captured). **`description`** is the HTML meta description. **`authors`** is filled when the extractor finds bylines. **`content`** is the extracted article text (length capped by `TREND_ENGINE_SCRAPE_MAX_CHARS`, `0` = only the library’s own limit). The LLM still receives only the first `TREND_ENGINE_ENRICH_MAX_CHARS` characters of the body.

```json
{
  "title": "...",
  "url": "...",
  "summary": "...",
  "main_topic": "...",
  "why_trending": "...",
  "why_people_care": "...",
  "who_should_care": "...",
  "content_angle_ideas": ["...", "..."],
  "image": "...",
  "images": ["...", "..."],
  "description": "...",
  "authors": ["..."],
  "content": "...",
  "score": 8.5,
  "score_breakdown": {
    "trend_signal": 0.0,
    "social_signal": 0.0,
    "recency": 0.85,
    "source_quality": 0.95,
    "semantic_relevance": 0.42,
    "semantic_skipped": false,
    "length_bonus": 1.0,
    "image_bonus": 1.0,
    "weights": { "trend": 2.5, "social": 2.0, "recency": 1.5, "source": 1.0, "semantic": 3.0 }
  },
  "matched_topics": ["..."],
  "source_rss": "...",
  "semantic_best": 0.42,
  "story_cluster_id": 0,
  "title_fingerprint": "...",
  "published": "...",
  "seo": null
}
```

When SEO runs for an item, `seo` is an object: `optimized_title`, `meta_description`, `keywords` (array), `slug`. Otherwise `null`. Run `python manage.py migrate` after pulling changes so `ArticleEnrichment.seo` exists for persistence.

`title_embedding` is not included in CLI output (it is used internally and stored when persisting).

With **`--skip-ai`**, embeddings are not computed, so `semantic_relevance` is usually `0.0` and `score_breakdown.semantic_skipped` is **`true`**; the total score **does not** apply the semantic weight (so the breakdown is not misleading).

## Environment variables

Core and RSS (see also [`.env.example`](.env.example)):

| Variable                                                  | Meaning                                                                                          |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `TREND_ENGINE_GEO`                                      | Default region if you omit `--geo`                                                             |
| `TREND_ENGINE_LANG`                                     | trendspy language (`en`, `hi`, …)                                                           |
| `TREND_ENGINE_RSS`                                      | If non-empty,**only** these URLs are used (category `general`); overrides category feeds |
| `TREND_ENGINE_RSS_CATEGORIES`                           | Comma-separated category keys when `TREND_ENGINE_RSS` is empty; default = all categories       |
| `TREND_ENGINE_RSS_LIMIT`                                | Max entries per feed                                                                             |
| `TREND_ENGINE_RSS_MIN_CHARS_FOR_SKIP_SCRAPE`            | Min RSS plain-text length to skip newspaper3k (default `200`)                                  |
| `TREND_ENGINE_CACHE_DIR`                                | Cache directory                                                                                  |
| `TREND_ENGINE_TOPIC_MIN_LEN`                            | Min topic string length                                                                          |
| `TREND_ENGINE_TOPIC_BLOCKLIST`                          | Comma-separated substrings; drop trend labels containing any (case-insensitive)                  |
| `TREND_ENGINE_TOPIC_MAX_LABEL_LEN`                      | If > 0, drop labels longer than this                                                             |
| `TREND_ENGINE_TOPIC_MIN_MEANINGFUL_TOKENS`              | If > 0, drop labels with fewer non-stopword tokens than this                                     |
| `TREND_ENGINE_GT_RETRIES` / `TREND_ENGINE_GT_BACKOFF` | Trends fetch retries                                                                             |
| `TREND_ENGINE_SCRAPE_MAX_CHARS`                         | Trim extracted body (`0` = no extra trim)                                                      |
| `TREND_ENGINE_SCRAPE_MAX_IMAGES`                        | Max image URLs per article in output                                                             |

OpenAI-compatible:

| Variable                          | Meaning                                                         |
| --------------------------------- | --------------------------------------------------------------- |
| `OPENAI_API_KEY`                | Chat + embeddings when enabled                                  |
| `OPENAI_BASE_URL`               | API base (default OpenAI)                                       |
| `OPENAI_MODEL`                  | Chat model                                                      |
| `OPENAI_EMBEDDING_MODEL`        | Embeddings model                                                |
| `TREND_ENGINE_ENRICH_MAX_CHARS` | Max article chars sent to chat model                            |
| `TREND_ENGINE_SEO_ENABLED`      | `1` / `0` — optional post-enrichment SEO LLM (default off) |
| `TREND_ENGINE_SEO_MIN_SCORE`    | Min pipeline `score` to call SEO (default `5.0`)            |
| `TREND_ENGINE_SEO_MAX_PER_RUN`  | Max SEO API calls per run (default `5`)                       |
| `TREND_ENGINE_SEO_MODEL`        | Optional; defaults to `OPENAI_MODEL`                          |

Reddit:

| Variable                                                                | Meaning               |
| ----------------------------------------------------------------------- | --------------------- |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` / `REDDIT_USER_AGENT` | For `--with-reddit` |

Database and API:

| Variable                   | Meaning                                                                            |
| -------------------------- | ---------------------------------------------------------------------------------- |
| `DATABASE_URL`           | PostgreSQL URL (`postgresql+psycopg://…`) or empty for SQLite (dev)             |
| `DJANGO_SETTINGS_MODULE` | e.g.`config.settings.development` (required for Django, API, Celery, DB persist) |

Semantic matching and scoring:

| Variable                                        | Meaning                                                                  |
| ----------------------------------------------- | ------------------------------------------------------------------------ |
| `TREND_ENGINE_MATCH_MODE`                     | `hybrid`, `semantic`, or `token`                                   |
| `TREND_ENGINE_SEMANTIC_ENABLED`               | `1` / `0`                                                            |
| `TREND_ENGINE_SEMANTIC_MIN_SIM`               | Cosine threshold for topic match                                         |
| `TREND_ENGINE_STORY_SIM_THRESHOLD`            | Near-duplicate clustering threshold                                      |
| `TREND_ENGINE_SCORE_W_*`                      | Weights:`TREND`, `SOCIAL`, `RECENCY`, `SOURCE`, `SEMANTIC`     |
| `TREND_ENGINE_SCORE_BONUS_IMAGE` / `LENGTH` | Small additive bonuses                                                   |
| `TREND_ENGINE_SOURCE_QUALITY_JSON`            | JSON map host → 0..1 (merged with built-in defaults for common outlets) |

## Dependencies (high level)

- **trendspy** — primary live trends.
- **pytrends** — optional fallback.
- **feedparser**, **newspaper3k**, **lxml**, **lxml_html_clean**, **httpx**, **typer**, **python-dotenv**, **praw** (optional).
- **Django**, **djangorestframework**, **psycopg** — web API and PostgreSQL (SQLite optional without `DATABASE_URL`).
- **celery**, **redis** — background pipeline tasks (optional).

## Windows note

The CLI sets **UTF-8 stdout** when possible so JSON with Indic or other scripts prints correctly in the terminal
