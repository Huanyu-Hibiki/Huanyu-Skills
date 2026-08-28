"""
Convert Whisper transcript JSON to AI剪口播 subtitles_words.json format.

Whisper format (from transcribe.py):
{
  "words": [
    {"type": "word", "text": "你", "start": 1.5, "end": 1.6},
    {"type": "word", "text": "好", "start": 1.6, "end": 1.7},
    ...
  ]
}

AI剪口播 subtitles_words.json format:
[
  {"text": "你", "start": 1.5, "end": 1.6, "isGap": false},
  {"text": "好", "start": 1.6, "end": 1.7, "isGap": false},
  {"text": "", "start": 1.7, "end": 2.1, "isGap": true},
  ...
]

Usage: python whisper_to_subtitles_words.py <whisper.json> <output.json>
"""
import argparse
import json
import sys
from pathlib import Path

def convert(whisper_path: Path, output_path: Path):
    raw = whisper_path.read_bytes()
    for enc in ['gbk', 'utf-8', 'cp936']:
        try:
            data = json.loads(raw.decode(enc))
            break
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue

    words = data.get('words', [])
    result = []

    for i, w in enumerate(words):
        if w.get('type') != 'word':
            continue

        # Insert gap if there's silence between this word and the previous
        if result and not result[-1].get('isGap'):
            prev_end = result[-1]['end']
            curr_start = w['start']
            if curr_start - prev_end > 0.01:  # >10ms gap
                result.append({
                    'text': '',
                    'start': prev_end,
                    'end': curr_start,
                    'isGap': True
                })

        result.append({
            'text': w['text'].strip(),
            'start': w['start'],
            'end': w['end'],
            'isGap': False
        })

    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    word_count = sum(1 for w in result if not w.get('isGap'))
    gap_count = sum(1 for w in result if w.get('isGap'))
    duration = result[-1]['end'] if result else 0

    print(f'  words: {word_count}, gaps: {gap_count}, duration: {duration:.1f}s')
    print(f'  saved: {output_path}')

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Whisper word timestamps to subtitles_words.json"
    )
    parser.add_argument("input", type=Path, help="Whisper transcript JSON")
    parser.add_argument("output", type=Path, help="Output subtitles_words.json")
    args = parser.parse_args()
    if not args.input.exists():
        raise SystemExit(f"input transcript not found: {args.input}")
    convert(args.input, args.output)


if __name__ == "__main__":
    main()
