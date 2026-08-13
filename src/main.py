"""Eval Tape orchestrator — one GitHub Actions run."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.captions import (
    ComparableFact,
    format_alt_evals,
    format_alt_ranked,
    format_alt_shipped,
    format_evals_caption,
    format_ranked_evals_list,
    format_shipped_caption,
)
from src.cards import render_evals_card, render_ranked_evals_card, render_shipped_card
from src.config import LAB_BY_KEY, OUT_DIR
from src.detect import detect_candidates, seed_seen_from_current
from src.evals import fetch_aa_models, find_new_evals
from src.post import dry_run_enabled, post_with_media
from src.state import load_state, mark_evals_posted, record_post, remaining_posts_today, save_state, upsert_shipped

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("evaltape")


def render_samples(out_dir: Path | None = None) -> list[Path]:
    """Dry-run Action helper: sample SHIPPED + EVALS cards into /out."""
    out = out_dir or OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    shipped_path = render_shipped_card(
        model_name="Claude Opus 5",
        lab_key="anthropic",
        open_closed="closed",
        out_path=out / "sample_shipped.png",
    )
    evals_path = render_evals_card(
        model_name="GPT-5.6 Sol",
        lab_key="openai",
        score=61,
        rank=5,
        out_path=out / "sample_evals.png",
    )
    open_evals = render_evals_card(
        model_name="DeepSeek V4",
        lab_key="deepseek",
        score=58,
        rank=12,
        out_path=out / "sample_evals_open.png",
    )
    openai_shipped = render_shipped_card(
        model_name="GPT-5.6 Sol",
        lab_key="openai",
        open_closed="closed",
        out_path=out / "sample_shipped_openai.png",
    )
    ranked = render_ranked_evals_card(
        rows=[("Opus 5", 63, 1), ("GPT-5.6 Sol", 61, 5), ("DeepSeek V4", 58, 12)],
        lab_key="anthropic",
        out_path=out / "sample_evals_ranked.png",
    )
    shipped_caption = format_shipped_caption("Claude Opus 5", "closed")
    evals_caption = format_evals_caption(
        "GPT-5.6 Sol",
        "closed",
        61,
        5,
        comparable=ComparableFact(kind="behind", other_name="Opus 5 (max)", other_score=63),
    )
    open_caption = format_evals_caption(
        "DeepSeek V4",
        "open",
        58,
        12,
        comparable=ComparableFact(kind="open_vs_closed"),
    )
    print("--- SAMPLE SHIPPED ---")
    print(shipped_caption)
    print(f"card: {shipped_path}")
    print(format_alt_shipped("Claude Opus 5", "Anthropic", "closed"))
    print("--- SAMPLE EVALS ---")
    print(evals_caption)
    print(f"card: {evals_path}")
    print(format_alt_evals("GPT-5.6 Sol", 61, 5, "closed"))
    print("--- SAMPLE OPEN EVALS ---")
    print(open_caption)
    print(f"card: {open_evals}")
    print(format_alt_evals("DeepSeek V4", 58, 12, "open"))
    print(f"card: {openai_shipped}")
    print(f"card: {ranked}")
    return [shipped_path, evals_path, open_evals, openai_shipped, ranked]


def run_once(*, force_seed: bool = False) -> int:
    load_dotenv()
    state = load_state()
    dry = dry_run_enabled()
    log.info("DRY_RUN=%s seeded=%s", dry, state.get("seeded"))

    # First run: seed state, post NOTHING (do not dump history).
    if force_seed or not state.get("seeded"):
        added = seed_seen_from_current(state)
        save_state(state)
        log.info("Seeded %s existing candidates; posting nothing this run", added)
        return 0

    budget = remaining_posts_today(state)
    if budget <= 0:
        log.info("Daily post cap reached; exiting")
        return 0

    posts_made = 0

    # 1) Detect new allowlisted models → SHIPPED
    candidates = detect_candidates(state)
    log.info("New ship candidates: %s", len(candidates))
    for cand in candidates:
        if posts_made >= budget:
            break
        # Always mark seen so we don't re-process forever when over budget
        if cand.id not in state["seen_candidate_ids"]:
            state["seen_candidate_ids"].append(cand.id)

        if posts_made >= budget:
            continue

        slug = cand.name.lower().replace(" ", "_")[:60]
        card_path = OUT_DIR / f"shipped_{cand.lab_key}_{slug}.png"
        render_shipped_card(
            model_name=cand.name,
            lab_key=cand.lab_key,
            open_closed=cand.open_closed,
            out_path=card_path,
        )
        caption = format_shipped_caption(cand.name, cand.open_closed)
        lab_display = LAB_BY_KEY[cand.lab_key].display if cand.lab_key in LAB_BY_KEY else cand.lab_key
        result = post_with_media(
            caption=caption,
            media_path=card_path,
            source_url=cand.source_url,
            alt_text=format_alt_shipped(cand.name, lab_display, cand.open_closed),
            dry_run=dry,
        )
        model_key = cand.id
        upsert_shipped(
            state,
            model_id=model_key,
            name=cand.name,
            lab_key=cand.lab_key,
            open_closed=cand.open_closed,
            source_url=cand.source_url,
            tweet_id=result.tweet_id,
        )
        record_post(state, result.tweet_id)
        posts_made += 1
        log.info("SHIPPED processed: %s", cand.name)

    budget_left = budget - posts_made
    if budget_left <= 0:
        save_state(state)
        return 0

    # 2) For shipped models missing evals, check AA → EVALS
    aa_key = os.getenv("AA_API_KEY", "")
    try:
        aa_models = fetch_aa_models(aa_key, state)
    except Exception as exc:  # noqa: BLE001
        log.error("AA fetch failed: %s", exc)
        save_state(state)
        return 1

    ready = find_new_evals(state, aa_models)
    log.info("EVALS ready: %s", len(ready))

    if not ready:
        save_state(state)
        return 0

    # Cap 3/day. If several evals land together, one ranked list, not six tweets.
    if len(ready) > 1 and budget_left >= 1:
        batch = ready[: min(5, len(ready))]
        rows = [(r["name"], r["aa"].score, r["aa"].rank) for r in batch]
        # Use open_closed of majority / first for caption tone; list post is neutral
        open_closed = batch[0]["open_closed"]
        caption = format_ranked_evals_list(rows, open_closed)
        card_path = OUT_DIR / "evals_batch.png"
        render_ranked_evals_card(rows=rows, lab_key=batch[0]["lab"], out_path=card_path)
        result = post_with_media(
            caption=caption,
            media_path=card_path,
            source_url="https://artificialanalysis.ai/",
            alt_text=format_alt_ranked(rows),
            dry_run=dry,
        )
        for r in batch:
            mark_evals_posted(
                state,
                model_id=r["model_id"],
                aa_model_id=r["aa"].id,
                score=r["aa"].score,
                rank=r["aa"].rank,
                tweet_id=result.tweet_id,
            )
        record_post(state, result.tweet_id)
        posts_made += 1
        log.info("EVALS batch posted (%s models)", len(batch))
    else:
        r = ready[0]
        caption = format_evals_caption(
            r["name"],
            r["open_closed"],
            r["aa"].score,
            r["aa"].rank,
            comparable=r["comparable"],
        )
        slug = r["name"].lower().replace(" ", "_")[:60]
        card_path = OUT_DIR / f"evals_{slug}.png"
        render_evals_card(
            model_name=r["name"],
            lab_key=r["lab"],
            score=r["aa"].score,
            rank=r["aa"].rank,
            out_path=card_path,
        )
        result = post_with_media(
            caption=caption,
            media_path=card_path,
            source_url="https://artificialanalysis.ai/",
            alt_text=format_alt_evals(r["name"], r["aa"].score, r["aa"].rank, r["open_closed"]),
            dry_run=dry,
        )
        mark_evals_posted(
            state,
            model_id=r["model_id"],
            aa_model_id=r["aa"].id,
            score=r["aa"].score,
            rank=r["aa"].rank,
            tweet_id=result.tweet_id,
        )
        record_post(state, result.tweet_id)
        posts_made += 1
        log.info("EVALS posted: %s", r["name"])

    save_state(state)
    log.info("Run complete. posts_made=%s dry_run=%s", posts_made, dry)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Eval Tape bot")
    parser.add_argument(
        "--samples",
        action="store_true",
        help="Render sample SHIPPED/EVALS cards to /out and print captions",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Force seed of current RSS/HF surface without posting",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run one detection/evals cycle",
    )
    args = parser.parse_args(argv)

    if args.samples or (not args.run and not args.seed):
        # Default CI entry: samples are always safe / no secrets required
        render_samples()
        if not args.run and not args.seed:
            return 0

    if args.seed and not args.run:
        load_dotenv()
        state = load_state()
        added = seed_seen_from_current(state)
        save_state(state)
        log.info("Seeded %s candidates", added)
        return 0

    return run_once(force_seed=args.seed)


if __name__ == "__main__":
    sys.exit(main())
