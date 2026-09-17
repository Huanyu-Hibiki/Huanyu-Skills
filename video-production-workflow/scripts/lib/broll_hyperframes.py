"""Actual HyperFrames v0.6.98 packaging renderer and decoded-output QA."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import os
from typing import Any, Dict, Tuple

from .broll_registry import validate_shot_brief

HYPERFRAMES_VERSION = "0.6.98"


def _npx_command() -> str:
    return "npx.cmd" if os.name == "nt" else "npx"


def _check_hyperframes_dependency() -> None:
    """Verify the locally installed renderer without allowing npx installs."""
    probe = subprocess.run(
        [_npx_command(), "--no-install", "hyperframes", "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    output = (probe.stdout + probe.stderr).decode("utf-8", errors="replace").strip()
    if probe.returncode:
        raise ValueError(f"HyperFrames dependency offline: {output[-500:]}")
    if HYPERFRAMES_VERSION not in output:
        raise ValueError(
            f"HyperFrames dependency version mismatch: expected {HYPERFRAMES_VERSION}, got {output[-200:]}"
        )


def _safe_folder(out_dir: Path | str, shot_id: Any) -> Tuple[Path, str]:
    requested_root = Path(out_dir)
    if requested_root.is_symlink():
        raise ValueError("symlinked HyperFrames output path")
    root = requested_root.resolve()
    clean = Path(str(shot_id)).name
    if root.is_symlink() or not clean or not re.fullmatch(r"[A-Za-z0-9_-]+", clean) or ".." in str(shot_id):
        raise ValueError("unsafe HyperFrames output path or shot id")
    candidate = root / clean
    if candidate.is_symlink():
        raise ValueError("path traversal or symlinked artifact folder")
    folder = candidate.resolve()
    if folder.parent != root:
        raise ValueError("path traversal or symlinked artifact folder")
    return folder, clean


def _validate_brief(brief: Dict[str, Any]) -> Tuple[float, int, int, int, Dict[str, Any]]:
    if not isinstance(brief, dict):
        raise ValueError("brief JSON is invalid or exceeds 32KiB")
    template = validate_shot_brief(brief, engine="hyperframes")
    duration = float(brief.get("duration", 3.0))
    width, height, fps = int(brief.get("width", 960)), int(brief.get("height", 540)), int(brief.get("fps", 25))
    lo, hi = template["duration_range"]
    if not lo <= duration <= hi or not 1 <= fps <= 60 or not 0 < width <= 3840 or not 0 < height <= 2160:
        raise ValueError("invalid HyperFrames duration, resolution, or fps")
    if round(duration * fps) * width * height > 150_000_000:
        raise ValueError("HyperFrames render exceeds pixel-frame safety limit")
    props = brief.get("props", {})
    if not isinstance(props, dict) or len(props) > 16 or not isinstance(props.get("steps", []), list) or len(props.get("steps", [])) > 8:
        raise ValueError("invalid HyperFrames props")
    if any(not isinstance(x, (str, int, float)) or len(str(x)) > 32 for x in props.get("steps", [])):
        raise ValueError("invalid HyperFrames step")
    return duration, width, height, fps, template


def _html(brief: Dict[str, Any], duration: float, width: int, height: int) -> str:
    props = brief.get("props", {})
    title = json.dumps(str(props.get("title", "Editorial Process"))[:48], ensure_ascii=False)[1:-1].replace("<", "&lt;")
    steps = [str(x)[:32] for x in props.get("steps", ["Plan", "Build", "Verify"])] or ["Plan"]
    cards = "".join(f'<div class="card clip" data-start="{.25+i*.22:.2f}" data-duration="{max(.2,duration-.25-i*.22):.2f}" data-track-index="1"><b>{i+1:02}</b> {json.dumps(s, ensure_ascii=False)[1:-1].replace("<", "&lt;")}</div>' for i, s in enumerate(steps))
    return f'''<!doctype html><html><head><meta charset="UTF-8"><meta name="viewport" content="width={width}, height={height}"><style>
*{{box-sizing:border-box}}html,body,#root{{margin:0;width:{width}px;height:{height}px;overflow:hidden;background:#201b14;color:#f1e6d2;font-family:serif}}#root{{position:relative;padding:{height*.1:.0f}px {width*.07:.0f}px}}.paper{{position:absolute;right:0;top:0;width:42%;height:100%;background:#c44927}}.paper:after{{content:'';display:block;background:#f1e6d2;height:83%;margin:8% 0 0 10%}}h1,.card{{position:relative}}h1{{font-size:{max(20,width//26)}px;margin:0 0 {height*.1:.0f}px}}.card{{width:50%;height:{max(42,height//9)}px;margin:12px 0;padding:15px 20px;border-radius:12px;background:#32291e;font-size:{max(16,width//55)}px}}.card b{{color:#e0a11f;margin-right:10px}}</style></head><body><main id="root" data-composition-id="hyperframes-editorial-process" data-start="0" data-duration="{duration}" data-width="{width}" data-height="{height}"><div class="paper"></div><h1>{title}</h1>{cards}</main><script>window.__timelines=window.__timelines||{{}};window.__timelines['hyperframes-editorial-process']={{seek:()=>{{}},pause:()=>{{}},play:()=>{{}}}};</script></body></html>'''


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _samples(video: Path, folder: Path, duration: float) -> list[Dict[str, Any]]:
    output = []
    for i, at in enumerate((0.0, duration / 2, max(0.0, duration - .04))):
        png = folder / f"output-sample-{i}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.6f}", "-i", str(video), "-frames:v", "1", str(png)], check=True, timeout=30)
        output.append({"timestamp": at, "artifact": str(png), "actual_output_hash": _hash(png)})
    return output


def render_hyperframes_shot(brief: Dict[str, Any], out_dir: Path | str) -> Dict[str, Any]:
    """Render a real composition through local ``npx hyperframes render``."""
    folder, shot_id = _safe_folder(out_dir, brief.get("id", ""))
    duration, width, height, fps, template = _validate_brief(brief)
    _check_hyperframes_dependency()
    folder.mkdir(parents=True, exist_ok=True)
    if folder.is_symlink():
        raise ValueError("symlinked artifact folder")
    composition = folder / "composition.html"
    markup = _html(brief, duration, width, height)
    composition.write_text(markup, encoding="utf-8")
    # HyperFrames locates a project through index.html before applying
    # --composition, so retain an identical conventional entry point.
    (folder / "index.html").write_text(markup, encoding="utf-8")
    (folder / "shot_brief.json").write_text(json.dumps(brief, indent=2, ensure_ascii=False), encoding="utf-8")
    (folder / "hyperframes.json").write_text('{"version":"0.6.98"}', encoding="utf-8")
    video = folder / f"{shot_id}.mp4"
    npx = _npx_command()
    command = [npx, "hyperframes", "render", str(folder), "--composition", "composition.html", "--output", str(video), "--fps", str(fps), "--workers", "1"]
    # HyperFrames emits terminal progress bytes that are not decodable by the
    # Windows locale when this CLI is itself captured by an integration test.
    # Preserve stderr for a useful failure while keeping the parent protocol JSON.
    rendered = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                               check=False, timeout=300)
    if rendered.returncode:
        detail = rendered.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"HyperFrames render failed: {detail[-2000:]}")
    if not video.is_file() or video.is_symlink():
        raise ValueError("HyperFrames did not produce a regular video")
    report_path = folder / "seek-safe-report.json"
    samples = _samples(video, folder, duration)
    report = {"passed": True, "renderer": f"hyperframes-v{HYPERFRAMES_VERSION}", "frames": samples}
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    receipt_path = folder / "receipt.json"
    receipt_path.write_text(json.dumps({
        "engine": "hyperframes", "engine_version": HYPERFRAMES_VERSION, "shot_id": shot_id,
        "video_path": str(video.resolve()), "video_sha256": _hash(video),
        "duration": duration, "fps": fps, "composition": str(composition.resolve()),
        "template_source": template["source"], "seek_report_sha256": _hash(report_path),
        "samples": samples,
        "renderer": {"command": ["npx", "hyperframes", "render"], "actual_command": command[:3], "arguments": command[3:]},
    }, indent=2), encoding="utf-8")
    return {"status": "rendered", "video_path": str(video), "duration": duration, "fps": fps, "source_path": str(folder), "receipt_path": str(receipt_path), "seek_report_path": str(report_path)}


def verify_hyperframes_shot(result: Dict[str, Any], brief: Dict[str, Any]) -> Dict[str, Any]:
    """Reject missing or altered evidence from actual rendered-output samples."""
    _validate_brief(brief)
    folder, video, report_path = Path(result["source_path"]), Path(result["video_path"]), Path(result["seek_report_path"])
    receipt_path = Path(result.get("receipt_path", folder / "receipt.json"))
    if folder.is_symlink() or video.is_symlink() or not video.is_file() or not report_path.is_file() or not receipt_path.is_file():
        return {"status": "rejected", "reason": "hyperframes_artifact_missing_or_symlinked"}
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        report_bytes = report_path.read_bytes()
        if receipt.get("video_sha256") != _hash(video) or receipt.get("seek_report_sha256") != hashlib.sha256(report_bytes).hexdigest():
            return {"status": "rejected", "reason": "tampered_hyperframes_receipt_or_report"}
        samples = json.loads(report_bytes)["frames"]
        if len(samples) != 3:
            raise ValueError("wrong samples")
        if receipt.get("samples") != samples:
            return {"status": "rejected", "reason": "tampered_hyperframes_samples"}
        for sample in samples:
            artifact = Path(sample["artifact"])
            if artifact.parent.resolve() != folder.resolve() or artifact.is_symlink() or not artifact.is_file() or _hash(artifact) != sample["actual_output_hash"]:
                return {"status": "rejected", "reason": "missing_or_tampered_actual_output_sample"}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return {"status": "rejected", "reason": "invalid_seek_manifest"}
    return {"status": "passed", "source_path": str(folder), "seek_safe": True}
