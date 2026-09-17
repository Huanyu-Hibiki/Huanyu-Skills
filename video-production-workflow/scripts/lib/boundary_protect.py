"""Cut boundary protection with local text alignment, audio VAD/energy analysis, and stable silence snapping."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import numpy as np
import scipy.io.wavfile as wavfile
import subprocess


def _normalize_text(t: str) -> str:
    if not t:
        return ""
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", t).lower()


def verify_sentence_boundary(
    sentence_transcript: str,
    manuscript_sentence: str,
    full_context_text: Optional[str] = None,
    tail_chars: int = 3,
    head_chars: int = 3,
) -> Dict[str, Any]:
    """
    Verify that the transcript locally contains both the head and tail of the manuscript sentence.
    Does NOT use global text matching to avoid falsely passing when the same words appear elsewhere.
    """
    norm_tr = _normalize_text(sentence_transcript)
    norm_ms = _normalize_text(manuscript_sentence)

    if not norm_ms:
        return {
            "head_matched": True,
            "tail_matched": True,
            "expected_head": "",
            "expected_tail": "",
            "missing_head": "",
            "missing_tail": "",
            "norm_transcript": norm_tr,
            "norm_manuscript": norm_ms,
        }

    # Head check
    actual_head_len = min(head_chars, len(norm_ms))
    expected_head = norm_ms[:actual_head_len] if actual_head_len > 0 else ""
    head_matched = False
    if expected_head:
        head_window = norm_tr[:len(expected_head) + 2]
        if expected_head in head_window:
            head_matched = True
        elif len(norm_tr) >= actual_head_len:
            overlap = sum(1 for a, b in zip(norm_tr[:actual_head_len], expected_head) if a == b)
            if overlap / actual_head_len >= 0.75:
                head_matched = True

    # Tail check
    actual_tail_len = min(tail_chars, len(norm_ms))
    expected_tail = norm_ms[-actual_tail_len:] if actual_tail_len > 0 else ""
    tail_matched = False
    if expected_tail:
        tail_window = norm_tr[-len(expected_tail) - 2:] if len(norm_tr) >= len(expected_tail) else norm_tr
        if expected_tail in tail_window:
            tail_matched = True
        elif len(norm_tr) >= actual_tail_len:
            overlap = sum(1 for a, b in zip(reversed(norm_tr), reversed(expected_tail)) if a == b)
            if overlap / actual_tail_len >= 0.75:
                tail_matched = True

    return {
        "head_matched": head_matched,
        "tail_matched": tail_matched,
        "expected_head": expected_head,
        "expected_tail": expected_tail,
        "missing_head": "" if head_matched else expected_head,
        "missing_tail": "" if tail_matched else expected_tail,
        "norm_transcript": norm_tr,
        "norm_manuscript": norm_ms,
    }


def load_audio_segment(path: Path, start_s: float, end_s: float, target_sr: int = 16000) -> tuple[np.ndarray, int]:
    """Load audio segment as mono float32 array normalized to [-1.0, 1.0]."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {path}")

    # If already a WAV file, attempt direct read
    if path.suffix.lower() == ".wav":
        try:
            sr, data = wavfile.read(str(path))
            if data.ndim > 1:
                data = data.mean(axis=1)
            # convert to float32
            if data.dtype == np.int16:
                data = data.astype(np.float32) / 32768.0
            elif data.dtype == np.int32:
                data = data.astype(np.float32) / 2147483648.0
            s_idx = max(0, int(start_s * sr))
            e_idx = min(len(data), int(end_s * sr))
            chunk = data[s_idx:e_idx]
            return chunk, sr
        except Exception:
            pass

    # Use ffmpeg to extract specific chunk to raw PCM s16le
    duration = max(0.01, end_s - start_s)
    cmd = [
        "ffmpeg", "-v", "error", "-ss", f"{start_s:.3f}", "-t", f"{duration:.3f}",
        "-i", str(path), "-f", "s16le", "-acodec", "pcm_s16le", "-ar", str(target_sr),
        "-ac", "1", "pipe:1"
    ]
    res = subprocess.run(cmd, capture_output=True, check=True, timeout=30)
    data = np.frombuffer(res.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return data, target_sr


def analyze_audio_energy(
    audio: np.ndarray,
    sr: int,
    frame_ms: float = 20.0,
    hop_ms: float = 10.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate short-time RMS energy and timestamps."""
    frame_len = max(1, int(sr * frame_ms / 1000.0))
    hop_len = max(1, int(sr * hop_ms / 1000.0))

    if len(audio) < frame_len:
        rms = np.array([np.sqrt(np.mean(audio**2))] if len(audio) > 0 else [0.0])
        times = np.array([0.0])
        return rms, times

    # Vectorized sliding window RMS
    n_frames = 1 + (len(audio) - frame_len) // hop_len
    shape = (n_frames, frame_len)
    strides = (audio.strides[0] * hop_len, audio.strides[0])
    frames = np.lib.stride_tricks.as_strided(audio, shape=shape, strides=strides)
    rms = np.sqrt(np.mean(frames**2, axis=1) + 1e-9)
    times = np.arange(n_frames) * (hop_ms / 1000.0)
    return rms, times


def analyze_cut_boundary(
    audio_path: Path,
    candidate_end: float,
    sentence_text: str,
    manuscript_text: str,
    next_speech_start: Optional[float] = None,
    source_duration: Optional[float] = None,
    segment_id: Optional[str] = None,
    source_id: Optional[str] = None,
    tail_chars: int = 3,
    head_chars: int = 3,
    max_search_window: float = 1.0,
    silence_margin: float = 0.05,
    energy_threshold: float = 0.035,
) -> Dict[str, Any]:
    """
    Perform multi-signal boundary protection:
    1. Local text head and tail matching against manuscript.
    2. Audio VAD / Energy detection forward in bounded window.
    3. Stable silence boundary snapping.
    """
    audio_path = Path(audio_path)
    text_check = verify_sentence_boundary(
        sentence_transcript=sentence_text,
        manuscript_sentence=manuscript_text,
        tail_chars=tail_chars,
        head_chars=head_chars,
    )

    base_decision = {
        "id": segment_id,
        "sourceId": source_id,
        "sourcePath": str(audio_path),
        "sentence": sentence_text,
        "manuscript": manuscript_text,
        "candidate_end": candidate_end,
    }

    if not text_check["tail_matched"] or not text_check["head_matched"]:
        reasons = []
        if not text_check["tail_matched"]:
            reasons.append(f"tail_mismatch: missing '{text_check['missing_tail']}'")
        if not text_check["head_matched"]:
            reasons.append(f"head_mismatch: missing '{text_check['missing_head']}'")
        reason_str = "; ".join(reasons)
        return {
            **base_decision,
            "safe_end": candidate_end,
            "tail_preserved": False,
            "head_preserved": text_check["head_matched"],
            "status": "review_required",
            "reason": reason_str,
            "reviewQueueItem": {
                "id": segment_id or "boundary-check",
                "sourceId": source_id,
                "sourcePath": str(audio_path),
                "type": "cut_boundary_text_mismatch",
                "sentence": sentence_text,
                "missing_tail": text_check["missing_tail"],
                "missing_head": text_check["missing_head"],
                "candidate_end": candidate_end,
                "action": "hold_and_review",
            },
        }

    # Bounded forward search
    search_start = max(0.0, candidate_end - 0.2)
    max_end = candidate_end + max_search_window
    if next_speech_start is not None:
        max_end = min(max_end, max(candidate_end, next_speech_start - 0.05))
    if source_duration is not None:
        max_end = min(max_end, source_duration)

    audio_chunk, sr = load_audio_segment(audio_path, search_start, max_end)
    if len(audio_chunk) == 0:
        return {
            **base_decision,
            "safe_end": candidate_end,
            "tail_preserved": False,
            "head_preserved": False,
            "status": "review_required",
            "reason": "audio_empty_or_unreadable",
            "reviewQueueItem": {
                "id": segment_id or "boundary-check",
                "sourceId": source_id,
                "sourcePath": str(audio_path),
                "type": "audio_empty",
                "sentence": sentence_text,
                "candidate_end": candidate_end,
                "action": "hold_and_review",
            },
        }

    rms, times = analyze_audio_energy(audio_chunk, sr)
    absolute_times = search_start + times

    # Dynamic noise floor estimation: 15th percentile of energy, capped at energy_threshold
    # to avoid threshold explosion when the window is predominantly speech
    raw_floor = float(np.percentile(rms, 15)) if len(rms) > 0 else 0.0
    noise_floor = min(raw_floor, energy_threshold)
    active_threshold = max(energy_threshold, noise_floor * 2.5)

    # Find last voice activity in window
    active_mask = rms >= active_threshold
    if np.any(active_mask):
        last_active_idx = np.where(active_mask)[0][-1]
        speech_end_s = float(absolute_times[last_active_idx])
    else:
        speech_end_s = candidate_end

    # Snap into stable silence after speech ends
    snapped_end = speech_end_s + silence_margin

    # If next speech is close, constrain boundary
    if next_speech_start is not None and snapped_end >= next_speech_start:
        snapped_end = max(candidate_end, next_speech_start - 0.05)

    # If source duration is constrained, bound snapped_end
    if source_duration is not None and snapped_end > source_duration:
        snapped_end = min(candidate_end, source_duration)

    # If candidate_end was already past speech end into silence, keep candidate_end or safe extension
    final_end = max(candidate_end, snapped_end)

    # Check for boundary ambiguity:
    # 1. Voice activity still loud at the window boundary (did not fade into silence)
    # 2. Speech ends too close to next speech start (< silence_margin gap, risk of collision)
    # 3. Speech ends too close to source end (< silence_margin gap, risk of truncation)
    ambiguous = False
    ambiguity_reasons = []
    if np.any(active_mask) and (last_active_idx >= len(rms) - 2):
        ambiguous = True
        ambiguity_reasons.append("speech_continues_at_search_boundary")
    if next_speech_start is not None and (next_speech_start - speech_end_s < silence_margin):
        ambiguous = True
        ambiguity_reasons.append("speech_collides_with_next_speech")
    if source_duration is not None and (source_duration - speech_end_s < silence_margin):
        ambiguous = True
        ambiguity_reasons.append("speech_continues_at_source_end")

    status = "review_required" if ambiguous else "approved"
    reason = "; ".join(ambiguity_reasons) if ambiguous else "snapped_to_stable_silence"

    result = {
        **base_decision,
        "safe_end": round(final_end, 3),
        "speech_end": round(speech_end_s, 3),
        "tail_preserved": True,
        "head_preserved": True,
        "status": status,
        "reason": reason,
    }

    if ambiguous:
        result["reviewQueueItem"] = {
            "id": segment_id or "boundary-check",
            "sourceId": source_id,
            "sourcePath": str(audio_path),
            "type": "cut_boundary_ambiguous",
            "sentence": sentence_text,
            "candidate_end": candidate_end,
            "speech_end": speech_end_s,
            "action": "hold_and_review",
        }

    return result


def generate_boundary_report(decisions: List[Dict[str, Any]], output_path: Path) -> Dict[str, Any]:
    """Write Rough/cut-boundary-report.json summarizing boundary safety analysis."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total = len(decisions)
    approved = sum(1 for d in decisions if d.get("status") == "approved")
    review_req = total - approved
    extensions = [d["safe_end"] - d["candidate_end"] for d in decisions if "safe_end" in d and "candidate_end" in d]
    avg_extension = (sum(extensions) / len(extensions)) if extensions else 0.0

    report = {
        "summary": {
            "total_checked": total,
            "approved": approved,
            "review_required": review_req,
            "avg_extension_seconds": round(avg_extension, 3),
        },
        "boundaries": decisions,
    }

    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
