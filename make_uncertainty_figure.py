#!/usr/bin/env python3
"""Generate a paper-ready uncertainty figure with sampled video frames."""

from __future__ import annotations

import base64
import html
import json
import math
import sys
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / ".tools"
if TOOLS.exists():
    sys.path.insert(0, str(TOOLS))

try:
    import imageio.v2 as imageio  # type: ignore[reportMissingImports]
    from PIL import Image  # type: ignore[reportMissingImports]
except ImportError as error:
    raise SystemExit(
        "Missing local plotting dependencies. Run:\n"
        "python3 -m pip install --target .tools imageio imageio-ffmpeg pillow"
    ) from error


OUT_DIR = ROOT / "assets" / "uncertainty"
SVG_PATH = OUT_DIR / "uncertainty_paper_figure.svg"
PDF_PATH = OUT_DIR / "uncertainty_paper_figure.pdf"


@dataclass(frozen=True)
class Rollout:
    title: str
    prompt: str
    status: str
    json_path: Path
    video_path: Path
    frame_chunks: tuple[int, ...]


ROLLOUT = Rollout(
    title="Uncertainty threshold exceedance in an imagined rollout",
    prompt="pick up blue bowl and put it in bin",
    status="Terminate interaction",
    json_path=OUT_DIR
    / "2026-04-02-084739Z-ur5e_single_4-5168577acfce__eval_17725__apr8_episode_buckets_120000__pick_up_blue_bowl_and_put_it_in_bin_bottomrow_uncertainty.json",
    video_path=OUT_DIR
    / "2026-04-02-084739Z-ur5e_single_4-5168577acfce__eval_17725__apr8_episode_buckets_120000__pick_up_blue_bowl_and_put_it_in_bin_bottomrow.mp4",
    frame_chunks=(1, 10),
)


COLORS = {
    "text": "#18212b",
    "muted": "#5b6673",
    "axis": "#8b98a7",
    "grid": "#d9e1e8",
    "panel": "#ffffff",
    "border": "#cfd8e2",
    "blue": "#2f6f9f",
    "blue_soft": "#dcecf7",
    "red": "#c94f4f",
    "red_soft": "#f7dddd",
}


WIDTH = 700
HEIGHT = 580
MARGIN_X = 0
PANEL_X = MARGIN_X
PANEL_Y = -15
PANEL_W = WIDTH - 2 * MARGIN_X
PANEL_H = 615

FRAME_X = PANEL_X + 28
FRAME_Y = PANEL_Y + 90
FRAME_W = 320
FRAME_H = 234
FRAME_GAP = (PANEL_W - len(ROLLOUT.frame_chunks) * FRAME_W) / (len(ROLLOUT.frame_chunks) - 1)
FRAME_X = PANEL_X

CHART_PAD_LEFT = 72
CHART_PAD_RIGHT = 38
CHART_X = PANEL_X + CHART_PAD_LEFT
CHART_Y = FRAME_Y + FRAME_H + 48
CHART_W = PANEL_W - CHART_PAD_LEFT - CHART_PAD_RIGHT
CHART_H = 130


def load_rollout() -> dict:
    with ROLLOUT.json_path.open() as fh:
        data = json.load(fh)
    values = [float(value) for value in data["uncertainty"]]
    threshold = float(data["threshold"])
    crossing = next((idx for idx, value in enumerate(values) if value >= threshold), None)
    return {
        "meta": ROLLOUT,
        "values": values,
        "threshold": threshold,
        "crossing": crossing,
        "frames": extract_frames(ROLLOUT.video_path, ROLLOUT.frame_chunks, len(values)),
    }


def extract_frames(video_path: Path, chunks: tuple[int, ...], n_chunks: int) -> list[dict]:
    reader = imageio.get_reader(video_path)
    try:
        meta = reader.get_meta_data()
        fps = float(meta.get("fps") or 10)
        duration = float(meta.get("duration") or n_chunks)
        frames = []
        for chunk in chunks:
            timestamp = duration * (chunk - 0.5) / n_chunks
            frame_index = max(0, int(round(timestamp * fps)))
            image = crop_third_person_view(Image.fromarray(reader.get_data(frame_index)).convert("RGB"))
            jpeg = encode_jpeg(image, width=900)
            frames.append({"chunk": chunk, "timestamp": timestamp, "jpeg": jpeg})
        return frames
    finally:
        reader.close()


def crop_third_person_view(image: Image.Image) -> Image.Image:
    """The rollout videos concatenate ext_0, ext_1, and wrist horizontally."""
    width, height = image.size
    return image.crop((round(width / 3), 0, round(width * 2 / 3), height))


def encode_jpeg(image: Image.Image, *, width: int) -> dict:
    scale = width / image.width
    resized = image.resize((width, round(image.height * scale)), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    resized.save(buffer, format="JPEG", quality=92, optimize=True)
    return {
        "bytes": buffer.getvalue(),
        "width": resized.width,
        "height": resized.height,
        "data_uri": "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii"),
    }


def nice_y_max(item: dict) -> float:
    max_value = max(max(visible_values(item)), item["threshold"])
    return max(0.04, math.ceil(max_value * 120) / 100)


def visible_values(item: dict) -> list[float]:
    crossing = item["crossing"]
    if crossing is None:
        return item["values"]
    return item["values"][: crossing + 1]


def x_scale(index: int, n_values: int) -> float:
    if n_values == 1:
        return CHART_X + CHART_W / 2
    return CHART_X + CHART_W * index / (n_values - 1)


def y_scale(value: float, y_max: float) -> float:
    return CHART_Y + CHART_H - CHART_H * value / y_max


def svg_text(
    x: float,
    y: float,
    text: str,
    *,
    size: int = 24,
    weight: str = "400",
    color: str = COLORS["text"],
    anchor: str = "start",
    transform: str | None = None,
) -> str:
    transform_attr = f' transform="{transform}"' if transform else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
        f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}"{transform_attr}>'
        f"{html.escape(text)}</text>"
    )


def draw_frame_strip_svg(item: dict) -> str:
    threshold = item["threshold"]
    values = item["values"]
    crossing = item["crossing"]
    parts = []
    for idx, frame in enumerate(item["frames"]):
        x = FRAME_X + idx * (FRAME_W + FRAME_GAP)
        chunk = frame["chunk"]
        is_above = values[chunk - 1] >= threshold
        stroke = COLORS["red"] if is_above else COLORS["blue"]
        if crossing is not None and chunk == crossing + 1:
            parts.extend(
                [
                    f'<rect x="{x:.1f}" y="{FRAME_Y - 43:.1f}" width="{FRAME_W:.1f}" height="34" rx="17" fill="{COLORS["red_soft"]}" />',
                    svg_text(x + FRAME_W / 2, FRAME_Y - 20, item["meta"].status, size=22, weight="700", color=COLORS["red"], anchor="middle"),
                ]
            )
        parts.extend(
            [
                f'<image href="{frame["jpeg"]["data_uri"]}" x="{x:.1f}" y="{FRAME_Y:.1f}" width="{FRAME_W:.1f}" height="{FRAME_H:.1f}" preserveAspectRatio="xMidYMid meet" />',
                f'<rect x="{x:.1f}" y="{FRAME_Y:.1f}" width="{FRAME_W:.1f}" height="{FRAME_H:.1f}" fill="none" stroke="{stroke}" stroke-width="3" />',
                svg_text(x + FRAME_W / 2, FRAME_Y + FRAME_H + 25, f"chunk {chunk}", size=21, weight="700", color=stroke, anchor="middle"),
            ]
        )
    return "\n".join(parts)


def draw_chart_svg(item: dict, y_max: float) -> str:
    values = visible_values(item)
    threshold = item["threshold"]
    crossing = item["crossing"]
    parts = []

    for tick in [0.00, 0.01, 0.02, 0.03, 0.04]:
        y = y_scale(tick, y_max)
        parts.append(
            f'<line x1="{CHART_X:.1f}" y1="{y:.1f}" x2="{CHART_X + CHART_W:.1f}" y2="{y:.1f}" stroke="{COLORS["grid"]}" stroke-width="1" />'
        )
        parts.append(svg_text(CHART_X - 13, y + 7, f"{tick:.2f}", size=20, color=COLORS["muted"], anchor="end"))

    parts.extend(
        [
            f'<line x1="{CHART_X:.1f}" y1="{CHART_Y:.1f}" x2="{CHART_X:.1f}" y2="{CHART_Y + CHART_H:.1f}" stroke="{COLORS["axis"]}" stroke-width="1.4" />',
            f'<line x1="{CHART_X:.1f}" y1="{CHART_Y + CHART_H:.1f}" x2="{CHART_X + CHART_W:.1f}" y2="{CHART_Y + CHART_H:.1f}" stroke="{COLORS["axis"]}" stroke-width="1.4" />',
        ]
    )

    if crossing is not None:
        x_cross = x_scale(crossing, len(values))
        parts.extend(
            [
                f'<line x1="{x_cross:.1f}" y1="{CHART_Y:.1f}" x2="{x_cross:.1f}" y2="{CHART_Y + CHART_H:.1f}" stroke="{COLORS["red"]}" stroke-width="1.6" stroke-dasharray="5 6" />',
                svg_text(x_cross - 8, CHART_Y + 25, f"first crossing: chunk {crossing + 1}", size=21, weight="700", color=COLORS["red"], anchor="end"),
            ]
        )

    threshold_y = y_scale(threshold, y_max)
    parts.extend(
        [
            f'<line x1="{CHART_X:.1f}" y1="{threshold_y:.1f}" x2="{CHART_X + CHART_W:.1f}" y2="{threshold_y:.1f}" stroke="{COLORS["red"]}" stroke-width="2" stroke-dasharray="8 8" />',
        ]
    )

    bar_w = max(13, CHART_W / len(values) * 0.42)
    highlighted_chunks = {frame["chunk"] for frame in item["frames"]}
    for idx, value in enumerate(values):
        if idx + 1 not in highlighted_chunks:
            continue
        x = x_scale(idx, len(values))
        y = y_scale(value, y_max)
        color = COLORS["red"] if value >= threshold else COLORS["blue"]
        parts.append(
            f'<rect x="{x - bar_w / 2:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{CHART_Y + CHART_H - y:.1f}" rx="4" fill="{color}" opacity="0.26" />'
        )

    points = " ".join(
        f"{x_scale(idx, len(values)):.1f},{y_scale(value, y_max):.1f}"
        for idx, value in enumerate(values)
    )
    parts.append(f'<polyline points="{points}" fill="none" stroke="{COLORS["blue"]}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />')
    for idx, value in enumerate(values):
        x = x_scale(idx, len(values))
        y = y_scale(value, y_max)
        fill = COLORS["red"] if value >= threshold else COLORS["blue"]
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="{fill}" stroke="#ffffff" stroke-width="2" />')

    for idx in (0, 4, len(values) - 1):
        parts.append(svg_text(x_scale(idx, len(values)), CHART_Y + CHART_H + 25, str(idx + 1), size=20, color=COLORS["muted"], anchor="middle"))

    parts.extend(
        [
            svg_text(CHART_X + CHART_W / 2, CHART_Y + CHART_H + 57, "Rollout chunk", size=24, weight="700", color=COLORS["muted"], anchor="middle"),
            svg_text(CHART_X - 52, CHART_Y + CHART_H / 2, "Uncertainty", size=24, weight="700", color=COLORS["muted"], anchor="middle", transform=f"rotate(-90 {CHART_X - 52:.1f} {CHART_Y + CHART_H / 2:.1f})"),
        ]
    )
    return "\n".join(parts)


def make_svg(item: dict, y_max: float) -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="Inverse-dynamics uncertainty thresholding with sampled video frames">',
        '<style>text{font-family:"Times New Roman",Times,serif}</style>',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#ffffff" />',
        svg_text(PANEL_X + 28, PANEL_Y + 42, f'Prompt: "{item["meta"].prompt}"', size=28, weight="700", color=COLORS["text"]),
        draw_frame_strip_svg(item),
        draw_chart_svg(item, y_max),
    ]

    legend_y = PANEL_Y + PANEL_H - 37
    legend_x = WIDTH / 2 - 325
    parts.extend(
        [
            f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x + 50}" y2="{legend_y}" stroke="{COLORS["blue"]}" stroke-width="4" />',
            f'<circle cx="{legend_x + 25}" cy="{legend_y}" r="6" fill="{COLORS["blue"]}" stroke="#ffffff" stroke-width="2" />',
            svg_text(legend_x + 62, legend_y + 7, "UVA uncertainty", size=22, color=COLORS["muted"]),
            f'<line x1="{legend_x + 220}" y1="{legend_y}" x2="{legend_x + 270}" y2="{legend_y}" stroke="{COLORS["red"]}" stroke-width="2.5" stroke-dasharray="8 8" />',
            svg_text(legend_x + 282, legend_y + 7, "termination threshold", size=22, color=COLORS["muted"]),
            f'<circle cx="{legend_x + 504}" cy="{legend_y}" r="7" fill="{COLORS["red"]}" stroke="#ffffff" stroke-width="2" />',
            svg_text(legend_x + 521, legend_y + 7, "above threshold", size=22, color=COLORS["muted"]),
        ]
    )
    parts.append("</svg>")
    return "\n".join(parts)


def hex_to_rgb(color: str) -> tuple[float, float, float]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) / 255 for i in (0, 2, 4))


class PdfCanvas:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.ops: list[str] = []
        self.images: list[dict] = []

    def _y(self, y: float) -> float:
        return self.height - y

    def set_stroke(self, color: str) -> None:
        r, g, b = hex_to_rgb(color)
        self.ops.append(f"{r:.4f} {g:.4f} {b:.4f} RG")

    def set_fill(self, color: str) -> None:
        r, g, b = hex_to_rgb(color)
        self.ops.append(f"{r:.4f} {g:.4f} {b:.4f} rg")

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str, width: float = 1, dash: str | None = None) -> None:
        self.set_stroke(color)
        self.ops.append(f"{width:.2f} w")
        self.ops.append(f"[{dash}] 0 d" if dash else "[] 0 d")
        self.ops.append(f"{x1:.2f} {self._y(y1):.2f} m {x2:.2f} {self._y(y2):.2f} l S")
        self.ops.append("[] 0 d")

    def rect(self, x: float, y: float, w: float, h: float, fill: str | None, stroke: str | None = None, stroke_width: float = 1) -> None:
        if fill:
            self.set_fill(fill)
            self.ops.append(f"{x:.2f} {self._y(y + h):.2f} {w:.2f} {h:.2f} re f")
        if stroke:
            self.set_stroke(stroke)
            self.ops.append(f"{stroke_width:.2f} w")
            self.ops.append(f"{x:.2f} {self._y(y + h):.2f} {w:.2f} {h:.2f} re S")

    def circle(self, x: float, y: float, r: float, fill: str, stroke: str | None = None, stroke_width: float = 1) -> None:
        c = 0.5522847498 * r
        y_pdf = self._y(y)
        self.set_fill(fill)
        path = (
            f"{x + r:.2f} {y_pdf:.2f} m "
            f"{x + r:.2f} {y_pdf + c:.2f} {x + c:.2f} {y_pdf + r:.2f} {x:.2f} {y_pdf + r:.2f} c "
            f"{x - c:.2f} {y_pdf + r:.2f} {x - r:.2f} {y_pdf + c:.2f} {x - r:.2f} {y_pdf:.2f} c "
            f"{x - r:.2f} {y_pdf - c:.2f} {x - c:.2f} {y_pdf - r:.2f} {x:.2f} {y_pdf - r:.2f} c "
            f"{x + c:.2f} {y_pdf - r:.2f} {x + r:.2f} {y_pdf - c:.2f} {x + r:.2f} {y_pdf:.2f} c"
        )
        self.ops.append(f"{path} f")
        if stroke:
            self.set_stroke(stroke)
            self.ops.append(f"{stroke_width:.2f} w")
            self.ops.append(f"{path} S")

    def polyline(self, points: list[tuple[float, float]], color: str, width: float = 2) -> None:
        if len(points) < 2:
            return
        self.set_stroke(color)
        self.ops.append(f"{width:.2f} w")
        self.ops.append("1 J 1 j")
        start = points[0]
        commands = [f"{start[0]:.2f} {self._y(start[1]):.2f} m"]
        commands.extend(f"{x:.2f} {self._y(y):.2f} l" for x, y in points[1:])
        commands.append("S")
        self.ops.append(" ".join(commands))

    def text(
        self,
        x: float,
        y: float,
        text: str,
        *,
        size: int = 12,
        color: str = COLORS["text"],
        bold: bool = False,
        align: str = "left",
    ) -> None:
        self.set_fill(color)
        font = "F2" if bold else "F1"
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        approx_width = len(text) * size * 0.48
        if align == "center":
            x -= approx_width / 2
        elif align == "right":
            x -= approx_width
        self.ops.append(f"BT /{font} {size} Tf {x:.2f} {self._y(y):.2f} Td ({escaped}) Tj ET")

    def image(self, x: float, y: float, w: float, h: float, jpeg: dict) -> None:
        name = f"Im{len(self.images) + 1}"
        self.images.append({"name": name, **jpeg})
        self.ops.append(f"q {w:.2f} 0 0 {h:.2f} {x:.2f} {self._y(y + h):.2f} cm /{name} Do Q")

    def save(self, path: Path) -> None:
        stream = "\n".join(self.ops).encode("latin-1")
        xobjects = " ".join(f"/{image['name']} {7 + idx} 0 R" for idx, image in enumerate(self.images))
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width} {self.height}] "
                f"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> /XObject << {xobjects} >> >> "
                f"/Contents 6 0 R >>"
            ).encode("latin-1"),
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold >>",
            b"<< /Length " + str(len(stream)).encode("latin-1") + b" >>\nstream\n" + stream + b"\nendstream",
        ]
        for image in self.images:
            data = image["bytes"]
            objects.append(
                (
                    f"<< /Type /XObject /Subtype /Image /Width {image['width']} /Height {image['height']} "
                    f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(data)} >>\n"
                    "stream\n"
                ).encode("latin-1")
                + data
                + b"\nendstream"
            )

        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for idx, obj in enumerate(objects, start=1):
            offsets.append(len(output))
            output.extend(f"{idx} 0 obj\n".encode("latin-1"))
            output.extend(obj)
            output.extend(b"\nendobj\n")
        xref = len(output)
        output.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
        output.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            output.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
        output.extend(
            (
                f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref}\n%%EOF\n"
            ).encode("latin-1")
        )
        path.write_bytes(output)


def draw_frame_strip_pdf(canvas: PdfCanvas, item: dict) -> None:
    values = item["values"]
    threshold = item["threshold"]
    crossing = item["crossing"]
    for idx, frame in enumerate(item["frames"]):
        x = FRAME_X + idx * (FRAME_W + FRAME_GAP)
        chunk = frame["chunk"]
        is_above = values[chunk - 1] >= threshold
        stroke = COLORS["red"] if is_above else COLORS["blue"]
        if crossing is not None and chunk == crossing + 1:
            canvas.rect(x, FRAME_Y - 43, FRAME_W, 34, COLORS["red_soft"])
            canvas.text(x + FRAME_W / 2, FRAME_Y - 20, item["meta"].status, size=22, color=COLORS["red"], bold=True, align="center")
        canvas.image(x, FRAME_Y, FRAME_W, FRAME_H, frame["jpeg"])
        canvas.rect(x, FRAME_Y, FRAME_W, FRAME_H, None, stroke, 3)
        canvas.text(x + FRAME_W / 2, FRAME_Y + FRAME_H + 25, f"chunk {chunk}", size=21, color=stroke, bold=True, align="center")


def draw_chart_pdf(canvas: PdfCanvas, item: dict, y_max: float) -> None:
    values = visible_values(item)
    threshold = item["threshold"]
    crossing = item["crossing"]
    for tick in [0.00, 0.01, 0.02, 0.03, 0.04]:
        y = y_scale(tick, y_max)
        canvas.line(CHART_X, y, CHART_X + CHART_W, y, COLORS["grid"], 1)
        canvas.text(CHART_X - 13, y + 7, f"{tick:.2f}", size=20, color=COLORS["muted"], align="right")
    canvas.line(CHART_X, CHART_Y, CHART_X, CHART_Y + CHART_H, COLORS["axis"], 1.4)
    canvas.line(CHART_X, CHART_Y + CHART_H, CHART_X + CHART_W, CHART_Y + CHART_H, COLORS["axis"], 1.4)

    if crossing is not None:
        x_cross = x_scale(crossing, len(values))
        canvas.line(x_cross, CHART_Y, x_cross, CHART_Y + CHART_H, COLORS["red"], 1.6, dash="5 6")
        canvas.text(x_cross - 8, CHART_Y + 25, f"first crossing: chunk {crossing + 1}", size=21, color=COLORS["red"], bold=True, align="right")

    threshold_y = y_scale(threshold, y_max)
    canvas.line(CHART_X, threshold_y, CHART_X + CHART_W, threshold_y, COLORS["red"], 2, dash="8 8")

    bar_w = max(13, CHART_W / len(values) * 0.42)
    highlighted_chunks = {frame["chunk"] for frame in item["frames"]}
    for idx, value in enumerate(values):
        if idx + 1 not in highlighted_chunks:
            continue
        x = x_scale(idx, len(values))
        y = y_scale(value, y_max)
        color = COLORS["red"] if value >= threshold else COLORS["blue"]
        canvas.rect(x - bar_w / 2, y, bar_w, CHART_Y + CHART_H - y, color)

    points = [(x_scale(idx, len(values)), y_scale(value, y_max)) for idx, value in enumerate(values)]
    canvas.polyline(points, COLORS["blue"], 4)
    for idx, value in enumerate(values):
        x, y = points[idx]
        fill = COLORS["red"] if value >= threshold else COLORS["blue"]
        canvas.circle(x, y, 6.5, fill, "#ffffff", 2)

    for idx in (0, 4, len(values) - 1):
        canvas.text(x_scale(idx, len(values)), CHART_Y + CHART_H + 25, str(idx + 1), size=20, color=COLORS["muted"], align="center")
    canvas.text(CHART_X + CHART_W / 2, CHART_Y + CHART_H + 57, "Rollout chunk", size=24, color=COLORS["muted"], bold=True, align="center")
    canvas.text(CHART_X - 62, CHART_Y + CHART_H / 2, "Uncertainty", size=24, color=COLORS["muted"], bold=True)


def make_pdf(item: dict, y_max: float) -> PdfCanvas:
    canvas = PdfCanvas(WIDTH, HEIGHT)
    canvas.rect(0, 0, WIDTH, HEIGHT, "#ffffff")
    canvas.text(PANEL_X + 28, PANEL_Y + 42, f'Prompt: "{item["meta"].prompt}"', size=28, color=COLORS["text"], bold=True)
    draw_frame_strip_pdf(canvas, item)
    draw_chart_pdf(canvas, item, y_max)

    legend_y = PANEL_Y + PANEL_H - 37
    legend_x = WIDTH / 2 - 325
    canvas.line(legend_x, legend_y, legend_x + 50, legend_y, COLORS["blue"], 4)
    canvas.circle(legend_x + 25, legend_y, 6, COLORS["blue"], "#ffffff", 2)
    canvas.text(legend_x + 62, legend_y + 7, "UVA uncertainty", size=22, color=COLORS["muted"])
    canvas.line(legend_x + 220, legend_y, legend_x + 270, legend_y, COLORS["red"], 2.5, dash="8 8")
    canvas.text(legend_x + 282, legend_y + 7, "termination threshold", size=22, color=COLORS["muted"])
    canvas.circle(legend_x + 504, legend_y, 7, COLORS["red"], "#ffffff", 2)
    canvas.text(legend_x + 521, legend_y + 7, "above threshold", size=22, color=COLORS["muted"])
    return canvas


def main() -> None:
    item = load_rollout()
    y_max = nice_y_max(item)
    SVG_PATH.write_text(make_svg(item, y_max), encoding="utf-8")
    make_pdf(item, y_max).save(PDF_PATH)
    print(f"Wrote {SVG_PATH.relative_to(ROOT)}")
    print(f"Wrote {PDF_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
