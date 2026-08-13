"""Render SHIPPED and EVALS 16:9 PNG cards with Pillow (no image-gen API)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from src.config import CARD_HEIGHT, CARD_WIDTH, LAB_BY_KEY, PALETTES, ROOT

FONTS_DIR = ROOT / "assets" / "fonts"

# 35mm-style side rails — the tape signature. ~5% each side; reads as a frame at timeline size.
RAIL_W = 76
HOLE_W, HOLE_H = 34, 22
HOLE_GAP = 16
HOLE_INSET = 21
LOWER_THIRD_H = 128

_FONT_FILES = {
    "display": ("BebasNeue-Regular.ttf", "Anton-Regular.ttf", "BarlowCondensed-Black.ttf"),
    "condensed": ("BarlowCondensed-Black.ttf", "BarlowCondensed-ExtraBold.ttf", "Anton-Regular.ttf"),
    "label": ("BarlowCondensed-SemiBold.ttf", "BarlowCondensed-ExtraBold.ttf", "Inter-Bold.ttf"),
    "ui": ("Inter-Bold.ttf", "BarlowCondensed-SemiBold.ttf"),
}

_SYSTEM_FALLBACKS = (
    "/usr/share/fonts/truetype/macos/Inter-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
)

# 5×7 stadium jumbotron bitmaps. Unlit cells stay visible so tap-to-expand rewards.
PIXEL_5X7: dict[str, tuple[str, ...]] = {
    "0": ("01110", "10001", "10001", "10011", "10101", "11001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("01110", "10001", "00001", "00110", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
}


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")[:6]
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _mix(a: str, b: str, t: float) -> str:
    ar, ag, ab = _rgb(a)
    br, bg, bb = _rgb(b)
    return _hex(
        (
            int(ar + (br - ar) * t),
            int(ag + (bg - ag) * t),
            int(ab + (bb - ab) * t),
        )
    )


def _palette(lab_key: str) -> dict[str, str]:
    return PALETTES.get(lab_key) or PALETTES["unknown"]


def _lab_display(lab_key: str) -> str:
    lab = LAB_BY_KEY.get(lab_key)
    return lab.display.upper() if lab else lab_key.upper()


def _font(role: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = _FONT_FILES.get(role, _FONT_FILES["ui"])
    for name in names:
        path = FONTS_DIR / name
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    for path in _SYSTEM_FALLBACKS:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int, int, int]:
    return draw.textbbox((0, 0), text, font=font)


def _size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    l, t, r, b = _bbox(draw, text, font)
    return r - l, b - t


def _draw_tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: str,
    tracking: float = 0,
) -> tuple[float, float]:
    """Draw text with letter-spacing. Returns (width, height)."""
    x, y = xy
    max_h = 0
    for i, ch in enumerate(text):
        draw.text((x, y), ch, font=font, fill=fill)
        w, h = _size(draw, ch, font)
        max_h = max(max_h, h)
        x += w + (tracking if i < len(text) - 1 else 0)
    total_w = x - xy[0]
    return total_w, max_h


def _tracked_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, tracking: float) -> float:
    if not text:
        return 0
    w = sum(_size(draw, ch, font)[0] for ch in text) + tracking * (len(text) - 1)
    return w


def _content_box() -> tuple[int, int, int, int]:
    return RAIL_W, 0, CARD_WIDTH - RAIL_W, CARD_HEIGHT


def _draw_film_rails(draw: ImageDraw.ImageDraw, *, rail: str = "#0B0B0B", hole: str = "#2E2E2E") -> None:
    """Left/right perforation rails — punched holes, not outlined rectangles."""
    w, h = CARD_WIDTH, CARD_HEIGHT
    draw.rectangle([0, 0, RAIL_W, h], fill=rail)
    draw.rectangle([w - RAIL_W, 0, w, h], fill=rail)
    # Inner gate line between film and picture.
    gate = _mix(rail, "#FFFFFF", 0.08)
    draw.line([(RAIL_W, 0), (RAIL_W, h)], fill=gate, width=2)
    draw.line([(w - RAIL_W, 0), (w - RAIL_W, h)], fill=gate, width=2)

    y = 28
    rim = _mix(hole, "#000000", 0.35)
    glint = _mix(hole, "#FFFFFF", 0.22)
    while y + HOLE_H < h - 20:
        for x in (HOLE_INSET, w - HOLE_INSET - HOLE_W):
            draw.rounded_rectangle([x, y, x + HOLE_W, y + HOLE_H], radius=6, fill=rim)
            draw.rounded_rectangle(
                [x + 2, y + 2, x + HOLE_W - 2, y + HOLE_H - 2],
                radius=4,
                fill=hole,
            )
            draw.arc([x + 4, y + 3, x + 18, y + 12], start=200, end=320, fill=glint, width=2)
        y += HOLE_H + HOLE_GAP


def _grain(img: Image.Image, amount: float = 0.045) -> Image.Image:
    noise = Image.effect_noise(img.size, 18).convert("RGB")
    return Image.blend(img.convert("RGB"), noise, amount)


def _vignette(img: Image.Image, strength: float = 0.28) -> Image.Image:
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    mdraw = ImageDraw.Draw(mask)
    inset_x, inset_y = int(w * 0.08), int(h * 0.10)
    mdraw.ellipse([-inset_x, -inset_y, w + inset_x, h + inset_y], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(90))
    mask = ImageChops.invert(mask)
    # Scale vignette alpha
    mask = mask.point(lambda p: int(p * strength))
    shade = Image.new("RGB", (w, h), (0, 0, 0))
    return Image.composite(shade, img.convert("RGB"), mask)


def _max_font_for_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    role: str,
    max_width: int,
    max_size: int,
    min_size: int,
) -> tuple[ImageFont.ImageFont, int]:
    """Grow type until it fills the well — stop-scroll at timeline thumbnail size."""
    lo, hi = min_size, max_size
    best = min_size
    while lo <= hi:
        mid = (lo + hi) // 2
        font = _font(role, mid)
        w, _ = _size(draw, text, font)
        if w <= max_width:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return _font(role, best), best


def _draw_text_halo(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: str,
    halo: str,
    radius: int = 2,
) -> None:
    """Thin halo so condensed type survives X's JPEG/PNG recompress."""
    x, y = xy
    if radius > 0:
        for dx, dy in ((-radius, 0), (radius, 0), (0, -radius), (0, radius)):
            draw.text((x + dx, y + dy), text, font=font, fill=halo)
    draw.text((x, y), text, font=font, fill=fill)


def _fit_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    *,
    role: str,
    max_width: int,
    start: int,
    min_size: int,
) -> tuple[ImageFont.ImageFont, int, list[str]]:
    size = start
    while size >= min_size:
        font = _font(role, size)
        if all(_size(draw, line, font)[0] <= max_width for line in lines if line):
            return font, size, lines
        size -= 6
    font = _font(role, min_size)
    return font, min_size, lines


def _split_name(name: str) -> list[str]:
    words = name.strip().upper().split()
    if len(words) <= 1:
        return [name.strip().upper()]
    last = words[-1]
    if len(words) >= 3 and (last[:1].isdigit() or last[0] in "V" or len(last) <= 4):
        return [" ".join(words[:-1]), last]
    if len(words) >= 3:
        mid = (len(words) + 1) // 2
        return [" ".join(words[:mid]), " ".join(words[mid:])]
    return [" ".join(words)]


def _draw_name_block(
    draw: ImageDraw.ImageDraw,
    name: str,
    *,
    role: str,
    box: tuple[int, int, int, int],
    fill: str,
    align: str = "left",
    start: int = 260,
    min_size: int = 96,
    uppercase: bool = True,
) -> None:
    x0, y0, x1, y1 = box
    max_w = x1 - x0
    text = name.upper() if uppercase else name
    # Fill the well on a single line when possible (timeline thumbnail must read the name).
    font, size = _max_font_for_width(
        draw, text, role=role, max_width=max_w, max_size=start, min_size=max(min_size, 72)
    )
    lines = [text]
    if _size(draw, text, font)[0] > max_w:
        wrapped = _split_name(text) if uppercase else [text]
        longest = max(wrapped, key=lambda line: _size(draw, line, _font(role, min_size))[0])
        font, size = _max_font_for_width(
            draw, longest, role=role, max_width=max_w, max_size=start, min_size=min_size
        )
        lines = wrapped

    assert font is not None
    line_sizes = [_size(draw, line, font) for line in lines]
    gap = max(8, int(size * 0.04))
    total_h = sum(h for _, h in line_sizes) + gap * (len(lines) - 1)
    y = y0 + max(0, (y1 - y0 - total_h) // 2)
    use_halo = fill.lower() not in {"#0a0a0a", "#000000", "#1a0f00"}
    for line, (lw, lh) in zip(lines, line_sizes, strict=True):
        x = x0 if align == "left" else x0 + (max_w - lw) // 2
        if use_halo:
            _draw_text_halo(draw, (x, y), line, font, fill, halo="#000000", radius=3)
        else:
            draw.text((x, y), line, font=font, fill=fill)
        y += lh + gap


def _pixel_digit_size(cell: int, gap: int) -> tuple[int, int]:
    return 5 * cell + 4 * gap, 7 * cell + 6 * gap


def _draw_pixel_digit(
    draw: ImageDraw.ImageDraw,
    digit: str,
    origin: tuple[int, int],
    *,
    cell: int,
    gap: int,
    on: str,
    off: str,
    bead: str,
) -> None:
    bitmap = PIXEL_5X7.get(digit)
    if not bitmap:
        return
    x0, y0 = origin
    radius = max(3, cell // 5)
    inset = max(3, cell // 5)
    for r, row in enumerate(bitmap):
        for c, bit in enumerate(row):
            x = x0 + c * (cell + gap)
            y = y0 + r * (cell + gap)
            lit = bit == "1"
            draw.rounded_rectangle([x, y, x + cell, y + cell], radius=radius, fill=on if lit else off)
            if lit:
                draw.rounded_rectangle(
                    [x + inset, y + inset, x + cell - inset, y + int(cell * 0.45)],
                    radius=max(2, radius - 1),
                    fill=bead,
                )


def _draw_led_score(base: Image.Image, score_text: str, cx: int, cy: int, led: str) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Enormous pixel-grid Intelligence Index — glow + unlit cells (photo-expand)."""
    n = max(1, len(score_text))
    # Sized so the number is ~half the card at 1600×900, still a glowing blob at ~400px timeline width.
    cell = 54 if n <= 2 else 42 if n == 3 else 32
    gap = 10 if n <= 2 else 8
    digit_w, digit_h = _pixel_digit_size(cell, gap)
    spacing = cell
    total_w = n * digit_w + (n - 1) * spacing
    x = cx - total_w // 2
    y = cy - digit_h // 2

    off = _mix(led, "#050505", 0.88)
    bead = _mix(led, "#FFFFFF", 0.35)
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(layer)

    # Dark instrument panel behind the digits.
    pad_x, pad_y = 48, 36
    panel = [
        x - pad_x,
        y - pad_y,
        x + total_w + pad_x,
        y + digit_h + pad_y,
    ]
    ldraw.rounded_rectangle(panel, radius=22, fill=(12, 12, 14, 230), outline=(32, 32, 36, 255), width=2)

    for i, ch in enumerate(score_text):
        origin = (x + i * (digit_w + spacing), y)
        _draw_pixel_digit(ldraw, ch, origin, cell=cell, gap=gap, on=led, off=off, bead=bead)

    glow = layer.filter(ImageFilter.GaussianBlur(22))
    glow2 = layer.filter(ImageFilter.GaussianBlur(48))
    out = base.convert("RGBA")
    out.alpha_composite(glow2)
    out.alpha_composite(glow)
    out.alpha_composite(layer)
    return out.convert("RGB"), (int(panel[0]), int(panel[1]), int(panel[2]), int(panel[3]))


def _led_color(pal: dict[str, str]) -> str:
    accent = pal.get("accent") or pal.get("fg") or "#39FF14"
    if accent.lower() in {"#ffffff", "#f5f5f5", "#f8fafc", "#f3e8ff", "#e6fffa", "#d4f5e9"}:
        return "#39FF14"
    if accent.lower() in {"#0a0a0a", "#000000", "#1a0f00"}:
        return "#39FF14"
    return accent


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
    _draw_film_rails(draw)

    left, _, right, _ = _content_box()
    pad = 64

    # OPEN / CLOSED pill — small stamp, not a competing headline.
    pill = "OPEN" if open_closed == "open" else "CLOSED"
    pill_font = _font("ui", 28)
    tracking = 4
    tw = _tracked_width(draw, pill, pill_font, tracking)
    ph = _size(draw, pill, pill_font)[1]
    pad_x, pad_y = 22, 12
    pill_box = [left + pad, 52, left + pad + int(tw) + pad_x * 2, 52 + ph + pad_y * 2]
    draw.rounded_rectangle(pill_box, radius=999, fill=pal["pill_bg"])
    _draw_tracked(
        draw,
        (pill_box[0] + pad_x, pill_box[1] + pad_y - 2),
        pill,
        pill_font,
        pal["pill_fg"],
        tracking,
    )

    # Micro brand, top-right of the picture well.
    brand_font = _font("label", 28)
    brand = "EVALTAPE"
    bw = _tracked_width(draw, brand, brand_font, 6)
    brand_fill = pal["fg"] if pal["bg"].lower() not in {"#000000", "#0a0a0a"} else "#888888"
    _draw_tracked(draw, (right - pad - bw, 62), brand, brand_font, brand_fill, 6)

    # Giant condensed model name, left-aligned in the well (poster, not PowerPoint).
    name_top = pill_box[3] + 24
    name_bottom = CARD_HEIGHT - LOWER_THIRD_H - 12
    _draw_name_block(
        draw,
        model_name,
        role="display",
        box=(left + pad, name_top, right - pad, name_bottom),
        fill=pal["fg"],
        align="left",
        start=320,
        min_size=110,
        uppercase=True,
    )

    # Black lower-third: SHIPPED · LAB · EVALTAPE
    y0 = CARD_HEIGHT - LOWER_THIRD_H
    draw.rectangle([left, y0, right, CARD_HEIGHT], fill="#0A0A0A")
    rule = pal.get("accent") or pal["fg"]
    if rule.lower() in {"#0a0a0a", "#000000", "#1a0f00"}:
        rule = "#F5F5F5"
    draw.rectangle([left, y0, right, y0 + 6], fill=rule)

    meta_font = _font("label", 42)
    parts = ["SHIPPED", _lab_display(lab_key), "EVALTAPE"]
    tracking = 5
    gap = 28
    dot_r = 4
    widths = [_tracked_width(draw, p, meta_font, tracking) for p in parts]
    total = sum(widths) + gap * 2 + dot_r * 4 + 24
    x = left + (right - left - total) / 2
    y = y0 + 52
    for i, part in enumerate(parts):
        _draw_tracked(draw, (x, y), part, meta_font, "#F2F2F2", tracking)
        x += widths[i]
        if i < len(parts) - 1:
            x += gap
            cx, cy = x + dot_r, y + 18
            draw.rectangle([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill="#F2F2F2")
            x += dot_r * 2 + gap

    img = _vignette(img, 0.18)
    img = _grain(img, 0.04)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)
    return out_path


def render_evals_card(
    *,
    model_name: str,
    lab_key: str,
    score: float,
    rank: int,
    out_path: Path,
) -> Path:
    pal = _palette(lab_key)
    led = _led_color(pal)
    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), "#0A0A0A")
    draw = ImageDraw.Draw(img)
    _draw_film_rails(draw, rail="#111111", hole="#3A3A3A")

    left, _, right, _ = _content_box()
    pad = 64

    # Model name — condensed, top of the jumbotron.
    name_font, _, name_lines = _fit_lines(
        draw,
        [model_name],
        role="condensed",
        max_width=right - left - pad * 2,
        start=92,
        min_size=48,
    )
    # If still too wide, split.
    if _size(draw, name_lines[0], name_font)[0] > right - left - pad * 2:
        _draw_name_block(
            draw,
            model_name,
            role="condensed",
            box=(left + pad, 40, right - pad, 200),
            fill="#F4F4F4",
            align="center",
            start=84,
            min_size=44,
            uppercase=False,
        )
    else:
        nw, nh = _size(draw, model_name, name_font)
        draw.text((left + (right - left - nw) // 2, 56), model_name, font=name_font, fill="#F4F4F4")

    score_text = str(int(round(score)))
    img, panel = _draw_led_score(img, score_text, CARD_WIDTH // 2, CARD_HEIGHT // 2 + 4, led)
    draw = ImageDraw.Draw(img)

    # RANK n — scoreboard label just under the jumbotron panel (visible at thumbnail).
    rank_font = _font("label", 40)
    rank_text = f"RANK  {rank}"
    rw = _tracked_width(draw, rank_text, rank_font, 8)
    rank_y = min(panel[3] + 16, CARD_HEIGHT - 150)
    _draw_tracked(
        draw,
        ((CARD_WIDTH - rw) / 2, rank_y),
        rank_text,
        rank_font,
        "#A8A8A8",
        8,
    )

    # Required attribution.
    foot_font = _font("label", 32)
    footer = "EVALTAPE  ·  ARTIFICIAL ANALYSIS"
    fw = _tracked_width(draw, footer, foot_font, 4)
    _draw_tracked(
        draw,
        ((CARD_WIDTH - fw) / 2, CARD_HEIGHT - 118),
        footer,
        foot_font,
        "#6E6E6E",
        4,
    )

    img = _vignette(img, 0.22)
    img = _grain(img, 0.035)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)
    return out_path


def render_ranked_evals_card(
    *,
    rows: list[tuple[str, float, int]],
    lab_key: str,
    out_path: Path,
) -> Path:
    pal = _palette(lab_key)
    led = _led_color(pal)
    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), "#0A0A0A")
    draw = ImageDraw.Draw(img)
    _draw_film_rails(draw, rail="#111111", hole="#3A3A3A")

    left, _, right, _ = _content_box()
    pad = 72

    title_font = _font("display", 84)
    title = "INDEPENDENT EVALS"
    tw, th = _size(draw, title, title_font)
    draw.text((left + (right - left - tw) // 2, 40), title, font=title_font, fill="#F4F4F4")
    draw.rectangle([left + pad, 40 + th + 14, right - pad, 40 + th + 18], fill="#2A2A2A")

    visible = rows[:5]
    score_font = _font("condensed", 78)
    rank_font = _font("label", 36)
    row_h = 88
    block_h = row_h * len(visible)
    y = 40 + th + 36 + max(0, (CARD_HEIGHT - 160 - (40 + th + 36) - block_h) // 2)
    for name, score, rank in visible:
        rank_s = f"{rank:02d}"
        draw.text((left + pad, y + 18), rank_s, font=rank_font, fill="#888888")
        max_name_w = (right - left) - pad * 2 - 240
        nf, _, _ = _fit_lines(draw, [name], role="condensed", max_width=max_name_w, start=58, min_size=36)
        draw.text((left + pad + 86, y + 8), name, font=nf, fill="#EDEDED")
        score_s = str(int(round(score)))
        sw, _sh = _size(draw, score_s, score_font)
        draw.text((right - pad - sw, y - 4), score_s, font=score_font, fill=led)
        y += row_h

    foot_font = _font("label", 32)
    footer = "EVALTAPE  ·  ARTIFICIAL ANALYSIS"
    fw = _tracked_width(draw, footer, foot_font, 4)
    _draw_tracked(draw, ((CARD_WIDTH - fw) / 2, CARD_HEIGHT - 118), footer, foot_font, "#6E6E6E", 4)

    img = _vignette(img, 0.2)
    img = _grain(img, 0.035)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)
    return out_path
