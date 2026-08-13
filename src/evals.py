"""Artificial Analysis poll + match to shipped models."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from src.captions import ComparableFact
from src.config import AA_API_URL, AA_CACHE_MAX_AGE_SECONDS

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AAModel:
    id: str
    name: str
    slug: str
    creator_name: str
    score: float
    rank: int


def _normalize(text: str) -> str:
    text = text.lower()
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def names_match(shipped_name: str, aa_name: str) -> bool:
    """Fuzzy match a SHIPPED model name to an AA catalog name."""
    a = _normalize(shipped_name)
    b = _normalize(aa_name)
    if not a or not b:
        return False
    if a == b:
        return True
    # Strip common AA suffixes like "(max)", "high", reasoning effort tags
    b_core = re.sub(
        r"\b(max|high|medium|low|mini|nano|preview|experimental|thinking|reasoning)\b",
        " ",
        b,
    )
    b_core = re.sub(r"\s+", " ", b_core).strip()
    if a == b_core or a in b or b_core in a:
        # Require shared distinctive token (version-ish or family+number)
        a_tokens = set(a.split())
        b_tokens = set(b_core.split())
        if len(a_tokens & b_tokens) >= max(2, min(len(a_tokens), len(b_core.split())) - 1):
            return True
        # Short names like "o3" / "grok 4"
        if a in b or b_core.startswith(a):
            return True
    # Token overlap heuristic for "Claude Opus 5" vs "Claude Opus 5 (max)"
    a_tokens = [t for t in a.split() if t not in {"the", "model", "ai"}]
    b_tokens = [t for t in b.split() if t not in {"the", "model", "ai", "max", "high", "low"}]
    if not a_tokens:
        return False
    overlap = sum(1 for t in a_tokens if t in b_tokens)
    return overlap >= len(a_tokens) and overlap >= 2


def parse_aa_payload(payload: dict[str, Any]) -> list[AAModel]:
    rows = payload.get("data") or []
    scored: list[tuple[str, str, str, str, float]] = []
    for row in rows:
        ev = row.get("evaluations") or {}
        score = ev.get("artificial_analysis_intelligence_index")
        if score is None:
            continue
        try:
            score_f = float(score)
        except (TypeError, ValueError):
            continue
        creator = row.get("model_creator") or {}
        scored.append(
            (
                str(row.get("id") or ""),
                str(row.get("name") or ""),
                str(row.get("slug") or ""),
                str(creator.get("name") or ""),
                score_f,
            )
        )
    scored.sort(key=lambda r: (-r[4], r[1].lower()))
    out: list[AAModel] = []
    for idx, (mid, name, slug, creator, score_f) in enumerate(scored, start=1):
        out.append(AAModel(id=mid, name=name, slug=slug, creator_name=creator, score=score_f, rank=idx))
    return out


def cache_is_fresh(state: dict[str, Any], *, max_age: int = AA_CACHE_MAX_AGE_SECONDS) -> bool:
    cache = state.get("aa_cache") or {}
    fetched_at = cache.get("fetched_at")
    if not fetched_at or not cache.get("data"):
        return False
    try:
        ts = datetime.fromisoformat(fetched_at)
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - ts).total_seconds()
    return age < max_age


def fetch_aa_models(
    api_key: str,
    state: dict[str, Any],
    *,
    session: requests.Session | None = None,
    force: bool = False,
) -> list[AAModel]:
    if not force and cache_is_fresh(state):
        log.info("Using cached Artificial Analysis snapshot")
        return parse_aa_payload({"data": state["aa_cache"]["data"]})

    if not api_key:
        log.warning("AA_API_KEY missing; using cache if present")
        return parse_aa_payload({"data": (state.get("aa_cache") or {}).get("data") or []})

    session = session or requests.Session()
    resp = session.get(AA_API_URL, headers={"x-api-key": api_key}, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    data = payload.get("data") or []
    state["aa_cache"] = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    return parse_aa_payload(payload)


def match_shipped_to_aa(
    shipped_name: str,
    aa_models: list[AAModel],
) -> AAModel | None:
    # Prefer exact-ish matches; avoid huge models swallowing short names.
    matches = [m for m in aa_models if names_match(shipped_name, m.name)]
    if not matches:
        return None
    matches.sort(key=lambda m: (abs(len(m.name) - len(shipped_name)), m.rank))
    return matches[0]


def models_awaiting_evals(state: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    waiting = []
    for model_id, meta in (state.get("posted_models") or {}).items():
        if meta.get("evals_tweet_id") or meta.get("aa_score") is not None:
            continue
        waiting.append((model_id, meta))
    return waiting


def find_new_evals(
    state: dict[str, Any],
    aa_models: list[AAModel],
) -> list[dict[str, Any]]:
    """Return EVALS-ready rows for shipped models that newly appear on AA."""
    results: list[dict[str, Any]] = []
    for model_id, meta in models_awaiting_evals(state):
        hit = match_shipped_to_aa(meta.get("name") or "", aa_models)
        if not hit:
            continue
        comparable = build_comparable(hit, aa_models, open_closed=meta.get("open_closed") or "closed")
        results.append(
            {
                "model_id": model_id,
                "name": meta.get("name") or hit.name,
                "lab": meta.get("lab") or "unknown",
                "open_closed": meta.get("open_closed") or "closed",
                "source_url": meta.get("source_url") or "https://artificialanalysis.ai/",
                "aa": hit,
                "comparable": comparable,
            }
        )
    # Prefer highest ranks first when batching
    results.sort(key=lambda r: r["aa"].rank)
    return results


def build_comparable(
    target: AAModel,
    aa_models: list[AAModel],
    *,
    open_closed: str,
) -> ComparableFact:
    if open_closed == "open":
        closed = [m for m in aa_models if _looks_closed_creator(m.creator_name)]
        if closed:
            nearest = min(closed, key=lambda m: (abs(m.score - target.score), m.rank))
            # If nearest closed is clearly older-gen / worse rank by a lot, use stock line
            if nearest.rank > target.rank + 3 or nearest.score + 3 < target.score:
                return ComparableFact(kind="open_vs_closed", other_name=nearest.name, other_score=nearest.score)
        return ComparableFact(kind="open_vs_closed")

    # Closed: mention the model immediately ahead when useful
    ahead = next((m for m in aa_models if m.rank == target.rank - 1), None)
    if ahead:
        return ComparableFact(
            kind="behind",
            other_name=_short_name(ahead.name),
            other_score=ahead.score,
            delta=1,
        )
    behind = next((m for m in aa_models if m.rank == target.rank + 1), None)
    if behind:
        return ComparableFact(
            kind="ahead",
            other_name=_short_name(behind.name),
            other_score=behind.score,
            delta=1,
        )
    return ComparableFact(kind="generic")


def _short_name(name: str) -> str:
    # Keep parenthetical effort tags if present — useful in captions ("Opus 5 (max)")
    return name.strip()


def _looks_closed_creator(creator: str) -> bool:
    c = creator.lower()
    return any(
        x in c
        for x in (
            "openai",
            "anthropic",
            "google",
            "deepmind",
            "xai",
            "amazon",
            "microsoft",
            "azure",
        )
    )
