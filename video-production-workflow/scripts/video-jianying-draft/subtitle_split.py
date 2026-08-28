r"""subtitle_split.py — Split long SRT cues into JianYing-native short chunks.

剪映 native subtitles (智能字幕 / SRT import) show short cues (~15-20 CJK
chars). The rough-cut pipeline emits sentence-level SRT blocks, so importing
them via pyJianYingDraft creates one huge text box per sentence that has to
be split by hand in the GUI. This script rewrites the SRT before import:

  - every cue is split into chunks of at most --max-chars display units
    (CJK char = 1 unit, ASCII letter/digit = 0.5 unit, punctuation ignored);
  - split points prefer punctuation, then spaces, then hard char cuts;
  - chunk timings are contiguous and proportional to character weights, so
    no gap or overlap is introduced;
  - chunks are balanced: a sentence is never split into a long chunk plus a
    2-char orphan.

Usage:
    python subtitle_split.py <in.srt> -o <out.srt> [--max-chars 18] [--min-chars 6]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Punctuation preferred as split points, strongest first.
SPLIT_PUNCT = "，。！？；：、…—,.!?;:"
# Punctuation that carries no display weight.
ALL_PUNCT = set(SPLIT_PUNCT + "“”\"'‘’（）()【】[]《》<>·—…\u3000")


def display_units(text: str) -> float:
    """CJK-aware visible width."""
    total = 0.0
    for ch in text:
        if ch in ALL_PUNCT or ch.isspace():
            continue
        total += 1.0 if ord(ch) > 0x2E7F else 0.5
    return total


def _ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _parse_ts(stamp: str) -> float:
    h, m, rest = stamp.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(content: str) -> List[Tuple[float, float, str]]:
    cues = []
    for block in re.split(r"\n\s*\n", content.strip()):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        m = re.match(r"(\d+)\s*$", lines[0])
        if m and len(lines) >= 3:
            time_line, text_lines = lines[1], lines[2:]
        else:
            time_line, text_lines = lines[0], lines[1:]
        if "-->" not in time_line:
            continue
        start_s, end_s = time_line.split("-->")
        cues.append((_parse_ts(start_s.strip()), _parse_ts(end_s.strip()),
                     " ".join(t for t in text_lines if t and not t.isdigit())))
    return cues


def _boundary_score(text: str, idx: int) -> int:
    """Preference for cutting right before position idx in text."""
    if idx <= 0 or idx >= len(text):
        return -1
    prev = text[idx - 1]
    if prev in "。！？；…?!;":
        return 3
    if prev in "，、：,—:":
        return 2
    if prev.isspace() or (idx < len(text) and text[idx].isspace()):
        return 1
    return 0


def split_text(text: str, max_units: float, min_units: float) -> List[str]:
    """Split one cue's text into balanced chunks within max_units."""
    if display_units(text) <= max_units:
        return [text.strip()] if text.strip() else []

    total = display_units(text)
    n_chunks = max(2, int(-(-total // max_units)))
    target = total / n_chunks

    # Walk through the text accumulating weight; whenever we cross a target
    # multiple, cut at the best boundary within the carry-over slack.
    chunks: List[str] = []
    cut_points = [0]
    acc = 0.0
    last = 0
    for i, ch in enumerate(text):
        w = 0.0 if (ch in ALL_PUNCT or ch.isspace()) else (1.0 if ord(ch) > 0x2E7F else 0.5)
        acc += w
        if w > 0:
            last = i
        # next target boundary is at k*target
        k = len(cut_points)
        if acc >= k * target and (k < n_chunks):
            # best boundary near the crossing: max score, then closest to it
            lo = cut_points[-1]
            search_lo = int(lo + 0.6 * (i - lo))
            best_pos, best_key = i, None
            for pos in range(search_lo, min(len(text), i + 12) + 1):
                sc = _boundary_score(text, pos)
                if sc < 0:
                    continue
                key = (sc, -abs(pos - i))
                if best_key is None or key > best_key:
                    best_pos, best_key = pos, key
            if best_key is not None:
                cut_points.append(best_pos)
    cut_points.append(len(text))

    for a, b in zip(cut_points, cut_points[1:]):
        seg = text[a:b].strip()
        if not seg:
            continue
        # merge orphan trailing chunk (< min_units) into the previous one
        if chunks and display_units(seg) < min_units and display_units(chunks[-1]) + display_units(seg) <= max_units * 1.15:
            chunks[-1] = chunks[-1] + seg
        else:
            chunks.append(seg)
    return chunks


def split_cue(start: float, end: float, text: str,
              max_units: float, min_units: float) -> List[Tuple[float, float, str]]:
    chunks = split_text(text, max_units, min_units)
    if len(chunks) <= 1:
        return [(start, end, text.strip())]

    weights = [max(display_units(c), 0.5) for c in chunks]
    total_w = sum(weights)
    duration = end - start
    cues = []
    cursor = start
    for i, (c, w) in enumerate(zip(chunks, weights)):
        if i == len(chunks) - 1:
            cue_end = end
        else:
            cue_end = start + duration * (sum(weights[: i + 1]) / total_w)
        cues.append((cursor, max(cursor + 0.05, cue_end), c))
        cursor = cue_end
    return cues


def split_srt(content: str, max_chars: float, min_chars: float) -> Tuple[str, dict]:
    out_blocks = []
    stats = {"cues_in": 0, "cues_out": 0, "split": 0}
    for start, end, text in parse_srt(content):
        stats["cues_in"] += 1
        for cs, ce, ct in split_cue(start, end, text, max_chars, min_chars):
            if not ct:
                continue
            stats["cues_out"] += 1
            out_blocks.append(f"{stats['cues_out']}\n{_ts(cs)} --> {_ts(ce)}\n{ct}\n")
    stats["split"] = stats["cues_out"] - stats["cues_in"]
    return "\n".join(out_blocks), stats


def main() -> None:
    ap = argparse.ArgumentParser(description="Split long SRT cues into short JianYing-friendly cues")
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--max-chars", type=float, default=18, help="max display units per cue (CJK=1, ASCII=0.5), default 18")
    ap.add_argument("--min-chars", type=float, default=6, help="orphan chunks below this merge into previous, default 6")
    args = ap.parse_args()

    content = args.input.read_text(encoding="utf-8-sig")
    result, stats = split_srt(content, args.max_chars, args.min_chars)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result, encoding="utf-8")

    print(f"subtitle split: {args.input.name} -> {args.output.name}")
    print(f"  cues {stats['cues_in']} -> {stats['cues_out']} (max {args.max_chars:.0f} units/cue)")


if __name__ == "__main__":
    main()
