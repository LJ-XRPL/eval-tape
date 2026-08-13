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


def test_palettes_use_official_brand_hex():
    from src.config import PALETTES

    assert PALETTES["anthropic"]["bg"] == "#D97757"
    assert PALETTES["openai"]["accent"] == "#10A37F"
    assert PALETTES["google"]["bg"] == "#4285F4"
    assert PALETTES["mistral"]["bg"] == "#FA520F"
    assert PALETTES["deepseek"]["bg"] == "#4D6BFE"
    assert PALETTES["qwen"]["bg"] == "#615CED"
    assert PALETTES["kimi"]["bg"] == "#0A7AFF"
    assert PALETTES["gemma"]["bg"] == "#15B789"
    assert PALETTES["cohere"]["bg"] == "#152455"
    assert PALETTES["cohere"]["accent"] == "#DA532C"
    assert PALETTES["gemma"]["bg"] != PALETTES["google"]["bg"]


def test_ranked_evals_card_renders(tmp_path):
    path = tmp_path / "ranked.png"
    render_ranked_evals_card(
        rows=[("Opus 5", 63, 1), ("GPT-5.6 Sol", 61, 5), ("DeepSeek V4", 58, 12)],
        lab_key="anthropic",
        out_path=path,
    )
    img = Image.open(path)
    assert img.size == (CARD_WIDTH, CARD_HEIGHT)
