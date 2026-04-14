# Generated manually for article body persistence.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("articles", "0002_article_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="content",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Full raw article body from RSS or scrape.",
            ),
        ),
        migrations.AddField(
            model_name="article",
            name="processed_content",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Normalized body (whitespace cleanup) for search and reuse.",
            ),
        ),
    ]
