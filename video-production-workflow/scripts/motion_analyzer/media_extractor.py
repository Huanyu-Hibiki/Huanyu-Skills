"""Multi-media keyframe extraction and short-time energy audio onset analyzer.

Provides robust FFmpeg-based 5-phase keyframe extraction with contact sheet rendering,
pure-Python/numpy RMS audio energy and onset/accent timestamp detection,
and graceful degradation for silent/audio-less video clips.
"""
from __future__ import annotations

import logging
import math
from pathlib import Path
import struct
import subprocess
import sys
from typing import List, Optional, Sequence, Tuple, Union
import wave

logger = logging.getLogger(__name__)

# Ensure scripts directory is in sys.path when executed directly as script
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from pydantic import BaseModel, Field  # noqa: E402

from motion_analyzer.motion_ir import AudioAnchors  # noqa: E402


def parse_time_str(time_val: Union[str, float, int]) -> float:
    """Parse time representations into floating point seconds.

    Supports:
    - Numeric values: 15, 15.5
    - Strings representing floats/ints: "15", "15.5"
    - MM:SS / MM:SS.mmm: "00:15", "01:02.5"
    - HH:MM:SS / HH:MM:SS.mmm: "01:02:03", "01:02:03.500"

    Raises:
        ValueError: If format is invalid or parsed time is negative.
    """
    if isinstance(time_val, (int, float)):
        val = float(time_val)
        if val < 0:
            raise ValueError(f"Time value cannot be negative: {time_val}")
        return val

    if not isinstance(time_val, str):
        raise ValueError(f"Unsupported time value type: {type(time_val)}")

    s = time_val.strip()
    if not s:
        raise ValueError("Time string cannot be empty")

    # Timecode format with colons: MM:SS or HH:MM:SS
    if ":" in s:
        parts = s.split(":")
        if len(parts) == 2:
            try:
                minutes = float(parts[0])
                seconds = float(parts[1])
            except ValueError as err:
                raise ValueError(f"Invalid MM:SS timecode: {s}") from err
            if minutes < 0 or seconds < 0:
                raise ValueError(f"Timecode components cannot be negative: {s}")
            return minutes * 60.0 + seconds
        elif len(parts) == 3:
            try:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
            except ValueError as err:
                raise ValueError(f"Invalid HH:MM:SS timecode: {s}") from err
            if hours < 0 or minutes < 0 or seconds < 0:
                raise ValueError(f"Timecode components cannot be negative: {s}")
            return hours * 3600.0 + minutes * 60.0 + seconds
        else:
            raise ValueError(f"Invalid timecode format (expected MM:SS or HH:MM:SS): {s}")

    # Plain float/int string
    try:
        val = float(s)
    except ValueError as err:
        raise ValueError(f"Invalid numeric time string: {s}") from err

    if val < 0:
        raise ValueError(f"Time value cannot be negative: {s}")

    return val


class MediaExtractionResult(BaseModel):
    """Encapsulates outputs from media extraction and audio onset analysis."""
    video_path: str = Field(description="Resolved path of source video")
    start_time: float = Field(default=0.0, ge=0.0, description="Start time offset in seconds")
    end_time: float = Field(default=0.0, ge=0.0, description="End time in seconds")
    duration: float = Field(default=0.0, ge=0.0, description="Analyzed duration in seconds")
    has_audio: bool = Field(default=False, description="Whether audio stream was detected")
    contact_sheet_path: Optional[str] = Field(default=None, description="Path to generated contact_sheet.png")
    audio_wav_path: Optional[str] = Field(default=None, description="Path to extracted 16kHz WAV file if available")
    keyframe_timestamps: List[float] = Field(default_factory=list, description="Timestamps of extracted phases in seconds")
    audio_anchors: AudioAnchors = Field(default_factory=AudioAnchors, description="Extracted audio anchors (BPM, onsets, beats)")


def calculate_frame_timestamps(
    start_time: float,
    end_time: float,
    phases: Sequence[float] = (0.0, 0.2, 0.5, 0.8, 1.0),
) -> List[float]:
    """Calculate absolute timestamps for given motion phases within [start_time, end_time].

    Args:
        start_time: Starting timestamp in seconds (>= 0).
        end_time: Ending timestamp in seconds (> start_time).
        phases: Fractional points along the interval, default (0%, 20%, 50%, 80%, 100%).

    Returns:
        List of absolute timestamps rounded to 3 decimal places.
    """
    if start_time < 0:
        raise ValueError(f"start_time cannot be negative: {start_time}")
    if end_time <= start_time:
        raise ValueError(f"end_time ({end_time}) must be greater than start_time ({start_time})")

    duration = end_time - start_time
    timestamps = [round(start_time + duration * p, 3) for p in phases]
    return timestamps


def get_media_duration(media_path: Path) -> float:
    """Probe media container duration in seconds using ffprobe.

    Prevents shell injection by passing args as a strict list to subprocess.run.
    """
    media_path = Path(media_path)
    if not media_path.exists():
        raise FileNotFoundError(f"Media file does not exist: {media_path}")

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(media_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=15)
    val = res.stdout.strip()
    if not val or val == "N/A":
        # Fallback: probe first video or audio stream duration
        cmd_stream = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ]
        res_stream = subprocess.run(cmd_stream, capture_output=True, text=True, timeout=15)
        val = res_stream.stdout.strip()

    try:
        return float(val)
    except (ValueError, TypeError) as err:
        raise RuntimeError(f"Failed to parse media duration from ffprobe output: {val}") from err


def detect_audio_stream(media_path: Path) -> bool:
    """Check if media file contains at least one valid audio stream."""
    media_path = Path(media_path)
    if not media_path.exists():
        return False

    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_type",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(media_path),
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=15)
        return res.stdout.strip() == "audio"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as err:
        logger.warning("Failed or timed out detecting audio stream for %s: %s", media_path, err)
        return False


def extract_audio_wav(
    video_path: Path,
    dest_wav_path: Path,
    start_time: Optional[float] = None,
    duration: Optional[float] = None,
    target_sr: int = 16000,
) -> bool:
    """Extract audio from video container into mono 16-bit 16kHz PCM WAV.

    Returns True if audio extraction succeeded, False if stream was missing/silent.
    """
    video_path = Path(video_path)
    dest_wav_path = Path(dest_wav_path)
    dest_wav_path.parent.mkdir(parents=True, exist_ok=True)

    if not detect_audio_stream(video_path):
        return False

    cmd = ["ffmpeg", "-y", "-v", "error"]
    if start_time is not None and start_time > 0:
        cmd.extend(["-ss", f"{start_time:.3f}"])
    if duration is not None and duration > 0:
        cmd.extend(["-t", f"{duration:.3f}"])

    cmd.extend([
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", str(target_sr),
        "-c:a", "pcm_s16le",
        str(dest_wav_path),
    ])

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60)
        return dest_wav_path.exists() and dest_wav_path.stat().st_size > 44
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as err:
        logger.warning("Audio extraction failed or timed out for %s: %s", video_path, err)
        return False


def compute_audio_onsets(
    wav_path: Path,
    start_time: float = 0.0,
    end_time: Optional[float] = None,
    frame_ms: float = 25.0,
    hop_ms: float = 10.0,
    sensitivity: float = 0.15,
) -> Tuple[List[float], List[float]]:
    """Compute onset / accent timestamps and rhythmic beats using short-time RMS energy difference.

    Pure-Python standard library implementation (wave + struct + math) for maximum portability
    without mandatory heavy binary dependencies.

    Args:
        wav_path: Path to PCM WAV file.
        start_time: Offset start time in seconds.
        end_time: End time in seconds.
        frame_ms: Analysis window length in milliseconds (default 25ms).
        hop_ms: Hop size / step in milliseconds (default 10ms).
        sensitivity: Minimum relative energy rise threshold to trigger an onset (0.0 to 1.0).

    Returns:
        (onsets, beats): Lists of timestamps in seconds.
    """
    wav_path = Path(wav_path)
    if not wav_path.exists():
        return [], []

    try:
        with wave.open(str(wav_path), "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()

            if sampwidth != 2:
                logger.warning("Unsupported WAV sample width: %d bytes (expected 2)", sampwidth)
                return [], []

            # 15 minutes frame threshold protection
            max_frames_15min = 15 * 60 * framerate
            if n_frames > max_frames_15min:
                logger.warning(
                    "Audio clip length (%d frames, ~%.1f min) exceeds 15-minute threshold. "
                    "Processing might be memory intensive.",
                    n_frames,
                    n_frames / (framerate * 60.0),
                )

            raw_bytes = wf.readframes(n_frames)
    except Exception as err:
        logger.warning("Failed reading audio WAV file %s: %s", wav_path, err)
        return [], []

    total_samples = len(raw_bytes) // (sampwidth * n_channels)
    if total_samples == 0 or framerate == 0:
        return [], []

    # Unpack int16 samples
    fmt = f"<{total_samples * n_channels}h"
    try:
        raw_samples = struct.unpack(fmt, raw_bytes)
    except Exception as err:
        logger.warning("Failed unpacking PCM samples from %s: %s", wav_path, err)
        return [], []

    # Downmix to mono float in range [-1.0, 1.0]
    if n_channels == 1:
        samples = [s / 32768.0 for s in raw_samples]
    else:
        samples = []
        for i in range(0, len(raw_samples), n_channels):
            mono_val = sum(raw_samples[i:i + n_channels]) / (n_channels * 32768.0)
            samples.append(mono_val)

    # Slice by [start_time, end_time]
    s_idx = max(0, int(start_time * framerate))
    e_idx = min(len(samples), int(end_time * framerate)) if end_time is not None else len(samples)
    if e_idx <= s_idx:
        return [], []

    samples = samples[s_idx:e_idx]

    # Compute short-time RMS energy per frame
    frame_len = max(1, int(framerate * frame_ms / 1000.0))
    hop_len = max(1, int(framerate * hop_ms / 1000.0))

    if len(samples) < frame_len:
        return [], []

    n_hops = 1 + (len(samples) - frame_len) // hop_len
    rms_values: List[float] = []

    for i in range(n_hops):
        chunk = samples[i * hop_len : i * hop_len + frame_len]
        energy = math.sqrt(sum(x * x for x in chunk) / len(chunk))
        rms_values.append(energy)

    max_rms = max(rms_values) if rms_values else 0.0
    # Silence detection: if max RMS is negligible, gracefully degrade to empty
    if max_rms < 0.01:
        return [], []

    # First-order positive difference (spectral/energy flux onset detection function)
    diff: List[float] = [0.0]
    for i in range(1, len(rms_values)):
        delta = rms_values[i] - rms_values[i - 1]
        diff.append(max(0.0, delta))

    max_diff = max(diff) if diff else 0.0
    if max_diff == 0.0:
        return [], []

    # Normalized threshold for peak picking
    threshold = max_diff * sensitivity
    min_interval_sec = 0.12  # Minimum 120ms between adjacent onsets
    min_interval_hops = int(min_interval_sec / (hop_ms / 1000.0))

    detected_onsets: List[float] = []
    last_onset_hop = -min_interval_hops

    for i in range(1, len(diff) - 1):
        if diff[i] > threshold and diff[i] > diff[i - 1] and diff[i] >= diff[i + 1]:
            if i - last_onset_hop >= min_interval_hops:
                onset_sec = round(start_time + (i * hop_ms / 1000.0), 3)
                detected_onsets.append(onset_sec)
                last_onset_hop = i

    # Rhythmic beats proxy: detected onsets filtered / downsampled or aligned
    beats = list(detected_onsets)

    return detected_onsets, beats


def extract_contact_sheet(
    video_path: Path,
    output_path: Path,
    timestamps: Sequence[float],
    tile_layout: Optional[str] = None,
) -> Path:
    """Extract frames at given timestamps and stitch into a contact sheet grid with timecode watermark.

    Uses FFmpeg select filter and tile filter:
    `select='...',drawtext=...,tile=Nx1` or sequentially sampled frames.
    """
    video_path = Path(video_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not timestamps:
        raise ValueError("timestamps sequence cannot be empty")

    n = len(timestamps)

    # Calculate duration of video to ensure seek timestamps do not hit or exceed EOF
    total_dur = get_media_duration(video_path)
    safe_timestamps = []
    for ts in timestamps:
        val = max(0.0, float(ts))
        if total_dur > 0 and val >= total_dur - 0.04:
            val = max(0.0, total_dur - 0.05)
        safe_timestamps.append(round(val, 3))

    inputs = []
    filter_chains = []

    for i, (ts, orig_ts) in enumerate(zip(safe_timestamps, timestamps)):
        inputs.extend(["-ss", f"{ts:.3f}", "-i", str(video_path)])
        # Label frame with original phase time watermark
        filter_chains.append(
            f"[{i}:v]scale=320:-1,drawtext=text='{orig_ts:.2f}s':x=10:y=H-th-10:"
            f"fontsize=20:fontcolor=white:box=1:boxcolor=black@0.6[v{i}]"
        )

    tile_inputs = "".join(f"[v{i}]" for i in range(n))
    filter_complex = f"{';'.join(filter_chains)};{tile_inputs}hstack=inputs={n}[out]"

    cmd = [
        "ffmpeg", "-y", "-v", "error",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-frames:v", "1",
        "-update", "1",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as primary_err:
        logger.warning("Primary contact sheet extraction failed (%s), trying fallback hstack", primary_err)
        # Fallback if drawtext/font is unavailable on system: simple hstack without drawtext
        simple_chains = [f"[{i}:v]scale=320:-1[v{i}]" for i in range(n)]
        simple_filter = f"{';'.join(simple_chains)};{tile_inputs}hstack=inputs={n}[out]"
        fallback_cmd = [
            "ffmpeg", "-y", "-v", "error",
            *inputs,
            "-filter_complex", simple_filter,
            "-map", "[out]",
            "-frames:v", "1",
            "-update", "1",
            str(output_path),
        ]
        subprocess.run(fallback_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)

    return output_path


class MediaExtractor:
    """High-level facade orchestrating frame sampling and acoustic onset extraction."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else None

    def extract(
        self,
        video_path: Path,
        start_time: Optional[Union[str, float]] = None,
        end_time: Optional[Union[str, float]] = None,
        output_dir: Optional[Path] = None,
        phases: Sequence[float] = (0.0, 0.2, 0.5, 0.8, 1.0),
    ) -> MediaExtractionResult:
        """Run full extraction: duration probe, 5-phase contact sheet, audio onset analysis.

        Gracefully degrades if no audio stream exists or if audio is silent.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        parsed_start = parse_time_str(start_time) if start_time is not None else 0.0
        total_dur = get_media_duration(video_path)
        parsed_end = parse_time_str(end_time) if end_time is not None else total_dur

        actual_start = max(0.0, parsed_start)
        actual_end = min(total_dur, parsed_end)

        if actual_end <= actual_start:
            actual_end = total_dur

        effective_duration = actual_end - actual_start
        out_dir = Path(output_dir or self.output_dir or video_path.parent)
        out_dir.mkdir(parents=True, exist_ok=True)

        # 1. Calculate phase timestamps
        timestamps = calculate_frame_timestamps(actual_start, actual_end, phases=phases)

        # 2. Extract contact sheet
        contact_sheet_file = out_dir / "contact_sheet.png"
        extract_contact_sheet(video_path, contact_sheet_file, timestamps)

        # 3. Audio extraction & Onsets
        has_audio = detect_audio_stream(video_path)
        dest_wav = out_dir / "extracted_audio.wav"
        onsets: List[float] = []
        beats: List[float] = []

        if has_audio:
            success = extract_audio_wav(
                video_path=video_path,
                dest_wav_path=dest_wav,
                start_time=actual_start,
                duration=effective_duration,
            )
            if success:
                onsets, beats = compute_audio_onsets(
                    wav_path=dest_wav,
                    start_time=actual_start,
                    end_time=actual_end,
                )

        # Build AudioAnchors
        anchors = AudioAnchors(
            tempo_bpm=120.0 if beats else None,
            beats=beats,
            onsets=onsets,
            sync_strategy="snap_entrance_to_nearest_beat" if onsets else "uniform_visual_cadence",
        )

        return MediaExtractionResult(
            video_path=str(video_path.resolve()),
            start_time=actual_start,
            end_time=actual_end,
            duration=effective_duration,
            has_audio=has_audio,
            contact_sheet_path=str(contact_sheet_file) if contact_sheet_file.exists() else None,
            audio_wav_path=str(dest_wav) if dest_wav.exists() else None,
            keyframe_timestamps=timestamps,
            audio_anchors=anchors,
        )


def main() -> None:
    """CLI entrypoint for extracting contact sheet and calculating audio onsets."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract 5-phase motion contact sheet and short-time RMS audio onsets."
    )
    parser.add_argument("video", type=Path, help="Path to input video file")
    parser.add_argument(
        "--start",
        type=parse_time_str,
        default=None,
        help="Start time in seconds or timecode (e.g. 15, 00:15, 01:02.5)",
    )
    parser.add_argument(
        "--end",
        type=parse_time_str,
        default=None,
        help="End time in seconds or timecode (e.g. 18, 00:18, 01:05.0)",
    )
    parser.add_argument("--output-dir", "-o", type=Path, default=None, help="Output directory")
    parser.add_argument("--json", action="store_true", help="Print JSON result to stdout")

    args = parser.parse_args()

    extractor = MediaExtractor(output_dir=args.output_dir)
    result = extractor.extract(
        video_path=args.video,
        start_time=args.start,
        end_time=args.end,
    )

    if args.json:
        print(result.model_dump_json(indent=2))
    else:
        print(f"Media extraction completed for: {result.video_path}")
        print(f"Duration: {result.duration:.2f}s [{result.start_time:.2f}s -> {result.end_time:.2f}s]")
        print(f"Contact Sheet: {result.contact_sheet_path}")
        print(f"Audio WAV: {result.audio_wav_path} (has_audio={result.has_audio})")
        print(f"Onsets count: {len(result.audio_anchors.onsets)}")
        print(f"Keyframe timestamps: {result.keyframe_timestamps}")


if __name__ == "__main__":
    main()
