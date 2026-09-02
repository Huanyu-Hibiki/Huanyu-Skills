"""Transcribe a video with faster-whisper (default) or openai-whisper.

faster-whisper is the default engine: it works well on Windows (CPU int8 and
CUDA), is fast, and produces word-level timestamps. openai-whisper remains
available with --engine whisper.

Models are resolved in this order:
1. <skill>/models/faster-whisper/<name>/ or <skill>/models/whisper/<name>.pt
2. Engine auto-download into <skill>/models/ (never the user cache)

Usage:
    python scripts/video-rough-cut/transcribe.py <video_path>
    python scripts/video-rough-cut/transcribe.py <video_path> --engine whisper
    python scripts/video-rough-cut/transcribe.py <video_path> --language zh
    python scripts/video-rough-cut/transcribe.py <video_path> --model large-v3
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.env import load_skill_env

load_skill_env()

SKILL_ROOT = Path(__file__).resolve().parents[2]
MODELS_ROOT = SKILL_ROOT / "models"

ENGINES = ("faster-whisper", "whisper")


def default_engine() -> str:
    env_engine = os.environ.get("ASR_ENGINE", "").strip().lower()
    if env_engine in ENGINES:
        return env_engine
    return "faster-whisper"


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


def resolve_faster_whisper_model(name: str) -> str:
    """Prefer a pre-downloaded model under <skill>/models/faster-whisper/<name>."""
    local = MODELS_ROOT / "faster-whisper" / name
    if (local / "model.bin").exists() or (local / "config.json").exists():
        return str(local)
    return name


def resolve_whisper_model(name: str) -> str:
    """Prefer a pre-downloaded .pt under <skill>/models/whisper/<name>.pt."""
    if os.path.isabs(name):
        return name
    local = MODELS_ROOT / "whisper" / f"{name}.pt"
    if local.exists():
        return str(local)
    return name


def transcribe_with_faster_whisper(
    audio_path: Path,
    model_name: str = "large-v3",
    language: Optional[str] = None,
    device: str = "cpu",
    initial_prompt: Optional[str] = None,
) -> dict:
    from faster_whisper import WhisperModel

    resolved = resolve_faster_whisper_model(model_name)
    compute_type = "float16" if device.startswith("cuda") else "int8"
    print(f"  loading faster-whisper model: {model_name} (device={device}, compute={compute_type})")
    if resolved == model_name:
        # let faster-whisper auto-download into <skill>/models/faster-whisper
        download_root = str(MODELS_ROOT / "faster-whisper")
        model = WhisperModel(resolved, device=device, compute_type=compute_type, download_root=download_root)
    else:
        print(f"  using local model: {resolved}")
        model = WhisperModel(resolved, device=device, compute_type=compute_type)

    print("  transcribing with faster-whisper...")
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
        vad_filter=True,
        initial_prompt=initial_prompt,
    )

    words = []
    for segment in segments_iter:
        for word in segment.words or []:
            text = word.word.strip()
            if text:
                words.append({
                    "type": "word",
                    "text": text,
                    "start": word.start,
                    "end": word.end,
                    "confidence": float(word.probability or 0.0),
                })

    return {
        "text": " ".join(w["text"] for w in words),
        "segments": [],
        "words": words,
        "language": info.language if info is not None else "",
        "source": "faster_whisper",
    }


def transcribe_with_whisper(
    audio_path: Path,
    model_name: str = "large-v3",
    language: Optional[str] = None,
    initial_prompt: Optional[str] = None,
) -> dict:
    import whisper

    resolved = resolve_whisper_model(model_name)
    download_root = str(MODELS_ROOT / "whisper")
    print(f"  loading Whisper model: {model_name}")
    model = whisper.load_model(resolved, download_root=download_root)

    print("  transcribing with Whisper...")
    result = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
        initial_prompt=initial_prompt,
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

    return {
        "text": result.get("text", ""),
        "segments": [],
        "words": words,
        "language": result.get("language", ""),
        "source": "whisper",
    }


def transcribe_one(
    video: Path,
    edit_dir: Path,
    model: str = "large-v3",
    engine: str = "faster-whisper",
    language: Optional[str] = None,
    device: str = "auto",
    initial_prompt: Optional[str] = None,
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
        if engine == "whisper":
            result = transcribe_with_whisper(audio, model, language, initial_prompt)
        else:
            # faster-whisper on cuda:0 / cpu; large models on low VRAM fall
            # back to CPU int8 automatically via compute_type choice
            fw_device = "cuda" if resolved_device.startswith("cuda") else "cpu"
            result = transcribe_with_faster_whisper(audio, model, language, fw_device, initial_prompt)

        result["source_video"] = str(video)
        result["asr_engine"] = engine
        result["whisper_model"] = model
        result["processing_time"] = time.time() - t0

    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    dt = time.time() - t0

    if verbose:
        kb = out_path.stat().st_size / 1024
        print(f"  saved: {out_path.name} ({kb:.1f} KB) in {dt:.1f}s")
        print(f"    words: {len(result.get('words', []))}")
        print(f"    engine: {engine}")

    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Transcribe a video with faster-whisper / Whisper")
    ap.add_argument("video", type=Path, help="Path to video file")
    ap.add_argument(
        "--edit-dir",
        type=Path,
        default=None,
        help="Edit output directory (default: <video_parent>/Rough)",
    )
    ap.add_argument(
        "--engine",
        type=str,
        default=default_engine(),
        choices=list(ENGINES),
        help="ASR engine (default: faster-whisper; override with env ASR_ENGINE)",
    )
    ap.add_argument(
        "--language",
        type=str,
        default=None,
        help="Optional language code (e.g., 'zh', 'en'). Omit to auto-detect.",
    )
    ap.add_argument(
        "--initial-prompt",
        type=str,
        default=None,
        help="Optional domain vocabulary / style prompt fed to the ASR model "
        "(e.g. product names, jargon) to bias recognition.",
    )
    ap.add_argument(
        "--model",
        "--whisper-model",
        dest="model",
        type=str,
        default="large-v3",
        help="Model name (default: large-v3)",
    )
    ap.add_argument(
        "--device",
        type=str,
        default="auto",
        help="Device (default: auto, uses cuda when available)",
    )
    args = ap.parse_args()

    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"video not found: {video}")

    edit_dir = (args.edit_dir or (video.parent / "Rough")).resolve()

    transcribe_one(
        video=video,
        edit_dir=edit_dir,
        model=args.model,
        engine=args.engine,
        language=args.language,
        device=args.device,
        initial_prompt=args.initial_prompt,
    )


if __name__ == "__main__":
    main()
