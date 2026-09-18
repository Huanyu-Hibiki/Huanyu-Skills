"""Actual HyperFrames v0.6.98 packaging renderer and decoded-output QA."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import os
import stat
from typing import Any, Dict, Tuple

from .broll_registry import validate_shot_brief

HYPERFRAMES_VERSION = "0.6.98"
GSAP_VERSION = "3.14.2"
GSAP_ASSET = Path(__file__).with_name("assets") / f"gsap-{GSAP_VERSION}.min.js"
GSAP_SHA256 = "c174bfce53a729418d57a8ad8625e7247c793a22fef8e2851e3cfa3de9cd8280"


def _is_link_like(path: Path) -> bool:
    """Reject symlinks, junctions, and Windows reparse points without resolving."""
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        return True
    try:
        return bool(getattr(path.lstat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    except OSError:
        return False


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
    versions = re.findall(r"(?<![0-9])\d+\.\d+\.\d+(?![0-9])", output)
    if HYPERFRAMES_VERSION not in versions:
        raise ValueError(
            f"HyperFrames dependency version mismatch: expected {HYPERFRAMES_VERSION}, got {output[-200:]}"
        )


def _safe_folder(out_dir: Path | str, shot_id: Any) -> Tuple[Path, str]:
    requested_root = Path(out_dir)
    current = requested_root
    while True:
        if _is_link_like(current):
            raise ValueError("symlinked HyperFrames output path")
        if current.parent == current:
            break
        current = current.parent
    root = requested_root.resolve()
    clean = Path(str(shot_id)).name
    if _is_link_like(root) or not clean or not re.fullmatch(r"[A-Za-z0-9_-]+", clean) or ".." in str(shot_id):
        raise ValueError("unsafe HyperFrames output path or shot id")
    candidate = root / clean
    if _is_link_like(candidate):
        raise ValueError("path traversal or symlinked artifact folder")
    folder = candidate.resolve()
    if folder.parent != root:
        raise ValueError("path traversal or symlinked artifact folder")
    return folder, clean


def _safe_target(path: Path, folder: Path) -> Path:
    """Reject pre-existing links and targets escaping the shot directory."""
    if _is_link_like(path):
        raise ValueError("symlinked HyperFrames artifact")
    if path.parent.resolve() != folder.resolve():
        raise ValueError("HyperFrames artifact escaped shot folder")
    return path


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
    cards = "".join(
        f'<div id="step-card-{i+1}" class="card clip" data-start="{.25+i*.22:.2f}" '
        f'data-duration="{max(.2,duration-.25-i*.22):.2f}" data-track-index="{2+i}">'
        f'<b>{i+1:02}</b> {json.dumps(s, ensure_ascii=False)[1:-1].replace("<", "&lt;")}</div>'
        for i, s in enumerate(steps)
    )
    return f'''<!doctype html><html><head><meta charset="UTF-8"><meta name="viewport" content="width={width}, height={height}"><style>
*{{box-sizing:border-box}}html,body,#root{{margin:0;width:{width}px;height:{height}px;overflow:hidden;background:#201b14;color:#f1e6d2;font-family:serif}}#root{{position:relative;padding:{height*.1:.0f}px {width*.07:.0f}px}}.paper{{position:absolute;right:0;top:0;width:42%;height:100%;background:#c44927}}.paper:after{{content:'';display:block;background:#f1e6d2;height:83%;margin:8% 0 0 10%}}h1,.card{{position:relative;opacity:0}}h1{{font-size:{max(20,width//26)}px;margin:0 0 {height*.1:.0f}px}}.card{{width:50%;height:{max(42,height//9)}px;margin:12px 0;padding:15px 20px;border-radius:12px;background:#32291e;font-size:{max(16,width//55)}px}}.card b{{color:#e0a11f;margin-right:10px}}</style></head><body><main id="root" data-composition-id="hyperframes-editorial-process" data-start="0" data-duration="{duration}" data-width="{width}" data-height="{height}"><div class="paper"></div><h1>{title}</h1>{cards}</main><script src="gsap-3.14.2.min.js"></script><script>
window.__timelines=window.__timelines||{{}};
const tl=gsap.timeline({{paused:true}});
tl.fromTo('.paper',{{xPercent:8}},{{xPercent:0,duration:0.7,ease:'power2.out'}},0);
tl.fromTo('h1',{{xPercent:-7,opacity:0}},{{xPercent:0,opacity:1,duration:0.45,ease:'power2.out'}},0.2);
tl.fromTo('.card',{{xPercent:-7,opacity:0}},{{xPercent:0,opacity:1,duration:0.4,ease:'power2.out'}},0.35);
window.__timelines['hyperframes-editorial-process']=tl;
</script></body></html>'''


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _brief_hash(brief: Dict[str, Any]) -> str:
    canonical = json.dumps(brief, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _lint_project(folder: Path) -> Dict[str, Any]:
    """Run the pinned local HyperFrames linter before spending render time."""
    completed = subprocess.run(
        [_npx_command(), "--no-install", "hyperframes", "lint", str(folder), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    raw = (completed.stdout + completed.stderr).decode("utf-8", errors="replace").strip()
    try:
        report = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"HyperFrames lint returned invalid JSON: {raw[-500:]}") from error
    errors = [item for item in report.get("findings", []) if item.get("severity") == "error"]
    if completed.returncode or int(report.get("errorCount", len(errors))) > 0:
        codes = ", ".join(str(item.get("code", "unknown")) for item in errors)
        raise ValueError(f"HyperFrames composition lint failed: {codes or raw[-500:]}")
    return report


def _samples(video: Path, folder: Path, duration: float) -> tuple[list[Dict[str, Any]], list[str], bool]:
    times = (0.0, duration / 2, max(0.0, duration - .04))
    seek_order = [1, 0, 2, 1]
    output: Dict[int, Dict[str, Any]] = {}
    repeated_hashes: Dict[int, list[str]] = {}
    for seek_index, frame_index in enumerate(seek_order):
        at = times[frame_index]
        png = _safe_target(folder / (f"output-sample-{frame_index}.png" if frame_index not in output else f"output-repeat-{seek_index}.png"), folder)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.6f}", "-i", str(video), "-frames:v", "1", str(png)], check=True, timeout=30)
        digest = _hash(png)
        if frame_index not in output:
            output[frame_index] = {"index": frame_index, "timestamp": at, "artifact": str(png), "actual_output_hash": digest}
        else:
            repeated_hashes.setdefault(frame_index, []).append(digest)
    consistent = all(all(digest == output[index]["actual_output_hash"] for digest in hashes)
                     for index, hashes in repeated_hashes.items())
    return [output[index] for index in range(3)], seek_order, consistent


def render_hyperframes_shot(brief: Dict[str, Any], out_dir: Path | str) -> Dict[str, Any]:
    """Render a real composition through local ``npx hyperframes render``."""
    folder, shot_id = _safe_folder(out_dir, brief.get("id", ""))
    duration, width, height, fps, template = _validate_brief(brief)
    _check_hyperframes_dependency()
    folder.mkdir(parents=True, exist_ok=True)
    if _is_link_like(folder):
        raise ValueError("symlinked artifact folder")
    composition = _safe_target(folder / "composition.html", folder)
    entry = _safe_target(folder / "index.html", folder)
    markup = _html(brief, duration, width, height)
    # Keep one root-level composition (index.html). The sibling composition
    # file is a source snapshot with a non-root marker so project lint does not
    # discover duplicate entry points.
    source_markup = markup.replace("data-composition-id=\"hyperframes-editorial-process\"", "data-composition-source-id=\"hyperframes-editorial-process\"")
    composition.write_text(source_markup, encoding="utf-8")
    entry.write_text(markup, encoding="utf-8")
    if (not GSAP_ASSET.is_file() or _is_link_like(GSAP_ASSET)
            or _is_link_like(GSAP_ASSET.parent) or _hash(GSAP_ASSET) != GSAP_SHA256):
        raise ValueError(f"Pinned GSAP runtime is missing: {GSAP_ASSET}")
    gsap_asset = _safe_target(folder / f"gsap-{GSAP_VERSION}.min.js", folder)
    gsap_asset.write_bytes(GSAP_ASSET.read_bytes())
    _safe_target(folder / "shot_brief.json", folder).write_text(json.dumps(brief, indent=2, ensure_ascii=False), encoding="utf-8")
    _safe_target(folder / "hyperframes.json", folder).write_text(json.dumps({"version": HYPERFRAMES_VERSION}), encoding="utf-8")
    lint_report = _lint_project(folder)
    video = _safe_target(folder / f"{shot_id}.mp4", folder)
    npx = _npx_command()
    command = [npx, "--no-install", "hyperframes", "render", str(folder), "--composition", "index.html", "--output", str(video), "--fps", str(fps), "--workers", "1"]
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
    report_path = _safe_target(folder / "seek-safe-report.json", folder)
    samples, seek_order, seek_consistent = _samples(video, folder, duration)
    distinct_frames = len({sample["actual_output_hash"] for sample in samples}) > 1
    report = {"passed": bool(seek_consistent and distinct_frames), "renderer": f"hyperframes-v{HYPERFRAMES_VERSION}", "frames": samples,
              "seek_order": seek_order, "seek_consistent": seek_consistent, "distinct_frames": distinct_frames,
              "lint": {"ok": bool(lint_report.get("ok")), "error_count": int(lint_report.get("errorCount", 0))}}
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["passed"]:
        raise ValueError("HyperFrames seek-safe QA failed: repeated seeks or sampled frames were not deterministic/dynamic")
    receipt_path = _safe_target(folder / "receipt.json", folder)
    receipt_path.write_text(json.dumps({
        "engine": "hyperframes", "engine_version": HYPERFRAMES_VERSION, "shot_id": shot_id,
        "brief_sha256": _brief_hash(brief),
        "video_path": str(video.resolve()), "video_sha256": _hash(video),
        "duration": duration, "fps": fps, "composition": str(entry.resolve()), "composition_sha256": _hash(entry),
        "composition_source": str(composition.resolve()), "composition_source_sha256": _hash(composition),
        "gsap_version": GSAP_VERSION, "gsap_sha256": _hash(gsap_asset),
        "template_source": template["source"],
        "composition_source_ref": template.get("composition_source"),
        "registry_source": template.get("registry_source"),
        "design_tokens_source": template.get("design_tokens_source"),
        "seek_safe_source": template.get("seek_safe_source"),
        "design_tokens": template.get("design_tokens"),
        "seek_report_sha256": _hash(report_path),
        "samples": samples,
        "adoption_scope": template.get("adoption_scope", {}),
        "renderer": {"command": ["npx", "hyperframes", "render"], "actual_command": command[:3], "arguments": command[3:]},
    }, indent=2), encoding="utf-8")
    return {"status": "rendered", "video_path": str(video), "duration": duration, "fps": fps, "source_path": str(folder), "receipt_path": str(receipt_path), "seek_report_path": str(report_path)}


def verify_hyperframes_shot(result: Dict[str, Any], brief: Dict[str, Any]) -> Dict[str, Any]:
    """Reject missing or altered evidence from actual rendered-output samples."""
    expected_duration, _, _, expected_fps, template = _validate_brief(brief)
    folder, video, report_path = Path(result["source_path"]), Path(result["video_path"]), Path(result["seek_report_path"])
    receipt_path = Path(result.get("receipt_path", folder / "receipt.json"))
    try:
        folder_resolved = folder.resolve()
        local_files = (video, report_path, receipt_path)
        if (_is_link_like(folder) or not folder.is_dir()
                or any(_is_link_like(item) or item.resolve().parent != folder_resolved or not item.is_file() for item in local_files)):
            return {"status": "rejected", "reason": "hyperframes_artifact_missing_or_symlinked"}
    except OSError:
        return {"status": "rejected", "reason": "hyperframes_artifact_missing_or_symlinked"}
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        report_bytes = report_path.read_bytes()
        if receipt.get("video_sha256") != _hash(video) or receipt.get("seek_report_sha256") != hashlib.sha256(report_bytes).hexdigest():
            return {"status": "rejected", "reason": "tampered_hyperframes_receipt_or_report"}
        report = json.loads(report_bytes)
        samples = report["frames"]
        if len(samples) != 3:
            raise ValueError("wrong samples")
        if receipt.get("samples") != samples:
            return {"status": "rejected", "reason": "tampered_hyperframes_samples"}
        if receipt.get("engine") != "hyperframes":
            return {"status": "rejected", "reason": "hyperframes_receipt_engine_mismatch"}
        if (receipt.get("shot_id") != brief.get("id") or receipt.get("engine_version") != HYPERFRAMES_VERSION
                or receipt.get("brief_sha256") != _brief_hash(brief)
                or receipt.get("duration") != expected_duration or receipt.get("fps") != expected_fps
                or receipt.get("gsap_version") != GSAP_VERSION
                or receipt.get("template_source") != template.get("source")
                or receipt.get("composition_source_ref") != template.get("composition_source")
                or receipt.get("registry_source") != template.get("registry_source")
                or receipt.get("design_tokens_source") != template.get("design_tokens_source")
                or receipt.get("seek_safe_source") != template.get("seek_safe_source")
                or receipt.get("design_tokens") != template.get("design_tokens")
                or receipt.get("adoption_scope") != template.get("adoption_scope")):
            return {"status": "rejected", "reason": "hyperframes_receipt_metadata_mismatch"}
        if report.get("passed") is not True or report.get("seek_consistent") is not True:
            return {"status": "rejected", "reason": "hyperframes_seek_safety_failed"}
        if report.get("seek_order") != [1, 0, 2, 1] or report.get("distinct_frames") is not True:
            return {"status": "rejected", "reason": "hyperframes_seek_contract_missing"}
        composition = Path(receipt["composition"])
        if composition.resolve().parent != folder.resolve() or _is_link_like(composition) or not composition.is_file():
            return {"status": "rejected", "reason": "missing_or_tampered_hyperframes_composition"}
        if receipt.get("composition_sha256") != _hash(composition):
            return {"status": "rejected", "reason": "tampered_hyperframes_composition"}
        composition_source = Path(receipt["composition_source"])
        if (composition_source.resolve().parent != folder.resolve() or _is_link_like(composition_source)
                or not composition_source.is_file()
                or receipt.get("composition_source_sha256") != _hash(composition_source)):
            return {"status": "rejected", "reason": "missing_or_tampered_hyperframes_source"}
        gsap_asset = folder / f"gsap-{GSAP_VERSION}.min.js"
        if (_is_link_like(gsap_asset) or not gsap_asset.is_file()
                or receipt.get("gsap_sha256") != _hash(gsap_asset)
                or receipt.get("gsap_sha256") != GSAP_SHA256):
            return {"status": "rejected", "reason": "missing_or_tampered_gsap_runtime"}
        if receipt.get("video_path") != str(video.resolve()):
            return {"status": "rejected", "reason": "hyperframes_video_path_mismatch"}
        for sample in samples:
            artifact = Path(sample["artifact"])
            if artifact.parent.resolve() != folder_resolved or _is_link_like(artifact) or not artifact.is_file() or _hash(artifact) != sample["actual_output_hash"]:
                return {"status": "rejected", "reason": "missing_or_tampered_actual_output_sample"}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return {"status": "rejected", "reason": "invalid_seek_manifest"}
    return {"status": "passed", "source_path": str(folder), "seek_safe": True}
