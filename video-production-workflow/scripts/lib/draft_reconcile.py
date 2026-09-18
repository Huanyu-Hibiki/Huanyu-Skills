"""Draft reconciliation, B-roll anchor realignment, subtitle versioning, and cache invalidation."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple



def reconcile_plan_from_draft(base_plan: Dict[str, Any], draft_path: Path | str) -> Dict[str, Any]:
    """
    Read manually adjusted A-roll timeline from JianYing draft_content.json,
    and generate a reconciled edit-plan reflecting user trims/cuts.
    """
    draft_file = Path(draft_path)
    if not draft_file.exists():
        raise FileNotFoundError(f"Draft file not found: {draft_path}")

    draft_data = json.loads(draft_file.read_text(encoding="utf-8"))
    fps = draft_data.get("fps", base_plan.get("fps", 30))

    # Identify primary A-roll video track
    tracks = draft_data.get("tracks", [])
    a_roll_track = None
    for tr in tracks:
        if tr.get("type") == "video" and tr.get("name") in ("A-roll Final", "Main", "A-roll"):
            a_roll_track = tr
            break
    if not a_roll_track:
        # Fallback to first video track
        for tr in tracks:
            if tr.get("type") == "video" and tr.get("name") != "A-roll Recovery":
                a_roll_track = tr
                break

    if not a_roll_track or not a_roll_track.get("segments"):
        raise ValueError("Cannot find valid A-roll video track with segments in draft")

    # Build materials map: material_id -> path
    materials_map = {}
    for mat in draft_data.get("materials", {}).get("videos", []):
        materials_map[mat["id"]] = Path(mat.get("path", "")).resolve()

    # Build base plan sources map: resolved path -> sourceId
    source_by_path = {}
    for sid, sinfo in base_plan.get("sources", {}).items():
        source_by_path[Path(sinfo["path"]).resolve()] = sid

    # Sort draft segments by target start time
    draft_segs = sorted(a_roll_track["segments"], key=lambda s: s.get("target_timerange", {}).get("start", 0))

    orig_timeline = base_plan.get("timeline", [])
    orig_by_id = {item.get("id"): item for item in orig_timeline if item.get("id")}

    new_timeline: List[Dict[str, Any]] = []

    for idx, seg in enumerate(draft_segs):
        mat_id = seg.get("material_id")
        seg_path = materials_map.get(mat_id)
        source_id = source_by_path.get(seg_path) if seg_path else None
        if not source_id:
            # Fallback to first source if single source
            if len(base_plan.get("sources", {})) == 1:
                source_id = next(iter(base_plan["sources"].keys()))
            else:
                source_id = "unknown_source"

        t_range = seg.get("target_timerange", {})
        s_range = seg.get("source_timerange", {})

        s_start_f = round(s_range.get("start", 0) / 1_000_000 * fps)
        dur_f = round(s_range.get("duration", 0) / 1_000_000 * fps)
        s_end_f = s_start_f + dur_f

        t_start_f = round(t_range.get("start", 0) / 1_000_000 * fps)

        seg_id = seg.get("id") or f"seg-{idx}"
        matched_orig = orig_by_id.get(seg_id)

        if not matched_orig:
            # Try matching by source range overlap
            for o_item in orig_timeline:
                if o_item.get("sourceId") == source_id:
                    o_sf = o_item.get("sourceStartFrame", 0)
                    o_ef = o_item.get("sourceEndFrame", 0)
                    if max(s_start_f, o_sf) < min(s_end_f, o_ef):
                        matched_orig = o_item
                        break

        new_item = {
            "id": seg_id,
            "op": "keep",
            "sourceId": source_id,
            "sourceStart": round(float(s_start_f) / fps, 6),
            "sourceEnd": round(float(s_end_f) / fps, 6),
            "sourceStartFrame": s_start_f,
            "sourceEndFrame": s_end_f,
            "durationFrames": dur_f,
            "targetStart": round(float(t_start_f) / fps, 6),
            "targetStartFrame": t_start_f,
            "track": "A-roll Final",
        }
        if matched_orig:
            for field in ("text", "manuscript", "speaker", "words"):
                if field in matched_orig:
                    new_item[field] = matched_orig[field]

        new_timeline.append(new_item)

    total_duration_frames = max((item["targetStartFrame"] + item["durationFrames"] for item in new_timeline), default=0)

    reconciled_plan = copy.deepcopy(base_plan)
    reconciled_plan["fps"] = fps
    reconciled_plan["durationFrames"] = total_duration_frames
    reconciled_plan["timeline"] = new_timeline

    # Canonical planHash calculation
    p_bytes = json.dumps(reconciled_plan, sort_keys=True).encode("utf-8")
    reconciled_plan["planHash"] = hashlib.sha256(p_bytes).hexdigest()

    return reconciled_plan


def realign_broll_manifest(
    manifest: Dict[str, Any],
    reconciled_plan: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Realign B-roll items according to reconciled A-roll timeline.
    If anchor sentence moved, update target_start.
    If anchor sentence was deleted, mark orphaned and route to reviewQueue.
    """
    manifest_copy = copy.deepcopy(manifest)
    plan_copy = copy.deepcopy(reconciled_plan)
    review_queue = plan_copy.setdefault("reviewQueue", [])

    a_roll_keeps = [
        item for item in plan_copy.get("timeline", [])
        if item.get("op") == "keep" and item.get("track", "A-roll Final") == "A-roll Final"
    ]

    fps = plan_copy.get("fps", 30)

    for item in manifest_copy.get("items", []):
        anchor = item.get("anchor") or item.get("shot_brief", {}).get("anchor") or ""
        # Also try matching by id if previously recorded
        target_item_id = item.get("target_item_id")

        matched_keep = None
        if target_item_id:
            matched_keep = next((k for k in a_roll_keeps if k.get("id") == target_item_id), None)

        if not matched_keep and anchor:
            # Search by anchor text in A-roll
            matched_candidates = [
                k for k in a_roll_keeps
                if anchor in k.get("text", "") or anchor in k.get("manuscript", "")
            ]
            if len(matched_candidates) == 1:
                matched_keep = matched_candidates[0]

        if matched_keep:
            # Successfully realigned!
            offset = float(item.get("anchor_offset", 0.0))
            new_target_start = float(matched_keep.get("targetStart", 0.0)) + offset
            item["target_start"] = round(new_target_start, 6)
            if "targetStartFrame" in item:
                item["targetStartFrame"] = matched_keep.get("targetStartFrame", round(new_target_start * fps)) + round(offset * fps)
            item["status"] = "approved"
            item.pop("reason", None)
        else:
            # Anchor deleted or completely lost
            item["status"] = "orphaned"
            item["reason"] = "anchor_deleted_in_draft"
            review_queue.append({
                "id": f"{item.get('id', 'broll')}-anchor-orphaned",
                "type": "broll_anchor_orphaned",
                "broll_id": item.get("id"),
                "anchor": anchor,
                "action": "hold_and_review",
                "reason": "anchor_deleted_in_draft_tuning",
            })

    return manifest_copy, plan_copy


def rebuild_subtitles_for_plan(
    plan: Dict[str, Any],
    out_srt_path: Path | str,
    timeline_version: Optional[str] = None
) -> Path:
    """Generate SRT subtitles bound to the planHash / timelineVersion."""
    out_path = Path(out_srt_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    version_tag = timeline_version or plan.get("planHash", "unknown")
    fps = plan.get("fps", 30)

    keeps = [
        item for item in plan.get("timeline", [])
        if item.get("op") == "keep" and item.get("text") and item.get("track", "A-roll Final") == "A-roll Final"
    ]

    def _fmt_ts(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int(round((sec - int(sec)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = [f"# timelineVersion: {version_tag}\n"]
    for idx, item in enumerate(keeps, 1):
        t_start = item.get("targetStart", float(item.get("targetStartFrame", 0)) / fps)
        dur = item.get("durationFrames", 0) / fps
        t_end = t_start + dur
        lines.append(f"{idx}")
        lines.append(f"{_fmt_ts(t_start)} --> {_fmt_ts(t_end)}")
        lines.append(f"{item['text']}\n")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def check_subtitles_compatible(srt_path: Path | str, plan: Dict[str, Any]) -> Tuple[bool, str]:
    """Check if existing subtitle file is compatible with plan or stale."""
    p = Path(srt_path)
    if not p.exists():
        return False, "Subtitle file does not exist"

    text = p.read_text(encoding="utf-8")
    curr_hash = plan.get("planHash", "")

    # Look for explicit timelineVersion header
    match = re.search(r"#\s*timelineVersion:\s*(\S+)", text)
    if match:
        tag = match.group(1).strip()
        if tag == curr_hash:
            return True, ""
        return False, f"Stale subtitle: timelineVersion {tag} != current planHash {curr_hash}"

    # Fallback to duration check if no header
    fps = plan.get("fps", 30)
    plan_dur = plan.get("durationFrames", 0) / fps
    time_matches = re.findall(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", text)
    if time_matches:
        last = time_matches[-1]
        last_s = int(last[0]) * 3600 + int(last[1]) * 60 + int(last[2]) + int(last[3]) / 1000.0
        if abs(last_s - plan_dur) > 2.0:
            return False, f"Stale subtitle: last cue time {last_s:.2f}s differs from plan duration {plan_dur:.2f}s"

    return True, ""


def audit_broll_manifest(manifest: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Audit B-roll manifest: intercept completed/approved status without video file,
    ensuring status and output files are consistent.
    """
    manifest_copy = copy.deepcopy(manifest)
    issues: List[Dict[str, Any]] = []

    for item in manifest_copy.get("items", []):
        status = item.get("status")
        if status in ("completed", "approved"):
            vp_str = item.get("video_path")
            if not vp_str:
                item["status"] = "failed"
                item["reason"] = "missing_video_path"
                issues.append({
                    "item_id": item.get("id"),
                    "type": "missing_output_file",
                    "reason": "video_path is not defined",
                })
                continue
            vp = Path(vp_str)
            if not vp.is_file() or vp.stat().st_size == 0:
                item["status"] = "failed"
                item["reason"] = f"output_file_missing_or_empty: {vp_str}"
                issues.append({
                    "item_id": item.get("id"),
                    "type": "missing_output_file",
                    "reason": f"File does not exist or empty: {vp_str}",
                })

    return manifest_copy, issues


def evaluate_broll_cache_invalidation(manifest_item: Dict[str, Any], new_shot_brief: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Check if B-roll cache is still valid or needs regeneration.
    Returns (is_valid, reason).
    """
    old_brief = manifest_item.get("shot_brief", {})
    critical_keys = ("template_id", "style_pack", "text", "prompt", "theme", "engine", "font")
    for key in critical_keys:
        old_v = old_brief.get(key)
        new_v = new_shot_brief.get(key)
        if old_v != new_v:
            return False, f"Attribute {key} changed: '{old_v}' != '{new_v}'"
    return True, ""
