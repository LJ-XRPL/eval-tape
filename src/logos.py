"""Rasterize vendored lab SVG marks for the film-tape cards."""

from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image

from src.config import LAB_BY_KEY, ROOT

LOGOS_DIR = ROOT / "assets" / "logos"


def logo_path(lab_key: str) -> Path | None:
    path = LOGOS_DIR / f"{lab_key}.svg"
    return path if path.exists() else None


def _svg_for_raster(path: Path, color: str) -> bytes:
    text = path.read_text(encoding="utf-8")
    if 'fill="currentColor"' in text:
        text = text.replace('fill="currentColor"', f'fill="{color}"')
    elif "fill=" not in text.split(">", 1)[0]:
        text = text.replace("<svg ", f'<svg fill="{color}" ', 1)
    text = text.replace('width="1em"', 'width="24"').replace('height="1em"', 'height="24"')
    return text.encode("utf-8")


@lru_cache(maxsize=64)
def load_logo(lab_key: str, size: int, color: str) -> Image.Image | None:
    """Return an RGBA mark, or None if this lab has no SVG."""
    path = logo_path(lab_key)
    if path is None or size < 8:
        return None
    png = cairosvg.svg2png(
        bytestring=_svg_for_raster(path, color),
        output_width=size * 2,
        output_height=size * 2,
    )
    mark = Image.open(BytesIO(png)).convert("RGBA")
    if mark.size != (size, size):
        mark = mark.resize((size, size), Image.Resampling.LANCZOS)
    return mark


def paste_logo(
    img: Image.Image,
    lab_key: str,
    xy: tuple[int, int],
    *,
    size: int,
    color: str,
    opacity: float = 1.0,
) -> None:
    """Composite a lab mark onto `img` in place (RGB or RGBA)."""
    mark = load_logo(lab_key, size, color)
    if mark is None:
        return
    if opacity < 1.0:
        r, g, b, a = mark.split()
        a = a.point(lambda p: int(p * opacity))
        mark = Image.merge("RGBA", (r, g, b, a))
    img.paste(mark, xy, mark)


def expected_logo_keys() -> tuple[str, ...]:
    return tuple(lab.key for lab in LAB_BY_KEY.values())
