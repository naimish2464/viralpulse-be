"""Run the viral trend pipeline (RSS, match, enrich, optional AI/SEO, persist)."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.processing.pipeline_runner import run_pipeline_and_persist


class Command(BaseCommand):
    help = "Run the trend pipeline with Django persistence (same path as Celery)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Max articles after clustering (default 10).",
        )
        parser.add_argument(
            "--skip-ai",
            action="store_true",
            help="Skip LLM enrichment and embedding-based match/cluster.",
        )
        parser.add_argument(
            "--skip-seo",
            action="store_true",
            help="Skip SEO LLM pass.",
        )
        parser.add_argument(
            "--with-reddit",
            action="store_true",
            help="Include Reddit in topic signals.",
        )
        parser.add_argument(
            "--no-save",
            action="store_true",
            help="Run pipeline without persisting to the database.",
        )
        parser.add_argument(
            "--include-unmatched",
            action="store_true",
            help="Include articles that did not match a topic signal.",
        )

    def handle(self, *args, **options) -> None:
        save_to_db = not options["no_save"]
        results, run_id = run_pipeline_and_persist(
            limit=options["limit"],
            skip_ai=options["skip_ai"],
            skip_seo=options["skip_seo"],
            with_reddit=options["with_reddit"],
            save_to_db=save_to_db,
            include_unmatched=options["include_unmatched"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {len(results)} result row(s), run_id={run_id!r}"
            )
        )
