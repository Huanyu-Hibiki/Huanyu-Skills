#!/usr/bin/env python3
"""Normalize one media asset and append its provenance to the project manifest."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import date
from pathlib import Path


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize and register a media asset")
    parser.add_argument("input", type=Path)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--type", choices=["music", "sfx", "stock-video", "stock-image", "raw"], required=True)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--source-site", default="user-provided")
    parser.add_argument("--source-url", default="")
    parser.add_argument("--title", default="")
    parser.add_argument("--creator", default="")
    parser.add_argument("--license", dest="license_name", default="user-provided")
    parser.add_argument("--commercial-use", action="store_true")
    parser.add_argument("--attribution-required", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    source = args.input.resolve()
    if not source.exists():
        raise SystemExit(f"asset not found: {source}")
    project = args.project.resolve()
    assets = project / "assets"
    if args.output:
        target = args.output.resolve()
    elif args.type == "music":
        target = assets / "audio" / "music" / f"{args.asset_id}_{source.stem}.wav"
    elif args.type == "sfx":
        target = assets / "audio" / "sfx" / f"{args.asset_id}_{source.stem}.wav"
    elif args.type == "stock-video":
        target = assets / "video" / "stock" / f"{args.asset_id}_{source.stem}.mp4"
    elif args.type == "stock-image":
        target = assets / "image" / "stock" / f"{args.asset_id}_{source.name}"
    else:
        target = assets / "raw" / source.parent.name / source.name

    target.parent.mkdir(parents=True, exist_ok=True)
    if args.type in {"music", "sfx"}:
        run(["ffmpeg", "-y", "-i", str(source), "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(target)])
    elif args.type == "stock-video":
        run(["ffmpeg", "-y", "-i", str(source), "-vf", "fps=30,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(target)])
    else:
        shutil.copy2(source, target)

    manifest_path = assets / "licenses" / "media_asset_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"assets": []}
    manifest.setdefault("assets", []).append({
        "asset_id": args.asset_id,
        "path": str(target.relative_to(project)).replace("\\", "/"),
        "source_site": args.source_site,
        "source_url": args.source_url,
        "title": args.title or source.name,
        "creator": args.creator,
        "license": args.license_name,
        "commercial_use_allowed": args.commercial_use,
        "attribution_required": args.attribution_required,
        "download_date": str(date.today()),
    })
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(target), "manifest": str(manifest_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
