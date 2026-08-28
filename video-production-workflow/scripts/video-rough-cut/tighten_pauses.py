r"""tighten_pauses.py — Remove dead air inside kept take segments.

The rough cut keeps whole takes, so interior hesitations (false starts,
breaths, "呃…", long thinking pauses) survive into the JianYing draft and
the user has to cut them by hand. This script walks each keep segment from
finalKeeps_<source>.json, finds interior silences >= --threshold (default
0.35s), and shortens each one to --keep seconds (default 0.25s) by splitting
the segment at the word boundaries around the pause. Cut points stay on word
boundaries; the render pipeline already bakes 30ms audio fades per segment.

Outputs (written to --output-dir, default keeps file's directory):
  - keeps_tightened_<stem>.json  sub-segments [{start, end, sentence_idx, note}]
  - pauses_report.md             what was removed, per sentence
  - edl_from_takes.json          EDL skeleton (render.py-compatible) if
                                 --source-media is given

Usage:
    python tighten_pauses.py <subtitles_words.json> \
        --keeps <Rough>/finalKeeps_<stem>.json \
        [--threshold 0.35] [--keep 0.25] [--min-gain 0.12] \
        [--source-media <path-to-raw-video>]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List


def load_json(path: Path):
    raw = path.read_bytes()
    for enc in ("utf-8", "gbk", "cp936"):
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise SystemExit(f"cannot decode {path}")


def speech_words_of(words: List[dict]) -> List[dict]:
    return [w for w in words if not w.get("isGap")]


def tighten_segment(
    seg: dict,
    speech_words: List[dict],
    threshold: float,
    keep: float,
    min_gain: float,
) -> tuple[List[dict], List[dict]]:
    """Split one keep segment around long interior pauses.

    Returns (sub_segments, removed_pauses). Each removed pause keeps its
    first `keep` seconds (natural breath before the cut) and drops the rest.
    Pauses that would gain less than min_gain are left alone.
    """
    s, e = float(seg["start"]), float(seg["end"])
    inside = [w for w in speech_words if w["start"] >= s - 1e-6 and w["end"] <= e + 1e-6]
    if len(inside) < 2:
        return [dict(seg, note="single word")], []

    # Candidate pauses: silence between consecutive words inside the segment.
    pauses = []
    for a, b in zip(inside, inside[1:]):
        gap = b["start"] - a["end"]
        if gap >= threshold and gap - keep >= min_gain:
            pauses.append({"start": a["end"], "end": b["start"], "gap": gap})

    if not pauses:
        return [dict(seg, note="clean")], []

    sub_segments: List[dict] = []
    cursor = s
    for p in pauses:
        cut_from = p["start"] + keep  # keep the breath, drop the dead tail
        if cut_from - cursor > 0.15:
            sub_segments.append({
                "start": round(cursor, 3),
                "end": round(cut_from, 3),
                "sentence_idx": seg.get("sentence_idx"),
                "note": "speech",
            })
        cursor = p["end"]
    if e - cursor > 0.15:
        sub_segments.append({
            "start": round(cursor, 3),
            "end": round(e, 3),
            "sentence_idx": seg.get("sentence_idx"),
            "note": "speech",
        })

    removed = [{**p, "removed": round(p["gap"] - keep, 3)} for p in pauses]
    return sub_segments, removed


def main() -> None:
    ap = argparse.ArgumentParser(description="Tighten interior pauses in keep segments")
    ap.add_argument("words_json", type=Path)
    ap.add_argument("--keeps", type=Path, required=True, help="finalKeeps_<stem>.json from select_takes")
    ap.add_argument("--output-dir", type=Path, default=None, help="default: keeps file's directory")
    ap.add_argument("--threshold", type=float, default=0.35, help="pause length to trigger a cut (s)")
    ap.add_argument("--keep", type=float, default=0.25, help="seconds of each pause to keep (s)")
    ap.add_argument("--min-gain", type=float, default=0.12, help="skip cuts that save less than this (s)")
    ap.add_argument("--source-media", type=Path, default=None, help="raw video path, enables EDL skeleton")
    args = ap.parse_args()

    keeps_path = args.keeps
    out_dir = args.output_dir or keeps_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    words = load_json(args.words_json)
    keeps = load_json(keeps_path)
    if not keeps:
        raise SystemExit("keeps file is empty — run select_takes.py first")

    speech_words = speech_words_of(words)

    all_sub_segments: List[dict] = []
    per_sentence = []
    total_removed = 0.0
    for seg in sorted(keeps, key=lambda k: k["start"]):
        subs, removed = tighten_segment(seg, speech_words, args.threshold, args.keep, args.min_gain)
        all_sub_segments.extend(subs)
        removed_total = sum(r["removed"] for r in removed)
        total_removed += removed_total
        per_sentence.append({
            "sentence_idx": seg.get("sentence_idx"),
            "segment": [round(float(seg["start"]), 2), round(float(seg["end"]), 2)],
            "sub_segments": len(subs),
            "pauses_cut": len(removed),
            "removed_seconds": round(removed_total, 3),
            "pauses": removed,
        })

    stem = keeps_path.stem.replace("finalKeeps_", "")
    out_json = out_dir / f"keeps_tightened_{stem}.json"
    out_json.write_text(json.dumps(all_sub_segments, ensure_ascii=False, indent=2), encoding="utf-8")

    # Human-readable report.
    orig_dur = sum(float(k["end"]) - float(k["start"]) for k in keeps)
    new_dur = sum(s["end"] - s["start"] for s in all_sub_segments)
    lines = [
        "# 停顿收紧报告",
        "",
        f"- 阈值: ≥{args.threshold}s 的句中停顿收紧到保留 {args.keep}s",
        f"- 保留段: {len(keeps)} → 子片段: {len(all_sub_segments)}",
        f"- 总时长: {orig_dur:.1f}s → {new_dur:.1f}s（移除 {total_removed:.1f}s 死停顿）",
        "",
        "| 句号 | 原片段 | 子片段 | 剪掉停顿 | 移除时长 |",
        "|---:|---|---:|---:|---:|",
    ]
    for row in per_sentence:
        seg = row["segment"]
        lines.append(
            f"| {row['sentence_idx']} | [{seg[0]:.1f}-{seg[1]:.1f}] "
            f"| {row['sub_segments']} | {row['pauses_cut']} | {row['removed_seconds']:.2f}s |"
        )
    report_path = out_dir / "pauses_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    # Optional EDL skeleton compatible with render.py.
    if args.source_media is not None:
        edl = {
            "sources": {stem: str(args.source_media.resolve())},
            "grade": "auto",
            "ranges": [
                {"source": stem, "start": s["start"], "end": s["end"],
                 "sentence_idx": s.get("sentence_idx"), "note": s.get("note", "")}
                for s in all_sub_segments
            ],
        }
        (out_dir / "edl_from_takes.json").write_text(
            json.dumps(edl, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"edl skeleton → {out_dir}/edl_from_takes.json")

    print(f"tightened keeps → {out_json}")
    print(f"  segments {len(keeps)} → {len(all_sub_segments)}, removed {total_removed:.2f}s of pauses")
    print(f"  report → {report_path}")


if __name__ == "__main__":
    main()
