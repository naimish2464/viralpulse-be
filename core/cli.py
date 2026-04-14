"""Typer CLI for the trend pipeline (``core``)."""

from __future__ import annotations

import io
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import typer

from core import __version__
from core.pipeline import run_pipeline
from core.signals.google_trends import fetch_trending_topic_signals, resolve_trends_geo

app = typer.Typer(help="Viral Trend Engine: trends + RSS + scrape + enrich + score")


def _ensure_utf8_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    elif sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


@app.command("run")
def run_cmd(
    out: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Write JSON array to this file (default: stdout)",
    ),
    limit: int = typer.Option(10, "--limit", "-n", help="Max articles to scrape and enrich"),
    geo: Optional[str] = typer.Option(
        None,
        "--geo",
        "-g",
        help="Trends region: IN, US, or alias india, united_states (default: env TREND_ENGINE_GEO)",
    ),
    lang: Optional[str] = typer.Option(
        None,
        "--lang",
        "-l",
        help="Trends language for trendspy (default: env TREND_ENGINE_LANG, usually en)",
    ),
    with_reddit: bool = typer.Option(False, "--with-reddit", help="Include Reddit r/all hot titles"),
    skip_ai: bool = typer.Option(
        False,
        "--skip-ai",
        help="No OpenAI calls (no chat, no embeddings); token match only; placeholder summary",
    ),
    categories: Optional[str] = typer.Option(
        None,
        "--categories",
        help="Comma-separated RSS category keys (ignored if TREND_ENGINE_RSS is set); see README",
    ),
    include_unmatched: bool = typer.Option(
        False,
        "--include-unmatched",
        help="After trend match, add unmatched RSS items round-robin by category (needs topics)",
    ),
    seo: bool = typer.Option(
        False,
        "--seo",
        help="Enable post-enrichment SEO LLM for this run (needs API key; not with --skip-ai)",
    ),
    no_seo: bool = typer.Option(
        False,
        "--no-seo",
        help="Disable SEO for this run even if TREND_ENGINE_SEO_ENABLED=1",
    ),
    no_persist: bool = typer.Option(
        False,
        "--no-persist",
        help="Do not write results to PostgreSQL (when DATABASE_URL is set)",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run full pipeline and print or save JSON."""
    _ensure_utf8_stdout()
    _setup_logging(verbose)
    rss_categories = (
        [s.strip() for s in categories.split(",") if s.strip()] if categories else None
    )
    items = run_pipeline(
        limit=limit,
        with_reddit=with_reddit,
        skip_ai=skip_ai,
        skip_seo=no_seo,
        rss_categories=rss_categories,
        trends_geo=geo,
        trends_lang=lang,
        save_to_db=False if no_persist else None,
        include_unmatched=include_unmatched,
        seo_cli_on=seo,
        seo_cli_off=no_seo,
    )
    text = json.dumps(items, ensure_ascii=False, indent=2)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        typer.echo(f"Wrote {len(items)} items to {out}", err=True)
    else:
        typer.echo(text)


@app.command("topics")
def topics_cmd(
    geo: Optional[str] = typer.Option(
        None,
        "--geo",
        "-g",
        help="Region code or alias (default: env TREND_ENGINE_GEO)",
    ),
    lang: Optional[str] = typer.Option(
        None,
        "--lang",
        "-l",
        help="Language code for trendspy (default: env TREND_ENGINE_LANG)",
    ),
    max_items: int = typer.Option(30, "--max", "-n", help="Max keywords to print"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Fetch and print live trending keywords as JSON (debug trend signal)."""
    _ensure_utf8_stdout()
    _setup_logging(verbose)
    from core import config

    raw = geo if geo is not None else config.GOOGLE_TRENDS_PN
    code = resolve_trends_geo(raw)
    sigs = fetch_trending_topic_signals(geo=raw, language=lang)
    typer.echo(
        json.dumps(
            {
                "geo_resolved": code,
                "count": len(sigs),
                "signals": [
                    {
                        "label": s.label,
                        "source": s.source,
                        "rank_in_source": s.rank_in_source,
                    }
                    for s in sigs[:max_items]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command()
def version() -> None:
    """Print package version."""
    typer.echo(__version__)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
