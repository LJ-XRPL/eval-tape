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
    media_paths: tuple[str, ...] = ()


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
    source_url: str,
    media_path: Path | None = None,
    media_paths: list[Path] | tuple[Path, ...] | None = None,
    alt_text: str | None = None,
    alt_texts: list[str] | tuple[str, ...] | None = None,
    dry_run: bool | None = None,
) -> PostResult:
    """Create tweet with 1–4 images; put canonical URL in the first reply only."""
    if "http://" in caption or "https://" in caption:
        raise ValueError("Caption must not contain URLs (costs more + throttled)")
    if "#" in caption:
        raise ValueError("Caption must not contain hashtags")

    paths = [Path(p) for p in (media_paths or ([media_path] if media_path is not None else []))]
    if not paths:
        raise ValueError("media_path or media_paths required")
    if len(paths) > 4:
        raise ValueError("X allows at most 4 photos per tweet")

    alts: list[str | None]
    if alt_texts is not None:
        alts = [(a or "")[:1000] or None for a in alt_texts]
        if len(alts) != len(paths):
            raise ValueError("alt_texts must match media_paths")
    else:
        alts = [((alt_text or "")[:1000] or None)] + [None] * (len(paths) - 1)

    is_dry = dry_run if dry_run is not None else dry_run_enabled()
    path_strs = tuple(str(p) for p in paths)

    if is_dry:
        log.info("DRY_RUN caption:\n%s", caption)
        log.info("DRY_RUN media (%s): %s", len(paths), ", ".join(path_strs))
        for i, alt in enumerate(alts):
            if alt:
                log.info("DRY_RUN alt[%s]: %s", i, alt)
        log.info("DRY_RUN reply would be: %s", source_url)
        return PostResult(
            tweet_id=None,
            reply_id=None,
            dry_run=True,
            caption=caption,
            media_path=path_strs[0],
            media_paths=path_strs,
        )

    client, api_v1 = _client()
    media_ids: list[str] = []
    for path, alt in zip(paths, alts, strict=True):
        media = api_v1.media_upload(filename=str(path))
        media_id = media.media_id_string
        if alt:
            api_v1.create_media_metadata(media_id, alt_text=alt)
        media_ids.append(media_id)
    created = client.create_tweet(text=caption, media_ids=media_ids)
    tweet_id = str(created.data["id"])
    reply = client.create_tweet(
        text=source_url,
        in_reply_to_tweet_id=tweet_id,
    )
    reply_id = str(reply.data["id"])
    log.info("Posted tweet %s reply %s photos=%s", tweet_id, reply_id, len(media_ids))
    return PostResult(
        tweet_id=tweet_id,
        reply_id=reply_id,
        dry_run=False,
        caption=caption,
        media_path=path_strs[0],
        media_paths=path_strs,
    )
