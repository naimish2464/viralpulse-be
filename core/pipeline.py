"""Orchestrate signals -> RSS -> match -> scrape -> AI -> score.

Implementation lives in ``services.pipeline``; this module re-exports for
backward compatibility (CLI, tests, legacy imports).
"""

from __future__ import annotations

from services.pipeline import run_pipeline

__all__ = ("run_pipeline",)
