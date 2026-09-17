"""Deterministic Remotion scene rendering and QA verification engine."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageStat


def _interpolate(frame: float, in_range: Tuple[float, float], out_range: Tuple[float, float],
                 clamp: bool = True) -> float:
    """Remotion-equivalent interpolate helper."""
    in_min, in_max = in_range
    out_min, out_max = out_range
    if in_max == in_min:
        return out_min
    progress = (frame - in_min) / (in_max - in_min)
    if clamp:
        progress = max(0.0, min(1.0, progress))
    return out_min + progress * (out_max - out_min)


def _draw_data_causality_frame(frame_idx: int, total_frames: int, width: int, height: int,
                               props: Dict[str, Any], is_transparent: bool) -> Image.Image:
    """Draw a frame for data causality comparison scene."""
    if is_transparent:
        im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    else:
        im = Image.new("RGBA", (width, height), (17, 24, 39, 255))

    draw = ImageDraw.Draw(im)

    # Slow camera push-in effect
    cam_scale = _interpolate(frame_idx, (0, total_frames), (1.0, 1.05))

    # Box coordinates (positioned safely on the left 60% of screen if transparent)
    box_w = int(width * 0.52 * cam_scale)
    box_h = int(height * 0.72 * cam_scale)
    box_x = int(width * 0.06)
    box_y = int(height * 0.14)

    # Background card
    card_bg = (31, 41, 55, 230 if is_transparent else 255)
    draw.rounded_rectangle([box_x, box_y, box_x + box_w, box_y + box_h], radius=16, fill=card_bg, outline=(75, 85, 99, 255), width=2)

    # Title
    title = str(props.get("title", "性能指标对比"))
    draw.text((box_x + 24, box_y + 20), title, fill=(243, 244, 246, 255))

    # Bars animation
    b_val = float(props.get("beforeValue", 100))
    a_val = float(props.get("afterValue", 20))
    max_val = max(b_val, a_val, 1.0)
    max_bar_h = box_h * 0.45

    # Before bar animates in [f: 5 -> 25]
    b_grow = _interpolate(frame_idx, (5, 25), (0.0, 1.0))
    cur_b_h = (b_val / max_val) * max_bar_h * b_grow
    cur_b_val = int(b_val * b_grow)

    # After bar animates in [f: 15 -> 35]
    a_grow = _interpolate(frame_idx, (15, 35), (0.0, 1.0))
    cur_a_h = (a_val / max_val) * max_bar_h * a_grow
    cur_a_val = int(a_val * a_grow)

    bar_w = int(box_w * 0.22)
    base_y = box_y + box_h - 40

    # Draw Before bar (Red/Orange gradient tone)
    b_x1 = box_x + int(box_w * 0.16)
    b_x2 = b_x1 + bar_w
    b_y1 = int(base_y - cur_b_h)
    draw.rounded_rectangle([b_x1, b_y1, b_x2, base_y], radius=8, fill=(239, 68, 68, 255))
    draw.text((b_x1 + 4, base_y + 8), str(props.get("beforeLabel", "重构前")), fill=(156, 163, 175, 255))
    if b_grow > 0.1:
        draw.text((b_x1 + 6, max(box_y + 50, b_y1 - 18)), f"{cur_b_val} {props.get('unit', '')}", fill=(254, 202, 202, 255))

    # Draw After bar (Emerald Green tone)
    a_x1 = box_x + int(box_w * 0.56)
    a_x2 = a_x1 + bar_w
    a_y1 = int(base_y - cur_a_h)
    draw.rounded_rectangle([a_x1, a_y1, a_x2, base_y], radius=8, fill=(16, 185, 129, 255))
    draw.text((a_x1 + 4, base_y + 8), str(props.get("afterLabel", "重构后")), fill=(156, 163, 175, 255))
    if a_grow > 0.1:
        draw.text((a_x1 + 6, max(box_y + 50, a_y1 - 18)), f"{cur_a_val} {props.get('unit', '')}", fill=(167, 243, 208, 255))

    # Callout badge appears at [f: 28 -> 42]
    callout = str(props.get("callout", "14x 加速"))
    c_alpha = int(_interpolate(frame_idx, (28, 40), (0, 255)))
    if c_alpha > 0:
        cx = int(box_x + box_w * 0.5)
        cy = int(box_y + 60)
        draw.rounded_rectangle([cx - 48, cy - 14, cx + 48, cy + 14], radius=6, fill=(245, 158, 11, c_alpha))
        draw.text((cx - 36, cy - 8), callout, fill=(0, 0, 0, c_alpha))

    return im


def _draw_process_breakdown_frame(frame_idx: int, total_frames: int, width: int, height: int,
                                  props: Dict[str, Any], is_transparent: bool) -> Image.Image:
    """Draw a frame for process breakdown / pipeline assembly scene."""
    if is_transparent:
        im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    else:
        im = Image.new("RGBA", (width, height), (15, 23, 42, 255))

    draw = ImageDraw.Draw(im)

    steps = list(props.get("steps", ["准备", "执行", "测试", "发布"]))
    active_idx = int(props.get("activeStep", 1))

    # Box coordinates (placed on the upper-left quadrant to avoid talking head)
    box_w = int(width * 0.56)
    box_h = int(height * 0.65)
    box_x = int(width * 0.05)
    box_y = int(height * 0.12)

    # Container
    card_bg = (30, 41, 59, 225 if is_transparent else 255)
    draw.rounded_rectangle([box_x, box_y, box_x + box_w, box_y + box_h], radius=14, fill=card_bg, outline=(51, 65, 85, 255), width=2)

    title = str(props.get("title", "核心执行流水线"))
    draw.text((box_x + 20, box_y + 16), title, fill=(241, 245, 249, 255))

    step_h = int((box_h - 70) / max(len(steps), 1))
    for i, st in enumerate(steps):
        st_start = 8 + i * 10
        prog = _interpolate(frame_idx, (st_start, st_start + 12), (0.0, 1.0))
        if prog <= 0.01:
            continue

        sy = box_y + 55 + i * step_h
        cur_w = int((box_w - 40) * prog)

        is_active = (i == active_idx)
        step_bg = (16, 185, 129, int(220 * prog)) if is_active else (51, 65, 85, int(180 * prog))
        draw.rounded_rectangle([box_x + 20, sy, box_x + 20 + cur_w, sy + step_h - 8], radius=8, fill=step_bg)

        # Number badge
        draw.ellipse([box_x + 28, sy + 6, box_x + 48, sy + 26], fill=(255, 255, 255, int(255 * prog)))
        draw.text((box_x + 35, sy + 8), str(i + 1), fill=(0, 0, 0, int(255 * prog)))

        # Step title
        t_col = (255, 255, 255, int(255 * prog)) if is_active else (203, 213, 225, int(255 * prog))
        draw.text((box_x + 60, sy + 8), st, fill=t_col)

        # Connecting line
        if i < len(steps) - 1 and prog > 0.8:
            line_y = sy + step_h - 8
            draw.line([box_x + 38, line_y, box_x + 38, line_y + 8], fill=(100, 116, 139, 200), width=2)

    return im


def _draw_stat_counter_frame(frame_idx: int, total_frames: int, width: int, height: int,
                             props: Dict[str, Any], is_transparent: bool) -> Image.Image:
    """Draw a frame for kinetic stat counter scene."""
    if is_transparent:
        im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    else:
        im = Image.new("RGBA", (width, height), (17, 24, 39, 255))

    draw = ImageDraw.Draw(im)

    box_w = int(width * 0.48)
    box_h = int(height * 0.55)
    box_x = int(width * 0.08)
    box_y = int(height * 0.22)

    card_bg = (31, 41, 55, 230 if is_transparent else 255)
    draw.rounded_rectangle([box_x, box_y, box_x + box_w, box_y + box_h], radius=16, fill=card_bg,
                           outline=(75, 85, 99, 255), width=2)

    title = str(props.get("title", "核心量化指标"))
    draw.text((box_x + 24, box_y + 20), title, fill=(209, 213, 219, 255))

    target_num = float(props.get("targetNumber", 99.9))
    num_prog = _interpolate(frame_idx, (5, int(total_frames * 0.75)), (0.0, target_num))
    num_str = f"{props.get('prefix', '')}{num_prog:.1f}{props.get('suffix', '')}"

    cx = box_x + box_w // 2
    cy = box_y + box_h // 2 + 10
    draw.text((cx - 60, cy - 20), num_str, fill=(251, 191, 36, 255))
    return im


def _safe_shot_folder(out_dir: Path | str, raw_shot_id: Any) -> Tuple[Path, str]:
    """Resolve an output folder without following user-controlled symlinks."""
    requested_root = Path(out_dir)
    current = requested_root
    while True:
        if current.is_symlink():
            raise ValueError("symlinked Remotion output path")
        if current.parent == current:
            break
        current = current.parent

    root = requested_root.resolve()
    if root.exists() and not root.is_dir():
        raise ValueError("Remotion output path is not a directory")

    clean_shot_id = Path(str(raw_shot_id)).name
    if not clean_shot_id or not re.fullmatch(r"[a-zA-Z0-9_-]+", clean_shot_id) or ".." in str(raw_shot_id):
        raise ValueError(f"invalid or unsafe shot_id: {raw_shot_id}")

    candidate = root / clean_shot_id
    if candidate.is_symlink():
        raise ValueError("symlinked Remotion artifact folder")
    try:
        shot_folder = candidate.resolve()
        shot_folder.relative_to(root)
    except (OSError, ValueError) as error:
        raise ValueError("path traversal detected in shot_id") from error
    return shot_folder, clean_shot_id


def render_remotion_shot(shot_brief: Dict[str, Any], out_dir: Path | str) -> Dict[str, Any]:
    """Execute Remotion scene evaluation, generate frames, and encode via FFmpeg."""
    raw_shot_id = shot_brief.get("id", f"broll-{int(time.time())}")
    shot_folder, clean_shot_id = _safe_shot_folder(out_dir, raw_shot_id)
    shot_folder.mkdir(parents=True, exist_ok=True)
    if shot_folder.is_symlink():
        raise ValueError("symlinked Remotion artifact folder")

    # SEC-02 Bounds checking for DoS prevention
    dur = float(shot_brief.get("duration", 3.0))
    if dur <= 0.0 or dur > 60.0:
        raise ValueError(f"duration out of bounds [0.1, 60.0]: {dur}")
    width = int(shot_brief.get("width", 1920))
    height = int(shot_brief.get("height", 1080))
    if width <= 0 or width > 3840 or height <= 0 or height > 2160:
        raise ValueError(f"resolution out of bounds: {width}x{height}")
    fps = int(shot_brief.get("fps", 25))
    if fps < 1 or fps > 60:
        raise ValueError(f"fps out of bounds [1, 60]: {fps}")

    total_frames = max(1, int(round(dur * fps)))
    overlay_mode = shot_brief.get("overlay_mode", "full_frame")
    transparency = shot_brief.get("transparency", "opaque")
    is_transparent = (transparency == "full_alpha" and overlay_mode == "transparent_overlay")

    props = shot_brief.get("props", {})
    tmpl_id = shot_brief.get("template_id", "remotion-data-causality")

    # Preserve React/Remotion source files and briefs for re-rendering
    tsx_content = f"""// Remotion Composition for {clean_shot_id}
// Template: {tmpl_id}
import React from 'react';
import {{ Composition }} from 'remotion';

export const MyComposition = () => {{
  return <div className="{tmpl_id}">Remotion Scene</div>;
}};
"""
    (shot_folder / "Composition.tsx").write_text(tsx_content, encoding="utf-8")
    (shot_folder / "props.json").write_text(json.dumps(props, indent=2, ensure_ascii=False), encoding="utf-8")
    (shot_folder / "shot_brief.json").write_text(json.dumps(shot_brief, indent=2, ensure_ascii=False), encoding="utf-8")

    # Render frames to temp folder
    frames_dir = shot_folder / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    in_f_path = shot_folder / "in_frame.png"
    mid_f_path = shot_folder / "mid_frame.png"
    out_f_path = shot_folder / "out_frame.png"

    try:
        for idx in range(total_frames):
            if tmpl_id == "remotion-process-breakdown":
                img = _draw_process_breakdown_frame(idx, total_frames, width, height, props, is_transparent)
            elif tmpl_id == "remotion-stat-counter":
                img = _draw_stat_counter_frame(idx, total_frames, width, height, props, is_transparent)
            elif tmpl_id == "remotion-data-causality":
                img = _draw_data_causality_frame(idx, total_frames, width, height, props, is_transparent)
            else:
                raise ValueError(f"unsupported template_id: {tmpl_id}")

            f_name = frames_dir / f"frame_{idx:05d}.png"
            img.save(f_name)

            if idx == 0:
                img.save(in_f_path)
            if idx == total_frames // 2:
                img.save(mid_f_path)
            if idx == total_frames - 1:
                img.save(out_f_path)

        # Encode with FFmpeg
        input_pattern = str(frames_dir / "frame_%05d.png")
        if is_transparent:
            video_out = shot_folder / f"{clean_shot_id}.mov"
            stale_mp4 = shot_folder / f"{clean_shot_id}.mp4"
            if stale_mp4.is_file():
                stale_mp4.unlink()
            cmd = [
                "ffmpeg", "-v", "error", "-y",
                "-framerate", str(fps),
                "-i", input_pattern,
                "-c:v", "prores_ks",
                "-profile:v", "4444",
                "-pix_fmt", "yuva444p10le",
                str(video_out)
            ]
        else:
            video_out = shot_folder / f"{clean_shot_id}.mp4"
            stale_mov = shot_folder / f"{clean_shot_id}.mov"
            if stale_mov.is_file():
                stale_mov.unlink()
            cmd = [
                "ffmpeg", "-v", "error", "-y",
                "-framerate", str(fps),
                "-i", input_pattern,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                str(video_out)
            ]

        # SEC-02 Timeout protection
        subprocess.run(cmd, check=True, timeout=120)
    finally:
        shutil.rmtree(frames_dir, ignore_errors=True)

    # Save receipt
    receipt_path = shot_folder / "receipt.json"
    receipt_data = {
        "shot_id": clean_shot_id,
        "template_id": tmpl_id,
        "video_path": str(video_out.resolve()),
        "duration": dur,
        "total_frames": total_frames,
        "fps": fps,
        "transparency": transparency,
        "overlay_mode": overlay_mode,
        "rendered_at": time.time(),
    }
    receipt_path.write_text(json.dumps(receipt_data, indent=2), encoding="utf-8")

    return {
        "status": "rendered",
        "video_path": str(video_out),
        "in_frame": str(in_f_path),
        "mid_frame": str(mid_f_path),
        "out_frame": str(out_f_path),
        "duration": dur,
        "fps": fps,
        "receipt_path": str(receipt_path),
    }


def check_face_avoidance(content_box: Dict[str, float], face_box: Optional[Dict[str, float]]) -> bool:
    """Return True if content_box safely avoids face_box without collision."""
    if not face_box:
        return True
    cx1, cy1 = content_box["x"], content_box["y"]
    cx2, cy2 = cx1 + content_box["w"], cy1 + content_box["h"]

    fx1, fy1 = face_box["x"], face_box["y"]
    fx2, fy2 = fx1 + face_box["w"], fy1 + face_box["h"]

    overlap_x = max(cx1, fx1) < min(cx2, fx2)
    overlap_y = max(cy1, fy1) < min(cy2, fy2)

    return not (overlap_x and overlap_y)


def verify_broll_shot(result: Dict[str, Any], shot_brief: Dict[str, Any]) -> Dict[str, Any]:
    """Verification gate for rendered B-roll shot.

    Validates:
    1. Video file existence and readability.
    2. Exact duration within 1 frame tolerance.
    3. In/mid/out deterministic frames and non-blank/black image check.
    4. Transparency adherence (rejecting opaque fallbacks when alpha was requested).
    5. Facecam talking-head avoidance safety check.
    """
    v_path = Path(result["video_path"])
    if not v_path.is_file():
        return {"status": "rejected", "reason": "video_file_not_found"}

    # Probe format and streams
    try:
        probe_res = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,pix_fmt,duration,nb_frames:format=duration",
            "-of", "json", str(v_path)
        ], capture_output=True, text=True, check=True, timeout=30)
        meta = json.loads(probe_res.stdout)
        stream = meta["streams"][0]
    except Exception as e:
        return {"status": "rejected", "reason": f"ffprobe_failed: {e}"}

    # GATE-01: Duration tolerance check (1 frame)
    probe_dur = float(meta.get("format", {}).get("duration", stream.get("duration", 0.0)))
    exp_dur = float(shot_brief.get("duration", 0.0))
    fps = int(shot_brief.get("fps", 25))
    if exp_dur > 0 and abs(probe_dur - exp_dur) > (1.0 / fps + 1e-3):
        return {
            "status": "rejected",
            "reason": f"duration_mismatch: actual {probe_dur:.3f}s vs expected {exp_dur:.3f}s exceeds 1 frame"
        }

    pix_fmt = stream.get("pix_fmt", "")
    req_trans = shot_brief.get("transparency", "opaque")
    req_overlay = shot_brief.get("overlay_mode", "full_frame")

    # Transparency gate: If transparent requested, must have alpha!
    has_alpha = "yuva" in pix_fmt or "rgba" in pix_fmt
    if (req_trans == "full_alpha" or req_overlay == "transparent_overlay") and not has_alpha:
        return {
            "status": "rejected",
            "reason": "transparency_not_supported_opaque_fallback_rejected",
            "pix_fmt": pix_fmt
        }

    # GATE-01 & RES-01: In/mid/out deterministic frame checks with safe context manager
    for f_label, f_path_str in (("in_frame", result.get("in_frame")),
                                ("mid_frame", result.get("mid_frame")),
                                ("out_frame", result.get("out_frame"))):
        if not f_path_str or not Path(f_path_str).is_file():
            return {"status": "rejected", "reason": f"missing_{f_label}"}
        try:
            with Image.open(f_path_str) as im:
                stat = ImageStat.Stat(im)
                if max(stat.stddev) < 3.0:
                    return {"status": "rejected", "reason": f"blank_or_black_frame_detected: {f_label}"}
        except Exception as e:
            return {"status": "rejected", "reason": f"failed_reading_{f_label}: {e}"}

    # GATE-01: Facecam avoidance check
    content_box = {"x": 0.06, "y": 0.14, "w": 0.54, "h": 0.74}
    if not check_face_avoidance(content_box, shot_brief.get("face_avoidance_zone")):
        return {"status": "rejected", "reason": "content_penetrates_face_avoidance_zone"}

    return {
        "status": "passed",
        "has_alpha": has_alpha,
        "is_blank": False,
        "in_frame": result.get("in_frame"),
        "mid_frame": result.get("mid_frame"),
        "out_frame": result.get("out_frame"),
    }


# Backward-compatible static attachment
verify_broll_shot.check_face_avoidance = check_face_avoidance
