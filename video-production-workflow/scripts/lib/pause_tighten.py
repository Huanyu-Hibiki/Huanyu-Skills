"""Pause tightening library: tighten interior hesitations and cross-keep gaps on timeline."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from .edit_plan import frame, load_plan
from .boundary_protect import load_audio_segment, analyze_audio_energy


def join_words(words: List[Dict[str, Any]]) -> str:
    texts = [w.get('text', '') for w in words if w.get('text')]
    if not texts:
        return ""
    has_ascii = any(any(c.isascii() and c.isalnum() for c in t) for t in texts)
    if has_ascii:
        return " ".join(texts)
    return "".join(texts)


def tighten_pauses(
    plan: Dict[str, Any],
    threshold: float = 0.35,
    keep: float = 0.25,
    min_gain: float = 0.10,
    words_per_segment: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    verify_audio_energy: bool = True,
    energy_threshold: float = 0.035,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Tighten silences on edit plan timeline:
    1. Interior, head, and tail silences inside keep segments.
    2. Cross-keep silences on the target timeline.
    Returns (tightened_plan, pauses_report).
    """
    fps = plan['fps']
    project_root = Path(plan.get('projectRoot', '.'))
    words_per_segment = words_per_segment or {}

    new_timeline: List[Dict[str, Any]] = []
    pauses_ledger: List[Dict[str, Any]] = []
    review_queue: List[Dict[str, Any]] = list(plan.get('reviewQueue', []))

    # Calculate original duration
    orig_dur_frames = plan.get('durationFrames', 0)
    if orig_dur_frames == 0:
        orig_dur_frames = max(
            (frame(item['targetStart'], fps) + (frame(item['sourceEnd'], fps) - frame(item['sourceStart'], fps))
             for item in plan['timeline'] if item['op'] == 'keep'),
            default=0
        )
    orig_dur_s = round(orig_dur_frames / fps, 3)

    # Step 1: Interior, head, and tail pauses tightening
    track_shifts: Dict[str, float] = {}

    for item in plan['timeline']:
        if item['op'] != 'keep':
            new_timeline.append(copy.deepcopy(item))
            continue

        track = item.get('track', 'A-roll Final')
        current_shift = track_shifts.get(track, 0.0)
        item_target_start = round(item['targetStart'] - current_shift, 6)

        seg_id = item['id']
        src_id = item['sourceId']
        s_start = item['sourceStart']
        s_end = item['sourceEnd']
        words = words_per_segment.get(seg_id, [])
        speech_words = [w for w in words if not w.get('isGap')]

        src_info = plan['sources'].get(src_id)
        audio_path = None
        if src_info:
            p = project_root / (src_info['path'] if isinstance(src_info, dict) else src_info)
            if p.is_file():
                audio_path = p

        if len(speech_words) == 0:
            kept = copy.deepcopy(item)
            kept['targetStart'] = item_target_start
            new_timeline.append(kept)
            continue

        # Check lead-in (head) silence
        w_first = speech_words[0]
        head_gap = w_first['start'] - s_start
        effective_start = s_start
        if head_gap >= threshold and (head_gap - keep) >= min_gain:
            trim_end = w_first['start'] - keep
            is_noisy = False
            if verify_audio_energy and audio_path is not None:
                try:
                    chunk, sr = load_audio_segment(audio_path, s_start, trim_end)
                    if len(chunk) > 0:
                        rms, _ = analyze_audio_energy(chunk, sr)
                        if np.percentile(rms, 75) >= energy_threshold:
                            is_noisy = True
                except Exception:
                    is_noisy = True  # SEC-05 Fail-safe

            if is_noisy:
                pauses_ledger.append({
                    'id': f"{seg_id}-head-pause",
                    'type': 'head_silence',
                    'segment_id': seg_id,
                    'start': round(s_start, 3),
                    'end': round(w_first['start'], 3),
                    'gap': round(head_gap, 3),
                    'retained': round(head_gap, 3),
                    'removed': 0.0,
                    'status': 'flagged_review',
                    'reason': 'pause_with_audio_activity',
                })
                review_queue.append({
                    'id': f"{seg_id}-head-pause",
                    'sourceId': src_id,
                    'type': 'pause_with_audio_activity',
                    'start': round(s_start, 3),
                    'end': round(w_first['start'], 3),
                    'action': 'hold_and_review',
                })
            else:
                rem_frames = frame(head_gap, fps) - frame(keep, fps)
                rem_s = round(rem_frames / fps, 3)
                effective_start = trim_end
                # Emit remove item into timeline
                new_timeline.append({
                    'id': f"trim-{seg_id}-head",
                    'op': 'remove',
                    'sourceId': src_id,
                    'sourceStart': round(s_start, 3),
                    'sourceEnd': round(trim_end, 3),
                    'reason': ['lead_in_silence'],
                    'confidence': 0.95,
                    'undoGroup': seg_id,
                })
                pauses_ledger.append({
                    'id': f"{seg_id}-head-pause",
                    'type': 'head_silence',
                    'segment_id': seg_id,
                    'start': round(s_start, 3),
                    'end': round(trim_end, 3),
                    'gap': round(head_gap, 3),
                    'retained': round(keep, 3),
                    'removed': rem_s,
                    'status': 'cut',
                    'reason': 'head_silence_tightened',
                })

        # Check lead-out (tail) silence
        w_last = speech_words[-1]
        tail_gap = s_end - w_last['end']
        effective_end = s_end
        tail_trim_start = None
        if tail_gap >= threshold and (tail_gap - keep) >= min_gain:
            tail_trim_start = w_last['end'] + keep
            is_noisy = False
            if verify_audio_energy and audio_path is not None:
                try:
                    chunk, sr = load_audio_segment(audio_path, tail_trim_start, s_end)
                    if len(chunk) > 0:
                        rms, _ = analyze_audio_energy(chunk, sr)
                        if np.percentile(rms, 75) >= energy_threshold:
                            is_noisy = True
                except Exception:
                    is_noisy = True  # SEC-05 Fail-safe

            if is_noisy:
                pauses_ledger.append({
                    'id': f"{seg_id}-tail-pause",
                    'type': 'tail_silence',
                    'segment_id': seg_id,
                    'start': round(w_last['end'], 3),
                    'end': round(s_end, 3),
                    'gap': round(tail_gap, 3),
                    'retained': round(tail_gap, 3),
                    'removed': 0.0,
                    'status': 'flagged_review',
                    'reason': 'pause_with_audio_activity',
                })
                review_queue.append({
                    'id': f"{seg_id}-tail-pause",
                    'sourceId': src_id,
                    'type': 'pause_with_audio_activity',
                    'start': round(w_last['end'], 3),
                    'end': round(s_end, 3),
                    'action': 'hold_and_review',
                })
            else:
                rem_frames = frame(tail_gap, fps) - frame(keep, fps)
                rem_s = round(rem_frames / fps, 3)
                effective_end = tail_trim_start

        # Find interior pauses between words
        candidate_pauses = []
        if len(speech_words) >= 2:
            inside = [w for w in speech_words if w['start'] >= effective_start - 1e-4 and w['end'] <= effective_end + 1e-4]
            for a, b in zip(inside, inside[1:]):
                gap = b['start'] - a['end']
                if gap >= threshold and (gap - keep) >= min_gain:
                    candidate_pauses.append({
                        'start': a['end'],
                        'end': b['start'],
                        'gap': gap,
                    })

        cursor = effective_start
        target_cursor = item_target_start
        split_count = 0
        created_sub_items: List[Dict[str, Any]] = []

        for p in candidate_pauses:
            flag_review = False
            if verify_audio_energy and audio_path is not None:
                chk_start = p['start'] + keep
                chk_end = p['end']
                if chk_end - chk_start > 0.02:
                    try:
                        chunk, sr = load_audio_segment(audio_path, chk_start, chk_end)
                        if len(chunk) > 0:
                            rms, _ = analyze_audio_energy(chunk, sr)
                            if np.percentile(rms, 75) >= energy_threshold:
                                flag_review = True
                    except Exception:
                        flag_review = True  # SEC-05 Fail-safe

            if flag_review:
                pauses_ledger.append({
                    'id': f"{seg_id}-pause-{split_count}",
                    'type': 'interior',
                    'segment_id': seg_id,
                    'start': round(p['start'], 3),
                    'end': round(p['end'], 3),
                    'gap': round(p['gap'], 3),
                    'retained': round(p['gap'], 3),
                    'removed': 0.0,
                    'status': 'flagged_review',
                    'reason': 'pause_with_audio_activity',
                })
                review_queue.append({
                    'id': f"{seg_id}-pause-{split_count}",
                    'sourceId': src_id,
                    'type': 'pause_with_audio_activity',
                    'start': round(p['start'], 3),
                    'end': round(p['end'], 3),
                    'action': 'hold_and_review',
                })
                continue

            cut_from = p['start'] + keep
            if frame(cut_from, fps) > frame(cursor, fps):
                split_count += 1
                sub_item = copy.deepcopy(item)
                sub_item['sourceStart'] = round(cursor, 3)
                sub_item['sourceEnd'] = round(cut_from, 3)
                sub_item['targetStart'] = round(target_cursor, 6)
                dur = sub_item['sourceEnd'] - sub_item['sourceStart']
                target_cursor += dur
                sub_words = [w for w in speech_words if w['start'] >= cursor - 1e-4 and w['end'] <= cut_from + 1e-4]
                if sub_words:
                    sub_item['text'] = join_words(sub_words)
                created_sub_items.append(sub_item)

            # Emit remove item into timeline
            rem_frames = frame(p['gap'], fps) - frame(keep, fps)
            rem_s = round(rem_frames / fps, 3)
            new_timeline.append({
                'id': f"trim-{seg_id}-{split_count}",
                'op': 'remove',
                'sourceId': src_id,
                'sourceStart': round(cut_from, 3),
                'sourceEnd': round(p['end'], 3),
                'reason': ['intra_sentence_pause'],
                'confidence': 0.95,
                'undoGroup': seg_id,
            })
            pauses_ledger.append({
                'id': f"{seg_id}-pause-{split_count}",
                'type': 'interior',
                'segment_id': seg_id,
                'start': round(p['start'], 3),
                'end': round(p['end'], 3),
                'gap': round(p['gap'], 3),
                'retained': round(keep, 3),
                'removed': rem_s,
                'status': 'cut',
                'reason': 'interior_silence_tightened',
            })
            cursor = p['end']

        if frame(effective_end, fps) > frame(cursor, fps):
            split_count += 1
            sub_item = copy.deepcopy(item)
            sub_item['sourceStart'] = round(cursor, 3)
            sub_item['sourceEnd'] = round(effective_end, 3)
            sub_item['targetStart'] = round(target_cursor, 6)
            dur = sub_item['sourceEnd'] - sub_item['sourceStart']
            target_cursor += dur
            sub_words = [w for w in speech_words if w['start'] >= cursor - 1e-4 and w['end'] <= effective_end + 1e-4]
            if sub_words:
                sub_item['text'] = join_words(sub_words)
            created_sub_items.append(sub_item)

        # Emit tail remove item if tail was trimmed
        if tail_trim_start is not None and effective_end == tail_trim_start:
            rem_frames = frame(tail_gap, fps) - frame(keep, fps)
            rem_s = round(rem_frames / fps, 3)
            new_timeline.append({
                'id': f"trim-{seg_id}-tail",
                'op': 'remove',
                'sourceId': src_id,
                'sourceStart': round(tail_trim_start, 3),
                'sourceEnd': round(s_end, 3),
                'reason': ['lead_out_silence'],
                'confidence': 0.95,
                'undoGroup': seg_id,
            })
            pauses_ledger.append({
                'id': f"{seg_id}-tail-pause",
                'type': 'tail_silence',
                'segment_id': seg_id,
                'start': round(tail_trim_start, 3),
                'end': round(s_end, 3),
                'gap': round(tail_gap, 3),
                'retained': round(keep, 3),
                'removed': rem_s,
                'status': 'cut',
                'reason': 'tail_silence_tightened',
            })

        # SEC-08: Assign ID without altering single unsplit items
        if len(created_sub_items) > 1:
            for idx, s_it in enumerate(created_sub_items, 1):
                s_it['id'] = f"{seg_id}_p{idx}"
            new_timeline.extend(created_sub_items)
        elif len(created_sub_items) == 1:
            created_sub_items[0]['id'] = seg_id
            new_timeline.extend(created_sub_items)
        else:
            fallback = copy.deepcopy(item)
            fallback['targetStart'] = item_target_start
            new_timeline.append(fallback)
            target_cursor = item_target_start + (s_end - s_start)

        # SEC-01: Update track ripple shift for downstream items
        orig_dur = s_end - s_start
        actual_dur = target_cursor - item_target_start
        item_removed = max(0.0, orig_dur - actual_dur)
        track_shifts[track] = current_shift + item_removed

    # Step 2: Cross-keep pauses tightening on each track
    tracks = set(item.get('track', 'A-roll Final') for item in new_timeline if item['op'] == 'keep')
    for track in tracks:
        track_keeps = [item for item in new_timeline if item['op'] == 'keep' and item.get('track', 'A-roll Final') == track]
        for i in range(len(track_keeps) - 1):
            curr_item = track_keeps[i]
            next_item = track_keeps[i + 1]

            curr_dur = curr_item['sourceEnd'] - curr_item['sourceStart']
            curr_target_end = curr_item['targetStart'] + curr_dur
            target_gap = next_item['targetStart'] - curr_target_end

            if target_gap >= threshold and (target_gap - keep) >= min_gain:
                # SEC-03: Check audio energy only if source interval reflects this timeline gap
                is_noisy = False
                source_gap = (next_item['sourceStart'] - curr_item['sourceEnd']) if curr_item['sourceId'] == next_item['sourceId'] else -1.0
                if curr_item['sourceId'] == next_item['sourceId'] and abs(source_gap - target_gap) < 0.10:
                    src_info = plan['sources'].get(curr_item['sourceId'])
                    audio_path = None
                    if src_info:
                        p = project_root / (src_info['path'] if isinstance(src_info, dict) else src_info)
                        if p.is_file():
                            audio_path = p
                    if verify_audio_energy and audio_path is not None:
                        chk_s = curr_item['sourceEnd'] + keep
                        chk_e = curr_item['sourceEnd'] + target_gap
                        if chk_e - chk_s > 0.02:
                            try:
                                chunk, sr = load_audio_segment(audio_path, chk_s, chk_e)
                                if len(chunk) > 0:
                                    rms, _ = analyze_audio_energy(chunk, sr)
                                    if np.percentile(rms, 75) >= energy_threshold:
                                        is_noisy = True
                            except Exception:
                                is_noisy = True  # SEC-05 Fail-safe

                if is_noisy:
                    pauses_ledger.append({
                        'id': f"cross-{curr_item['id']}-{next_item['id']}",
                        'type': 'cross_keep',
                        'segment_id': f"{curr_item['id']} -> {next_item['id']}",
                        'start': round(curr_target_end, 3),
                        'end': round(next_item['targetStart'], 3),
                        'gap': round(target_gap, 3),
                        'retained': round(target_gap, 3),
                        'removed': 0.0,
                        'status': 'flagged_review',
                        'reason': 'pause_with_audio_activity',
                    })
                    review_queue.append({
                        'id': f"cross-{curr_item['id']}-{next_item['id']}",
                        'sourceId': curr_item['sourceId'],
                        'type': 'pause_with_audio_activity',
                        'start': round(curr_target_end, 3),
                        'end': round(next_item['targetStart'], 3),
                        'action': 'hold_and_review',
                    })
                else:
                    rem_frames = frame(target_gap, fps) - frame(keep, fps)
                    rem_s = round(rem_frames / fps, 3)
                    old_target = next_item['targetStart']
                    new_target = round(curr_target_end + keep, 3)
                    delta_shift = old_target - new_target
                    next_item['targetStart'] = new_target

                    # Ripple downstream
                    for down in track_keeps[i + 2:]:
                        down['targetStart'] = round(down['targetStart'] - delta_shift, 3)

                    pauses_ledger.append({
                        'id': f"cross-{curr_item['id']}-{next_item['id']}",
                        'type': 'cross_keep',
                        'segment_id': f"{curr_item['id']} -> {next_item['id']}",
                        'start': round(curr_target_end, 3),
                        'end': round(old_target, 3),
                        'gap': round(target_gap, 3),
                        'retained': round(keep, 3),
                        'removed': rem_s,
                        'status': 'cut',
                        'reason': 'cross_keep_gap_tightened',
                    })

    # Step 3: Recalculate frame-accurate timeline preserving natural gaps
    for track in tracks:
        cursor_frames = 0
        for item in new_timeline:
            if item['op'] == 'keep' and item.get('track', 'A-roll Final') == track:
                s_f = frame(item['sourceStart'], fps)
                e_f = frame(item['sourceEnd'], fps)
                dur_f = e_f - s_f
                t_f = frame(item['targetStart'], fps)
                if t_f < cursor_frames:
                    t_f = cursor_frames
                item['targetStartFrame'] = t_f
                item['targetStart'] = round(float(t_f) / fps, 6)
                item['sourceStartFrame'] = s_f
                item['sourceEndFrame'] = e_f
                item['durationFrames'] = dur_f
                cursor_frames = t_f + dur_f

    # Build tightened plan
    final_dur_frames = max((item['targetStartFrame'] + item['durationFrames']
                            for item in new_timeline if item['op'] == 'keep'), default=0)
    final_dur_s = round(final_dur_frames / fps, 3)

    tightened_plan = copy.deepcopy(plan)
    tightened_plan['timeline'] = new_timeline
    tightened_plan['durationFrames'] = final_dur_frames
    tightened_plan['reviewQueue'] = review_queue
    if 'planHash' in tightened_plan:
        del tightened_plan['planHash']  # SEC-06
    tightened_plan['planHash'] = hashlib.sha256(
        json.dumps(tightened_plan, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    # Calculate summary metrics with frame-level conservation
    interior_cuts = sum(1 for p in pauses_ledger if p['type'] == 'interior' and p['status'] == 'cut')
    head_cuts = sum(1 for p in pauses_ledger if p['type'] == 'head_silence' and p['status'] == 'cut')
    tail_cuts = sum(1 for p in pauses_ledger if p['type'] == 'tail_silence' and p['status'] == 'cut')
    cross_cuts = sum(1 for p in pauses_ledger if p['type'] == 'cross_keep' and p['status'] == 'cut')
    flagged_rev = sum(1 for p in pauses_ledger if p['status'] == 'flagged_review')
    total_removed = round(max(0, orig_dur_frames - final_dur_frames) / fps, 3)

    summary = {
        'total_pauses_checked': len(pauses_ledger),
        'total_pauses_cut': interior_cuts + head_cuts + tail_cuts + cross_cuts,
        'interior_pauses_cut': interior_cuts,
        'head_pauses_cut': head_cuts,
        'tail_pauses_cut': tail_cuts,
        'cross_keep_pauses_cut': cross_cuts,
        'pauses_flagged_review': flagged_rev,
        'original_duration_seconds': orig_dur_s,
        'tightened_duration_seconds': final_dur_s,
        'seconds_removed': total_removed,
    }

    report = {
        'summary': summary,
        'pauses': pauses_ledger,
    }

    return tightened_plan, report


def generate_pauses_report(report: Dict[str, Any], output_path: Path) -> Dict[str, Any]:
    """Write Rough/pauses-report.json and Rough/pauses-report.md."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    # Also generate markdown table
    md_path = output_path.with_suffix('.md')
    summary = report.get('summary', {})
    lines = [
        "# 停顿收紧报告 (Pause Tightening Report)",
        "",
        f"- 原视频时长: {summary.get('original_duration_seconds', 0.0):.2f}s",
        f"- 收紧后时长: {summary.get('tightened_duration_seconds', 0.0):.2f}s",
        f"- 累计移除停顿: {summary.get('seconds_removed', 0.0):.2f}s",
        f"- 剪除停顿数: {summary.get('total_pauses_cut', 0)} (句内 {summary.get('interior_pauses_cut', 0)} / 首尾 {summary.get('head_pauses_cut', 0) + summary.get('tail_pauses_cut', 0)} / 跨段 {summary.get('cross_keep_pauses_cut', 0)})",
        f"- 待人工复核停顿: {summary.get('pauses_flagged_review', 0)}",
        "",
        "| ID | 类型 | 片段 | 原始间隙 | 保留静音 | 移除时长 | 状态 | 原因 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for p in report.get('pauses', []):
        lines.append(
            f"| {p.get('id')} | {p.get('type')} | {p.get('segment_id')} | "
            f"{p.get('gap', 0.0):.2f}s | {p.get('retained', 0.0):.2f}s | {p.get('removed', 0.0):.2f}s | "
            f"{p.get('status')} | {p.get('reason')} |"
        )
    md_path.write_text("\n".join(lines), encoding='utf-8')

    return report
