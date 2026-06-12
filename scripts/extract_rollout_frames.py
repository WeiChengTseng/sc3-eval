#!/usr/bin/env python3
"""Extract every rollout video frame and split each frame into camera views."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for local_deps in (ROOT / ".tools", ROOT / ".tmp_paper_figure_deps"):
    if local_deps.exists():
        sys.path.insert(0, str(local_deps))

try:
    import imageio.v2 as imageio
    from PIL import Image
except ImportError as exc:  # pragma: no cover - developer-facing error path.
    raise SystemExit(
        "Missing dependencies. Install with:\n"
        "  python3 -m pip install pillow imageio imageio-ffmpeg"
    ) from exc


VIEW_NAMES = ("ext_0", "ext_1", "wrist")


def view_bounds(width: int) -> list[tuple[int, int]]:
    """Rollout videos concatenate ext_0, ext_1, and wrist horizontally."""
    boundaries = [round(width * idx / len(VIEW_NAMES)) for idx in range(len(VIEW_NAMES) + 1)]
    return list(zip(boundaries[:-1], boundaries[1:]))


def save_image(image: Image.Image, path: Path, image_format: str, quality: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if image_format == "jpg":
        image.save(path, quality=quality, optimize=True)
    else:
        image.save(path)


def extract_video(video_path: Path, output_dir: Path, image_format: str, quality: int, save_full: bool) -> int:
    video_output_dir = output_dir / video_path.stem
    suffix = "jpg" if image_format == "jpg" else "png"
    reader = imageio.get_reader(video_path, "ffmpeg")

    frame_count = 0
    try:
        for frame_idx, frame_array in enumerate(reader):
            frame = Image.fromarray(frame_array).convert("RGB")
            frame_name = f"frame_{frame_idx:06d}.{suffix}"

            if save_full:
                save_image(frame, video_output_dir / "full" / frame_name, image_format, quality)

            for view_name, (left, right) in zip(VIEW_NAMES, view_bounds(frame.width)):
                view = frame.crop((left, 0, right, frame.height))
                save_image(view, video_output_dir / "views" / view_name / frame_name, image_format, quality)

            frame_count += 1
    finally:
        reader.close()

    return frame_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=ROOT / "assets" / "rollouts_split",
        help="Directory containing rollout .mp4 files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "assets" / "rollouts_split_frames",
        help="Directory where extracted frames will be written.",
    )
    parser.add_argument(
        "--image-format",
        choices=("png", "jpg"),
        default="png",
        help="Image format for extracted frames.",
    )
    parser.add_argument("--jpg-quality", type=int, default=95, help="JPEG quality when --image-format=jpg.")
    parser.add_argument(
        "--views-only",
        action="store_true",
        help="Only save per-view crops; skip full concatenated frames.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    video_paths = sorted(args.input_dir.glob("*.mp4"))
    if not video_paths:
        raise SystemExit(f"No .mp4 files found in {args.input_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    total_frames = 0
    for video_path in video_paths:
        frame_count = extract_video(
            video_path=video_path,
            output_dir=args.output_dir,
            image_format=args.image_format,
            quality=args.jpg_quality,
            save_full=not args.views_only,
        )
        total_frames += frame_count
        print(f"{video_path.name}: {frame_count} frames")

    print(f"Done: {len(video_paths)} videos, {total_frames} frames, output={args.output_dir}")


if __name__ == "__main__":
    main()
