#!/usr/bin/env python3
"""Compose the ablation panels into one paper-ready figure."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT / ".tmp_paper_figure_deps"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - developer-facing error path.
    raise SystemExit("Missing dependency. Install with:\n  python3 -m pip install pillow") from exc


OUTPUT_DIR = ROOT / "assets" / "ablation"
OUTPUT_PNG = OUTPUT_DIR / "ablation_paper_figure.png"
OUTPUT_PDF = OUTPUT_DIR / "ablation_paper_figure.pdf"

SOURCE_PANELS = [
    {
        "label": "A",
        "title": "Cross-view reference mode stabilizes the wrist camera",
        "subtitle": "When the robot leaves and re-enters the workspace, CVR helps recover the scene in wrist-view rollouts.",
        "path": ROOT / "assets" / "ablation_cvr" / "cvr_ablation_figure.png",
        "accent": (49, 95, 140),
    },
    {
        "label": "B",
        "title": "Inverse dynamics joint training reduces rollout drift",
        "subtitle": "ID joint training keeps imagined rollouts aligned with the object-centric real interaction.",
        "path": ROOT / "assets" / "ablation_id" / "inverse_dynamics_ablation_figure.png",
        "accent": (59, 139, 194),
    },
]

PALETTE = {
    "background": (255, 255, 255),
    "text": (28, 35, 45),
    "muted": (88, 98, 112),
    "border": (210, 216, 225),
    "panel_fill": (248, 250, 252),
}


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def fit_to_width(image: Image.Image, width: int) -> Image.Image:
    if image.width == width:
        return image
    height = round(image.height * width / image.width)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def fit_inside(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    width, height = size
    scale = min(width / image.width, height / image.height)
    resized_size = (round(image.width * scale), round(image.height * scale))
    return image.resize(resized_size, Image.Resampling.LANCZOS)


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
    max_width: int,
    line_gap: int = 6,
) -> int:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    x, y = xy
    line_height = draw.textbbox((0, 0), "Ag", font=font)[3]
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height + line_gap
    return y


def make_figure() -> Image.Image:
    width = 2700
    margin = 34
    panel_pad = 20
    panel_gap = 28
    label_size = 42
    header_h = 86
    panel_w = (width - 2 * margin - panel_gap) // 2
    content_w = panel_w - 2 * panel_pad

    title_font = load_font(25, bold=True)
    subtitle_font = load_font(17)
    label_font = load_font(25, bold=True)

    panels: list[dict[str, object]] = []
    for spec in SOURCE_PANELS:
        source_path = spec["path"]
        if not isinstance(source_path, Path) or not source_path.exists():
            raise SystemExit(f"Missing source panel: {source_path}")
        image = fit_to_width(Image.open(source_path).convert("RGB"), content_w)
        panels.append({**spec, "image": image})

    panel_heights = [header_h + panel_pad * 2 + panel["image"].height for panel in panels]
    height = 2 * margin + max(panel_heights)

    canvas = Image.new("RGB", (width, height), PALETTE["background"])
    draw = ImageDraw.Draw(canvas)

    for idx, panel in enumerate(panels):
        accent = panel["accent"]
        image = panel["image"]
        if not isinstance(accent, tuple) or not isinstance(image, Image.Image):
            raise TypeError("Panel specification has an invalid type.")

        x0 = margin + idx * (panel_w + panel_gap)
        y = margin
        x1 = width - margin
        if idx == 0:
            x1 = x0 + panel_w
        panel_h = panel_heights[idx]
        y1 = y + panel_h
        draw.rounded_rectangle(
            (x0, y, x1, y1),
            radius=22,
            fill=PALETTE["panel_fill"],
            outline=PALETTE["border"],
            width=2,
        )
        draw.rounded_rectangle(
            (x0 + panel_pad, y + panel_pad, x0 + panel_pad + label_size, y + panel_pad + label_size),
            radius=11,
            fill=accent,
        )
        draw.text(
            (x0 + panel_pad + 12, y + panel_pad + 6),
            str(panel["label"]),
            font=label_font,
            fill=PALETTE["background"],
        )

        text_x = x0 + panel_pad + label_size + 16
        text_w = content_w - label_size - 16
        draw.text((text_x, y + panel_pad + 2), str(panel["title"]), font=title_font, fill=PALETTE["text"])
        draw_wrapped_text(
            draw,
            (text_x, y + panel_pad + 35),
            str(panel["subtitle"]),
            subtitle_font,
            PALETTE["muted"],
            text_w,
            line_gap=3,
        )

        image_box_x = x0 + panel_pad
        image_box_y = y + panel_pad + header_h
        image_x = image_box_x
        image_y = image_box_y
        canvas.paste(image, (image_x, image_y))
        draw.rounded_rectangle(
            (image_x, image_y, image_x + image.width, image_y + image.height),
            radius=10,
            outline=PALETTE["border"],
            width=2,
        )

    return canvas


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    figure = make_figure()
    figure.save(OUTPUT_PNG)
    figure.save(OUTPUT_PDF, resolution=300.0)
    print(f"Wrote {OUTPUT_PNG.relative_to(ROOT)}")
    print(f"Wrote {OUTPUT_PDF.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
