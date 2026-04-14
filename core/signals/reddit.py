"""Optional Reddit r/all hot posts for extra topic signal."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import praw

from core import config

logger = logging.getLogger(__name__)


@dataclass
class RedditPost:
    title: str
    score: int


def fetch_reddit_hot(limit: int = 20) -> list[RedditPost]:
    """
    Fetch hot post titles and scores. Requires REDDIT_* env vars.
    Returns [] if credentials missing or on error.
    """
    cid = config.REDDIT_CLIENT_ID
    secret = config.REDDIT_CLIENT_SECRET
    if not cid or not secret:
        logger.debug("Reddit credentials not set; skipping")
        return []
    try:
        reddit = praw.Reddit(
            client_id=cid,
            client_secret=secret,
            user_agent=config.REDDIT_USER_AGENT,
        )
        posts: list[RedditPost] = []
        for post in reddit.subreddit("all").hot(limit=limit):
            title = (post.title or "").strip()
            if title:
                posts.append(RedditPost(title=title, score=int(post.score or 0)))
        return posts
    except Exception as e:
        logger.warning("Reddit fetch failed: %s", e)
        return []
