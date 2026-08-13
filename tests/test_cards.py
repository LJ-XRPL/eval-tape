"""Card renderer produces 16:9 PNGs."""

from PIL import Image

from src.cards import render_evals_card, render_ranked_evals_card, render_shipped_card
from src.config import CARD_HEIGHT, CARD_WIDTH


def test_shipped_card_is_16x9(tmp_path):
    path = tmp_path / "shipped.png"
    render_shipped_card(
        model_name="Claude Opus 5",
        lab_key="anthropic",
        open_closed="closed",
        out_path=path,
    )
    img = Image.open(path)
    assert img.size == (CARD_WIDTH, CARD_HEIGHT)
    assert CARD_WIDTH / CARD_HEIGHT == 16 / 9
    assert path.stat().st_size < 5 * 1024 * 1024  # X photo limit


def test_evals_card_is_16x9(tmp_path):
    path = tmp_path / "evals.png"
    render_evals_card(
        model_name="GPT-5.6 Sol",
        lab_key="openai",
        score=61,
        rank=5,
        out_path=path,
    )
    img = Image.open(path)
    assert img.size == (CARD_WIDTH, CARD_HEIGHT)


def test_ranked_evals_card_renders(tmp_path):
    path = tmp_path / "ranked.png"
    render_ranked_evals_card(
        rows=[("Opus 5", 63, 1), ("GPT-5.6 Sol", 61, 5), ("DeepSeek V4", 58, 12)],
        lab_key="anthropic",
        out_path=path,
    )
    img = Image.open(path)
    assert img.size == (CARD_WIDTH, CARD_HEIGHT)
