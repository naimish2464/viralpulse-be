"""Token matching: stopwords and false-positive guards."""

from __future__ import annotations

from core.match import match_article_to_topics


def test_strait_of_hormuz_does_not_match_generic_tech_title() -> None:
    ok, matched = match_article_to_topics(
        "Polymarket traders pile into Microsoft Copilot futures",
        ["strait of hormuz"],
    )
    assert not ok
    assert matched == []


def test_strait_of_hormuz_matches_when_phrase_in_title() -> None:
    ok, matched = match_article_to_topics(
        "Shipping fears grow amid Strait of Hormuz tensions",
        ["strait of hormuz"],
    )
    assert ok
    assert "strait of hormuz" in [m.lower() for m in matched]


def test_multiword_topic_requires_two_meaningful_overlaps() -> None:
    ok, matched = match_article_to_topics(
        "Apple unveils new iPhone model for holiday season",
        ["apple iphone"],
    )
    assert ok
    assert "apple iphone" in matched


def test_single_meaningful_token_not_enough_for_two_word_topic() -> None:
    ok, matched = match_article_to_topics(
        "Banana prices surge in wholesale markets",
        ["apple iphone"],
    )
    assert not ok


def test_single_token_topic_still_works() -> None:
    ok, matched = match_article_to_topics(
        "OpenAI announces GPT-5 roadmap",
        ["openai"],
    )
    assert ok
    assert "openai" in matched
