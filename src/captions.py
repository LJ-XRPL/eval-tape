"""Caption + alt-text formatter.

Copy is shaped for Phoenix (X's 2026 For You ranker), which predicts 19
actions and weights them — not a single "engagement" score.

Heads we write for (in priority order, given v1 constraints):
  REPLY          line 2 is a comparable fact people can argue with
  DWELL / TIME   line 1 opens a loop; line 2 is the payoff; specificity
  PHOTO_EXPAND   image carries detail the timeline can't resolve (LED grid)
  QUOTE/REPOST   line 1 is a standalone screenshotable sentence
  PROFILE_CLICK  stable Eval Tape voice so the author embedding compounds
  CLICK          never — URLs in the status are costlier and leave the app
  VQV            not in v1 (no native video)

Avoid: hashtags, questions-as-bait, "like if", dunks that read as ratio-farming
(those fire NOT_INTERESTED / MUTE / BLOCK, which outweigh dozens of likes).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComparableFact:
    """One reply-worthy fact for line 2 of an EVALS caption."""

    kind: str  # "behind" | "ahead" | "tied" | "open_vs_closed" | "generic"
    other_name: str | None = None
    other_score: float | None = None
    delta: int | None = None


def _open_closed_label(open_closed: str) -> str:
    if open_closed == "open":
        return "Open weights"
    return "Closed"


def format_shipped_caption(model_name: str, open_closed: str) -> str:
    # Line 1 = hook (what happened). Line 2 = payoff the first line does not contain.
    line1 = f"{model_name} just shipped."
    line2 = f"{_open_closed_label(open_closed)}. Evals when the independent board has it."
    return f"{line1}\n{line2}"


def format_evals_caption(
    model_name: str,
    open_closed: str,
    score: float,
    rank: int,
    comparable: ComparableFact | None = None,
) -> str:
    score_i = int(round(score))
    # Specificity is dwell density: name + number + source + rank in line 1.
    line1 = f"{model_name}: {score_i} on Artificial Analysis, rank {rank}."

    if comparable is None:
        line2 = f"{_open_closed_label(open_closed)}. Independent board, not a vendor card."
    elif comparable.kind == "behind" and comparable.other_name and comparable.other_score is not None:
        other_score = int(round(comparable.other_score))
        line2 = (
            f"{_open_closed_label(open_closed)}. "
            f"One behind {comparable.other_name} at {other_score}."
        )
    elif comparable.kind == "ahead" and comparable.other_name and comparable.other_score is not None:
        other_score = int(round(comparable.other_score))
        line2 = (
            f"{_open_closed_label(open_closed)}. "
            f"One ahead of {comparable.other_name} at {other_score}."
        )
    elif comparable.kind == "tied" and comparable.other_name:
        line2 = f"{_open_closed_label(open_closed)}. Tied with {comparable.other_name}."
    elif comparable.kind == "open_vs_closed":
        line2 = (
            f"{_open_closed_label(open_closed)}. "
            "Closest closed model at this score is a generation back."
        )
    else:
        line2 = f"{_open_closed_label(open_closed)}. Independent board, not a vendor card."

    return f"{line1}\n{line2}"


def format_ranked_evals_list(
    rows: list[tuple[str, float, int]],
    open_closed: str,
) -> str:
    """One post when several evals land together — ranked list, not six tweets."""
    if not rows:
        raise ValueError("rows required")
    if len(rows) == 1:
        name, score, rank = rows[0]
        return format_evals_caption(name, open_closed, score, rank)

    # Sequence-with-reveal: hook, then the board, then the thesis.
    lines = ["Independent evals just landed:"]
    for name, score, rank in rows[:3]:
        lines.append(f"{rank}. {name} — {int(round(score))}")
    lines.append("Artificial Analysis. Not vendor scorecards.")
    return "\n".join(lines)


def format_alt_shipped(model_name: str, lab_display: str, open_closed: str) -> str:
    kind = "open-weight" if open_closed == "open" else "closed"
    return (
        f"Eval Tape SHIPPED card for {model_name}, a {kind} model from {lab_display}. "
        f"Giant model name on {lab_display} color with film-tape sprocket rails. "
        f"Lower third reads SHIPPED, {lab_display}, EVALTAPE."
    )[:1000]


def format_alt_evals(
    model_name: str,
    score: float,
    rank: int,
    open_closed: str | None = None,
) -> str:
    kind = ""
    if open_closed == "open":
        kind = " Open weights."
    elif open_closed == "closed":
        kind = " Closed model."
    return (
        f"Eval Tape EVALS jumbotron: {model_name} scores {int(round(score))} "
        f"on the Artificial Analysis Intelligence Index, rank {rank}.{kind} "
        f"Pixel LED number on matte black with EVALTAPE and Artificial Analysis footer."
    )[:1000]


def format_alt_ranked(rows: list[tuple[str, float, int]]) -> str:
    bits = [f"{name} {int(round(score))} (rank {rank})" for name, score, rank in rows[:5]]
    return (
        "Eval Tape ranked EVALS card. Artificial Analysis Intelligence Index: "
        + "; ".join(bits)
        + ". EVALTAPE and Artificial Analysis footer."
    )[:1000]
