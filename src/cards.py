"""Render SHIPPED and EVALS 16:9 PNG cards with Pillow (no image-gen API)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.config import CARD_HEIGHT, CARD_WIDTH, LAB_BY_KEY, PALETTES

# Prefer condensed / heavy system faces for thumbnail readability.
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
]
_MONO_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]


def _load_font(size: int, *, mono: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    paths = _MONO_CANDIDATES if mono else _FONT_CANDIDATES
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _palette(lab_key: str) -> dict[str, str]:
    return PALETTES.get(lab_key) or PALETTES["unknown"]


def _lab_display(lab_key: str) -> str:
    lab = LAB_BY_KEY.get(lab_key)
    return lab.display.upper() if lab else lab_key.upper()


def _draw_sprocket_row(draw: ImageDraw.ImageDraw, y: int, width: int, color: str) -> None:
    """Film-tape signature: a row of sprocket holes."""
    hole_w, hole_h = 28, 18
    gap = 22
    x = 36
    while x + hole_w < width - 24:
        draw.rounded_rectangle([x, y, x + hole_w, y + hole_h], radius=4, outline=color, width=3)
        x += hole_w + gap


def _fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    max_width: int,
    start_size: int,
    min_size: int = 48,
    mono: bool = False,
) -> tuple[ImageFont.ImageFont, str]:
    size = start_size
    while size >= min_size:
        font = _load_font(size, mono=mono)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font, text
        size -= 4
    # Hard wrap as last resort
    font = _load_font(min_size, mono=mono)
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return font, "\n".join(lines[:3])


def render_shipped_card(
    *,
    model_name: str,
    lab_key: str,
    open_closed: str,
    out_path: Path,
) -> Path:
    pal = _palette(lab_key)
    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), pal["bg"])
    draw = ImageDraw.Draw(img)

    # Sprocket holes top + bottom (tape signature)
    hole = "#2A2A2A" if pal["bg"].lower() in {"#000000", "#0a0a0a", "#0b1f3a", "#111827"} else "#1A1A1A"
    _draw_sprocket_row(draw, 28, CARD_WIDTH, hole)
    _draw_sprocket_row(draw, CARD_HEIGHT - 46, CARD_WIDTH, hole)

    # OPEN / CLOSED pill
    pill = "OPEN" if open_closed == "open" else "CLOSED"
    pill_font = _load_font(36)
    pad_x, pad_y = 28, 14
    pb = draw.textbbox((0, 0), pill, font=pill_font)
    pw, ph = pb[2] - pb[0], pb[3] - pb[1]
    pill_box = [64, 90, 64 + pw + pad_x * 2, 90 + ph + pad_y * 2]
    draw.rounded_rectangle(pill_box, radius=999, fill=pal["pill_bg"])
    draw.text((pill_box[0] + pad_x, pill_box[1] + pad_y - 2), pill, font=pill_font, fill=pal["pill_fg"])

    # Giant condensed model name
    font, fitted = _fit_text(draw, model_name.upper(), max_width=CARD_WIDTH - 120, start_size=160, min_size=56)
    # Vertically center-ish above lower third
    y = 220
    for line in fitted.split("\n"):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((CARD_WIDTH - tw) // 2, y), line, font=font, fill=pal["fg"])
        y += (bbox[3] - bbox[1]) + 10

    # Black lower-third: SHIPPED · LAB · EVALTAPE
    band_h = 140
    draw.rectangle([0, CARD_HEIGHT - band_h, CARD_WIDTH, CARD_HEIGHT], fill="#0A0A0A")
    meta_font = _load_font(42)
    meta = f"SHIPPED  ·  {_lab_display(lab_key)}  ·  EVALTAPE"
    mb = draw.textbbox((0, 0), meta, font=meta_font)
    mw = mb[2] - mb[0]
    draw.text(((CARD_WIDTH - mw) // 2, CARD_HEIGHT - band_h + 48), meta, font=meta_font, fill="#F5F5F5")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)
    return out_path


def _draw_led_number(draw: ImageDraw.ImageDraw, score_text: str, cx: int, cy: int, color: str) -> None:
    """Enormous Intelligence Index number — LED/pixel feel for tap-to-expand rewards."""
    font = _load_font(280, mono=True)
    bbox = draw.textbbox((0, 0), score_text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = cx - tw // 2
    y = cy - th // 2
    # Soft pixel bloom
    for dx, dy in ((4, 0), (-4, 0), (0, 4), (0, -4)):
        draw.text((x + dx, y + dy), score_text, font=font, fill="#0F3D2E")
    draw.text((x, y), score_text, font=font, fill=color)
    # Scanline suggestion
    for i in range(0, th, 8):
        draw.line([(x - 20, y + i), (x + tw + 20, y + i)], fill="#00000055", width=1)


def render_evals_card(
    *,
    model_name: str,
    lab_key: str,
    score: float,
    rank: int,
    out_path: Path,
) -> Path:
    # Matte black jumbotron
    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), "#0A0A0A")
    draw = ImageDraw.Draw(img)
    pal = _palette(lab_key)
    accent = pal.get("accent") or "#39FF14"
    # Prefer green LED on black unless lab accent is already vivid
    led = accent if accent.lower() not in {"#ffffff", "#0a0a0a", "#000000"} else "#39FF14"

    _draw_sprocket_row(draw, 28, CARD_WIDTH, "#2A2A2A")
    _draw_sprocket_row(draw, CARD_HEIGHT - 46, CARD_WIDTH, "#2A2A2A")

    # Model name top
    name_font, fitted = _fit_text(draw, model_name, max_width=CARD_WIDTH - 120, start_size=72, min_size=40)
    y = 70
    for line in fitted.split("\n"):
        bbox = draw.textbbox((0, 0), line, font=name_font)
        tw = bbox[2] - bbox[0]
        draw.text(((CARD_WIDTH - tw) // 2, y), line, font=name_font, fill="#F5F5F5")
        y += (bbox[3] - bbox[1]) + 6

    # Enormous score
    score_text = str(int(round(score)))
    _draw_led_number(draw, score_text, CARD_WIDTH // 2, CARD_HEIGHT // 2 + 20, led)

    # RANK n
    rank_font = _load_font(48)
    rank_text = f"RANK {rank}"
    rb = draw.textbbox((0, 0), rank_text, font=rank_font)
    draw.text(((CARD_WIDTH - (rb[2] - rb[0])) // 2, CARD_HEIGHT - 210), rank_text, font=rank_font, fill="#AAAAAA")

    # Footer: EVALTAPE + ARTIFICIAL ANALYSIS (required attribution)
    foot_font = _load_font(32)
    footer = "EVALTAPE  ·  ARTIFICIAL ANALYSIS"
    fb = draw.textbbox((0, 0), footer, font=foot_font)
    draw.text(((CARD_WIDTH - (fb[2] - fb[0])) // 2, CARD_HEIGHT - 120), footer, font=foot_font, fill="#777777")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)
    return out_path


def render_ranked_evals_card(
    *,
    rows: list[tuple[str, float, int]],
    lab_key: str,
    out_path: Path,
) -> Path:
    """Single jumbotron when several evals land together."""
    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), "#0A0A0A")
    draw = ImageDraw.Draw(img)
    _draw_sprocket_row(draw, 28, CARD_WIDTH, "#2A2A2A")
    _draw_sprocket_row(draw, CARD_HEIGHT - 46, CARD_WIDTH, "#2A2A2A")

    title_font = _load_font(56)
    title = "INDEPENDENT EVALS"
    tb = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((CARD_WIDTH - (tb[2] - tb[0])) // 2, 80), title, font=title_font, fill="#F5F5F5")

    row_font = _load_font(48)
    y = 200
    for name, score, rank in rows[:5]:
        line = f"{rank:>2}  {name}  ·  {int(round(score))}"
        draw.text((120, y), line, font=row_font, fill="#E5E5E5")
        y += 70

    foot_font = _load_font(32)
    footer = "EVALTAPE  ·  ARTIFICIAL ANALYSIS"
    fb = draw.textbbox((0, 0), footer, font=foot_font)
    draw.text(((CARD_WIDTH - (fb[2] - fb[0])) // 2, CARD_HEIGHT - 120), footer, font=foot_font, fill="#777777")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)
    return out_path
