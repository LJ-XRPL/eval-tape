"""Caption formatter for SHIPPED and EVALS posts."""

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

    lines = ["Independent evals just landed:"]
    for name, score, rank in rows[:5]:
        lines.append(f"{rank}. {name} — {int(round(score))}")
    lines.append("Artificial Analysis. Not vendor scorecards.")
    return "\n".join(lines)
