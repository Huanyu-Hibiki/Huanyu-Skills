r"""
Align Whisper transcript to manuscript for calibrated sentence segmentation.

Replaces gen_analysis.js when a manuscript is available. Uses the manuscript
as ground truth for text content and sentence structure, while keeping
Whisper timestamps for timing.

Auto-detects manuscript files in scripts/ directory.
If multiple files found, asks user to choose.

Usage:
    python align_to_manuscript.py <video_project_dir> <subtitles_words.json> <output_dir>

Example:
    python align_to_manuscript.py \
        "<视频项目根>\把8个AI Agent塞进明代朝廷，我当了回朱元璋" \
        "Rough\review\OBS\1_转录\subtitles_words.json" \
        "Rough\review\OBS\2_分析"
"""
import json
import re
import sys
import difflib
from pathlib import Path
from typing import List, Tuple, Optional


# ─── Manuscript parsing ───────────────────────────────────────────────

def find_manuscripts(video_dir: Path) -> List[Path]:
    """Auto-detect manuscript .md files in the project script directories."""
    candidate_dirs = [video_dir / "video scripts", video_dir / "scripts"]
    md_files = []
    for scripts_dir in candidate_dirs:
        if scripts_dir.is_dir():
            md_files.extend(scripts_dir.glob("*.md"))
    md_files = sorted(set(md_files))
    # Filter out obvious non-manuscript files (README, templates, etc.)
    return [f for f in md_files if not f.name.startswith("README") and not f.name.startswith("template")]


def ask_user_manuscript(manuscripts: List[Path], choice: int = 0) -> Path:
    """Ask user to choose when multiple manuscripts found.
    
    Args:
        manuscripts: List of manuscript paths
        choice: If >0, use 1-based index directly (non-interactive mode)
    """
    if len(manuscripts) == 1:
        return manuscripts[0]
    if choice > 0 and choice <= len(manuscripts):
        return manuscripts[choice - 1]
    # Interactive mode
    print(f"\n找到 {len(manuscripts)} 个文稿文件：")
    for i, f in enumerate(manuscripts):
        print(f"  [{i + 1}] {f.name}")
    while True:
        user_input = input(f"\n选择文稿编号 (1-{len(manuscripts)}): ").strip()
        if user_input.isdigit() and 1 <= int(user_input) <= len(manuscripts):
            return manuscripts[int(user_input) - 1]


def parse_manuscript(manuscript_path: Path) -> List[dict]:
    """
    Parse manuscript markdown into spoken sentences.
    
    Extracts ONLY spoken text, skipping:
    - Section headers (# ...)
    - Visual cues 【画面：...】 【字幕卡：...】
    - Markdown formatting (**bold**, //, etc.)
    - Empty lines
    
    Returns list of {text, section, sentence_idx} dicts.
    """
    content = manuscript_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    
    sentences = []
    current_section = ""
    raw_text_buffer = ""
    
    for line in lines:
        stripped = line.strip()
        
        # Section header
        if stripped.startswith("#"):
            current_section = stripped.lstrip("#").strip()
            continue
        
        # Skip visual cues
        if stripped.startswith("【") or stripped.startswith("---"):
            continue
        
        # Skip empty lines (but flush buffer on empty)
        if not stripped:
            if raw_text_buffer:
                _flush_sentences(sentences, raw_text_buffer, current_section)
                raw_text_buffer = ""
            continue
        
        # Remove bold markers
        cleaned = re.sub(r"\*\*", "", stripped)
        # Remove pause markers
        cleaned = cleaned.replace("//", "")
        
        raw_text_buffer += cleaned
    
    # Flush remaining
    if raw_text_buffer:
        _flush_sentences(sentences, raw_text_buffer, current_section)
    
    return sentences


def _flush_sentences(sentences: list, text: str, section: str):
    """Split accumulated text into sentences by Chinese punctuation.

    Long sentences (>32 chars) are further split at commas so SRT cues stay
    subtitle-friendly; jianying.py's subtitle splitter is the second line of
    defense, but keeping cues short here makes every downstream consumer
    (review pages, caption correction) easier to read too.
    """
    # Split by sentence-ending punctuation, keep the punctuation
    parts = re.split(r"(?<=[。！？])", text)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Further split by commas if the segment is long (>32 chars)
        if len(part) > 32:
            sub_parts = re.split(r"(?<=[，；])", part)
            for sp in sub_parts:
                sp = sp.strip()
                if sp:
                    sentences.append({
                        "text": sp,
                        "section": section,
                        "idx": len(sentences),
                    })
        else:
            sentences.append({
                "text": part,
                "section": section,
                "idx": len(sentences),
            })


# ─── Cut-timeline remapping ───────────────────────────────────────────

def remap_words_to_cut_timeline(
    words: List[dict],
    final_keeps: List[dict],
) -> List[dict]:
    """
    Filter words to only those within finalKeeps segments, and remap
    timestamps from the original recording timeline to the cut timeline.
    
    Example:
      finalKeeps = [{start:0, end:10}, {start:15, end:25}]
      Word at original time 17 → new time 12 (10 + (17-15))
    
    Args:
        words: Original subtitles_words.json array (with isGap entries)
        final_keeps: List of {start, end} keep segments (sorted)
    
    Returns:
        New words array with remapped timestamps, only kept segments
    """
    if not final_keeps:
        return words
    
    # Sort keeps by start time
    keeps = sorted(final_keeps, key=lambda k: k["start"])
    
    # Build remapped word list
    result = []
    cumulative_kept = 0.0
    
    for keep in keeps:
        ks = keep["start"]
        ke = keep["end"]
        keep_duration = ke - ks
        
        for w in words:
            w_start = w.get("start", 0)
            w_end = w.get("end", 0)
            
            # Word must be fully within the keep segment
            if w_start >= ks and w_end <= ke:
                new_word = dict(w)
                new_word["start"] = cumulative_kept + (w_start - ks)
                new_word["end"] = cumulative_kept + (w_end - ks)
                result.append(new_word)
            # Word partially overlaps — keep the overlapping part
            elif w_start < ke and w_end > ks and w.get("isGap"):
                # Keep gap if it overlaps
                gap_start = max(w_start, ks)
                gap_end = min(w_end, ke)
                if gap_end > gap_start:
                    new_word = dict(w)
                    new_word["start"] = cumulative_kept + (gap_start - ks)
                    new_word["end"] = cumulative_kept + (gap_end - ks)
                    result.append(new_word)
        
        cumulative_kept += keep_duration
    
    return result


# ─── Whisper flattening ───────────────────────────────────────────────

def flatten_whisper(words: List[dict]) -> Tuple[str, List[Tuple[int, int, float, float]]]:
    """
    Flatten Whisper words into a character sequence with back-references.
    
    Returns:
        (normalized_text, char_map)
        where char_map[i] = (word_index, char_pos_in_word, start_time, end_time)
    """
    chars = []
    char_map = []
    
    for w_idx, w in enumerate(words):
        if w.get("isGap"):
            continue
        text = w.get("text", "")
        start = w.get("start", 0)
        end = w.get("end", 0)
        for c_idx, c in enumerate(text):
            normalized = _normalize_char(c)
            if normalized:
                chars.append(normalized)
                char_map.append((w_idx, c_idx, start, end))
    
    return "".join(chars), char_map


def _normalize_char(c: str) -> str:
    """Normalize a character for matching. Returns empty string to skip."""
    # Skip whitespace
    if c.isspace():
        return ""
    # Skip punctuation
    if c in "，。！？、；：""''（）《》【】""''…—·.,!?;:\"'()[]{}/":
        return ""
    # Keep everything else
    return c


# ─── Alignment ────────────────────────────────────────────────────────

def align_manuscript_to_whisper(
    manuscript_sentences: List[dict],
    whisper_chars: str,
    char_map: List[Tuple[int, int, float, float]],
) -> List[dict]:
    """
    Align each manuscript sentence to a range of Whisper word indices.
    
    Uses difflib.SequenceMatcher for character-level alignment.
    Handles ASR errors (substitutions), ad-libs (insertions), and skips (deletions).
    
    Returns manuscript_sentences with added fields:
        - startIdx: first Whisper word index
        - endIdx: last Whisper word index
        - start_time: sentence start time
        - end_time: sentence end time
        - confidence: alignment confidence (0-1)
        - matched: whether a match was found
    """
    # Build manuscript character sequence
    ms_chars = ""
    ms_sentence_ranges = []  # (start_char, end_char) for each sentence
    for sent in manuscript_sentences:
        start_char = len(ms_chars)
        for c in sent["text"]:
            normalized = _normalize_char(c)
            if normalized:
                ms_chars += normalized
        end_char = len(ms_chars)
        ms_sentence_ranges.append((start_char, end_char))
    
    # Run SequenceMatcher
    matcher = difflib.SequenceMatcher(None, ms_chars, whisper_chars, autojunk=False)
    
    # Build mapping: manuscript char index → whisper char index
    ms_to_whisper = {}  # ms_char_idx → whisper_char_idx
    for block in matcher.get_matching_blocks():
        ms_start, wh_start, length = block
        for i in range(length):
            ms_to_whisper[ms_start + i] = wh_start + i
    
    # For each sentence, find the word index range
    for sent_idx, (ms_start, ms_end) in enumerate(ms_sentence_ranges):
        sent = manuscript_sentences[sent_idx]
        
        # Find whisper char indices for this sentence's chars
        wh_char_indices = []
        for ms_c in range(ms_start, ms_end):
            if ms_c in ms_to_whisper:
                wh_char_indices.append(ms_to_whisper[ms_c])
        
        if not wh_char_indices:
            # No match found — this sentence wasn't spoken or alignment failed
            sent["startIdx"] = -1
            sent["endIdx"] = -1
            sent["start_time"] = 0
            sent["end_time"] = 0
            sent["confidence"] = 0.0
            sent["matched"] = False
            continue
        
        # Map whisper char indices to word indices
        wh_first = wh_char_indices[0]
        wh_last = wh_char_indices[-1]
        word_start = char_map[wh_first][0]  # word index of first matched char
        word_end = char_map[wh_last][0]     # word index of last matched char
        
        # Times
        start_time = char_map[wh_first][2]
        end_time = char_map[wh_last][3]
        
        # Confidence = matched chars / total sentence chars
        total_chars = ms_end - ms_start
        matched_chars = len(wh_char_indices)
        confidence = matched_chars / total_chars if total_chars > 0 else 0
        
        sent["startIdx"] = word_start
        sent["endIdx"] = word_end
        sent["start_time"] = start_time
        sent["end_time"] = end_time
        sent["confidence"] = round(confidence, 3)
        sent["matched"] = True
    
    return manuscript_sentences


# ─── Output generation ────────────────────────────────────────────────

def generate_outputs(
    aligned_sentences: List[dict],
    words: List[dict],
    output_dir: Path,
    video_dir: Path = None,
):
    """Generate analysis.txt, sentence_map.json, auto_selected.json, SRT."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Filter to matched sentences only
    matched = [s for s in aligned_sentences if s.get("matched")]
    unmatched = [s for s in aligned_sentences if not s.get("matched")]
    
    # analysis.txt: manuscript text (corrected)
    lines = []
    for i, sent in enumerate(matched):
        lines.append(f"{i}: {sent['text']}")
    (output_dir / "analysis.txt").write_text("\n".join(lines), encoding="utf-8")
    
    # sentence_map.json: word index ranges
    sentence_map = [{"startIdx": s["startIdx"], "endIdx": s["endIdx"]} for s in matched]
    (output_dir / "sentence_map.json").write_text(
        json.dumps(sentence_map, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    
    # auto_selected.json: silence gap indices (same as gen_analysis.js)
    gap_indices = [i for i, w in enumerate(words) if w.get("isGap") and (w.get("end", 0) - w.get("start", 0)) >= 0.2]
    (output_dir / "auto_selected.json").write_text(
        json.dumps(gap_indices, indent=2), encoding="utf-8"
    )
    
    # SRT subtitle file — output to Sub/ directory
    if video_dir:
        sub_dir = video_dir / "Sub"
        sub_dir.mkdir(parents=True, exist_ok=True)
        srt_path = sub_dir / "master.srt"
        srt_content = _generate_srt(matched)
        srt_path.write_text(srt_content, encoding="utf-8")
        print(f"  SRT: {srt_path} ({len(matched)} entries)")
    
    # alignment_report.json: detailed alignment info
    report = {
        "total_manuscript_sentences": len(aligned_sentences),
        "matched": len(matched),
        "unmatched": len(unmatched),
        "avg_confidence": round(sum(s["confidence"] for s in matched) / len(matched), 3) if matched else 0,
        "unmatched_sentences": [
            {"text": s["text"][:80], "section": s["section"]}
            for s in unmatched
        ],
        "low_confidence_sentences": [
            {
                "idx": s["idx"],
                "text": s["text"][:80],
                "section": s["section"],
                "confidence": s["confidence"],
                "start_time": s.get("start_time", 0),
            }
            for s in matched if s["confidence"] < 0.5
        ],
    }
    (output_dir / "alignment_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    
    return report


def _format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds * 1000) % 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def _generate_srt(sentences: List[dict]) -> str:
    """Generate SRT subtitle content from aligned sentences."""
    entries = []
    for i, sent in enumerate(sentences):
        start = sent.get("start_time", 0)
        end = sent.get("end_time", start + 1)
        
        # Minimum display duration: 1 second
        if end - start < 1.0:
            end = start + 1.0
        
        # Cap gap to next subtitle at 0.5s
        if i + 1 < len(sentences):
            next_start = sentences[i + 1].get("start_time", end)
            if next_start - end < 0.5:
                end = next_start - 0.05 if next_start > start + 0.3 else end
        
        text = sent["text"].strip()
        entries.append(f"{i + 1}\n{_format_srt_time(start)} --> {_format_srt_time(end)}\n{text}\n")
    
    return "\n".join(entries)


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return

    video_dir = Path(sys.argv[1])
    words_file = Path(sys.argv[2])
    output_dir = Path(sys.argv[3])
    manuscript_choice = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 0
    
    # Optional: --final-keeps <json_file> for post-cut subtitle calibration
    final_keeps = None
    for i, arg in enumerate(sys.argv):
        if arg == "--final-keeps" and i + 1 < len(sys.argv):
            keeps_path = Path(sys.argv[i + 1])
            if keeps_path.exists():
                final_keeps = json.loads(keeps_path.read_text(encoding="utf-8"))
                print(f"✂ 粗剪后模式: {len(final_keeps)} 个保留段")
            break
    
    # 1. Find manuscript
    manuscripts = find_manuscripts(video_dir)
    if not manuscripts:
        print("⚠ 未找到文稿文件，回退到静音分句（gen_analysis.js）")
        sys.exit(1)
    
    manuscript = ask_user_manuscript(manuscripts, manuscript_choice)
    print(f"📖 使用文稿: {manuscript.name}")
    
    # 2. Parse manuscript
    sentences = parse_manuscript(manuscript)
    print(f"📝 文稿句子: {len(sentences)}")
    
    # 3. Read Whisper transcript
    words_raw = words_file.read_bytes()
    for enc in ["utf-8", "gbk", "cp936"]:
        try:
            words = json.loads(words_raw.decode(enc))
            break
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    
    # 4. If final-keeps provided, filter + remap to cut timeline
    if final_keeps:
        original_count = sum(1 for w in words if not w.get("isGap"))
        words = remap_words_to_cut_timeline(words, final_keeps)
        cut_count = sum(1 for w in words if not w.get("isGap"))
        print(f"✂ 词数: {original_count} → {cut_count} (粗剪后)")
    
    whisper_chars, char_map = flatten_whisper(words)
    print(f"🎤 Whisper 词数: {sum(1 for w in words if not w.get('isGap'))}")
    print(f"🔤 Whisper 字符数: {len(whisper_chars)}")
    
    # 4. Align
    print(f"\n🔗 对齐中...")
    aligned = align_manuscript_to_whisper(sentences, whisper_chars, char_map)
    
    matched = [s for s in aligned if s.get("matched")]
    unmatched = [s for s in aligned if not s.get("matched")]
    print(f"  ✅ 匹配: {len(matched)}/{len(aligned)}")
    print(f"  ❌ 未匹配: {len(unmatched)}")
    
    avg_conf = sum(s["confidence"] for s in matched) / len(matched) if matched else 0
    print(f"  📊 平均置信度: {avg_conf:.1%}")
    
    # 5. Generate outputs (analysis + SRT)
    report = generate_outputs(aligned, words, output_dir, video_dir)
    print(f"\n📁 分析输出: {output_dir}")
    print(f"  analysis.txt ({len(matched)} 句)")
    print(f"  sentence_map.json ({len(matched)} 段)")
    if video_dir:
        print(f"  Sub/master.srt → {video_dir / 'Sub' / 'master.srt'}")
    
    # Show unmatched
    if unmatched:
        print(f"\n⚠ 未匹配的文稿句子:")
        for s in unmatched[:10]:
            print(f"  [{s['section']}] {s['text'][:60]}...")
    
    # Show low confidence
    low_conf = [s for s in matched if s["confidence"] < 0.5]
    if low_conf:
        print(f"\n⚠ 低置信度句子 ({len(low_conf)}):")
        for s in low_conf[:10]:
            print(f"  conf={s['confidence']:.0%} [{s['section']}] {s['text'][:60]}")


if __name__ == "__main__":
    main()
