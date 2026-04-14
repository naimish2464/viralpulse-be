"""Topic hygiene filter and score breakdown when semantic is skipped."""

from __future__ import annotations

from unittest.mock import patch

from core.score import trend_score_breakdown
from core.topics import TopicSignal, filter_topic_signals


def test_filter_topic_signals_blocklist() -> None:
    with patch("core.topics.config.TREND_ENGINE_TOPIC_BLOCKLIST", "acme,corp"):
        with patch("core.topics.config.TREND_ENGINE_TOPIC_MAX_LABEL_LEN", 0):
            with patch("core.topics.config.TREND_ENGINE_TOPIC_MIN_MEANINGFUL_TOKENS", 0):
                sigs = [
                    TopicSignal(label="ACME news today", source="google", rank_in_source=1),
                    TopicSignal(label="other story", source="google", rank_in_source=2),
                ]
                out = filter_topic_signals(sigs)
                assert len(out) == 1
                assert out[0].label == "other story"


def test_trend_score_breakdown_semantic_skipped_zeros_weight() -> None:
    art = {
        "url": "https://techcrunch.com/x",
        "matched_topics": [],
        "semantic_best": 0.0,
        "published": "",
        "content": "hello",
        "image": "",
    }
    total_on, br_on = trend_score_breakdown(
        {**art, "semantic_best": 0.95},
        topic_signals=[],
        semantic_skipped=False,
    )
    total_off, br_off = trend_score_breakdown(
        {**art, "semantic_best": 0.95},
        topic_signals=[],
        semantic_skipped=True,
    )
    assert br_off["semantic_skipped"] is True
    assert br_on["semantic_skipped"] is False
    assert total_off < total_on
