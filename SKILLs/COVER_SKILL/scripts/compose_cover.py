#!/usr/bin/env python3
"""Compose exact bilingual cover typography over a text-free background.

Outputs:
  cover.png       canonical cover
  cover_epub.jpg  EPUB derivative
  cover_pdf.png   PDF derivative

The script intentionally does not generate artwork. Use the image-generation tool
first to create a text-free ``cover_base.png``; then use this script for exact text.
"""

from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required: pip install pillow") from exc

CANVAS = (1760, 2500)
SAFE_X = 0.09


def _run_fc_match(pattern: str) -> str | None:
    if shutil.which("fc-match") is None:
        return None
    try:
        cp = subprocess.run(
            ["fc-match", "-f", "%{file}\n", pattern],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except Exception:
        return None
    for line in cp.stdout.splitlines():
        p = Path(line.strip())
        if p.is_file():
            return str(p)
    return None


def _candidate_paths() -> list[Path]:
    roots = [
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        Path.home() / ".fonts",
        Path("C:/Windows/Fonts"),
        Path("/System/Library/Fonts"),
        Path("/Library/Fonts"),
    ]
    out: list[Path] = []
    for root in roots:
        if root.exists():
            try:
                out.extend(root.rglob("*.ttf"))
                out.extend(root.rglob("*.otf"))
                out.extend(root.rglob("*.ttc"))
            except OSError:
                pass
    return out


def find_font(explicit: str, *, cjk: bool) -> str:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.is_file():
            raise FileNotFoundError(f"Font not found: {p}")
        return str(p)

    patterns = (
        ["Noto Serif CJK SC", "Source Han Serif SC", "FandolSong", "SimSun", "Songti SC", "serif"]
        if cjk
        else ["Noto Serif", "Source Serif 4", "Times New Roman", "Liberation Serif", "serif"]
    )
    for pattern in patterns:
        hit = _run_fc_match(pattern)
        if hit:
            return hit

    names = [
        "NotoSerifCJK", "SourceHanSerif", "FandolSong", "simsun", "Songti"
    ] if cjk else [
        "NotoSerif", "SourceSerif", "times", "LiberationSerif", "DejaVuSerif"
    ]
    for p in _candidate_paths():
        lower = p.name.lower()
        if any(name.lower() in lower for name in names):
            return str(p)
    raise RuntimeError(
        "Could not locate a suitable installed font. Pass --font-cjk and/or --font-latin explicitly."
    )


def crop_fill(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    src_w, src_h = image.size
    scale = max(target_w / src_w, target_h / src_h)
    resized = image.resize((round(src_w * scale), round(src_h * scale)), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - target_w) // 2)
    top = max(0, (resized.height - target_h) // 2)
    return resized.crop((left, top, left + target_w, top + target_h))


def text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, spacing: int) -> tuple[int, int]:
    box = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align="center")
    return box[2] - box[0], box[3] - box[1]


def wrap_english(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    words = text.split()
    if not words:
        return ""
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = current + " " + word
        width = draw.textbbox((0, 0), trial, font=font)[2]
        if width <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return "\n".join(lines)


def wrap_cjk(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    text = text.strip()
    if not text:
        return ""
    lines: list[str] = []
    current = ""
    for ch in text:
        if ch == "\n":
            if current:
                lines.append(current)
                current = ""
            continue
        trial = current + ch
        width = draw.textbbox((0, 0), trial, font=font)[2]
        if current and width > max_width:
            lines.append(current)
            current = ch
        else:
            current = trial
    if current:
        lines.append(current)
    return "\n".join(lines)


def fit_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: str,
    *,
    max_width: int,
    max_height: int,
    start_size: int,
    min_size: int,
    english: bool,
    spacing_ratio: float = 0.20,
) -> tuple[str, ImageFont.FreeTypeFont, int, tuple[int, int]]:
    for size in range(start_size, min_size - 1, -2):
        font = ImageFont.truetype(font_path, size=size)
        wrapped = wrap_english(draw, text, font, max_width) if english else wrap_cjk(draw, text, font, max_width)
        spacing = max(4, round(size * spacing_ratio))
        width, height = text_bbox(draw, wrapped, font, spacing)
        if width <= max_width and height <= max_height:
            return wrapped, font, spacing, (width, height)
    raise RuntimeError(f"Text cannot fit safely on cover: {text!r}")


def mean_luminance(image: Image.Image, box: tuple[int, int, int, int]) -> float:
    crop = image.crop(box).convert("L").resize((32, 32))
    return float(ImageStat.Stat(crop).mean[0])


def add_readability_field(image: Image.Image, box: tuple[int, int, int, int], *, light_text: bool) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    x0, y0, x1, y1 = box
    base_alpha = 92
    fill = (0, 0, 0, base_alpha) if light_text else (255, 255, 255, base_alpha)
    draw.rounded_rectangle((x0, y0, x1, y1), radius=42, fill=fill)
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=12))
    return Image.alpha_composite(image.convert("RGBA"), overlay)


def draw_centered_multiline(
    draw: ImageDraw.ImageDraw,
    center_x: int,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    spacing: int,
    *,
    shadow: bool = True,
) -> int:
    box = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align="center")
    width = box[2] - box[0]
    height = box[3] - box[1]
    x = center_x - width // 2
    if shadow:
        shadow_fill = (0, 0, 0, 110) if fill[0] > 128 else (255, 255, 255, 105)
        draw.multiline_text(
            (x + 3, y + 4), text, font=font, fill=shadow_fill,
            spacing=spacing, align="center"
        )
    draw.multiline_text((x, y), text, font=font, fill=fill, spacing=spacing, align="center")
    return height


def compose(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    base_path = Path(args.base).expanduser().resolve()
    if not base_path.is_file():
        raise FileNotFoundError(base_path)
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    zh_title = args.zh_title.strip()
    en_title = args.en_title.strip()
    if not zh_title or not en_title:
        raise ValueError("Both --zh-title and --en-title are required")

    author_parts = []
    if args.author_zh.strip():
        author_parts.append(args.author_zh.strip())
    if args.author_original.strip():
        author_parts.append(args.author_original.strip())
    author = " / ".join(author_parts)

    font_cjk = find_font(args.font_cjk, cjk=True)
    font_latin = find_font(args.font_latin, cjk=False)

    base = Image.open(base_path).convert("RGB")
    canvas = crop_fill(base, CANVAS).convert("RGBA")
    w, h = canvas.size
    max_width = round(w * (1 - 2 * SAFE_X))

    if args.position == "top":
        zone = (round(w * 0.065), round(h * 0.055), round(w * 0.935), round(h * 0.43))
    elif args.position == "center":
        zone = (round(w * 0.065), round(h * 0.29), round(w * 0.935), round(h * 0.70))
    else:
        zone = (round(w * 0.065), round(h * 0.57), round(w * 0.935), round(h * 0.94))

    lum = mean_luminance(canvas.convert("RGB"), zone)
    light_text = lum < 148
    text_fill = (248, 248, 246, 255) if light_text else (26, 26, 26, 255)
    canvas = add_readability_field(canvas, zone, light_text=light_text)
    draw = ImageDraw.Draw(canvas)

    zone_w = zone[2] - zone[0]
    zone_h = zone[3] - zone[1]
    inner_w = min(max_width, round(zone_w * 0.91))

    zh_wrapped, zh_font, zh_spacing, (_zh_w, zh_h) = fit_block(
        draw, zh_title, font_cjk,
        max_width=inner_w, max_height=round(zone_h * 0.43),
        start_size=150, min_size=74, english=False, spacing_ratio=0.13,
    )
    en_wrapped, en_font, en_spacing, (_en_w, en_h) = fit_block(
        draw, en_title, font_latin,
        max_width=inner_w, max_height=round(zone_h * 0.27),
        start_size=70, min_size=38, english=True, spacing_ratio=0.18,
    )
    author_h = 0
    author_font = None
    if author:
        _author_wrapped, author_font, _author_spacing, (_aw, author_h) = fit_block(
            draw, author, font_cjk if args.author_zh.strip() else font_latin,
            max_width=inner_w, max_height=round(zone_h * 0.14),
            start_size=50, min_size=30, english=False if args.author_zh.strip() else True, spacing_ratio=0.15,
        )
        author = _author_wrapped
        author_spacing = _author_spacing
    else:
        author_spacing = 0

    gap1 = round(h * 0.012)
    gap2 = round(h * 0.018)
    total_h = zh_h + gap1 + en_h + (gap2 + author_h if author else 0)
    y = zone[1] + max(0, (zone_h - total_h) // 2)
    cx = w // 2
    y += draw_centered_multiline(draw, cx, y, zh_wrapped, zh_font, text_fill, zh_spacing)
    y += gap1
    y += draw_centered_multiline(draw, cx, y, en_wrapped, en_font, text_fill, en_spacing)
    if author and author_font:
        y += gap2
        draw_centered_multiline(draw, cx, y, author, author_font, text_fill, author_spacing)

    rgb = canvas.convert("RGB")
    canonical = out_dir / "cover.png"
    epub = out_dir / "cover_epub.jpg"
    pdf = out_dir / "cover_pdf.png"
    rgb.save(canonical, format="PNG", optimize=True)
    rgb.save(pdf, format="PNG", optimize=True)
    rgb.save(epub, format="JPEG", quality=92, subsampling=0, optimize=True, progressive=True)

    for p in (canonical, epub, pdf):
        with Image.open(p) as check:
            if check.size != CANVAS:
                raise RuntimeError(f"Unexpected output size for {p}: {check.size}")
    print(f"CJK font  : {font_cjk}")
    print(f"Latin font: {font_latin}")
    print(f"Output    : {canonical}")
    print(f"EPUB      : {epub}")
    print(f"PDF       : {pdf}")
    return canonical, epub, pdf


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Overlay exact bilingual book-cover typography")
    p.add_argument("--base", required=True, help="text-free cover background")
    p.add_argument("--zh-title", required=True, help="Chinese main title only")
    p.add_argument("--en-title", required=True, help="English main title only")
    p.add_argument("--author-original", default="", help="original author name(s)")
    p.add_argument("--author-zh", default="", help="established Chinese author name(s), optional")
    p.add_argument("--position", choices=("top", "center", "bottom"), default="top")
    p.add_argument("--font-cjk", default="", help="optional installed CJK serif font path")
    p.add_argument("--font-latin", default="", help="optional installed Latin serif font path")
    p.add_argument("--out-dir", default=".")
    return p.parse_args()


if __name__ == "__main__":
    compose(parse_args())
