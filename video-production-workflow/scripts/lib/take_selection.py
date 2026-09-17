"""Multi-take selection, completeness hard-gating, circuit breaker, and undo-group restoration."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .edit_plan import frame


def convert_takes_to_plan(
    takes_decision: Dict[str, Any],
    sources: Dict[str, Any],
    fps: int = 25,
    project_root: str = ".",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Convert takes decision into a canonical edit-plan.v1.json.
    Enforces:
    1. Completeness hard gate (completeness >= 0.80) over secondary speed/pause scores.
    2. Hallucination/low-confidence detection (lowconf_ratio > 0.35 routes to reviewQueue).
    3. Rhetorical parallelism (each manuscript sentence keeps its own unique undoGroup).
    4. Manuscript sequence ordering on target timeline.
    5. Rejected takes preserved as op: 'remove' with undoGroup.
    """
    sentences = takes_decision.get("sentences", [])
    timeline: List[Dict[str, Any]] = []
    review_queue: List[Dict[str, Any]] = []
    takes_ledger: List[Dict[str, Any]] = []

    default_src = next(iter(sources.keys())) if sources else "src"

    cursor_frames = 0
    total_matched = 0
    total_unmatched = 0

    for s_item in sentences:
        s_idx = s_item.get("idx", 0)
        s_text = s_item.get("text", "")
        undo_group = f"sentence-{s_idx}"

        # Collect candidates
        raw_candidates = []
        if "takes" in s_item:
            raw_candidates = list(s_item["takes"])
        else:
            if s_item.get("chosen"):
                raw_candidates.append(s_item["chosen"])
            if s_item.get("rejected"):
                raw_candidates.extend(s_item["rejected"])

        # Validate candidate durations and non-None fields
        candidates = []
        for c in raw_candidates:
            if not isinstance(c, dict):
                continue
            s_val = c.get("start")
            e_val = c.get("end")
            if s_val is None or e_val is None:
                continue
            try:
                s_f = float(s_val)
                e_f = float(e_val)
                if e_f <= s_f:
                    continue
            except (ValueError, TypeError):
                continue
            candidates.append(c)

        if not candidates:
            total_unmatched += 1
            review_queue.append({
                "id": f"sentence-{s_idx}-missing",
                "type": "unmatched_sentence",
                "sentence_idx": s_idx,
                "text": s_text,
                "action": "hold_and_review",
                "reason": "no_candidate_takes_found",
            })
            continue

        # Evaluate completeness hard gate
        # Candidates with completeness >= 0.80 (or match >= 0.80 if completeness not present) are complete
        complete_candidates = []
        partial_candidates = []
        for c in candidates:
            c_comp = c.get("completeness")
            c_match = c.get("match")
            comp = float(c_comp) if c_comp is not None else (float(c_match) if c_match is not None else 1.0)
            match = float(c_match) if c_match is not None else 1.0
            if comp >= 0.80 and match >= 0.70:
                complete_candidates.append(c)
            else:
                partial_candidates.append(c)

        # Check for low-confidence hallucinations among complete candidates
        high_conf_complete = []
        low_conf_complete = []
        for c in complete_candidates:
            l_val = c.get("lowconf_ratio")
            lowconf = float(l_val) if l_val is not None else 0.0
            if lowconf > 0.35:
                low_conf_complete.append(c)
            else:
                high_conf_complete.append(c)

        chosen_candidate = None
        rejected_candidates = []

        if high_conf_complete:
            # Pick best complete high-confidence take by total score
            high_conf_complete.sort(
                key=lambda x: (round(x.get("total", x.get("match", 1.0)), 3),
                               -x.get("pause_ratio", 0.0),
                               -x.get("start", 0.0)),
                reverse=True
            )
            chosen_candidate = high_conf_complete[0]
            rejected_candidates = high_conf_complete[1:] + low_conf_complete + partial_candidates
            total_matched += 1
        elif low_conf_complete:
            # All complete candidates are low confidence -> route to reviewQueue!
            low_conf_complete.sort(key=lambda x: x.get("total", 0.0), reverse=True)
            chosen_candidate = low_conf_complete[0]
            rejected_candidates = low_conf_complete[1:] + partial_candidates
            total_matched += 1
            review_queue.append({
                "id": f"sentence-{s_idx}-low-confidence",
                "type": "low_confidence_take",
                "sentence_idx": s_idx,
                "sourceId": chosen_candidate.get("sourceId", default_src),
                "start": chosen_candidate["start"],
                "end": chosen_candidate["end"],
                "action": "hold_and_review",
                "reason": "candidate_has_low_confidence_words",
            })
        else:
            # Only partial candidates exist -> route to reviewQueue!
            partial_candidates.sort(key=lambda x: x.get("total", 0.0), reverse=True)
            chosen_candidate = partial_candidates[0]
            rejected_candidates = partial_candidates[1:]
            total_unmatched += 1
            review_queue.append({
                "id": f"sentence-{s_idx}-incomplete",
                "type": "incomplete_sentence",
                "sentence_idx": s_idx,
                "action": "hold_and_review",
                "reason": "no_complete_take_found",
            })

        # Add chosen take as keep
        src_id = chosen_candidate.get("sourceId", default_src)
        s_start = round(float(chosen_candidate["start"]), 3)
        s_end = round(float(chosen_candidate["end"]), 3)
        s_start_f = frame(s_start, fps)
        s_end_f = frame(s_end, fps)
        dur_f = s_end_f - s_start_f

        keep_id = chosen_candidate.get("id") or f"take-{s_idx}"
        keep_item = {
            "id": keep_id,
            "op": "keep",
            "sourceId": src_id,
            "sourceStart": s_start,
            "sourceEnd": s_end,
            "targetStart": round(float(cursor_frames) / fps, 6),
            "text": s_text,
            "manuscript": s_text,
            "reason": ["manuscript_match", "best_take"],
            "confidence": round(float(chosen_candidate.get("match", 1.0)), 3),
            "undoGroup": undo_group,
            "track": "A-roll Final",
            "sourceStartFrame": s_start_f,
            "sourceEndFrame": s_end_f,
            "durationFrames": dur_f,
            "targetStartFrame": cursor_frames,
        }
        timeline.append(keep_item)
        cursor_frames += dur_f

        # Add rejected takes as remove
        for r_idx, r in enumerate(rejected_candidates, 1):
            r_src = r.get("sourceId", default_src)
            r_s = round(float(r["start"]), 3)
            r_e = round(float(r["end"]), 3)
            r_s_f = frame(r_s, fps)
            r_e_f = frame(r_e, fps)
            r_dur_f = r_e_f - r_s_f

            why = ["duplicate_take", "lower_score"]
            if r in partial_candidates:
                why = ["partial_take"]
            elif r.get("lowconf_ratio", 0.0) > 0.35:
                why = ["low_confidence_take"]

            rem_id = r.get("id") or f"take-{s_idx}-rejected-{r_idx}"
            rem_item = {
                "id": rem_id,
                "op": "remove",
                "sourceId": r_src,
                "sourceStart": r_s,
                "sourceEnd": r_e,
                "reason": why,
                "confidence": round(float(r.get("match", 0.5)), 3),
                "undoGroup": undo_group,
                "sourceStartFrame": r_s_f,
                "sourceEndFrame": r_e_f,
                "durationFrames": r_dur_f,
            }
            if r.get("text"):
                rem_item["text"] = r["text"]
            timeline.append(rem_item)

        takes_ledger.append({
            "sentence_idx": s_idx,
            "text": s_text,
            "chosen_id": keep_item["id"],
            "rejected_count": len(rejected_candidates),
        })

    plan = {
        "version": "1",
        "fps": fps,
        "projectRoot": str(project_root),
        "sources": sources,
        "timeline": timeline,
        "durationFrames": cursor_frames,
        "reviewQueue": review_queue,
    }
    plan["planHash"] = hashlib.sha256(
        json.dumps(plan, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    report = {
        "summary": {
            "total_sentences": len(sentences),
            "matched_sentences": total_matched,
            "unmatched_sentences": total_unmatched,
            "total_takes_considered": sum(1 for item in timeline),
            "keeps_count": len([x for x in timeline if x["op"] == "keep"]),
            "removes_count": len([x for x in timeline if x["op"] == "remove"]),
            "review_queue_count": len(review_queue),
        },
        "sentences": takes_ledger,
    }

    return plan, report


def evaluate_circuit_breaker(
    plan: Dict[str, Any],
    total_sentences: Optional[int] = None,
    unmatched_sentences: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Evaluate safety circuit breaker rules:
    1. Total removed duration > 35% of total source duration.
    2. Unmatched manuscript sentences > 5% of total manuscript sentences.
    3. ReviewQueue items > 3.
    """
    sources = plan.get("sources", {})
    total_source_s = sum(s.get("duration", 0.0) if isinstance(s, dict) else 0.0 for s in sources.values())
    if total_source_s <= 0.0:
        total_source_s = max((item.get("sourceEnd", 0.0) for item in plan.get("timeline", [])), default=1.0)

    # Compute total removed seconds
    removed_items_dur = sum((item.get("sourceEnd", 0.0) - item.get("sourceStart", 0.0))
                            for item in plan.get("timeline", []) if item.get("op") == "remove")

    deletion_ratio = removed_items_dur / max(0.001, total_source_s)

    triggers: List[str] = []

    # Check 1: Deletion ratio > 35%
    if deletion_ratio > 0.35:
        triggers.append("deletion_limit_exceeded")

    # Check 2: Unmatched manuscript > 5%
    unmatched_ratio = 0.0
    if total_sentences is not None and total_sentences > 0:
        unmatched_cnt = unmatched_sentences or 0
        unmatched_ratio = unmatched_cnt / total_sentences
        if unmatched_ratio > 0.05:
            triggers.append("unmatched_manuscript_exceeded")

    # Check 3: High risk count > 3
    rq_count = len(plan.get("reviewQueue", []))
    if rq_count > 3:
        triggers.append("high_risk_items_exceeded")

    circuit_broken = len(triggers) > 0

    return {
        "planHash": plan.get("planHash"),
        "circuit_broken": circuit_broken,
        "triggers": triggers,
        "metrics": {
            "deletion": {
                "actual": round(deletion_ratio, 4),
                "threshold": 0.35,
                "removed_s": round(removed_items_dur, 2),
                "source_s": round(total_source_s, 2),
            },
            "unmatched_manuscript": {
                "actual": round(unmatched_ratio, 4),
                "threshold": 0.05,
                "unmatched": unmatched_sentences or 0,
                "total": total_sentences or 0,
            },
            "high_risk": {
                "actual": rq_count,
                "threshold": 3,
            }
        }
    }


def restore_take_in_plan(
    plan: Dict[str, Any],
    item_id: Optional[str] = None,
    undo_group: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Restore a removed segment in edit-plan.
    Swaps or promotes op: 'remove' to op: 'keep', ripple-shifts downstream targetStarts,
    and recalculates discrete frame timeline and hash.
    """
    fps = plan["fps"]
    new_timeline = copy.deepcopy(plan["timeline"])

    # Locate the remove item
    target_remove = None
    target_idx = -1
    for idx, it in enumerate(new_timeline):
        if it.get("op") == "remove":
            if item_id and it.get("id") == item_id:
                target_remove = it
                target_idx = idx
                break
            elif undo_group and it.get("undoGroup") == undo_group:
                target_remove = it
                target_idx = idx
                break

    if target_remove is None:
        raise ValueError(f"remove item not found for id={item_id} or undoGroup={undo_group}")

    group = target_remove.get("undoGroup")
    existing_keep = None
    existing_keep_idx = -1
    if group is not None:
        for idx, it in enumerate(new_timeline):
            if it.get("op") == "keep" and it.get("undoGroup") == group:
                existing_keep = it
                existing_keep_idx = idx
                break

    if existing_keep is not None:
        # Swap roles
        existing_keep["op"] = "remove"
        existing_keep["reason"] = ["user_replaced_with_retake"]
        if "targetStart" in existing_keep:
            del existing_keep["targetStart"]
        if "targetStartFrame" in existing_keep:
            del existing_keep["targetStartFrame"]

    target_remove["op"] = "keep"
    target_remove["reason"] = ["user_restored_take"]

    # Re-order timeline so keeps on A-roll Final maintain proper track sequence
    # Sort keeps primarily by manuscript order (undoGroup index) and secondary by sourceStart
    def _sort_key(it):
        g = it.get("undoGroup", "")
        if isinstance(g, str) and g.startswith("sentence-"):
            try:
                return (0, int(g.split("-")[1]), it.get("sourceStart", 0.0))
            except (ValueError, IndexError):
                pass
        return (1, 0, it.get("sourceStart", 0.0))

    keeps = [it for it in new_timeline if it.get("op") == "keep"]
    removes = [it for it in new_timeline if it.get("op") == "remove"]
    keeps.sort(key=_sort_key)

    # Recalculate targetStartFrame and durationFrames monotonically
    cursor_frames = 0
    for k in keeps:
        s_f = frame(k["sourceStart"], fps)
        e_f = frame(k["sourceEnd"], fps)
        dur_f = e_f - s_f
        k["sourceStartFrame"] = s_f
        k["sourceEndFrame"] = e_f
        k["durationFrames"] = dur_f
        k["targetStartFrame"] = cursor_frames
        k["targetStart"] = round(float(cursor_frames) / fps, 6)
        k["track"] = k.get("track", "A-roll Final")
        cursor_frames += dur_f

    ordered_timeline = keeps + removes

    restored_plan = copy.deepcopy(plan)
    restored_plan["timeline"] = ordered_timeline
    restored_plan["durationFrames"] = cursor_frames
    if "planHash" in restored_plan:
        del restored_plan["planHash"]
    restored_plan["planHash"] = hashlib.sha256(
        json.dumps(restored_plan, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    receipt = {
        "restored_item_id": target_remove.get("id"),
        "undo_group": group,
        "new_duration_frames": cursor_frames,
        "new_duration_seconds": round(float(cursor_frames) / fps, 3),
        "planHash": restored_plan["planHash"],
    }

    return restored_plan, receipt
