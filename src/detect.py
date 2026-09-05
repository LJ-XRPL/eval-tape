"""Detect allowlisted model ships via official RSS + Hugging Face orgs."""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import feedparser
import requests

from src.config import HF_API_URL, LABS, SKIP_HF_TAGS, SKIP_NAME_PATTERNS, SHIP_HINTS, Lab

log = logging.getLogger(__name__)

_UA = {"User-Agent": "EvalTapeBot/1.0 (+https://github.com/LJ-XRPL/eval-tape)"}
FETCH_TIMEOUT_SECONDS = 8
FETCH_WORKERS = 16

_SKIP_RE = re.compile("|".join(f"(?:{p})" for p in SKIP_NAME_PATTERNS), re.IGNORECASE)
_SHIP_HINT_RE = re.compile("|".join(f"(?:{p})" for p in SHIP_HINTS), re.IGNORECASE)


@dataclass(frozen=True)
class Candidate:
    id: str
    name: str
    lab_key: str
    open_closed: str
    source_url: str
    detected_via: str  # "rss" | "hf"
    raw_title: str = ""


def normalize_name(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def should_skip_model(
    name: str,
    *,
    tags: list[str] | None = None,
    pipeline_tag: str | None = None,
    already_shipped_names: set[str] | None = None,
) -> bool:
    """Return True if this is not a new allowlisted base / frontier LLM drop."""
    n = normalize_name(name)
    if not n:
        return True
    if _SKIP_RE.search(n):
        return True

    tag_set = {t.lower() for t in (tags or [])}
    if pipeline_tag:
        tag_set.add(pipeline_tag.lower())
    if tag_set & SKIP_HF_TAGS:
        return True

    # "now in the UI" / app surface of a model already posted
    if already_shipped_names:
        lowered = n.lower()
        for shipped in already_shipped_names:
            s = shipped.lower()
            if s and s in lowered and any(
                k in lowered for k in ("ui", "app", "chat", "playground", "available in")
            ):
                return True

    return False


def is_base_family_candidate(name: str, lab: Lab) -> bool:
    """Open-weight: require family signal. Closed: lab alias / model-ish title."""
    lowered = name.lower()
    if lab.kind == "open":
        # Gemma shares google HF org — only accept gemma-named drops.
        if lab.key == "gemma":
            return "gemma" in lowered
        return any(alias in lowered for alias in lab.aliases)
    return True


def match_lab(text: str, *, prefer_open_family: bool = False) -> Lab | None:
    lowered = text.lower()
    # Prefer more specific open families before generic google/meta matches.
    ordered = sorted(LABS, key=lambda lab: (0 if lab.kind == "open" else 1, -len(lab.key)))
    if prefer_open_family:
        ordered = [lab for lab in ordered if lab.kind == "open"] + [
            lab for lab in ordered if lab.kind == "closed"
        ]
    for lab in ordered:
        if any(alias in lowered for alias in lab.aliases):
            if lab.key == "gemma" and "gemma" not in lowered:
                continue
            return lab
    return None


def extract_model_name_from_title(title: str, lab: Lab) -> str | None:
    """Best-effort model name from an official blog title."""
    title = normalize_name(title)
    # Common patterns: "Introducing Claude Opus 5", "Llama 4 is here"
    patterns = [
        r"(?:introducing|announcing|releasing|meet)\s+([A-Za-z0-9][A-Za-z0-9 ./\-+]{1,60})",
        r"\b((?:GPT|Claude|Gemini|Llama|DeepSeek|Mistral|Qwen|Kimi|Gemma|GLM|Command|Nova|Phi|Grok)[A-Za-z0-9 ./\-+]{0,40})",
    ]
    for pat in patterns:
        m = re.search(pat, title, re.IGNORECASE)
        if m:
            name = normalize_name(m.group(1))
            name = re.split(r"\s+[—|:·]\s+", name)[0]
            name = re.sub(r"[\.!\?]+$", "", name).strip()
            if len(name) >= 3 and not should_skip_model(name):
                return name
    if _SHIP_HINT_RE.search(title) and is_base_family_candidate(title, lab):
        # Fall back to shortened title if it clearly mentions a family.
        return title[:80]
    return None


def _http_get(url: str, **kwargs: Any) -> requests.Response:
    return requests.get(url, headers=_UA, timeout=FETCH_TIMEOUT_SECONDS, **kwargs)


def _parse_rss_feed(lab: Lab, url: str, content: bytes) -> list[Candidate]:
    out: list[Candidate] = []
    feed = feedparser.parse(content)
    for entry in feed.entries:
        title = normalize_name(getattr(entry, "title", "") or "")
        link = getattr(entry, "link", "") or url
        if not title or not _SHIP_HINT_RE.search(title):
            continue
        if should_skip_model(title):
            continue
        matched = match_lab(title) or lab
        if matched.key != lab.key and matched.kind == "closed" and lab.kind == "closed":
            matched = lab
        name = extract_model_name_from_title(title, matched)
        if not name:
            continue
        if not is_base_family_candidate(name, matched):
            continue
        cid = f"rss:{matched.key}:{_slug(name)}"
        out.append(
            Candidate(
                id=cid,
                name=name,
                lab_key=matched.key,
                open_closed=matched.kind,
                source_url=link,
                detected_via="rss",
                raw_title=title,
            )
        )
    return out


def _fetch_one_rss(lab: Lab, url: str) -> list[Candidate]:
    try:
        resp = _http_get(url)
        resp.raise_for_status()
        return _parse_rss_feed(lab, url, resp.content)
    except Exception as exc:  # noqa: BLE001 — network resilience
        log.warning("RSS fetch failed %s: %s", url, exc)
        return []


def fetch_rss_candidates(session: requests.Session | None = None) -> list[Candidate]:
    del session  # per-request client; Session is not thread-safe
    jobs = [(lab, url) for lab in LABS for url in lab.rss_urls]
    out: list[Candidate] = []
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        futs = [pool.submit(_fetch_one_rss, lab, url) for lab, url in jobs]
        for fut in as_completed(futs):
            out.extend(fut.result())
    return _dedupe(out)


def _parse_hf_org(lab: Lab, org: str, models: list[dict[str, Any]]) -> list[Candidate]:
    out: list[Candidate] = []
    for item in models:
        model_id = item.get("modelId") or item.get("id") or ""
        if not model_id or "/" not in model_id:
            continue
        org_name, repo = model_id.split("/", 1)
        if org_name != org:
            continue
        tags = list(item.get("tags") or [])
        pipeline_tag = item.get("pipeline_tag")
        display = repo.replace("-", " ")
        card = item.get("cardData") or {}
        if isinstance(card, dict) and card.get("model_name"):
            display = str(card["model_name"])

        matched = lab
        if lab.key == "gemma" and "gemma" not in model_id.lower():
            continue
        if lab.key != "gemma":
            guessed = match_lab(model_id, prefer_open_family=True)
            if guessed:
                matched = guessed

        if should_skip_model(display, tags=tags, pipeline_tag=pipeline_tag):
            continue
        if should_skip_model(model_id, tags=tags, pipeline_tag=pipeline_tag):
            continue
        if not is_base_family_candidate(model_id + " " + display, matched):
            continue
        if any(t.startswith("adapter") or t == "peft" for t in tags):
            continue

        pretty = _prettify_hf_name(repo, matched)
        cid = f"hf:{model_id}"
        out.append(
            Candidate(
                id=cid,
                name=pretty,
                lab_key=matched.key,
                open_closed=matched.kind,
                source_url=f"https://huggingface.co/{quote(model_id)}",
                detected_via="hf",
                raw_title=model_id,
            )
        )
    return out


def _fetch_one_hf(lab: Lab, org: str) -> list[Candidate]:
    try:
        resp = _http_get(
            HF_API_URL,
            params={
                "author": org,
                "sort": "createdAt",
                "direction": "-1",
                "limit": 30,
                "full": "true",
            },
        )
        resp.raise_for_status()
        models = resp.json()
        if not isinstance(models, list):
            return []
        return _parse_hf_org(lab, org, models)
    except Exception as exc:  # noqa: BLE001
        log.warning("HF fetch failed %s: %s", org, exc)
        return []


def fetch_hf_candidates(session: requests.Session | None = None) -> list[Candidate]:
    del session
    jobs: list[tuple[Lab, str]] = []
    seen_orgs: set[str] = set()
    for lab in LABS:
        for org in lab.hf_orgs:
            if org in seen_orgs and lab.key != "gemma":
                continue
            seen_orgs.add(org)
            jobs.append((lab, org))
    out: list[Candidate] = []
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        futs = [pool.submit(_fetch_one_hf, lab, org) for lab, org in jobs]
        for fut in as_completed(futs):
            out.extend(fut.result())
    return _dedupe(out)


def filter_new_candidates(
    candidates: list[Candidate],
    *,
    seen_ids: set[str],
    shipped_names: set[str],
) -> list[Candidate]:
    fresh: list[Candidate] = []
    for c in candidates:
        if c.id in seen_ids:
            continue
        if should_skip_model(c.name, already_shipped_names=shipped_names):
            continue
        # Deduplicate against already shipped display names (case-insensitive)
        if any(_slug(c.name) == _slug(s) for s in shipped_names):
            continue
        fresh.append(c)
    return fresh


def collect_candidates() -> list[Candidate]:
    """RSS and HF in parallel so a slow feed does not delay the other source."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        rss_f = pool.submit(fetch_rss_candidates)
        hf_f = pool.submit(fetch_hf_candidates)
        return _dedupe(rss_f.result() + hf_f.result())


def detect_candidates(state: dict[str, Any]) -> list[Candidate]:
    candidates = collect_candidates()
    seen = set(state.get("seen_candidate_ids") or [])
    shipped_names = {m.get("name", "") for m in (state.get("posted_models") or {}).values()}
    return filter_new_candidates(candidates, seen_ids=seen, shipped_names=shipped_names)


def _slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _prettify_hf_name(repo: str, lab: Lab) -> str:
    name = repo.replace("_", " ").replace("-", " ")
    name = re.sub(r"\s+", " ", name).strip()
    # Title-case tokens but keep known acronyms
    parts = []
    for tok in name.split():
        low = tok.lower()
        if low in {"llama", "qwen", "glm", "gemma", "mistral", "deepseek", "kimi", "phi"}:
            parts.append(tok[0].upper() + tok[1:].lower() if len(tok) > 1 else tok.upper())
        elif re.fullmatch(r"v?\d+(\.\d+)*", low):
            parts.append(tok.upper() if tok.lower().startswith("v") else tok)
        else:
            parts.append(tok)
    pretty = " ".join(parts)
    return pretty or lab.display


def _dedupe(candidates: list[Candidate]) -> list[Candidate]:
    seen: set[str] = set()
    out: list[Candidate] = []
    for c in candidates:
        key = c.id
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def seed_seen_from_current(state: dict[str, Any]) -> int:
    """First run: mark current RSS/HF surface as seen, post NOTHING."""
    candidates = collect_candidates()
    before = len(state.get("seen_candidate_ids") or [])
    for c in candidates:
        if c.id not in state["seen_candidate_ids"]:
            state["seen_candidate_ids"].append(c.id)
    state["seeded"] = True
    state["seeded_at"] = datetime.now(timezone.utc).isoformat()
    return len(state["seen_candidate_ids"]) - before
