"""Screen Demo B-roll matching, anchoring, and manifest generation."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .edit_plan import frame


def match_screen_anchors(
    plan: Dict[str, Any],
    screen_source_id: str,
    markers: List[Dict[str, Any]],
    words_per_segment: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    lead_offset: float = 0.2,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Anchor silent screen recording markers to stable A-roll target timeline.

    Enforces:
    1. Resolves anchor to targetStart on the edited timeline, never raw sourceStart.
    2. Multiple ambiguous anchors or missing markers/references route to reviewQueue.
    3. Insufficient marker duration routes to reviewQueue without silent trimming.
    4. Silent on track 'Screen Demo'.
    """
    if not isinstance(markers, list):
        raise ValueError("markers must be a JSON array of marker objects")

    fps = plan["fps"]
    # Filter out existing insert_screen_demo items to ensure idempotence (CRITICAL-01)
    new_timeline = [
        item for item in copy.deepcopy(plan["timeline"])
        if item.get("op") != "insert_screen_demo"
    ]
    # Filter out previous screen-marker reviewQueue items (CRITICAL-01)
    review_queue = [
        rq for rq in copy.deepcopy(plan.get("reviewQueue", []))
        if not (
            rq.get("marker_id")
            or rq.get("type", "").startswith("screen_")
            or "anchor" in rq.get("type", "")
            or rq.get("type") in (
                "empty_anchor", "missing_marker_timerange", "marker_out_of_bounds",
                "insufficient_marker_duration", "unmatched_spoken_anchor",
                "ambiguous_anchor_match", "overlapping_screen_demo"
            )
        )
    ]

    a_roll_keeps = [
        item for item in new_timeline
        if item.get("op") == "keep" and item.get("track", "A-roll Final") == "A-roll Final"
    ]

    screen_src = plan.get("sources", {}).get(screen_source_id)
    screen_duration = screen_src.get("duration", 0.0) if screen_src else float("inf")

    approved_demos: List[Dict[str, Any]] = []
    pending_markers: List[Dict[str, Any]] = []

    for idx, marker in enumerate(markers):
        marker_id = marker.get("id", f"screen-marker-{idx}")
        anchor = marker.get("anchor", marker.get("title", "")).strip()
        m_start = marker.get("start")
        m_end = marker.get("end")

        if not anchor:
            review_queue.append({
                "id": f"{marker_id}-empty-anchor",
                "type": "empty_anchor",
                "marker_id": marker_id,
                "action": "hold_and_review",
                "reason": "marker_has_no_anchor_text",
            })
            pending_markers.append({
                "id": marker_id,
                "anchor": "",
                "status": "pending_review",
                "reason": "empty_anchor_text",
            })
            continue

        if m_start is None or m_end is None:
            review_queue.append({
                "id": f"{marker_id}-missing-timerange",
                "type": "missing_marker_timerange",
                "anchor": anchor,
                "marker_id": marker_id,
                "action": "hold_and_review",
                "reason": "marker_has_no_start_or_end_time",
            })
            pending_markers.append({
                "id": marker_id,
                "anchor": anchor,
                "status": "pending_review",
                "reason": "missing_timerange",
            })
            continue

        try:
            m_s = float(m_start)
            m_e = float(m_end)
            m_dur = m_e - m_s
        except (ValueError, TypeError):
            m_dur = -1.0

        if m_s < 0 or m_e <= m_s or (screen_duration > 0 and m_e > screen_duration + 1e-4):
            review_queue.append({
                "id": f"{marker_id}-out-of-bounds",
                "type": "marker_out_of_bounds",
                "anchor": anchor,
                "marker_id": marker_id,
                "start": m_s,
                "end": m_e,
                "action": "hold_and_review",
                "reason": f"timerange_[{m_s},{m_e}]_invalid_or_exceeds_source_{screen_duration:.2f}s",
            })
            pending_markers.append({
                "id": marker_id,
                "anchor": anchor,
                "status": "pending_review",
                "reason": "timerange_out_of_bounds",
            })
            continue

        min_required = float(marker.get("min_required_duration", 1.0))
        if m_dur < min_required or m_dur <= 0.05:
            review_queue.append({
                "id": f"{marker_id}-insufficient-duration",
                "type": "insufficient_marker_duration",
                "anchor": anchor,
                "marker_id": marker_id,
                "duration": round(m_dur, 3),
                "min_required": min_required,
                "action": "hold_and_review",
                "reason": f"duration_{m_dur:.2f}s_less_than_min_{min_required:.2f}s",
            })
            pending_markers.append({
                "id": marker_id,
                "anchor": anchor,
                "status": "pending_review",
                "duration": round(m_dur, 3),
                "reason": "insufficient_duration",
            })
            continue

        # Search for anchor in A-roll spoken sentences
        matched_keeps = []
        for k in a_roll_keeps:
            text = k.get("text", "")
            ms = k.get("manuscript", "")
            if anchor in text or anchor in ms:
                matched_keeps.append(k)

        if not matched_keeps:
            review_queue.append({
                "id": f"{marker_id}-unmatched",
                "type": "unmatched_spoken_anchor",
                "anchor": anchor,
                "marker_id": marker_id,
                "action": "hold_and_review",
                "reason": "anchor_not_found_in_spoken_timeline",
            })
            pending_markers.append({
                "id": marker_id,
                "anchor": anchor,
                "status": "pending_review",
                "reason": "anchor_not_found_in_speech",
            })
            continue

        if len(matched_keeps) > 1:
            review_queue.append({
                "id": f"{marker_id}-ambiguous",
                "type": "ambiguous_anchor_match",
                "anchor": anchor,
                "marker_id": marker_id,
                "matched_count": len(matched_keeps),
                "matched_segment_ids": [k["id"] for k in matched_keeps],
                "action": "hold_and_review",
                "reason": f"multiple_sentences_match_anchor_{anchor}",
            })
            pending_markers.append({
                "id": marker_id,
                "anchor": anchor,
                "status": "pending_review",
                "reason": "multiple_ambiguous_matches",
            })
            continue

        # Single unambiguous match!
        matched_seg = matched_keeps[0]

        # Calculate targetStart on edited timeline (Criterion 1)
        base_target_start = matched_seg["targetStart"]
        target_offset = lead_offset

        # Check for word-level precision if available (MEDIUM-01)
        seg_id = matched_seg.get("id")
        if words_per_segment and seg_id in words_per_segment:
            words = words_per_segment[seg_id]
            for w in words:
                w_text = w.get("word", "")
                if w_text and (w_text in anchor or anchor.startswith(w_text)):
                    word_offset = w.get("start", matched_seg["sourceStart"]) - matched_seg["sourceStart"]
                    target_offset = max(0.0, word_offset)
                    break

        seg_dur = matched_seg["sourceEnd"] - matched_seg["sourceStart"]
        target_start = base_target_start + min(target_offset, max(0.0, seg_dur - 0.5))

        s_start_f = frame(m_s, fps)
        s_end_f = frame(m_e, fps)
        dur_f = s_end_f - s_start_f
        t_start_f = frame(target_start, fps)

        # Check for collision with previously approved screen demos on Screen Demo track (HIGH-01)
        collision = False
        for app_item in approved_demos:
            if max(t_start_f, app_item["targetStartFrame"]) < min(t_start_f + dur_f, app_item["targetStartFrame"] + app_item["durationFrames"]):
                review_queue.append({
                    "id": f"{marker_id}-timeline-conflict",
                    "type": "overlapping_screen_demo",
                    "marker_id": marker_id,
                    "anchor": anchor,
                    "action": "hold_and_review",
                    "reason": f"conflicts_with_demo_{app_item['id']}",
                })
                pending_markers.append({
                    "id": marker_id,
                    "anchor": anchor,
                    "status": "pending_review",
                    "reason": "timeline_conflict",
                })
                collision = True
                break

        if collision:
            continue

        # Consistent discrete frame-to-seconds calculation (MEDIUM-02)
        item_id = marker_id if marker_id else f"screen-demo-{len(approved_demos)}"
        screen_item = {
            "id": item_id,
            "op": "insert_screen_demo",
            "sourceId": screen_source_id,
            "sourceStart": round(float(s_start_f) / fps, 6),
            "sourceEnd": round(float(s_end_f) / fps, 6),
            "targetStart": round(float(t_start_f) / fps, 6),
            "track": "Screen Demo",
            "anchor": anchor,
            "target_item_id": matched_seg.get("id"),
            "anchor_offset": round(float(t_start_f) / fps - base_target_start, 6),
            "status": "approved",
            "stylePack": "documentary_observe",
            "zoom": float(marker.get("zoom", 1.0)),
            "sourceStartFrame": s_start_f,
            "sourceEndFrame": s_end_f,
            "durationFrames": dur_f,
            "targetStartFrame": t_start_f,
        }
        if "crop" in marker:
            screen_item["crop"] = marker["crop"]

        approved_demos.append(screen_item)
        new_timeline.append(screen_item)

    # Sort timeline by track and targetStartFrame
    def _timeline_sort(it):
        t_name = it.get("track", "A-roll Final")
        # Keep A-roll Final first, then Screen Demo, then others
        track_prio = 0 if t_name == "A-roll Final" else (1 if t_name == "Screen Demo" else 2)
        return (track_prio, it.get("targetStartFrame", 0))

    new_timeline.sort(key=_timeline_sort)

    updated_plan = copy.deepcopy(plan)
    updated_plan["timeline"] = new_timeline
    updated_plan["reviewQueue"] = review_queue
    if "planHash" in updated_plan:
        del updated_plan["planHash"]
    updated_plan["planHash"] = hashlib.sha256(
        json.dumps(updated_plan, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    manifest = generate_broll_manifest(approved_demos, pending_markers)

    return updated_plan, manifest


def generate_broll_manifest(
    approved_demos: List[Dict[str, Any]],
    pending_markers: List[Dict[str, Any]],
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Generate canonical Polished/broll-manifest.v1.json structure."""
    items = []
    for d in approved_demos:
        item = copy.deepcopy(d)
        item.setdefault("route", "screen_demo")
        if "target_start" not in item and "targetStart" in item:
            item["target_start"] = item["targetStart"]
        items.append(item)
    manifest = {
        "version": "1",
        "route": "screen_demo",
        "summary": {
            "approved_count": len(approved_demos),
            "pending_count": len(pending_markers),
        },
        "items": items,
        "screen_demos": approved_demos,
        "pending_markers": pending_markers,
    }
    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest
