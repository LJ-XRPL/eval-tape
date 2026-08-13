"""Load and save Eval Tape state.json."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from src.config import MAX_POSTS_PER_DAY, STATE_PATH

DEFAULT_STATE: dict[str, Any] = {
    "seeded": False,
    "posted_models": {},
    "seen_candidate_ids": [],
    "aa_cache": {"fetched_at": None, "data": []},
    "posts_today": {"date": None, "count": 0},
    "last_tweet_ids": [],
}


def utc_today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def load_state(path: Path | None = None) -> dict[str, Any]:
    state_path = path or STATE_PATH
    if not state_path.exists():
        return deepcopy(DEFAULT_STATE)
    with state_path.open(encoding="utf-8") as fh:
        raw = json.load(fh)
    state = deepcopy(DEFAULT_STATE)
    state.update(raw)
    state.setdefault("posted_models", {})
    state.setdefault("seen_candidate_ids", [])
    state.setdefault("aa_cache", {"fetched_at": None, "data": []})
    state.setdefault("posts_today", {"date": None, "count": 0})
    state.setdefault("last_tweet_ids", [])
    return state


def save_state(state: dict[str, Any], path: Path | None = None) -> None:
    state_path = path or STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)
        fh.write("\n")
    tmp.replace(state_path)


def remaining_posts_today(state: dict[str, Any]) -> int:
    today = utc_today()
    bucket = state.get("posts_today") or {}
    if bucket.get("date") != today:
        return MAX_POSTS_PER_DAY
    return max(0, MAX_POSTS_PER_DAY - int(bucket.get("count") or 0))


def record_post(state: dict[str, Any], tweet_id: str | None = None) -> None:
    today = utc_today()
    bucket = state.setdefault("posts_today", {"date": None, "count": 0})
    if bucket.get("date") != today:
        bucket["date"] = today
        bucket["count"] = 0
    bucket["count"] = int(bucket.get("count") or 0) + 1
    if tweet_id:
        ids = state.setdefault("last_tweet_ids", [])
        ids.append(tweet_id)
        state["last_tweet_ids"] = ids[-50:]


def mark_seen(state: dict[str, Any], candidate_id: str) -> None:
    seen = state.setdefault("seen_candidate_ids", [])
    if candidate_id not in seen:
        seen.append(candidate_id)


def upsert_shipped(
    state: dict[str, Any],
    *,
    model_id: str,
    name: str,
    lab_key: str,
    open_closed: str,
    source_url: str,
    tweet_id: str | None = None,
) -> None:
    models = state.setdefault("posted_models", {})
    models[model_id] = {
        "name": name,
        "lab": lab_key,
        "open_closed": open_closed,
        "source_url": source_url,
        "shipped_at": datetime.now(timezone.utc).isoformat(),
        "shipped_tweet_id": tweet_id,
        "evals_tweet_id": None,
        "aa_model_id": None,
        "aa_score": None,
        "aa_rank": None,
        "evals_posted_at": None,
    }
    mark_seen(state, model_id)


def mark_evals_posted(
    state: dict[str, Any],
    *,
    model_id: str,
    aa_model_id: str,
    score: float,
    rank: int,
    tweet_id: str | None = None,
) -> None:
    model = state["posted_models"][model_id]
    model["aa_model_id"] = aa_model_id
    model["aa_score"] = score
    model["aa_rank"] = rank
    model["evals_tweet_id"] = tweet_id
    model["evals_posted_at"] = datetime.now(timezone.utc).isoformat()
