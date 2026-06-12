#!/usr/bin/env python3
"""Create a paper-ready qualitative result figure from rollout videos."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT / ".tmp_paper_figure_deps"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))
TOOLS = ROOT / ".tools"
if TOOLS.exists():
    sys.path.insert(0, str(TOOLS))

try:
    import imageio.v2 as imageio
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - developer-facing error path.
    raise SystemExit(
        "Missing dependencies. Install with:\n  python3 -m pip install pillow imageio imageio-ffmpeg"
    ) from exc


ROLLOUT_DIR = ROOT / "assets" / "rollouts_split"
OUTPUT_DIR = ROOT / "assets" / "results"
OUTPUT_PNG = OUTPUT_DIR / "main_result_figure.png"
OUTPUT_PDF = OUTPUT_DIR / "main_result_figure.pdf"

REAL_ROLLOUT = ("Real-world rollout", "roll1", (72, 143, 104))
ONLINE_ROLLOUT = ("Online world model", "roll3", (49, 95, 140))

POLICY_ROLLOUTS = [
    REAL_ROLLOUT,
    ONLINE_ROLLOUT,
]

TASKS = [
    {
        "label": "A",
        "title": "Pick up yellow cup and put it in bin",
        "prefix": "2026-04-01-211250Z-ur5e_single_4-c4e174b2581c__eval_17725__apr8_episode_buckets_120000__pick_up_yellow_cup_and_put_it_in_bin",
    },
    {
        "label": "D",
        "title": "Pick up foil tray and throw it away",
        "prefix": "2026-04-02-162712Z-ur5e_single_4-cbbb7d7452cd__eval_17725__apr8_full_large_run_5_100000_rtb__pick_up_foil_tray_and_throw_it_away",
    },
]

FRAME_FRACTIONS = (0.22, 0.52, 0.82)

PALETTE = {
    "background": (255, 255, 255),
    "panel": (248, 250, 252),
    "text": (28, 35, 45),
    "muted": (88, 98, 112),
    "border": (210, 216, 225),
    "grid": (226, 232, 240),
    "accent": (49, 95, 140),
    "accent_strong": (36, 71, 102),
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


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
    max_width: int,
    line_gap: int = 7,
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


def rollout_path(task: dict[str, str], suffix: str) -> Path:
    return ROLLOUT_DIR / f"{task['prefix']}_{suffix}.mp4"


def crop_wrist_camera(image: Image.Image) -> Image.Image:
    """Rollout videos concatenate three camera views horizontally."""
    width, height = image.size
    return image.crop((2 * width // 3, 0, width, height))


def cover_resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    scale = max(target_w / image.width, target_h / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def extract_frames(video_path: Path, size: tuple[int, int]) -> list[Image.Image]:
    if not video_path.exists():
        raise SystemExit(f"Missing rollout video: {video_path}")

    reader = imageio.get_reader(video_path, "ffmpeg")
    try:
        meta = reader.get_meta_data()
        fps = float(meta.get("fps") or 10)
        duration = float(meta.get("duration") or 20)
        frames = []
        for fraction in FRAME_FRACTIONS:
            frame_idx = max(0, round(duration * fraction * fps))
            frame = Image.fromarray(reader.get_data(frame_idx)).convert("RGB")
            frames.append(cover_resize(crop_wrist_camera(frame), size))
        return frames
    finally:
        reader.close()


def paste_with_border(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    image: Image.Image,
    xy: tuple[int, int],
    border: tuple[int, int, int],
) -> None:
    x, y = xy
    canvas.paste(image, (x, y))
    draw.rectangle((x, y, x + image.width - 1, y + image.height - 1), outline=border, width=3)


def make_figure() -> Image.Image:
    width = 2700
    height = 1120
    margin = 42
    title_h = 150
    col_gap = 30
    panel_pad = 28
    prompt_header_h = 96
    rollout_h = 356
    rollout_gap = 18
    frame_gap = 10

    grid_x = margin
    grid_y = margin + title_h
    prompt_w = (width - 2 * margin - col_gap) // 2
    panel_h = height - grid_y - margin
    frame_w = (prompt_w - 2 * panel_pad - 2 * frame_gap) // 3
    frame_h = 270

    canvas = Image.new("RGB", (width, height), PALETTE["background"])
    draw = ImageDraw.Draw(canvas)

    title_font = load_font(58, bold=True)
    subtitle_font = load_font(27)
    prompt_label_font = load_font(34, bold=True)
    prompt_font = load_font(27, bold=True)
    rollout_font = load_font(20, bold=True)
    tiny_font = load_font(17, bold=True)

    draw.text((margin, 36), "Qualitative results: online rollouts match real policy behavior", font=title_font, fill=PALETTE["text"])
    draw_wrapped_text(
        draw,
        (margin, 108),
        "Each column is a different prompt. Within a prompt, real-world and online world-model rollouts are stacked for early, middle, and late wrist-camera frames.",
        subtitle_font,
        PALETTE["muted"],
        width - 2 * margin,
        line_gap=5,
    )

    time_labels = ("early", "middle", "late")
    for prompt_idx, task in enumerate(TASKS):
        prompt_x = grid_x + prompt_idx * (prompt_w + col_gap)
        draw.rounded_rectangle(
            (prompt_x, grid_y, prompt_x + prompt_w, grid_y + panel_h),
            radius=26,
            fill=PALETTE["panel"],
            outline=PALETTE["border"],
            width=2,
        )
        draw.rounded_rectangle(
            (prompt_x + panel_pad, grid_y + 24, prompt_x + panel_pad + 44, grid_y + 68),
            radius=11,
            fill=PALETTE["accent"],
        )
        draw.text((prompt_x + panel_pad + 13, grid_y + 30), task["label"], font=prompt_label_font, fill=PALETTE["background"])
        draw_wrapped_text(
            draw,
            (prompt_x + panel_pad + 62, grid_y + 24),
            task["title"],
            prompt_font,
            PALETTE["text"],
            prompt_w - 2 * panel_pad - 70,
            line_gap=6,
        )

        content_x = prompt_x + panel_pad
        content_w = prompt_w - 2 * panel_pad
        rollout_y = grid_y + prompt_header_h + 24
        for rollout_idx, (rollout_label, suffix, color) in enumerate(POLICY_ROLLOUTS):
            sub_y = rollout_y + rollout_idx * (rollout_h + rollout_gap)
            sub_x = content_x
            frame_y = sub_y + 68
            draw.rounded_rectangle(
                (sub_x, sub_y, sub_x + content_w, sub_y + rollout_h),
                radius=18,
                fill=PALETTE["background"],
            )
            draw.text((sub_x + 18, sub_y + 16), rollout_label, font=rollout_font, fill=color)
            frames = extract_frames(rollout_path(task, suffix), (frame_w, frame_h))
            for frame_idx, frame in enumerate(frames):
                frame_x = sub_x + frame_idx * (frame_w + frame_gap)
                draw.text((frame_x + 4, frame_y - 10), time_labels[frame_idx], font=tiny_font, fill=color)
                paste_with_border(canvas, draw, frame, (frame_x, frame_y), color)

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
