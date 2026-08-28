"""Transcribe a video with Whisper + Fun-ASR.

Uses Whisper for word-level timestamps and Fun-ASR for accurate Chinese
recognition. Combines both results for optimal output.

Usage:
    python scripts/video-rough-cut/transcribe.py <video_path>
    python scripts/video-rough-cut/transcribe.py <video_path> --edit-dir /custom/edit
    python scripts/video-rough-cut/transcribe.py <video_path> --language zh
    python scripts/video-rough-cut/transcribe.py <video_path> --whisper-model large-v3
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

import whisper

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.env import load_skill_env

load_skill_env()


def default_device() -> str:
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda:0"
    except Exception:
        pass
    return "cpu"


def extract_audio(video_path: Path, dest: Path) -> None:
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def transcribe_with_whisper(
    audio_path: Path,
    model_name: str = "large-v3",
    language: Optional[str] = None,
) -> dict:
    print(f"  loading Whisper model: {model_name}")
    model = whisper.load_model(model_name)
    
    print(f"  transcribing with Whisper...")
    result = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
        verbose=False,
    )
    
    words = []
    for segment in result.get("segments", []):
        for word in segment.get("words", []):
            words.append({
                "type": "word",
                "text": word["word"].strip(),
                "start": word["start"],
                "end": word["end"],
                "confidence": word.get("probability", 0.0),
            })

    result_text = result.get("text", "")
    result_language = result.get("language", "")

    # Explicitly release model + GPU memory before Fun-ASR loads (prevents OOM on low-VRAM GPUs)
    del model
    del result
    import gc
    gc.collect()
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass

    return {
        "text": result_text,
        "segments": [],
        "words": words,
        "language": result_language,
    }


def transcribe_with_funasr(
    audio_path: Path,
    model_dir: str = "FunAudioLLM/Fun-ASR-Nano-2512",
    device: str = "cpu",
) -> dict:
    try:
        # FunASR Nano 1.3.1 ships model.py with local absolute imports like
        # `from ctc import CTC`; register that package path before AutoModel.
        funasr_candidates = []
        if os.environ.get("FUNASR_NANO_DIR"):
            funasr_candidates.append(Path(os.environ["FUNASR_NANO_DIR"]))
        for funasr_nano_dir in funasr_candidates:
            if funasr_nano_dir.exists() and str(funasr_nano_dir) not in sys.path:
                sys.path.insert(0, str(funasr_nano_dir))
                break
        try:
            import funasr.models.fun_asr_nano.model  # noqa: F401
        except ImportError:
            pass

        from funasr import AutoModel
        
        print(f"  loading Fun-ASR model: {model_dir}")
        model = AutoModel(
            model=model_dir,
            trust_remote_code=False,
            device=device,
        )
        
        print(f"  transcribing with Fun-ASR...")
        result = model.generate(
            input=[str(audio_path)],
            cache={},
            batch_size=1,
            language="中文",
            itn=True,
        )
        
        text = result[0]["text"] if result else ""
        return {"text": text}
        
    except Exception as e:
        print(f"  Fun-ASR failed: {e}")
        print(f"  Falling back to Whisper only")
        return {"text": ""}


def merge_transcriptions(
    whisper_result: dict,
    funasr_result: dict,
) -> dict:
    whisper_words = whisper_result.get("words", [])
    whisper_text = whisper_result.get("text", "")
    funasr_text = funasr_result.get("text", "")
    
    if not funasr_text:
        print("  using Whisper result only (Fun-ASR empty)")
        return {
            "text": whisper_text,
            "words": whisper_words,
            "language": whisper_result.get("language", ""),
            "source": "whisper_only",
        }

    if "[SP]" in funasr_text or "<|" in funasr_text:
        print("  using Whisper result only (Fun-ASR returned control tokens)")
        return {
            "text": whisper_text,
            "words": whisper_words,
            "language": whisper_result.get("language", ""),
            "source": "whisper_only",
            "funasr_text": funasr_text,
        }
    
    if not whisper_words:
        print("  warning: no word timestamps from Whisper")
        return {
            "text": funasr_text,
            "words": [],
            "language": whisper_result.get("language", ""),
            "source": "funasr_only",
        }
    
    print("  merging Whisper timestamps with Fun-ASR text...")
    
    merged_words = []
    whisper_idx = 0
    funasr_idx = 0
    
    while whisper_idx < len(whisper_words) and funasr_idx < len(funasr_text):
        w_word = whisper_words[whisper_idx]["text"]
        f_char = funasr_text[funasr_idx]
        
        if w_word and f_char and (
            w_word[0].lower() == f_char.lower() or
            (len(w_word) > 1 and w_word[0] == f_char)
        ):
            merged_words.append({
                "type": "word",
                "text": f_char,
                "start": whisper_words[whisper_idx]["start"],
                "end": whisper_words[whisper_idx]["end"],
                "confidence": whisper_words[whisper_idx].get("confidence", 0.0),
            })
            funasr_idx += 1
            if len(w_word) <= 1:
                whisper_idx += 1
            else:
                whisper_words[whisper_idx]["text"] = w_word[1:]
        else:
            whisper_idx += 1

    if len(merged_words) < max(10, len(whisper_words) * 0.5):
        print("  using Whisper result only (Fun-ASR merge coverage too low)")
        return {
            "text": whisper_text,
            "words": whisper_words,
            "language": whisper_result.get("language", ""),
            "source": "whisper_only",
            "funasr_text": funasr_text,
        }
    
    if funasr_idx < len(funasr_text):
        last_end = merged_words[-1]["end"] if merged_words else 0.0
        for i, char in enumerate(funasr_text[funasr_idx:]):
            merged_words.append({
                "type": "word",
                "text": char,
                "start": last_end + i * 0.1,
                "end": last_end + (i + 1) * 0.1,
                "confidence": 0.5,
            })
    
    merged_text = "".join(w["text"] for w in merged_words)
    
    if len(funasr_text) > len(merged_text) * 1.2:
        final_text = funasr_text
    else:
        final_text = merged_text
    
    return {
        "text": final_text,
        "words": merged_words,
        "language": whisper_result.get("language", ""),
        "source": "merged",
        "whisper_text": whisper_text,
        "funasr_text": funasr_text,
    }


def transcribe_one(
    video: Path,
    edit_dir: Path,
    whisper_model: str = "large-v3",
    language: Optional[str] = None,
    device: str = "auto",
    verbose: bool = True,
) -> Path:
    transcripts_dir = edit_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcripts_dir / f"{video.stem}.json"

    if out_path.exists():
        if verbose:
            print(f"cached: {out_path.name}")
        return out_path

    if verbose:
        print(f"  extracting audio from {video.name}", flush=True)

    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{video.stem}.wav"
        extract_audio(video, audio)
        size_mb = audio.stat().st_size / (1024 * 1024)
        if verbose:
            print(f"  processing {video.stem}.wav ({size_mb:.1f} MB)", flush=True)
        
        resolved_device = default_device() if device == "auto" else device
        whisper_result = transcribe_with_whisper(audio, whisper_model, language)
        funasr_result = transcribe_with_funasr(audio, device=resolved_device)
        merged_result = merge_transcriptions(whisper_result, funasr_result)
        
        merged_result["source_video"] = str(video)
        merged_result["whisper_model"] = whisper_model
        merged_result["processing_time"] = time.time() - t0

    out_path.write_text(json.dumps(merged_result, indent=2, ensure_ascii=False), encoding="utf-8")
    dt = time.time() - t0

    if verbose:
        kb = out_path.stat().st_size / 1024
        print(f"  saved: {out_path.name} ({kb:.1f} KB) in {dt:.1f}s")
        print(f"    words: {len(merged_result.get('words', []))}")
        print(f"    source: {merged_result.get('source', 'unknown')}")

    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Transcribe a video with Whisper + Fun-ASR")
    ap.add_argument("video", type=Path, help="Path to video file")
    ap.add_argument(
        "--edit-dir",
        type=Path,
        default=None,
        help="Edit output directory (default: <video_parent>/Rough)",
    )
    ap.add_argument(
        "--language",
        type=str,
        default=None,
        help="Optional language code (e.g., 'zh', 'en'). Omit to auto-detect.",
    )
    ap.add_argument(
        "--whisper-model",
        type=str,
        default="large-v3",
        help="Whisper model name (default: large-v3)",
    )
    ap.add_argument(
        "--device",
        type=str,
        default="auto",
        help="Device for Fun-ASR (default: auto, uses cuda:0 when available)",
    )
    args = ap.parse_args()

    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"video not found: {video}")

    edit_dir = (args.edit_dir or (video.parent / "Rough")).resolve()

    transcribe_one(
        video=video,
        edit_dir=edit_dir,
        whisper_model=args.whisper_model,
        language=args.language,
        device=args.device,
    )


if __name__ == "__main__":
    main()
