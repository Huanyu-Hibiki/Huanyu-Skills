r"""
select_takes.py — Best-take selection for multi-take recordings.

When the speaker reads the same manuscript sentence several times, the global
alignment in align_to_manuscript.py keeps only ONE (leftmost) occurrence and
leaves every duplicate take in the timeline. This script finds ALL takes of
each manuscript sentence, scores them, and picks the best one so the EDL can
be built from chosen takes only.

Scoring per take:
  - match        : matched chars / sentence chars (text accuracy)
  - completeness : head & tail coverage (rejects partial/false starts)
  - pause_ratio  : interior silence >= pause_threshold / speech duration
  - rate_score   : chars per second within a natural band (zh ≈ 3-6 c/s)
  - boundary     : silence before/after the take (clean cut points)

Outputs (written to --output-dir, default <edit-dir>):
  - takes_decision.json   machine-readable decision (all takes + chosen + score)
  - takes_decision.md     human review table
  - finalKeeps_<stem>.json  sorted [{start, end, sentence_idx}] for chosen takes
                           (same shape align_to_manuscript --final-keeps expects)

Usage:
    python select_takes.py <video_project_dir> <subtitles_words.json> \
        [--output-dir <Rough>] [--manuscript-choice N] [--min-match 0.6] \
        [--pause-threshold 0.25]
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from align_to_manuscript import (
    ask_user_manuscript,
    find_manuscripts,
    flatten_whisper,
    parse_manuscript,
)

# Silence that separates takes or paragraphs (s). Mid-sentence hesitations
# below this stay inside one utterance chunk and are handled by scoring /
# tighten_pauses.py instead.
CHUNK_SILENCE = 1.2
# Natural Mandarin delivery, in normalized chars per second of speech
# (pauses excluded). Outside this band the take sounds hesitant or rushed.
RATE_BAND = (2.5, 7.0)
# Weights for the total score.
W_MATCH, W_COMPLETE, W_PAUSE, W_RATE = 0.40, 0.25, 0.20, 0.15
# Pre/post roll absorbed around first/last word when cutting (seconds).
LEAD_PAD, TAIL_PAD = 0.08, 0.30


def load_words(path: Path) -> List[dict]:
    raw = path.read_bytes()
    for enc in ("utf-8", "gbk", "cp936"):
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise SystemExit(f"cannot decode {path}")


# ─── candidate discovery ──────────────────────────────────────────────


def build_utterance_chunks(
    speech_words: List[dict],
    char_map: List[Tuple[int, int, float, float]],
) -> List[Tuple[int, int]]:
    """Split the transcript into utterance chunks at silences >= CHUNK_SILENCE.

    Returns [(char_start, char_end)] ranges into the flattened whisper char
    string. A take of one manuscript sentence is expected to fit inside 1-3
    consecutive chunks; separate takes of the same sentence always live in
    separate chunks because speakers pause between them.
    """
    if not speech_words:
        return []
    # char index of the first char of each word + one past the last char
    word_first_char: List[int] = []
    total_chars = len(char_map)
    for i in range(len(speech_words)):
        word_first_char.append(None)  # type: ignore[arg-type]
    prev_word = -1
    for ci, (w_idx, _pos, _s, _e) in enumerate(char_map):
        if w_idx != prev_word:
            word_first_char[w_idx] = ci
            prev_word = w_idx

    chunks: List[Tuple[int, int]] = []
    start_char = 0
    for i in range(len(speech_words) - 1):
        gap = speech_words[i + 1]["start"] - speech_words[i]["end"]
        if gap >= CHUNK_SILENCE:
            chunks.append((start_char, word_first_char[i + 1]))
            start_char = word_first_char[i + 1]
    chunks.append((start_char, total_chars))
    return chunks


def find_candidate_regions(
    sent_chars: str,
    chunks: List[Tuple[int, int]],
    max_windows: int = 3,
) -> List[Tuple[int, int]]:
    """Candidate regions = sliding windows of 1..max_windows consecutive
    utterance chunks whose total length plausibly fits the sentence."""
    n = len(sent_chars)
    lo, hi = max(1, int(n * 0.5)), int(n * 2.5)
    regions: List[Tuple[int, int]] = []
    for i in range(len(chunks)):
        for w in range(1, max_windows + 1):
            if i + w > len(chunks):
                break
            cs, _ = chunks[i]
            _, ce = chunks[i + w - 1]
            if lo <= ce - cs <= hi:
                regions.append((cs, ce))
    return regions


# ─── take extraction & scoring ────────────────────────────────────────


class Take:
    __slots__ = (
        "start", "end", "word_first", "word_last", "match", "completeness",
        "pause_ratio", "rate_score", "total", "speech_duration", "pause_time",
    )

    def __init__(self):
        self.start = self.end = 0.0
        self.word_first = self.word_last = -1
        self.match = self.completeness = self.pause_ratio = 0.0
        self.rate_score = self.total = 0.0
        self.speech_duration = self.pause_time = 0.0

    def to_json(self) -> dict:
        return {
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "score": {
                "total": round(self.total, 3),
                "match": round(self.match, 3),
                "completeness": round(self.completeness, 3),
                "pause_ratio": round(self.pause_ratio, 3),
                "rate_score": round(self.rate_score, 3),
            },
            "speech_duration": round(self.speech_duration, 3),
            "interior_pause_time": round(self.pause_time, 3),
        }


def _word_gap(words: List[dict], i: int) -> float:
    """Silence between speech word i and i+1."""
    if i + 1 >= len(words):
        return 0.0
    gap = words[i + 1]["start"] - words[i]["end"]
    return gap if gap > 0 else 0.0


def score_take(
    sent_chars: str,
    whisper_chars: str,
    char_map: List[Tuple[int, int, float, float]],
    region: Tuple[int, int],
    speech_words: List[dict],
    pause_threshold: float,
) -> Optional[Take]:
    """Align the sentence against one candidate region and score the take."""
    rs, re_ = region
    matcher = difflib.SequenceMatcher(None, sent_chars, whisper_chars[rs:re_], autojunk=False)
    matched_ids = set()
    for ms, ws, length in matcher.get_matching_blocks():
        for i in range(length):
            matched_ids.add(ms + i)
    if not matched_ids:
        return None

    match_ratio = len(matched_ids) / len(sent_chars) if sent_chars else 0.0

    # Completeness: head and tail quarters of the sentence must be covered.
    n = len(sent_chars)
    head = sum(1 for i in matched_ids if i < n * 0.25) / max(1, sum(1 for i in range(n) if i < n * 0.25))
    tail = sum(1 for i in matched_ids if i >= n * 0.75) / max(1, sum(1 for i in range(n) if i >= n * 0.75))
    completeness = min(head, tail)

    # Map sentence chars back to whisper char positions to find word range.
    pos_by_sent: dict[int, int] = {}
    for ms, ws, length in matcher.get_matching_blocks():
        for i in range(length):
            pos_by_sent[ms + i] = ws + i + rs
    first_pos = min(pos_by_sent[i] for i in matched_ids if i in pos_by_sent)
    last_pos = max(pos_by_sent[i] for i in matched_ids if i in pos_by_sent)
    word_first = char_map[first_pos][0]
    word_last = char_map[last_pos][0]

    w_start = speech_words[word_first]["start"]
    w_end = speech_words[word_last]["end"]
    duration = w_end - w_start
    if duration <= 0.05:
        return None

    # Interior pauses between the first and last word of the take.
    pause_time = 0.0
    for i in range(word_first, word_last):
        g = _word_gap(speech_words, i)
        if g >= pause_threshold:
            pause_time += g
    pause_ratio = pause_time / duration

    speech_time = max(0.05, duration - pause_time)
    cps = len(sent_chars) / speech_time
    lo, hi = RATE_BAND
    if lo <= cps <= hi:
        rate_score = 1.0
    elif cps < lo:
        rate_score = max(0.0, cps / lo)
    else:
        rate_score = max(0.0, 1.0 - (cps - hi) / hi)

    total = (
        W_MATCH * match_ratio
        + W_COMPLETE * completeness
        + W_PAUSE * (1.0 - min(1.0, pause_ratio * 4.0))
        + W_RATE * rate_score
    )

    take = Take()
    take.word_first, take.word_last = word_first, word_last
    take.start, take.end = w_start, w_end
    take.match, take.completeness = match_ratio, completeness
    take.pause_ratio, take.rate_score, take.total = pause_ratio, rate_score, total
    take.speech_duration, take.pause_time = duration, pause_time
    return take


def snap_boundaries(take: Take, speech_words: List[dict]) -> None:
    """Absorb a little surrounding silence so cuts land in dead air and
    plosives are not clipped (hard rule: prefer snapping to silence)."""
    prev_end = speech_words[take.word_first - 1]["end"] if take.word_first > 0 else None
    next_start = speech_words[take.word_last + 1]["start"] if take.word_last + 1 < len(speech_words) else None

    start = take.start
    if prev_end is not None and take.start - prev_end <= 0.6:
        start = max(prev_end, take.start - LEAD_PAD)
    else:
        start = take.start - LEAD_PAD

    end = take.end
    if next_start is not None and next_start - take.end <= 0.8:
        end = min(next_start, take.end + TAIL_PAD)
    else:
        end = take.end + TAIL_PAD

    take.start, take.end = max(0.0, start), end


def find_all_takes(
    sentence_chars: str,
    whisper_chars: str,
    char_map,
    speech_words: List[dict],
    chunks: List[Tuple[int, int]],
    pause_threshold: float,
    min_match: float,
) -> List[Take]:
    regions = find_candidate_regions(sentence_chars, chunks)
    takes: List[Take] = []
    for region in regions:
        t = score_take(
            sentence_chars, whisper_chars, char_map,
            region, speech_words, pause_threshold,
        )
        if t is not None and t.match >= min_match and t.completeness >= 0.5:
            takes.append(t)

    # Dedup overlapping detections of the same physical take (>50% overlap).
    takes.sort(key=lambda t: (t.start, t.end))
    deduped: List[Take] = []
    for t in takes:
        if deduped:
            p = deduped[-1]
            overlap = min(p.end, t.end) - max(p.start, t.start)
            if overlap > 0.5 * min(p.end - p.start, t.end - t.start):
                if t.total > p.total:
                    deduped[-1] = t
                continue
        deduped.append(t)
    for t in deduped:
        snap_boundaries(t, speech_words)
    return deduped


# ─── decision & outputs ───────────────────────────────────────────────


def choose_takes(sentences: List[dict], takes_per_sentence: List[List[Take]]) -> dict:
    """Pick one take per sentence in manuscript order, enforcing a
    non-overlapping, non-decreasing timeline. Deterministic."""
    chosen: List[Optional[Take]] = [None] * len(sentences)
    rejected: List[List[dict]] = [[] for _ in sentences]
    last_end = 0.0

    for idx, takes in enumerate(takes_per_sentence):
        valid = [t for t in takes if t.start >= last_end - 0.05]
        if not valid:
            for t in takes:
                rejected[idx].append({
                    **t.to_json(), "reason": "overlaps_previous_sentence",
                })
            continue
        best = max(valid, key=lambda t: (round(t.total, 3), -t.pause_time, -t.start))
        chosen[idx] = best
        last_end = best.end
        for t in takes:
            if t is not best:
                why = "lower_score"
                if t.start < last_end - 0.05 and t.start < best.start:
                    why = "overlaps_previous_sentence"
                rejected[idx].append({**t.to_json(), "reason": why})

    matched = sum(1 for c in chosen if c is not None)
    multi = sum(1 for ts in takes_per_sentence if len(ts) > 1)
    return {
        "chosen": chosen,
        "rejected": rejected,
        "summary": {
            "sentences": len(sentences),
            "matched": matched,
            "unmatched": len(sentences) - matched,
            "multi_take_sentences": multi,
            "takes_total": sum(len(ts) for ts in takes_per_sentence),
            "rejected_takes": sum(len(ts) for ts in takes_per_sentence) - matched,
        },
    }


def render_md(sentences, takes_per_sentence, decision, source_name) -> str:
    s = decision["summary"]
    lines = [
        "# Take 挑选决策",
        "",
        f"- 转录源: `{source_name}`",
        f"- 文稿句子: {s['sentences']}，匹配: {s['matched']}，未匹配: {s['unmatched']}",
        f"- 检测到 take 总数: {s['takes_total']}，多 take 句子: {s['multi_take_sentences']}，淘汰: {s['rejected_takes']}",
        "",
        "评分 = 0.40×文本匹配 + 0.25×首尾完整 + 0.20×停顿控制 + 0.15×语速自然度。",
        "",
        "| # | 文稿句（截断） | take数 | 选定 [start-end] | 得分 | 淘汰 take |",
        "|---|---|---:|---|---|---|",
    ]
    for i, sent in enumerate(sentences):
        takes = takes_per_sentence[i]
        ch = decision["chosen"][i]
        text = sent["text"][:24]
        if ch is None:
            lines.append(f"| {i} | {text} | {len(takes)} | ⚠ 未匹配 | - | - |")
            continue
        t = ch.to_json()
        sel = f"[{t['start']:.2f}-{t['end']:.2f}]"
        score = t["score"]["total"]
        rej = decision["rejected"][i]
        rej_str = "; ".join(
            f"[{r['start']:.2f}-{r['end']:.2f}]({r['score']['total']:.2f},{r['reason']})"
            for r in rej
        ) or "-"
        lines.append(f"| {i} | {text} | {len(takes)} | {sel} | {score:.2f} | {rej_str} |")
    lines.append("")
    lines.append("⚠ 未匹配的句子需要人工确认：可能没读，或 ASR 质量太差。")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Best-take selection from word-level transcript")
    ap.add_argument("video_dir", type=Path)
    ap.add_argument("words_json", type=Path, help="subtitles_words.json (flat word array)")
    ap.add_argument("--output-dir", type=Path, default=None, help="default: words_json.parent.parent")
    ap.add_argument("--manuscript-choice", type=int, default=0)
    ap.add_argument("--min-match", type=float, default=0.6)
    ap.add_argument("--pause-threshold", type=float, default=0.25)
    ap.add_argument("--source-name", default=None,
                    help="name used in finalKeeps_<name>.json (default: words file stem)")
    args = ap.parse_args()

    words_path = args.words_json
    out_dir = args.output_dir or words_path.parent.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    manuscripts = find_manuscripts(args.video_dir)
    if not manuscripts:
        sys.exit("no manuscript found in video scripts/")
    manuscript = ask_user_manuscript(manuscripts, args.manuscript_choice)
    sentences = parse_manuscript(manuscript)
    if not sentences:
        sys.exit("manuscript produced no sentences")

    words = load_words(words_path)
    speech_words = [w for w in words if not w.get("isGap")]
    if not speech_words:
        sys.exit("transcript has no speech words")

    whisper_chars, char_map = flatten_whisper(words)
    chunks = build_utterance_chunks(speech_words, char_map)

    # Normalized char string per sentence (same normalization as align_to_manuscript).
    from align_to_manuscript import _normalize_char
    sent_chars_list = ["".join(c for c in sent["text"] if _normalize_char(c)) for sent in sentences]

    takes_per_sentence: List[List[Take]] = []
    for chars in sent_chars_list:
        if not chars:
            takes_per_sentence.append([])
            continue
        takes = find_all_takes(
            chars, whisper_chars, char_map, speech_words,
            chunks, args.pause_threshold, args.min_match,
        )
        takes_per_sentence.append(takes)

    decision = choose_takes(sentences, takes_per_sentence)

    keeps = [
        {"start": round(t.start, 3), "end": round(t.end, 3), "sentence_idx": i}
        for i, t in enumerate(decision["chosen"]) if t is not None
    ]

    payload = {
        "source_transcript": str(words_path),
        "manuscript": str(manuscript),
        "pause_threshold": args.pause_threshold,
        "min_match": args.min_match,
        "summary": decision["summary"],
        "sentences": [
            {
                "idx": i,
                "text": sent["text"],
                "section": sent.get("section", ""),
                "chosen": t.to_json() if t else None,
                "rejected": decision["rejected"][i],
            }
            for i, (sent, t) in enumerate(zip(sentences, decision["chosen"]))
        ],
    }

    stem = args.source_name or words_path.stem
    (out_dir / "takes_decision.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "takes_decision.md").write_text(
        render_md(sentences, takes_per_sentence, decision, words_path.name), encoding="utf-8")
    (out_dir / f"finalKeeps_{stem}.json").write_text(
        json.dumps(keeps, ensure_ascii=False, indent=2), encoding="utf-8")

    s = decision["summary"]
    print(f"takes decision → {out_dir}/takes_decision.md")
    print(f"  sentences={s['sentences']} matched={s['matched']} unmatched={s['unmatched']}")
    print(f"  takes={s['takes_total']} rejected={s['rejected_takes']} multi-take={s['multi_take_sentences']}")
    print(f"  keeps → {out_dir}/finalKeeps_{stem}.json ({len(keeps)} segments)")


if __name__ == "__main__":
    main()
