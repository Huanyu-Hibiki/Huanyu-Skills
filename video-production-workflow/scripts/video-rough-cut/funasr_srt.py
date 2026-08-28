from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.env import load_skill_env

load_skill_env()


def extract_audio(video: Path, audio: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(audio),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def audio_duration(audio: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return float(out)


def extract_chunk(audio: Path, out: Path, start: float, duration: float) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{duration:.3f}",
        "-i",
        str(audio),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(out),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def register_funasr_nano() -> None:
    candidates = []
    if os.environ.get("FUNASR_NANO_DIR"):
        candidates.append(Path(os.environ["FUNASR_NANO_DIR"]))
    for funasr_nano_dir in candidates:
        if funasr_nano_dir.exists() and str(funasr_nano_dir) not in sys.path:
            sys.path.insert(0, str(funasr_nano_dir))
            break
    try:
        import funasr.models.fun_asr_nano.model  # noqa: F401
    except ImportError:
        pass


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def clean_token(token: str) -> str:
    return token.strip().replace(" ", "")


def build_cues(tokens: list[dict], max_chars: int = 24, max_duration: float = 5.0, gap: float = 0.75) -> list[dict]:
    cues: list[dict] = []
    current: list[dict] = []

    def flush() -> None:
        nonlocal current
        text = "".join(clean_token(t.get("token", "")) for t in current).strip()
        if not text:
            current = []
            return
        cues.append(
            {
                "start": float(current[0]["start_time"]),
                "end": max(float(current[-1]["end_time"]), float(current[0]["start_time"]) + 0.4),
                "text": text,
            }
        )
        current = []

    for token in tokens:
        text = clean_token(token.get("token", ""))
        if not text:
            continue
        if current:
            prev_end = float(current[-1]["end_time"])
            start = float(token["start_time"])
            duration = start - float(current[0]["start_time"])
            chars = sum(len(clean_token(t.get("token", ""))) for t in current)
            if start - prev_end > gap or duration > max_duration or chars >= max_chars:
                flush()
        current.append(token)

    if current:
        flush()

    for idx in range(len(cues) - 1):
        if cues[idx]["end"] > cues[idx + 1]["start"] - 0.04:
            cues[idx]["end"] = max(cues[idx]["start"] + 0.35, cues[idx + 1]["start"] - 0.04)

    return cues


def write_srt(cues: list[dict], out: Path) -> None:
    blocks = []
    for idx, cue in enumerate(cues, start=1):
        blocks.append(
            f"{idx}\n{srt_time(cue['start'])} --> {srt_time(cue['end'])}\n{cue['text']}"
        )
    out.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SRT with FunASR Nano")
    parser.add_argument("video", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--chunk-seconds", type=float, default=30.0)
    args = parser.parse_args()

    video = args.video.resolve()
    if not video.exists():
        raise SystemExit(f"video not found: {video}")

    register_funasr_nano()
    from funasr import AutoModel

    with tempfile.TemporaryDirectory() as tmp_dir:
        audio = Path(tmp_dir) / f"{video.stem}.wav"
        print(f"extracting audio: {video}", flush=True)
        extract_audio(video, audio)

        print(f"loading FunASR on {args.device}", flush=True)
        model = AutoModel(
            model="FunAudioLLM/Fun-ASR-Nano-2512",
            trust_remote_code=False,
            device=args.device,
            disable_update=True,
        )

        duration = audio_duration(audio)
        chunk_count = int(math.ceil(duration / args.chunk_seconds))
        print(f"transcribing with FunASR in {chunk_count} chunks...", flush=True)

        result = []
        all_tokens: list[dict] = []
        texts: list[str] = []
        for index in range(chunk_count):
            offset = index * args.chunk_seconds
            chunk_duration = min(args.chunk_seconds, duration - offset)
            chunk = Path(tmp_dir) / f"chunk_{index:04}.wav"
            extract_chunk(audio, chunk, offset, chunk_duration)
            print(f"  chunk {index + 1}/{chunk_count}: {offset:.1f}s-{offset + chunk_duration:.1f}s", flush=True)
            chunk_result = model.generate(
                input=[str(chunk)],
                cache={},
                batch_size=1,
                language="中文",
                itn=True,
                sentence_timestamp=True,
            )
            first_chunk = chunk_result[0] if chunk_result else {}
            texts.append(first_chunk.get("text", ""))
            tokens = first_chunk.get("timestamps") or first_chunk.get("ctc_timestamps") or []
            for token in tokens:
                copied = dict(token)
                copied["start_time"] = float(copied["start_time"]) + offset
                copied["end_time"] = float(copied["end_time"]) + offset
                all_tokens.append(copied)
            result.append({"chunk": index, "offset": offset, "duration": chunk_duration, "result": chunk_result})

        result.append({"key": video.stem, "text": "".join(texts), "timestamps": all_tokens})

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    first = result[-1] if result else {}
    tokens = first.get("timestamps") or first.get("ctc_timestamps") or []
    if not tokens:
        raise SystemExit("FunASR result has no timestamps; cannot build SRT")

    cues = build_cues(tokens)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_srt(cues, args.out)
    print(f"saved srt: {args.out}", flush=True)
    print(f"cues: {len(cues)}", flush=True)


if __name__ == "__main__":
    main()
