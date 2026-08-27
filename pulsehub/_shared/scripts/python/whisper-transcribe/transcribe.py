"""whisper-transcribe — Whisper wrapper that returns transcription JSON.

Status: SKELETON. See ROADMAP.md M3.

Usage:
    python transcribe.py --input audio.mp3
    python transcribe.py --input audio.mp3 --model base --language zh
    python transcribe.py --input audio.mp3 --output transcript.json

Output:
    {
      "text": "...",
      "language": "zh",
      "segments": [
        { "start": 0.0, "end": 5.2, "text": "..." },
        ...
      ]
    }
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def transcribe(audio_path: str, model_name: str, language: str | None) -> dict[str, Any]:
    """Transcribe audio file using Whisper.

    TODO: implement using whisper.load_model(model_name).transcribe(...).
    """
    raise NotImplementedError("M3 task — see ROADMAP.md")


def main() -> int:
    parser = argparse.ArgumentParser(description="Whisper transcription")
    parser.add_argument("--input", required=True, help="Audio file path")
    parser.add_argument("--model", default="base", help="Whisper model (tiny|base|small|medium|large)")
    parser.add_argument("--language", default=None, help="Language hint (e.g., zh, en)")
    parser.add_argument("--output", help="Output JSON file (default: stdout)")
    args = parser.parse_args()

    result = transcribe(args.input, args.model, args.language)

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Wrote transcript to {args.output}", file=sys.stderr)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
