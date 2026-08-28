#!/usr/bin/env python3
"""Compose full-frame B-roll cutaways over a fine-cut video."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Compose B-roll cutaways over a fine-cut video")
    parser.add_argument("base", type=Path)
    parser.add_argument("manifest", type=Path, help="JSON manifest with beats")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()

    base = args.base.resolve()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    beats = manifest if isinstance(manifest, list) else manifest.get("beats", [])
    if not beats:
        raise SystemExit("manifest contains no beats")

    duration = probe_duration(base)
    vf = f"scale={args.width}:{args.height}:force_original_aspect_ratio=increase,crop={args.width}:{args.height},setsar=1,fps={args.fps}"
    inputs: list[str] = ["-i", str(base)]
    filters: list[str] = []
    segments: list[str] = []
    cursor = 0.0

    for index, beat in enumerate(sorted(beats, key=lambda item: float(item["start"]))):
        start = float(beat["start"])
        end = min(duration, float(beat["end"]))
        source = resolve_asset_path(beat["file"], manifest_path)
        if not source.exists():
            raise SystemExit(f"B-roll file not found: {source}")
        if start < 0 or start >= duration or start < cursor or end <= start:
            raise SystemExit(f"invalid or overlapping beat: {beat}")
        if start > cursor:
            filters.append(f"[0:v]trim=start={cursor}:end={start},setpts=PTS-STARTPTS,{vf}[base{index}]")
            segments.append(f"[base{index}]")
        inputs.extend(["-i", str(source)])
        input_index = index + 1
        filters.append(f"[{input_index}:v]trim=duration={end - start},setpts=PTS-STARTPTS,{vf}[cut{index}]")
        segments.append(f"[cut{index}]")
        cursor = end

    if cursor < duration:
        index = len(beats)
        filters.append(f"[0:v]trim=start={cursor}:end={duration},setpts=PTS-STARTPTS,{vf}[base{index}]")
        segments.append(f"[base{index}]")

    filters.append("".join(segments) + f"concat=n={len(segments)}:v=1:a=0[v]")
    args.output.parent.mkdir(parents=True, exist_ok=True)
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
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(args.output),
        ]
    )
    print(json.dumps({"output": str(args.output), "beats": len(beats)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
