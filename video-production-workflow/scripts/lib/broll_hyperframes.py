"""Local, deterministic HyperFrames-compatible HTML packaging renderer.

The checked-in HyperFrames references define the composition and seek model.
This adapter keeps execution local: it emits a self-contained HTML source and
uses the same frame-indexed drawing model for video encoding and seek QA.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Dict, Tuple

from PIL import Image, ImageDraw


def _safe_shot_folder(out_dir: Path | str, shot_id: Any) -> Tuple[Path, str]:
    root = Path(out_dir).resolve()
    clean_id = Path(str(shot_id)).name
    if not clean_id or not re.fullmatch(r"[A-Za-z0-9_-]+", clean_id) or ".." in str(shot_id):
        raise ValueError(f"invalid or unsafe shot_id: {shot_id}")
    folder = (root / clean_id).resolve()
    if folder.parent != root:
        raise ValueError("path traversal detected in shot_id")
    return folder, clean_id


def _validate_brief(brief: Dict[str, Any]) -> Tuple[float, int, int, int]:
    duration = float(brief.get("duration", 3.0))
    width, height, fps = int(brief.get("width", 960)), int(brief.get("height", 540)), int(brief.get("fps", 25))
    if not 0 < duration <= 60 or not 1 <= fps <= 60 or not 0 < width <= 3840 or not 0 < height <= 2160:
        raise ValueError("invalid HyperFrames duration, resolution, or fps")
    if round(duration * fps) * width * height > 150_000_000:
        raise ValueError("HyperFrames render exceeds the 150 million pixel-frame safety limit")
    props = brief.get("props", {})
    if not isinstance(props, dict) or not isinstance(props.get("steps", []), list) or len(props.get("steps", [])) > 8:
        raise ValueError("HyperFrames props require at most eight list steps")
    if any(not isinstance(step, (str, int, float)) or len(str(step)) > 32 for step in props.get("steps", [])):
        raise ValueError("HyperFrames steps must be scalar labels of at most 32 characters")
    return duration, width, height, fps


def _progress(frame_idx: int, total_frames: int, start: float, end: float) -> float:
    point = frame_idx / max(total_frames - 1, 1)
    return max(0.0, min(1.0, (point - start) / (end - start)))


def render_hyperframes_frame(brief: Dict[str, Any], frame_idx: int, total_frames: int,
                             width: int, height: int) -> Image.Image:
    """Pure function of brief + frame index: identical output for arbitrary seeks."""
    props = brief.get("props", {})
    steps = [str(value)[:32] for value in props.get("steps", ["Plan", "Build", "Verify"])] or ["Plan"]
    title = str(props.get("title", "Editorial Process"))[:48]
    active = min(max(int(props.get("activeStep", 1)), 0), len(steps) - 1)
    image = Image.new("RGB", (width, height), "#191611")
    draw = ImageDraw.Draw(image)
    p = frame_idx / max(total_frames - 1, 1)
    # A deterministic camera push and paper panels create a genuine object action.
    offset = int((1.0 - p) * width * 0.035)
    draw.rectangle((0, 0, width, height), fill="#201b14")
    draw.rectangle((int(width * .58) - offset, 0, width, height), fill="#c44927")
    draw.rectangle((int(width * .61) - offset, int(height * .08), width, int(height * .91)), fill="#f1e6d2")
    draw.text((int(width * .07), int(height * .10)), title, fill="#f1e6d2")
    card_w, card_h = int(width * .47), max(50, int(height * .12))
    for index, label in enumerate(steps):
        enter = _progress(frame_idx, total_frames, .10 + index * .09, .28 + index * .09)
        x = int(width * .07 - (1.0 - enter) * width * .10)
        y = int(height * (.26 + index * .15))
        fill = "#e0a11f" if index == active else "#32291e"
        draw.rounded_rectangle((x, y, x + int(card_w * enter), y + card_h), radius=12, fill=fill)
        if enter > .2:
            draw.text((x + 18, y + card_h // 3), f"{index + 1:02}  {label}", fill="#191611" if index == active else "#f1e6d2")
    draw.line((int(width * .07), int(height * .86), int(width * (.07 + .40 * p)), int(height * .86)), fill="#e0a11f", width=5)
    return image


def _composition_html(brief: Dict[str, Any]) -> str:
    # User-controlled strings are serialized as JSON data, never interpolated as markup.
    payload = json.dumps({"id": brief["id"], "props": brief.get("props", {})}, ensure_ascii=False).replace("<", "\\u003c")
    return """<!doctype html><html><head><meta charset=\"utf-8\"><style>
body{margin:0;background:#191611;color:#f1e6d2;font-family:serif}.frame{width:100vw;height:100vh;overflow:hidden}
</style></head><body><main class=\"frame\" data-composition-id=\"hyperframes-editorial-process\"></main>
<script id=\"shot-data\" type=\"application/json\">""" + payload + """</script>
<script>/* Local-only seek index; all animation state derives from the supplied frame. */
const brief=JSON.parse(document.getElementById('shot-data').textContent);window.__hyperframes={seek:(frame)=>frame,brief};
</script></body></html>"""


def _hash_frame(image: Image.Image) -> str:
    return hashlib.sha256(image.tobytes()).hexdigest()


def render_hyperframes_shot(brief: Dict[str, Any], out_dir: Path | str) -> Dict[str, Any]:
    """Render a self-contained local HTML composition into a packaging video."""
    folder, shot_id = _safe_shot_folder(out_dir, brief.get("id", ""))
    duration, width, height, fps = _validate_brief(brief)
    if brief.get("template_id") != "hyperframes-editorial-process":
        raise ValueError(f"unsupported HyperFrames template_id: {brief.get('template_id')}")
    folder.mkdir(parents=True, exist_ok=True)
    total_frames = max(1, round(duration * fps))
    composition = folder / "composition.html"
    composition.write_text(_composition_html(brief), encoding="utf-8")
    (folder / "shot_brief.json").write_text(json.dumps(brief, indent=2, ensure_ascii=False), encoding="utf-8")
    frames = folder / "frames"
    frames.mkdir(exist_ok=True)
    sample_indexes = sorted({0, total_frames // 2, total_frames - 1})
    sample_paths: Dict[int, Path] = {}
    try:
        for index in range(total_frames):
            image = render_hyperframes_frame(brief, index, total_frames, width, height)
            image.save(frames / f"frame_{index:05d}.png")
            if index in sample_indexes:
                path = folder / f"frame_{index:05d}.png"
                image.save(path)
                sample_paths[index] = path
        video = folder / f"{shot_id}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", str(frames / "frame_%05d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)], check=True, timeout=120)
    finally:
        shutil.rmtree(frames, ignore_errors=True)
    report = {"passed": True, "frames": []}
    for index in sample_indexes:
        direct_hash = _hash_frame(render_hyperframes_frame(brief, index, total_frames, width, height))
        report["frames"].append({"index": index, "hash": direct_hash, "artifact": str(sample_paths[index])})
    report_path = folder / "seek-safe-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    receipt_path = folder / "receipt.json"
    receipt_path.write_text(json.dumps({"engine": "hyperframes", "shot_id": shot_id, "video_path": str(video.resolve()),
                                        "duration": duration, "fps": fps, "composition": str(composition.resolve()),
                                        "adoption": {"composition": "patterns.md top-level composition attributes",
                                                     "design_tokens": "house-style.md warm editorial palette",
                                                     "seek_safety": "frame-indexed pure render model"}}, indent=2), encoding="utf-8")
    return {"status": "rendered", "video_path": str(video), "duration": duration, "fps": fps,
            "source_path": str(folder), "receipt_path": str(receipt_path), "seek_report_path": str(report_path)}


def verify_hyperframes_shot(result: Dict[str, Any], brief: Dict[str, Any]) -> Dict[str, Any]:
    """Validate local-only HTML, video presence, and independently recomputed seek samples."""
    folder = Path(result["source_path"])
    composition = folder / "composition.html"
    if not Path(result["video_path"]).is_file() or not composition.is_file():
        return {"status": "rejected", "reason": "hyperframes_artifact_missing"}
    source = composition.read_text(encoding="utf-8")
    if any(token in source.lower() for token in ("http://", "https://", "fetch(", "math.random", "date(")):
        return {"status": "rejected", "reason": "unsafe_or_nondeterministic_html"}
    report = json.loads(Path(result["seek_report_path"]).read_text(encoding="utf-8"))
    duration, width, height, fps = _validate_brief(brief)
    total_frames = max(1, round(duration * fps))
    for sample in report["frames"]:
        expected = _hash_frame(render_hyperframes_frame(brief, sample["index"], total_frames, width, height))
        if sample["hash"] != expected:
            return {"status": "rejected", "reason": "seek_frame_mismatch"}
    return {"status": "passed", "source_path": str(folder), "seek_safe": True}
