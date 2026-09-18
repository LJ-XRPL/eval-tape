"""Initial distribution: profile, pin, optional founder quote.

Does not reply-spam lab accounts, follow-for-follow, or put URLs/hashtags
in @evaltape status text. Founder quotes need a separate user-context token
for the personal account (FOUNDER_X_ACCESS_TOKEN / SECRET).
"""

from __future__ import annotations

import logging
import os
from typing import Any

from src.post import _oauth_client, dry_run_enabled

log = logging.getLogger(__name__)

WEBSITE_URL = "https://github.com/LJ-XRPL/eval-tape"
LAUNCH_TWEET_ID = "2087795205739274481"
FOUNDER_QUOTE_CAP = 5


def _dist(state: dict[str, Any]) -> dict[str, Any]:
    return state.setdefault(
        "distribution",
        {
            "profile_set": False,
            "launch_pinned": False,
            "launch_quoted_id": None,
            "founder_quotes": 0,
            "pinned_tweet_id": None,
        },
    )


def founder_tokens() -> tuple[str, str] | None:
    token = (os.getenv("FOUNDER_X_ACCESS_TOKEN") or "").strip()
    secret = (os.getenv("FOUNDER_X_ACCESS_SECRET") or "").strip()
    if token and secret:
        return token, secret
    return None


def format_founder_quote(kind: str, model_name: str | None = None) -> str:
    if kind == "shipped" and model_name:
        text = f"{model_name} just shipped. First to know.\n\n@evaltape"
    elif kind == "evals" and model_name:
        text = f"{model_name} just landed on the independent board.\n\n@evaltape"
    else:
        text = (
            "First to know when a real LLM ships. "
            "Then when independent evals land.\n\n@evaltape"
        )
    if "http://" in text or "https://" in text or "#" in text:
        raise ValueError("Founder quote must not contain URLs or hashtags")
    return text


def setup_profile(*, dry_run: bool | None = None) -> bool:
    """Set the website field on @evaltape."""
    is_dry = dry_run if dry_run is not None else dry_run_enabled()
    if is_dry:
        log.info("DRY_RUN would set website to %s", WEBSITE_URL)
        return True
    _, api_v1 = _oauth_client()
    updated = api_v1.update_profile(url=WEBSITE_URL, skip_status=True)
    log.info("Profile website set for @%s", updated.screen_name)
    return True


def pin_tweet(tweet_id: str, *, dry_run: bool | None = None) -> bool:
    """Pin a tweet on @evaltape (v1 account/pin_tweet)."""
    is_dry = dry_run if dry_run is not None else dry_run_enabled()
    if is_dry:
        log.info("DRY_RUN would pin %s", tweet_id)
        return True
    _, api_v1 = _oauth_client()
    api_v1.request("POST", "account/pin_tweet", post_data={"id": str(tweet_id)})
    log.info("Pinned tweet %s", tweet_id)
    return True


def quote_as_founder(
    tweet_id: str,
    *,
    kind: str = "launch",
    model_name: str | None = None,
    dry_run: bool | None = None,
) -> str | None:
    """Quote an @evaltape tweet from the founder account, if tokens exist."""
    caption = format_founder_quote(kind, model_name)
    is_dry = dry_run if dry_run is not None else dry_run_enabled()
    tokens = founder_tokens()
    if not tokens:
        log.info("FOUNDER_X_ACCESS_TOKEN unset; skip founder quote")
        return None
    if is_dry:
        log.info("DRY_RUN founder quote of %s:\n%s", tweet_id, caption)
        return "dry-run"
    client, _ = _oauth_client(access_token=tokens[0], access_secret=tokens[1])
    created = client.create_tweet(text=caption, quote_tweet_id=str(tweet_id))
    quote_id = str(created.data["id"])
    log.info("Founder quoted %s as %s", tweet_id, quote_id)
    return quote_id


def bootstrap_distribution(state: dict[str, Any], *, dry_run: bool | None = None) -> dict[str, Any]:
    """One-time profile + pin launch + founder quote of the launch tweet."""
    is_dry = dry_run if dry_run is not None else dry_run_enabled()
    dist = _dist(state)
    setup_profile(dry_run=is_dry)
    dist["profile_set"] = True
    pin_tweet(LAUNCH_TWEET_ID, dry_run=is_dry)
    dist["launch_pinned"] = True
    dist["pinned_tweet_id"] = LAUNCH_TWEET_ID
    if not dist.get("launch_quoted_id") and dist.get("founder_quotes", 0) < FOUNDER_QUOTE_CAP:
        quote_id = quote_as_founder(LAUNCH_TWEET_ID, kind="launch", dry_run=is_dry)
        if quote_id:
            dist["launch_quoted_id"] = quote_id
            dist["founder_quotes"] = int(dist.get("founder_quotes") or 0) + 1
    return dist


def amplify_post(
    state: dict[str, Any],
    *,
    tweet_id: str,
    kind: str,
    model_name: str | None = None,
    dry_run: bool | None = None,
) -> None:
    """After a live SHIPPED/EVALS post: pin it, quote from founder while under cap."""
    is_dry = dry_run if dry_run is not None else dry_run_enabled()
    dist = _dist(state)
    pin_tweet(tweet_id, dry_run=is_dry)
    dist["pinned_tweet_id"] = tweet_id
    if int(dist.get("founder_quotes") or 0) >= FOUNDER_QUOTE_CAP:
        return
    quote_id = quote_as_founder(
        tweet_id, kind=kind, model_name=model_name, dry_run=is_dry
    )
    if quote_id:
        dist["founder_quotes"] = int(dist.get("founder_quotes") or 0) + 1
        dist.setdefault("founder_quote_ids", []).append(quote_id)
