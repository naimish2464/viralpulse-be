# Article: extractive_summary, authors, image_urls, slug (backfilled then NOT NULL).

from __future__ import annotations

import hashlib

from django.db import migrations, models
from django.utils.text import slugify


def _slug_candidate(title: str, url: str, fingerprint: str) -> str:
    t = (title or "").strip() or "article"
    base = slugify(t)[:72] or "article"
    fp = (fingerprint or "").strip()[:32]
    if len(fp) < 8:
        fp = hashlib.sha256((url or "").encode("utf-8")).hexdigest()[:12]
    else:
        fp = fp[:12]
    s = f"{base}-{fp}"
    s = __import__("re").sub(r"-{2,}", "-", s).strip("-")
    return s[:200]


def _drop_stale_postgres_slug_indexes(schema_editor) -> None:
    """Remove orphan pattern indexes left by a failed/partial slug migration."""
    conn = schema_editor.connection
    if conn.vendor != "postgresql":
        return
    qn = conn.ops.quote_name
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'articles_article'
              AND indexname LIKE '%%slug%%'
              AND indexname LIKE '%%like%%'
            """
        )
        for (name,) in cursor.fetchall():
            cursor.execute("DROP INDEX IF EXISTS " + qn(name))


def backfill_article_slugs(apps, schema_editor) -> None:
    Article = apps.get_model("articles", "Article")
    for row in Article.objects.order_by("id").iterator():
        if getattr(row, "slug", None):
            continue
        candidate = _slug_candidate(row.title, row.url, row.title_fingerprint or "")
        n = 0
        while Article.objects.filter(slug=candidate).exclude(pk=row.pk).exists():
            n += 1
            candidate = f"{_slug_candidate(row.title, row.url, row.title_fingerprint or '')}-{n}"[
                :200
            ]
        row.slug = candidate
        row.save(update_fields=["slug"])


def drop_stale_slug_indexes_forward(apps, schema_editor) -> None:
    _drop_stale_postgres_slug_indexes(schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ("articles", "0003_article_content_fields"),
    ]

    operations = [
        migrations.RunPython(drop_stale_slug_indexes_forward, migrations.RunPython.noop),
        migrations.AddField(
            model_name="article",
            name="slug",
            field=models.CharField(
                blank=True,
                db_index=False,
                help_text="Stable URL slug (title + fingerprint hash).",
                max_length=200,
                null=True,
                unique=False,
            ),
        ),
        migrations.AddField(
            model_name="article",
            name="extractive_summary",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Newspaper3k NLP extractive summary (when available).",
            ),
        ),
        migrations.AddField(
            model_name="article",
            name="authors",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Normalized author display names from the article page.",
            ),
        ),
        migrations.AddField(
            model_name="article",
            name="image_urls",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Ordered image URLs (hero first): og, top, RSS, then inline.",
            ),
        ),
        migrations.RunPython(backfill_article_slugs, migrations.RunPython.noop),
        migrations.RunPython(drop_stale_slug_indexes_forward, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="article",
            name="slug",
            field=models.CharField(
                db_index=True,
                help_text="Stable URL slug (title + fingerprint hash).",
                max_length=200,
                unique=True,
            ),
        ),
    ]
