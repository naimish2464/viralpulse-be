from core.article_read_time import estimate_read_time_minutes


def test_read_time_empty_is_one() -> None:
    assert estimate_read_time_minutes("") == 1


def test_read_time_short_article() -> None:
    text = " ".join(["word"] * 100)
    assert estimate_read_time_minutes(text, words_per_minute=200) == 1


def test_read_time_longer_article() -> None:
    text = " ".join(["word"] * 500)
    assert estimate_read_time_minutes(text, words_per_minute=200) >= 2
