"""Unit and integration tests for Task 2: Multi-media keyframe extraction and audio onset analysis."""
from __future__ import annotations

import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import wave

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from motion_analyzer.media_extractor import (  # noqa: E402
    MediaExtractor,
    calculate_frame_timestamps,
    compute_audio_onsets,
    detect_audio_stream,
    parse_time_str,
)


def create_synthetic_wav(
    wav_path: Path,
    duration: float = 3.0,
    sample_rate: int = 16000,
    beeps: list[tuple[float, float, float]] | None = None,
) -> None:
    """Create a 16-bit mono PCM WAV file with optional beep pulses."""
    total_samples = int(duration * sample_rate)
    samples = [0.0] * total_samples

    if beeps:
        for start_s, dur_s, freq in beeps:
            start_idx = int(start_s * sample_rate)
            end_idx = min(total_samples, int((start_s + dur_s) * sample_rate))
            for i in range(start_idx, end_idx):
                t = (i - start_idx) / sample_rate
                # Hann window fade to avoid click artifacts
                win = 0.5 * (1.0 - math.cos(2.0 * math.pi * (i - start_idx) / max(1, end_idx - start_idx)))
                samples[i] += 0.8 * win * math.sin(2.0 * math.pi * freq * t)

    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        raw_bytes = bytearray()
        for s in samples:
            clamped = max(-1.0, min(1.0, s))
            int_val = int(clamped * 32767.0)
            raw_bytes.extend(struct.pack("<h", int_val))
        wf.writeframes(raw_bytes)


class TestMediaExtractorTDD(unittest.TestCase):
    def test_calculate_frame_timestamps_percentages(self):
        """Phase percentages (0%, 20%, 50%, 80%, 100%) must map to precise timestamps."""
        ts = calculate_frame_timestamps(start_time=0.0, end_time=4.0, phases=(0.0, 0.2, 0.5, 0.8, 1.0))
        self.assertEqual(len(ts), 5)
        self.assertAlmostEqual(ts[0], 0.0, places=3)
        self.assertAlmostEqual(ts[1], 0.8, places=3)
        self.assertAlmostEqual(ts[2], 2.0, places=3)
        self.assertAlmostEqual(ts[3], 3.2, places=3)
        self.assertAlmostEqual(ts[4], 4.0, places=3)

    def test_calculate_frame_timestamps_with_custom_slice(self):
        """Custom slice start_time=1.0, end_time=3.0 correctly offsets percentages."""
        ts = calculate_frame_timestamps(start_time=1.0, end_time=3.0)
        self.assertEqual(len(ts), 5)
        self.assertAlmostEqual(ts[0], 1.0, places=3)
        self.assertAlmostEqual(ts[1], 1.4, places=3)
        self.assertAlmostEqual(ts[2], 2.0, places=3)
        self.assertAlmostEqual(ts[3], 2.6, places=3)
        self.assertAlmostEqual(ts[4], 3.0, places=3)

    def test_calculate_frame_timestamps_invalid_bounds(self):
        """Invalid bounds (end <= start or negative) should raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_frame_timestamps(start_time=3.0, end_time=2.0)
        with self.assertRaises(ValueError):
            calculate_frame_timestamps(start_time=-1.0, end_time=2.0)

    def test_audio_onset_detection_with_synthetic_pulses(self):
        """Synthetic pulses at specific timestamps should be detected as onsets."""
        with tempfile.TemporaryDirectory() as td:
            wav_path = Path(td) / "test_pulses.wav"
            # Pulses at 0.5s, 1.2s, 2.0s
            beeps = [(0.5, 0.1, 880.0), (1.2, 0.1, 880.0), (2.0, 0.1, 880.0)]
            create_synthetic_wav(wav_path, duration=3.0, sample_rate=16000, beeps=beeps)

            onsets, beats = compute_audio_onsets(
                wav_path,
                start_time=0.0,
                end_time=3.0,
                sensitivity=0.15,
            )

            self.assertGreaterEqual(len(onsets), 3)
            # Verify detected onsets match the injected pulses closely (within 100ms)
            expected = [0.5, 1.2, 2.0]
            matched = 0
            for exp in expected:
                if any(abs(onset - exp) <= 0.1 for onset in onsets):
                    matched += 1
            self.assertEqual(matched, len(expected), f"Expected {expected} in {onsets}")

    def test_audio_onset_graceful_silence_degradation(self):
        """Pure silence should gracefully degrade to empty onsets or uniform visual anchors."""
        with tempfile.TemporaryDirectory() as td:
            wav_path = Path(td) / "silent.wav"
            create_synthetic_wav(wav_path, duration=2.5, sample_rate=16000, beeps=None)

            onsets, beats = compute_audio_onsets(
                wav_path,
                start_time=0.0,
                end_time=2.5,
            )
            self.assertEqual(onsets, [])
            self.assertEqual(beats, [])

    def test_detect_audio_stream_handles_no_audio(self):
        """detect_audio_stream returns False if video has no audio track, without throwing."""
        with tempfile.TemporaryDirectory() as td:
            dummy_file = Path(td) / "nonexistent.mp4"
            # Non-existent or empty file should return False or raise appropriate error
            self.assertFalse(detect_audio_stream(dummy_file))

    def test_security_prevents_shell_injection_in_arguments(self):
        """Command arguments containing shell meta-characters must not trigger injection even with real files."""
        extractor = MediaExtractor()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Create a real video file whose name contains shell injection syntax (; & $ - valid on all OS filesystems)
            malicious_video = root / "clip; echo hacked & echo hacked $env.mp4"
            cmd = [
                "ffmpeg", "-y", "-v", "error",
                "-f", "lavfi", "-i", "color=c=gray:s=160x120:d=1",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                str(malicious_video),
            ]
            import subprocess
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            self.assertTrue(malicious_video.exists())

            # Run extraction against this file
            res = extractor.extract(video_path=malicious_video, output_dir=root)
            self.assertIsNotNone(res.contact_sheet_path)
            self.assertTrue(Path(res.contact_sheet_path).exists())

            # Crucial assertion: no injected commands were executed by shell
            self.assertFalse((root / "hacked.txt").exists())
            self.assertFalse(Path("hacked.txt").exists())

    def test_media_extractor_with_synthesized_mp4(self):
        """End-to-end integration test with a synthesized video containing audio."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            video_path = root / "sample.mp4"
            # Generate 2-second test mp4 with sine audio
            cmd = [
                "ffmpeg", "-y", "-v", "error",
                "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2",
                "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
                "-c:v", "libx264", "-c:a", "aac",
                "-pix_fmt", "yuv420p",
                str(video_path),
            ]
            import subprocess
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            extractor = MediaExtractor(output_dir=root)
            res = extractor.extract(video_path=video_path, start_time=0.2, end_time=1.8)

            self.assertEqual(res.start_time, 0.2)
            self.assertEqual(res.end_time, 1.8)
            self.assertAlmostEqual(res.duration, 1.6, places=2)
            self.assertTrue(res.has_audio)
            self.assertEqual(len(res.keyframe_timestamps), 5)
            self.assertIsNotNone(res.contact_sheet_path)
            self.assertTrue(Path(res.contact_sheet_path).exists())
            self.assertIsNotNone(res.audio_wav_path)
            self.assertTrue(Path(res.audio_wav_path).exists())

    def test_media_extractor_silent_video_graceful_degradation(self):
        """End-to-end integration test with video without audio stream."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            video_path = root / "silent.mp4"
            cmd = [
                "ffmpeg", "-y", "-v", "error",
                "-f", "lavfi", "-i", "color=c=red:s=320x240:d=2",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                str(video_path),
            ]
            import subprocess
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            extractor = MediaExtractor(output_dir=root)
            res = extractor.extract(video_path=video_path)

            self.assertFalse(res.has_audio)
            self.assertIsNotNone(res.contact_sheet_path)
            self.assertTrue(Path(res.contact_sheet_path).exists())
            self.assertEqual(res.audio_anchors.onsets, [])
            self.assertEqual(res.audio_anchors.beats, [])
    def test_parse_time_str_various_formats(self):
        """Test parse_time_str with float, int, ss, mm:ss, and hh:mm:ss formats."""
        self.assertEqual(parse_time_str(15), 15.0)
        self.assertEqual(parse_time_str(15.5), 15.5)
        self.assertEqual(parse_time_str("15"), 15.0)
        self.assertEqual(parse_time_str("15.5"), 15.5)
        self.assertEqual(parse_time_str("00:15"), 15.0)
        self.assertEqual(parse_time_str("01:02.5"), 62.5)
        self.assertEqual(parse_time_str("01:02:03"), 3723.0)
        self.assertEqual(parse_time_str("01:02:03.500"), 3723.5)

    def test_parse_time_str_invalid(self):
        """Invalid time string formats should raise ValueError."""
        with self.assertRaises(ValueError):
            parse_time_str("invalid")
        with self.assertRaises(ValueError):
            parse_time_str("01:02:03:04")
        with self.assertRaises(ValueError):
            parse_time_str("-5")

    def test_cli_timecode_flags(self):
        """Test invoking media_extractor.py via CLI with timecode arguments --start 00:00.2 --end 00:01.8."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            video_path = root / "cli_sample.mp4"
            cmd = [
                "ffmpeg", "-y", "-v", "error",
                "-f", "lavfi", "-i", "color=c=green:s=320x240:d=2",
                "-f", "lavfi", "-i", "sine=frequency=800:duration=2",
                "-c:v", "libx264", "-c:a", "aac",
                "-pix_fmt", "yuv420p",
                str(video_path),
            ]
            import subprocess
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            script_path = SCRIPTS_DIR / "motion_analyzer" / "media_extractor.py"
            cli_cmd = [
                sys.executable,
                str(script_path),
                str(video_path),
                "--start", "00:00.2",
                "--end", "00:01.8",
                "--output-dir", str(root),
                "--json",
            ]
            res = subprocess.run(cli_cmd, capture_output=True, text=True, check=True)
            import json
            data = json.loads(res.stdout)
            self.assertAlmostEqual(data["start_time"], 0.2, places=2)
            self.assertAlmostEqual(data["end_time"], 1.8, places=2)
            self.assertTrue(Path(data["contact_sheet_path"]).exists())


if __name__ == "__main__":
    unittest.main()
