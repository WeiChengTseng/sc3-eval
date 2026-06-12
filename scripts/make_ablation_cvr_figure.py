#!/usr/bin/env python3
"""Create a paper-ready static figure from the CVR ablation videos."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT / ".tmp_paper_figure_deps"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))

try:
    import imageio
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - developer-facing error path.
    raise SystemExit(
        "Missing dependencies. Install with:\n"
        "  python3 -m pip install pillow imageio imageio-ffmpeg numpy"
    ) from exc


OUTPUT_DIR = ROOT / "assets" / "ablation_cvr"
OUTPUT_PNG = OUTPUT_DIR / "cvr_ablation_figure.png"
OUTPUT_PDF = OUTPUT_DIR / "cvr_ablation_figure.pdf"

VIDEOS = {
    "Without CVR": OUTPUT_DIR
    / "2026-04-02-164803Z-ur5e_single_4-d593b47b0e88__eval_17725__apr8_oct14_pretrain_rerun_80000__pick_up_bottle_and_throw_it_away_wo_cvr_bottomrow.mp4",
    "With CVR": OUTPUT_DIR
    / "2026-04-02-164632Z-ur5e_single_4-f528b7d80a5f__eval_17725__apr8_episode_buckets_120000__pick_up_bottle_and_throw_it_away_w_cvr_bottomrow.mp4",
}

TIMES_SECONDS = (3.3, 4.4, 5.5, 6.3)
FPS = 10

PALETTE = {
    "background": (255, 255, 255),
    "text": (28, 35, 45),
    "muted": (88, 98, 112),
    "border": (205, 211, 219),
    "without": (183, 121, 31),
    "with": (49, 95, 140),
    "without_fill": (255, 246, 231),
    "with_fill": (235, 245, 252),
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


def frame_at(path: Path, seconds: float) -> Image.Image:
    reader = imageio.get_reader(path, "ffmpeg")
    try:
        frame = reader.get_data(round(seconds * FPS))
    finally:
        reader.close()
    return Image.fromarray(frame).convert("RGB")


def cover_resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    scale = max(target_w / image.width, target_h / image.height)
    resized = image.resize(
        (round(image.width * scale), round(image.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int] | None = None,
    outline: tuple[int, int, int] | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def centered_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x0, y0, x1, y1 = xy
    draw.text(
        (x0 + (x1 - x0 - text_w) / 2, y0 + (y1 - y0 - text_h) / 2),
        text,
        font=font,
        fill=fill,
    )


def make_figure() -> Image.Image:
    margin_x = 64
    margin_y = 46
    label_w = 240
    col_w = 440
    col_gap = 26
    header_h = 54
    strip_h = 108
    zoom_h = 322
    cell_pad = 14
    row_gap = 34
    title_h = 0

    cell_h = cell_pad + strip_h + 10 + zoom_h + 36
    width = margin_x * 2 + label_w + len(TIMES_SECONDS) * col_w + (len(TIMES_SECONDS) - 1) * col_gap
    height = margin_y * 2 + title_h + header_h + 2 * cell_h + row_gap

    canvas = Image.new("RGB", (width, height), PALETTE["background"])
    draw = ImageDraw.Draw(canvas)

    header_font = load_font(24, bold=True)
    label_font = load_font(28, bold=True)
    small_font = load_font(18, bold=True)
    tiny_font = load_font(16)

    grid_x = margin_x + label_w
    header_y = margin_y + title_h
    for idx, seconds in enumerate(TIMES_SECONDS):
        x = grid_x + idx * (col_w + col_gap)
        centered_text(
            draw,
            (x, header_y, x + col_w, header_y + header_h),
            f"t = {seconds:.1f}s",
            header_font,
            PALETTE["text"],
        )

    row_y = header_y + header_h
    row_specs = [
        ("Without CVR", "Wrist view drifts", PALETTE["without"], PALETTE["without_fill"]),
        ("With CVR", "Wrist view recovers", PALETTE["with"], PALETTE["with_fill"]),
    ]
    for row_idx, (label, note, color, fill) in enumerate(row_specs):
        y = row_y + row_idx * (cell_h + row_gap)
        rounded_rect(
            draw,
            (margin_x, y + cell_pad, margin_x + label_w - 22, y + cell_h - 22),
            radius=24,
            fill=fill,
            outline=color,
            width=3,
        )
        draw.text((margin_x + 22, y + 110), label, font=label_font, fill=color)
        draw.text((margin_x + 22, y + 148), note, font=small_font, fill=PALETTE["text"])

        for col_idx, seconds in enumerate(TIMES_SECONDS):
            x = grid_x + col_idx * (col_w + col_gap)
            frame = frame_at(VIDEOS[label], seconds)
            strip = frame.resize((col_w, strip_h), Image.Resampling.LANCZOS)

            wrist_left = frame.width * 2 // 3
            wrist = frame.crop((wrist_left, 0, frame.width, frame.height))
            wrist = cover_resize(wrist, (col_w, zoom_h))

            rounded_rect(
                draw,
                (x - 6, y + 4, x + col_w + 6, y + cell_h - 8),
                radius=20,
                fill=(255, 255, 255),
                outline=PALETTE["border"],
                width=2,
            )
            strip_y = y + cell_pad
            canvas.paste(strip, (x, strip_y))
            draw.rectangle((x, strip_y, x + col_w - 1, strip_y + strip_h - 1), outline=PALETTE["border"], width=2)

            wrist_x0 = x + col_w * 2 // 3
            draw.rectangle((wrist_x0, strip_y, x + col_w - 1, strip_y + strip_h - 1), outline=color, width=5)
            draw.text((x + 12, strip_y + 10), "multi-view rollout", font=tiny_font, fill=PALETTE["text"])
            draw.text((wrist_x0 + 10, strip_y + strip_h - 28), "wrist", font=tiny_font, fill=color)

            zoom_y = strip_y + strip_h + 10
            canvas.paste(wrist, (x, zoom_y))
            draw.rectangle((x, zoom_y, x + col_w - 1, zoom_y + zoom_h - 1), outline=color, width=4)
            draw.text((x + 12, zoom_y + 10), "zoomed wrist view", font=small_font, fill=(255, 255, 255))

    return canvas


def main() -> None:
    figure = make_figure()
    figure.save(OUTPUT_PNG)
    figure.save(OUTPUT_PDF, resolution=300.0)
    print(f"Wrote {OUTPUT_PNG.relative_to(ROOT)}")
    print(f"Wrote {OUTPUT_PDF.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
