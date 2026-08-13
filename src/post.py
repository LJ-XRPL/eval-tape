"""Post to X (API v2) with media; reply with source link. Never put URLs in status text."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PostResult:
    tweet_id: str | None
    reply_id: str | None
    dry_run: bool
    caption: str
    media_path: str | None


def dry_run_enabled() -> bool:
    raw = os.getenv("DRY_RUN", "true").strip().lower()
    return raw not in {"0", "false", "no"}


def _client():
    import tweepy

    api_key = os.environ["X_API_KEY"]
    api_secret = os.environ["X_API_SECRET"]
    access_token = os.environ["X_ACCESS_TOKEN"]
    access_secret = os.environ["X_ACCESS_SECRET"]

    # OAuth 1.0a user context for posting + media upload
    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api_v1 = tweepy.API(auth)
    return client, api_v1


def post_with_media(
    *,
    caption: str,
    media_path: Path,
    source_url: str,
    dry_run: bool | None = None,
) -> PostResult:
    """Create tweet with image; put canonical URL in the first reply only."""
    if "http://" in caption or "https://" in caption:
        raise ValueError("Caption must not contain URLs (costs more + throttled)")
    if "#" in caption:
        raise ValueError("Caption must not contain hashtags")

    is_dry = dry_run if dry_run is not None else dry_run_enabled()
    media_path = Path(media_path)

    if is_dry:
        log.info("DRY_RUN caption:\n%s", caption)
        log.info("DRY_RUN media: %s", media_path)
        log.info("DRY_RUN reply would be: %s", source_url)
        return PostResult(
            tweet_id=None,
            reply_id=None,
            dry_run=True,
            caption=caption,
            media_path=str(media_path),
        )

    client, api_v1 = _client()
    media = api_v1.media_upload(filename=str(media_path))
    media_id = media.media_id_string
    created = client.create_tweet(text=caption, media_ids=[media_id])
    tweet_id = str(created.data["id"])
    reply = client.create_tweet(
        text=source_url,
        in_reply_to_tweet_id=tweet_id,
    )
    reply_id = str(reply.data["id"])
    log.info("Posted tweet %s reply %s", tweet_id, reply_id)
    return PostResult(
        tweet_id=tweet_id,
        reply_id=reply_id,
        dry_run=False,
        caption=caption,
        media_path=str(media_path),
    )
