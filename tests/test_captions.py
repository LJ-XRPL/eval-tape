"""Unit tests for caption formatter."""

from src.captions import (
    ComparableFact,
    format_alt_evals,
    format_alt_shipped,
    format_evals_caption,
    format_ranked_evals_list,
    format_shipped_caption,
)


def test_shipped_caption_closed():
    text = format_shipped_caption("Claude Opus 5", "closed")
    assert text == (
        "Claude Opus 5 just shipped.\n"
        "Closed. Evals when the independent board has it."
    )
    assert "http" not in text
    assert "#" not in text
    assert "Claude Opus 5" in text.split("\n")[0]


def test_shipped_caption_open():
    text = format_shipped_caption("DeepSeek V4", "open")
    assert text.startswith("DeepSeek V4 just shipped.")
    assert "Open weights." in text


def test_evals_caption_closed_behind():
    text = format_evals_caption(
        "GPT-5.6 Sol",
        "closed",
        61,
        5,
        comparable=ComparableFact(kind="behind", other_name="Opus 5 (max)", other_score=63),
    )
    assert text == (
        "GPT-5.6 Sol: 61 on Artificial Analysis, rank 5.\n"
        "Closed. One behind Opus 5 (max) at 63."
    )


def test_evals_caption_open_weights():
    text = format_evals_caption(
        "DeepSeek V4",
        "open",
        58,
        12,
        comparable=ComparableFact(kind="open_vs_closed"),
    )
    assert text == (
        "DeepSeek V4: 58 on Artificial Analysis, rank 12.\n"
        "Open weights. Closest closed model at this score is a generation back."
    )


def test_ranked_list_batches_several_evals():
    text = format_ranked_evals_list(
        [
            ("Opus 5", 63, 1),
            ("GPT-5.6 Sol", 61, 5),
            ("DeepSeek V4", 58, 12),
        ],
        "closed",
    )
    assert text.startswith("Independent evals just landed:")
    assert "1. Opus 5 — 63" in text
    assert "Artificial Analysis" in text


def test_two_line_dwell_structure():
    """Line 1 hooks; line 2 is the payoff the first line does not contain."""
    shipped = format_shipped_caption("Claude Opus 5", "closed")
    evals = format_evals_caption("GPT-5.6 Sol", "closed", 61, 5)
    for text in (shipped, evals):
        lines = text.split("\n")
        assert len(lines) == 2
        assert lines[0] != lines[1]
        assert "http" not in text
        assert "#" not in text


def test_alt_text_names_the_score_and_source():
    alt = format_alt_evals("GPT-5.6 Sol", 61, 5, "closed")
    assert "GPT-5.6 Sol" in alt
    assert "61" in alt
    assert "Artificial Analysis" in alt
    assert len(alt) <= 1000


def test_alt_text_shipped_names_model():
    alt = format_alt_shipped("Claude Opus 5", "Anthropic", "closed")
    assert "Claude Opus 5" in alt
    assert "SHIPPED" in alt
    assert len(alt) <= 1000
