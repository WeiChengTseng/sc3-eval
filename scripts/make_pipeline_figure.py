#!/usr/bin/env python3
"""Create the project-page pipeline overview figure."""

from __future__ import annotations

import math
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


OUTPUT_PNG = ROOT / "assets" / "pipeline_v1.png"

PALETTE = {
    "background": (255, 255, 255),
    "paper": (248, 250, 252),
    "surface": (255, 255, 255),
    "surface_muted": (241, 237, 229),
    "text": (31, 41, 51),
    "muted": (93, 102, 115),
    "border": (210, 216, 225),
    "line": (111, 123, 138),
    "accent": (49, 95, 140),
    "accent_dark": (36, 71, 102),
    "accent_soft": (231, 240, 247),
    "green": (72, 143, 104),
    "green_soft": (231, 245, 236),
    "gold": (183, 121, 31),
    "gold_soft": (255, 246, 231),
    "blue_soft": (230, 242, 252),
    "red": (178, 64, 64),
    "red_soft": (255, 236, 236),
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


def text_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
    max_width: int,
    line_gap: int = 8,
    align: str = "left",
) -> int:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if text_size(draw, candidate, font)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    x, y = xy
    line_h = text_size(draw, "Ag", font)[1]
    for line in lines:
        line_w = text_size(draw, line, font)[0]
        line_x = x
        if align == "center":
            line_x = x + (max_width - line_w) // 2
        draw.text((line_x, y), line, font=font, fill=fill)
        y += line_h + line_gap
    return y


def centered_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> None:
    x0, y0, x1, y1 = box
    w, h = text_size(draw, text, font)
    draw.text((x0 + (x1 - x0 - w) / 2, y0 + (y1 - y0 - h) / 2), text, font=font, fill=fill)


def rounded_box(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int] = PALETTE["border"],
    width: int = 2,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int] = PALETTE["line"],
    width: int = 5,
    head_len: int = 24,
    head_w: int = 18,
) -> None:
    sx, sy = start
    ex, ey = end
    angle = math.atan2(ey - sy, ex - sx)
    line_end = (ex - head_len * math.cos(angle), ey - head_len * math.sin(angle))
    draw.line((start, line_end), fill=color, width=width)

    left = (
        ex - head_len * math.cos(angle) + head_w * math.sin(angle) / 2,
        ey - head_len * math.sin(angle) - head_w * math.cos(angle) / 2,
    )
    right = (
        ex - head_len * math.cos(angle) - head_w * math.sin(angle) / 2,
        ey - head_len * math.sin(angle) + head_w * math.cos(angle) / 2,
    )
    draw.polygon((end, left, right), fill=color)


def draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
    width: int = 4,
    dash: int = 16,
    gap: int = 12,
) -> None:
    sx, sy = start
    ex, ey = end
    length = math.hypot(ex - sx, ey - sy)
    if length == 0:
        return
    ux = (ex - sx) / length
    uy = (ey - sy) / length
    position = 0
    while position < length:
        dash_end = min(position + dash, length)
        draw.line(
            (
                sx + ux * position,
                sy + uy * position,
                sx + ux * dash_end,
                sy + uy * dash_end,
            ),
            fill=color,
            width=width,
        )
        position += dash + gap


def draw_panel_header(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    label: str,
    title: str,
    accent: tuple[int, int, int],
    label_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    title_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    x0, y0, _, _ = box
    badge = (x0 + 28, y0 + 26, x0 + 76, y0 + 74)
    draw.rounded_rectangle(badge, radius=13, fill=accent)
    centered_text(draw, badge, label, label_font, PALETTE["background"])
    draw.text((x0 + 94, y0 + 30), title, font=title_font, fill=PALETTE["text"])


def draw_input_panel(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont]) -> None:
    box = (70, 180, 560, 805)
    rounded_box(draw, box, 30, PALETTE["paper"])
    draw_panel_header(draw, box, "1", "Policy inputs", PALETTE["green"], fonts["badge"], fonts["section"])

    draw.text((110, 300), "Instruction", font=fonts["small_bold"], fill=PALETTE["text"])
    prompt_box = (110, 342, 520, 428)
    rounded_box(draw, prompt_box, 20, PALETTE["green_soft"], PALETTE["green"])
    draw_wrapped_text(
        draw,
        (136, 366),
        "pick up the cup and place it in the bin",
        fonts["body_bold"],
        PALETTE["text"],
        358,
        line_gap=4,
    )

    draw.text((110, 466), "Observation", font=fonts["small_bold"], fill=PALETTE["text"])
    camera_y = 510
    for idx, label in enumerate(("Cam 1", "Cam 2", "Cam 3")):
        x = 110 + idx * 136
        rounded_box(draw, (x, camera_y, x + 112, camera_y + 86), 18, PALETTE["surface"], PALETTE["green"], width=3)
        draw.rectangle((x + 18, camera_y + 17, x + 94, camera_y + 55), fill=PALETTE["green_soft"], outline=PALETTE["green"], width=2)
        centered_text(draw, (x, camera_y + 54, x + 112, camera_y + 86), label, fonts["tiny_bold"], PALETTE["accent_dark"])

    draw.text((110, 638), "Action chunk", font=fonts["small_bold"], fill=PALETTE["text"])
    for idx in range(5):
        x = 112 + idx * 72
        rounded_box(draw, (x, 682, x + 46, 728), 12, PALETTE["surface"], PALETTE["line"], width=3)
        draw.line((x + 12, 706, x + 34, 706), fill=PALETTE["line"], width=3)


def draw_model_panel(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont]) -> None:
    box = (780, 145, 1560, 845)
    rounded_box(draw, box, 34, PALETTE["accent_soft"], PALETTE["accent"], width=4)
    draw_panel_header(draw, box, "2", "UVA-Eval", PALETTE["accent"], fonts["badge"], fonts["section"])
    draw_wrapped_text(
        draw,
        (835, 254),
        "A pre-trained Unified Video Action model is fine-tuned as a closed-loop evaluator.",
        fonts["subtitle"],
        PALETTE["muted"],
        670,
        line_gap=7,
    )

    inner = (850, 345, 1490, 610)
    rounded_box(draw, inner, 28, PALETTE["surface"], PALETTE["accent"], width=3)
    centered_text(draw, (850, 372, 1490, 426), "Unified Video Action Model", fonts["model"], PALETTE["accent_dark"])
    draw_wrapped_text(
        draw,
        (900, 444),
        "jointly learns forward dynamics and inverse dynamics over synchronized camera views",
        fonts["body"],
        PALETTE["muted"],
        540,
        line_gap=6,
        align="center",
    )

    module_y = 670
    modules = [
        ("Forward\nrollout", PALETTE["blue_soft"], PALETTE["accent"]),
        ("Cross-view\nreference", PALETTE["green_soft"], PALETTE["green"]),
        ("Inverse\ndynamics", PALETTE["gold_soft"], PALETTE["gold"]),
    ]
    for idx, (label, fill, color) in enumerate(modules):
        x = 850 + idx * 218
        rounded_box(draw, (x, module_y, x + 190, module_y + 106), 22, fill, color, width=3)
        lines = label.split("\n")
        centered_text(draw, (x, module_y + 18, x + 190, module_y + 53), lines[0], fonts["body_bold"], color)
        centered_text(draw, (x, module_y + 52, x + 190, module_y + 88), lines[1], fonts["body_bold"], color)


def draw_rollout_panel(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont]) -> None:
    box = (1710, 120, 2330, 610)
    rounded_box(draw, box, 30, PALETTE["paper"])
    draw_panel_header(draw, box, "3", "Imagined rollout", PALETTE["accent"], fonts["badge"], fonts["section"])
    draw_wrapped_text(
        draw,
        (1752, 234),
        "The evaluator simulates policy execution and keeps camera views mutually consistent.",
        fonts["subtitle"],
        PALETTE["muted"],
        520,
        line_gap=7,
    )

    frame_w = 132
    frame_h = 112
    start_x = 1754
    y = 360
    colors = [PALETTE["green"], PALETTE["accent"], PALETTE["gold"], PALETTE["accent"]]
    for idx in range(4):
        x = start_x + idx * 138
        rounded_box(draw, (x, y, x + frame_w, y + frame_h), 18, PALETTE["surface"], colors[idx], width=3)
        draw.rectangle((x + 18, y + 20, x + frame_w - 18, y + frame_h - 36), fill=PALETTE["surface_muted"], outline=colors[idx], width=2)
        draw.ellipse((x + 54, y + 42, x + 78, y + 66), fill=colors[idx])
        centered_text(draw, (x, y + 72, x + frame_w, y + frame_h), f"t+{idx + 1}", fonts["tiny_bold"], colors[idx])
        if idx < 3:
            draw_arrow(draw, (x + frame_w + 8, y + frame_h // 2), (x + frame_w + 38, y + frame_h // 2), PALETTE["line"], width=3, head_len=12, head_w=10)


def draw_output_panel(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont]) -> None:
    box = (1710, 685, 2330, 980)
    rounded_box(draw, box, 30, PALETTE["paper"])
    draw_panel_header(draw, box, "4", "Evaluation signal", PALETTE["gold"], fonts["badge"], fonts["section"])

    uncertainty_box = (1750, 798, 1990, 930)
    rounded_box(draw, uncertainty_box, 22, PALETTE["gold_soft"], PALETTE["gold"], width=3)
    draw.text((1778, 820), "Uncertainty", font=fonts["body_bold"], fill=PALETTE["gold"])
    values = [0.18, 0.25, 0.36, 0.64, 0.78]
    for idx, value in enumerate(values):
        x = 1778 + idx * 34
        bar_h = int(value * 70)
        color = PALETTE["red"] if value > 0.6 else PALETTE["gold"]
        draw.rounded_rectangle((x, 902 - bar_h, x + 20, 902), radius=5, fill=color)
    draw_dashed_line(draw, (1772, 858), (1962, 858), PALETTE["red"], width=3, dash=10, gap=8)

    success_box = (2030, 798, 2290, 930)
    rounded_box(draw, success_box, 22, PALETTE["blue_soft"], PALETTE["accent"], width=3)
    draw.text((2058, 820), "Predicted success", font=fonts["body_bold"], fill=PALETTE["accent_dark"])
    chart = (2062, 862, 2268, 910)
    draw.line((chart[0], chart[3], chart[2], chart[3]), fill=PALETTE["border"], width=3)
    draw.line((chart[0], chart[1], chart[0], chart[3]), fill=PALETTE["border"], width=3)
    draw.line((chart[0], chart[3], chart[2], chart[1] + 8), fill=PALETTE["accent"], width=4)
    for idx, dot in enumerate((0.18, 0.32, 0.54, 0.82, 0.93)):
        x = chart[0] + 24 + idx * 39
        y = chart[3] - int(dot * 44)
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=PALETTE["accent"])


def draw_feedback(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont]) -> None:
    # Closed-loop feedback from generated observations into the next policy action.
    y = 895
    draw.line((1740, y, 1170, y), fill=PALETTE["green"], width=5)
    draw.line((1170, y, 1170, 820), fill=PALETTE["green"], width=5)
    draw_arrow(draw, (1170, 820), (1170, 790), PALETTE["green"], width=5, head_len=20, head_w=18)
    label_box = (1028, 870, 1534, 938)
    rounded_box(draw, label_box, 34, PALETTE["green_soft"], PALETTE["green"], width=3)
    centered_text(draw, label_box, "closed-loop interaction", fonts["body_bold"], PALETTE["green"])

    draw_dashed_line(draw, (1444, 668), (1790, 858), PALETTE["gold"], width=5, dash=18, gap=12)
    draw_arrow(draw, (1444, 668), (1790, 858), PALETTE["gold"], width=0, head_len=22, head_w=18)
    draw.text((1485, 760), "inverse-dynamics\nuncertainty", font=fonts["tiny_bold"], fill=PALETTE["gold"])


def make_figure() -> Image.Image:
    width = 2400
    height = 1050
    canvas = Image.new("RGB", (width, height), PALETTE["background"])
    draw = ImageDraw.Draw(canvas)

    fonts: dict[str, ImageFont.ImageFont] = {
        "title": load_font(58, bold=True),
        "subtitle": load_font(27),
        "section": load_font(34, bold=True),
        "model": load_font(42, bold=True),
        "badge": load_font(28, bold=True),
        "body": load_font(25),
        "body_bold": load_font(25, bold=True),
        "small_bold": load_font(22, bold=True),
        "tiny_bold": load_font(19, bold=True),
    }

    draw.text((70, 42), "UVA-Eval pipeline", font=fonts["title"], fill=PALETTE["text"])
    draw_wrapped_text(
        draw,
        (70, 112),
        "A generalist policy proposes action chunks; a fine-tuned Unified Video Action model simulates closed-loop rollouts and converts inverse-dynamics uncertainty into evaluator confidence.",
        fonts["subtitle"],
        PALETTE["muted"],
        1760,
        line_gap=6,
    )

    draw_input_panel(draw, fonts)
    draw_model_panel(draw, fonts)
    draw_rollout_panel(draw, fonts)
    draw_output_panel(draw, fonts)

    draw_arrow(draw, (560, 490), (780, 490), PALETTE["line"], width=6, head_len=28, head_w=22)
    draw_arrow(draw, (1560, 482), (1710, 405), PALETTE["line"], width=6, head_len=28, head_w=22)
    draw_arrow(draw, (2020, 610), (2020, 685), PALETTE["line"], width=6, head_len=24, head_w=20)
    draw_feedback(draw, fonts)

    footer = (70, 925, 710, 982)
    rounded_box(draw, footer, 28, PALETTE["accent_soft"], PALETTE["accent"], width=2)
    centered_text(draw, footer, "train once, evaluate many policies at scale", fonts["body_bold"], PALETTE["accent_dark"])
    return canvas


def main() -> None:
    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    figure = make_figure()
    figure.save(OUTPUT_PNG)
    print(f"Wrote {OUTPUT_PNG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
