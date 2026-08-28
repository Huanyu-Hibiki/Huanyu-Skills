#!/usr/bin/env python3
"""Render full-frame B-roll cutaways while keeping the base audio track."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def resolve_asset_path(value: str, manifest_path: Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate.resolve()

    project_root = (
        manifest_path.parent.parent
        if manifest_path.parent.name == "Polished"
        else manifest_path.parent
    )
    candidates = [
        manifest_path.parent / candidate,
        project_root / candidate,
        Path.cwd() / candidate,
    ]
    for path in candidates:
        if path.exists():
            return path.resolve()
    return candidates[0].resolve()


def load_beats(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    beats = payload if isinstance(payload, list) else payload.get("beats", [])
    if not isinstance(beats, list) or not beats:
        raise SystemExit("manifest contains no beats")
    return beats


def render_cutaway(
    source: Path,
    output: Path,
    duration: float,
    width: int,
    height: int,
    fps: int,
    source_start: float,
    kind: str,
) -> None:
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1,fps={fps},format=yuv420p"
    )
    if kind == "still" or source.suffix.lower() in IMAGE_SUFFIXES:
        run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-loop",
                "1",
                "-t",
                f"{duration:.3f}",
                "-i",
                str(source),
                "-vf",
                vf,
                "-an",
                "-c:v",
                "libx264",
                "-crf",
                "18",
                "-preset",
                "fast",
                "-pix_fmt",
                "yuv420p",
                str(output),
            ]
        )
        return

    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-stream_loop",
            "-1",
            "-ss",
            f"{source_start:.3f}",
            "-t",
            f"{duration:.3f}",
            "-i",
            str(source),
            "-vf",
            vf,
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "fast",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render full-frame B-roll cutaways and preserve base audio"
    )
    parser.add_argument("base", type=Path, help="Base fine-cut video")
    parser.add_argument("output", type=Path, help="Output video")
    parser.add_argument("--beats", type=Path, required=True, help="JSON manifest with beats")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--end", type=float, default=None, help="Optional end time")
    args = parser.parse_args()

    base = args.base.resolve()
    manifest_path = args.beats.resolve()
    if not base.exists():
        raise SystemExit(f"base video not found: {base}")
    if not manifest_path.exists():
        raise SystemExit(f"manifest not found: {manifest_path}")

    duration = probe_duration(base)
    end_time = min(duration, args.end if args.end is not None else duration)
    if end_time <= 0:
        raise SystemExit("base video has no usable duration")

    beats = sorted(load_beats(manifest_path), key=lambda item: float(item["start"]))
    cursor = 0.0
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="video-polish-cutaways-") as temp_dir:
        temp_root = Path(temp_dir)
        inputs = ["-i", str(base)]
        filters: list[str] = []
        segments: list[str] = []

        for index, beat in enumerate(beats):
            start = float(beat["start"])
            beat_end = float(beat["end"])
            if start < 0 or beat_end <= start or beat_end > end_time or start < cursor:
                raise SystemExit(f"invalid or overlapping beat: {beat}")

            source = resolve_asset_path(str(beat["file"]), manifest_path)
            if not source.exists():
                raise SystemExit(f"B-roll file not found: {source}")

            if start > cursor:
                label = f"base{index}"
                filters.append(
                    f"[0:v]trim=start={cursor:.3f}:end={start:.3f},"
                    f"setpts=PTS-STARTPTS,{_video_filter(args.width, args.height, args.fps)}[{label}]"
                )
                segments.append(f"[{label}]")

            cutaway = temp_root / f"cutaway-{index:03d}.mp4"
            render_cutaway(
                source=source,
                output=cutaway,
                duration=beat_end - start,
                width=args.width,
                height=args.height,
                fps=args.fps,
                source_start=float(beat.get("source_start", beat.get("src_in", 0))),
                kind=str(beat.get("kind", "video")),
            )
            inputs.extend(["-i", str(cutaway)])
            cut_label = f"cut{index}"
            filters.append(f"[{index + 1}:v]setpts=PTS-STARTPTS[{cut_label}]")
            segments.append(f"[{cut_label}]")
            cursor = beat_end

        if cursor < end_time:
            label = f"base{len(beats)}"
            filters.append(
                f"[0:v]trim=start={cursor:.3f}:end={end_time:.3f},"
                f"setpts=PTS-STARTPTS,{_video_filter(args.width, args.height, args.fps)}[{label}]"
            )
            segments.append(f"[{label}]")

        filters.append("".join(segments) + f"concat=n={len(segments)}:v=1:a=0[v]")
        run(
            ["ffmpeg", "-y", "-v", "error"]
            + inputs
            + [
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[v]",
                "-map",
                "0:a?",
                "-t",
                f"{end_time:.3f}",
                "-c:v",
                "libx264",
                "-crf",
                "18",
                "-preset",
                "fast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                str(output),
            ]
        )

    print(json.dumps({"output": str(output), "beats": len(beats)}, ensure_ascii=False))
    return 0


def _video_filter(width: int, height: int, fps: int) -> str:
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1,fps={fps},format=yuv420p"
    )


if __name__ == "__main__":
    raise SystemExit(main())
