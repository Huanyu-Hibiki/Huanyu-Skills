"""Unit and integration tests for Task 3: Timeline pause tightening."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np
import scipy.io.wavfile as wavfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.edit_plan import load_plan, frame
from lib.pause_tighten import tighten_pauses, generate_pauses_report


def create_synthetic_audio(path: Path, segments: list[tuple[float, float, float]], total_duration: float, sr: int = 16000):
    n_samples = int(total_duration * sr)
    audio = np.zeros(n_samples, dtype=np.float32)
    for start, end, amp in segments:
        s_idx = int(start * sr)
        e_idx = int(end * sr)
        if amp > 0:
            t = np.linspace(0, end - start, e_idx - s_idx, endpoint=False)
            tone = amp * 0.7 * np.sin(2 * np.pi * 220 * t) + amp * 0.3 * np.sin(2 * np.pi * 440 * t)
            ramp_len = min(int(0.01 * sr), len(tone) // 2)
            if ramp_len > 0:
                tone[:ramp_len] *= np.linspace(0, 1, ramp_len)
                tone[-ramp_len:] *= np.linspace(1, 0, ramp_len)
            audio[s_idx:e_idx] = tone
    int16_audio = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    wavfile.write(str(path), sr, int16_audio)


class TestPauseTightening(unittest.TestCase):

    def test_interior_pause_tightened(self):
        """A long interior silence (> 0.35s) inside a keep segment is shortened to ~0.25s."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wav_path = root / "speech.wav"
            # Speech: 0.2-1.2s (1.0s), silence: 1.2-2.2s (1.0s pause), speech: 2.2-3.2s (1.0s)
            create_synthetic_audio(wav_path, [(0.2, 1.2, 0.8), (2.2, 3.2, 0.8)], total_duration=4.0)

            plan = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {"src": {"path": "speech.wav", "duration": 4.0}},
                "timeline": [
                    {
                        "id": "seg-1",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 0.2,
                        "sourceEnd": 3.2,
                        "targetStart": 0.0,
                        "text": "前半句话……后半句话",
                    }
                ],
                "reviewQueue": []
            }
            # Words metadata: word 1 ends at 1.2, word 2 starts at 2.2 (gap = 1.0s)
            words = [
                {"id": "w1", "text": "前半句话", "start": 0.2, "end": 1.2},
                {"id": "w2", "text": "后半句话", "start": 2.2, "end": 3.2},
            ]

            tightened_plan, report = tighten_pauses(
                plan,
                threshold=0.35,
                keep=0.25,
                words_per_segment={"seg-1": words},
            )

            # Segment should be split into 2 keeps
            keeps = [x for x in tightened_plan["timeline"] if x["op"] == "keep"]
            removes = [x for x in tightened_plan["timeline"] if x["op"] == "remove"]
            self.assertEqual(len(keeps), 2)
            self.assertEqual(len(removes), 1)
            self.assertEqual(removes[0]["undoGroup"], "seg-1")
            self.assertEqual(removes[0]["reason"], ["intra_sentence_pause"])
            self.assertEqual(keeps[0]["sourceStart"], 0.2)
            self.assertEqual(keeps[0]["sourceEnd"], 1.2 + 0.25)  # 1.2 + 0.25 breath margin
            self.assertEqual(keeps[1]["sourceStart"], 2.2)
            self.assertEqual(keeps[1]["sourceEnd"], 3.2)
            # Text slicing: each sub-segment gets only its corresponding words
            self.assertEqual(keeps[0]["text"], "前半句话")
            self.assertEqual(keeps[1]["text"], "后半句话")

            # Check target duration was compressed
            self.assertLess(tightened_plan["durationFrames"], plan_duration_frames(plan, 25))
            self.assertEqual(report["summary"]["interior_pauses_cut"], 1)
            self.assertAlmostEqual(report["summary"]["seconds_removed"], 1.0 - 0.25, delta=1.0/25)

    def test_cross_keep_pause_tightened(self):
        """Cross-keep gap on target timeline (> 0.35s) is tightened to ~0.25s and contiguous on A-roll."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wav_path = root / "speech.wav"
            create_synthetic_audio(wav_path, [(0.0, 1.0, 0.8), (3.0, 4.0, 0.8)], total_duration=5.0)

            plan = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {"src": {"path": "speech.wav", "duration": 5.0}},
                "timeline": [
                    {
                        "id": "seg-1",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 0.0,
                        "sourceEnd": 1.0,
                        "targetStart": 0.0,
                    },
                    {
                        "id": "seg-2",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 3.0,
                        "sourceEnd": 4.0,
                        "targetStart": 2.0,  # Gap between seg-1 (dur 1.0) and seg-2 is 2.0 - 1.0 = 1.0s > 0.35s
                    }
                ],
                "reviewQueue": []
            }

            tightened_plan, report = tighten_pauses(
                plan,
                threshold=0.35,
                keep=0.25,
            )

            keeps = [x for x in tightened_plan["timeline"] if x["op"] == "keep"]
            self.assertEqual(keeps[0]["targetStart"], 0.0)
            # Gap of 1.0s is tightened to ~0.25s (6 frames at 25fps = 0.24s, targetStart = 1.24s)
            self.assertAlmostEqual(keeps[1]["targetStart"], 1.25, delta=1.0 / 25)
            gap = keeps[1]["targetStart"] - (keeps[0]["targetStart"] + (keeps[0]["sourceEnd"] - keeps[0]["sourceStart"]))
            self.assertAlmostEqual(gap, 0.25, delta=1.0 / 25)

    def test_sub_threshold_pause_left_intact(self):
        """Pauses below threshold (e.g. 0.28s < 0.35s) are left untouched as natural pauses."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wav_path = root / "speech.wav"
            create_synthetic_audio(wav_path, [(0.0, 1.0, 0.8)], total_duration=3.0)

            plan = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {"src": {"path": "speech.wav", "duration": 3.0}},
                "timeline": [
                    {
                        "id": "seg-1",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 0.0,
                        "sourceEnd": 1.0,
                        "targetStart": 0.0,
                    },
                    {
                        "id": "seg-2",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 1.5,
                        "sourceEnd": 2.5,
                        "targetStart": 1.28,  # Gap is 0.28s < 0.35s
                    }
                ],
                "reviewQueue": []
            }

            tightened_plan, report = tighten_pauses(plan, threshold=0.35, keep=0.25)
            keeps = [x for x in tightened_plan["timeline"] if x["op"] == "keep"]
            self.assertEqual(keeps[1]["targetStart"], 1.28)
            self.assertEqual(report["summary"]["total_pauses_cut"], 0)

    def test_noisy_pause_downgrades_to_review(self):
        """When pause interval contains high audio energy (music, background noise), route to reviewQueue."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wav_path = root / "speech.wav"
            # Speech 0.0-1.0s, NOISY sound in pause 1.0-2.0s (amp 0.5), speech 2.0-3.0s
            create_synthetic_audio(wav_path, [(0.0, 1.0, 0.8), (1.0, 2.0, 0.5), (2.0, 3.0, 0.8)], total_duration=4.0)

            plan = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {"src": {"path": "speech.wav", "duration": 4.0}},
                "timeline": [
                    {
                        "id": "seg-1",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 0.0,
                        "sourceEnd": 3.0,
                        "targetStart": 0.0,
                    }
                ],
                "reviewQueue": []
            }
            words = [
                {"id": "w1", "text": "第一段", "start": 0.0, "end": 1.0},
                {"id": "w2", "text": "第二段", "start": 2.0, "end": 3.0},
            ]

            tightened_plan, report = tighten_pauses(
                plan,
                threshold=0.35,
                keep=0.25,
                words_per_segment={"seg-1": words},
                verify_audio_energy=True,
            )

            # Must NOT cut this pause blindly; should flag to reviewQueue
            self.assertGreater(len(tightened_plan.get("reviewQueue", [])), 0)
            rq_item = tightened_plan["reviewQueue"][0]
            self.assertEqual(rq_item["type"], "pause_with_audio_activity")
            self.assertEqual(report["summary"]["pauses_flagged_review"], 1)

    def test_pause_ledger_conservation_and_reports(self):
        """Report verifies duration conservation: original == tightened + removed."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wav_path = root / "speech.wav"
            create_synthetic_audio(wav_path, [(0.0, 1.0, 0.8), (3.0, 4.0, 0.8)], total_duration=5.0)

            plan = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {"src": {"path": "speech.wav", "duration": 5.0}},
                "timeline": [
                    {
                        "id": "seg-1",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 0.0,
                        "sourceEnd": 1.0,
                        "targetStart": 0.0,
                    },
                    {
                        "id": "seg-2",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 3.0,
                        "sourceEnd": 4.0,
                        "targetStart": 2.0,  # 1.0s gap
                    }
                ],
                "reviewQueue": []
            }

            tightened_plan, report = tighten_pauses(plan, threshold=0.35, keep=0.25)
            rep_path = root / "Rough/pauses-report.json"
            generate_pauses_report(report, rep_path)

            self.assertTrue(rep_path.is_file())
            saved_rep = json.loads(rep_path.read_text(encoding="utf-8"))
            self.assertIn("summary", saved_rep)
            self.assertIn("pauses", saved_rep)
            # Duration conservation
            orig_dur = report["summary"]["original_duration_seconds"]
            tight_dur = report["summary"]["tightened_duration_seconds"]
            removed = report["summary"]["seconds_removed"]
            self.assertAlmostEqual(orig_dur, tight_dur + removed, places=2)

    def test_short_phoneme_not_dropped(self):
        """Short phoneme (e.g. 0.08s < 100ms) at the tail must NOT be dropped."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wav_path = root / "speech.wav"
            # Speech: 0.0-1.0s, pause: 1.0-2.0s, tail word: 2.0-2.08s (only 80ms)
            create_synthetic_audio(wav_path, [(0.0, 1.0, 0.8), (2.0, 2.08, 0.8)], total_duration=3.0)

            plan = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {"src": {"path": "speech.wav", "duration": 3.0}},
                "timeline": [
                    {
                        "id": "seg-short",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 0.0,
                        "sourceEnd": 2.08,
                        "targetStart": 0.0,
                        "text": "测试尾部短促音",
                    }
                ],
                "reviewQueue": []
            }
            words = [
                {"id": "w1", "text": "测试", "start": 0.0, "end": 1.0},
                {"id": "w2", "text": "音", "start": 2.0, "end": 2.08},
            ]

            tightened_plan, report = tighten_pauses(
                plan,
                threshold=0.35,
                keep=0.25,
                words_per_segment={"seg-short": words},
            )

            keeps = [x for x in tightened_plan["timeline"] if x["op"] == "keep"]
            self.assertEqual(len(keeps), 2)
            # The 80ms tail word must be preserved in keeps[1]!
            self.assertEqual(keeps[1]["sourceStart"], 2.0)
            self.assertEqual(keeps[1]["sourceEnd"], 2.08)
            self.assertEqual(keeps[1]["text"], "音")

    def test_cli_tighten_apply_and_validate_and_preview(self):
        """CLI tighten --apply updates plan, passes validate --strict, and successfully generates preview."""
        cli = Path(__file__).resolve().parent / "auto_edit.py"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wav_path = root / "speech.wav"
            # Speech 1: 0.0 to 0.9s (clean silence at 1.0s boundary); Silence: 0.9 to 3.0s; Speech 2: 3.0 to 3.9s
            create_synthetic_audio(wav_path, [(0.0, 0.9, 0.8), (3.0, 3.9, 0.8)], total_duration=5.0)
            mp4_path = root / "speech.mp4"
            subprocess.run([
                "ffmpeg", "-v", "error", "-y",
                "-f", "lavfi", "-i", "color=size=160x90:rate=25:duration=5",
                "-i", str(wav_path),
                "-shortest", "-c:v", "libx264", "-c:a", "aac", str(mp4_path)
            ], check=True)

            plan_data = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {"src": {"path": "speech.mp4", "duration": 5.0}},
                "timeline": [
                    {
                        "id": "seg-1",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 0.0,
                        "sourceEnd": 1.0,
                        "targetStart": 0.0,
                        "text": "第一段预览测试",
                        "manuscript": "第一段预览测试",
                    },
                    {
                        "id": "seg-2",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 3.0,
                        "sourceEnd": 4.0,
                        "targetStart": 2.0,  # 1.0s gap
                        "text": "第二段预览测试",
                        "manuscript": "第二段预览测试",
                    }
                ],
                "reviewQueue": []
            }
            plan_dir = root / "Rough"
            plan_dir.mkdir(parents=True, exist_ok=True)
            plan_file = plan_dir / "edit-plan.v1.json"
            plan_file.write_text(json.dumps(plan_data, indent=2, ensure_ascii=False), encoding="utf-8")

            # 1. tighten --apply
            res = subprocess.run([sys.executable, str(cli), "tighten", str(root), "--apply"],
                                 capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

            # 2. preview generation: must succeed without ValueError('preview requires a contiguous A-roll Final timeline')
            prev_res = subprocess.run([sys.executable, str(cli), "preview", str(root)],
                                      capture_output=True, text=True)
            self.assertEqual(prev_res.returncode, 0, prev_res.stderr)
            self.assertTrue((plan_dir / "auto-cut-preview.mp4").is_file())

            # 3. validate --strict
            val_res = subprocess.run([sys.executable, str(cli), "validate", str(root), "--strict"],
                                     capture_output=True, text=True)
            self.assertEqual(val_res.returncode, 0, val_res.stderr)

    def test_multi_segment_cascade_maintains_target_start(self):
        """SEC-01: Multi-segment cascade ensures sub-segments have contiguous targetStart and downstream items ripple."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wav_path = root / "speech.wav"
            create_synthetic_audio(wav_path, [(0.0, 1.0, 0.8), (2.0, 3.0, 0.8), (5.0, 6.0, 0.8)], total_duration=8.0)

            plan = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {"src": {"path": "speech.wav", "duration": 8.0}},
                "timeline": [
                    {
                        "id": "seg-1",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 0.0,
                        "sourceEnd": 3.0,
                        "targetStart": 0.0,
                        "text": "第一句的前半部分和后半部分",
                    },
                    {
                        "id": "seg-2",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 5.0,
                        "sourceEnd": 6.0,
                        "targetStart": 3.5,  # 0.5s gap after original seg-1
                        "text": "第二句",
                    }
                ],
                "reviewQueue": []
            }
            words_per_segment = {
                "seg-1": [
                    {"word": "前半", "text": "前半", "start": 0.0, "end": 1.0},
                    {"word": "后半", "text": "后半", "start": 2.0, "end": 3.0},
                ]
            }

            tightened_plan, report = tighten_pauses(
                plan,
                threshold=0.35,
                keep=0.25,
                words_per_segment=words_per_segment,
                verify_audio_energy=True,
            )

            keeps = [x for x in tightened_plan["timeline"] if x["op"] == "keep"]
            # seg-1 splits into p1 (0.0-1.24) and p2 (1.24-2.24)
            self.assertEqual(len(keeps), 3)
            self.assertEqual(keeps[0]["id"], "seg-1_p1")
            self.assertEqual(keeps[0]["targetStart"], 0.0)
            self.assertEqual(keeps[1]["id"], "seg-1_p2")
            # p2 targetStart must be equal to p1's target end (no jump or reset to 0.0!)
            p1_dur = keeps[0]["sourceEnd"] - keeps[0]["sourceStart"]
            self.assertAlmostEqual(keeps[1]["targetStart"], keeps[0]["targetStart"] + p1_dur, delta=1.0/25)

            # seg-2 targetStart must be properly placed after p2 and tightened
            p2_dur = keeps[1]["sourceEnd"] - keeps[1]["sourceStart"]
            p2_end = keeps[1]["targetStart"] + p2_dur
            gap_to_seg2 = keeps[2]["targetStart"] - p2_end
            self.assertAlmostEqual(gap_to_seg2, 0.25, delta=1.0/25)

    def test_stereo_source_preview_with_gaps(self):
        """SEC-02 & SEC-04: Preview with stereo source and gaps succeeds without channel layout mismatch or cmdline limit."""
        cli = Path(__file__).resolve().parent / "auto_edit.py"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            media_path = root / "stereo.mp4"
            # Create a 2-channel stereo test video
            subprocess.run([
                'ffmpeg', '-v', 'error', '-y',
                '-f', 'lavfi', '-i', 'color=c=blue:s=320x180:r=25:d=5',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5',
                '-ac', '2', '-c:v', 'libx264', '-c:a', 'aac',
                str(media_path)
            ], check=True)

            plan_data = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {"src": {"path": "stereo.mp4", "duration": 5.0}},
                "timeline": [
                    {
                        "id": "seg-1",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 0.0,
                        "sourceEnd": 1.0,
                        "targetStart": 0.0,
                    },
                    {
                        "id": "seg-2",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 2.0,
                        "sourceEnd": 3.0,
                        "targetStart": 2.0,  # 1.0s gap
                    }
                ],
                "reviewQueue": []
            }
            plan_dir = root / "Rough"
            plan_dir.mkdir(parents=True, exist_ok=True)
            plan_file = plan_dir / "edit-plan.v1.json"
            plan_file.write_text(json.dumps(plan_data, indent=2, ensure_ascii=False), encoding="utf-8")

            prev_res = subprocess.run([sys.executable, str(cli), "preview", str(root)],
                                      capture_output=True, text=True)
            self.assertEqual(prev_res.returncode, 0, prev_res.stderr)
            preview_mp4 = plan_dir / "auto-cut-preview.mp4"
            self.assertTrue(preview_mp4.is_file())

            # Check channels in preview output using ffprobe
            probe_res = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(preview_mp4)],
                                       capture_output=True, text=True, check=True)
            streams = json.loads(probe_res.stdout)['streams']
            a_stream = next(s for s in streams if s['codec_type'] == 'audio')
            self.assertEqual(a_stream['channels'], 2)

    def test_large_discarded_source_gap_not_scanned(self):
        """SEC-03: Two keeps separated by large source gap (>300s) tighten timeline without scanning 300s of audio."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {"src": {"path": "dummy.wav", "duration": 600.0}},
                "timeline": [
                    {
                        "id": "seg-1",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 0.0,
                        "sourceEnd": 2.0,
                        "targetStart": 0.0,
                    },
                    {
                        "id": "seg-2",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 350.0,  # 348s gap in source!
                        "sourceEnd": 352.0,
                        "targetStart": 3.0,  # 1.0s gap on timeline
                    }
                ],
                "reviewQueue": []
            }
            tightened_plan, report = tighten_pauses(
                plan,
                threshold=0.35,
                keep=0.25,
                verify_audio_energy=True,
            )
            keeps = [x for x in tightened_plan["timeline"] if x["op"] == "keep"]
            # Target gap is tightened to ~0.25s
            gap = keeps[1]["targetStart"] - (keeps[0]["targetStart"] + (keeps[0]["sourceEnd"] - keeps[0]["sourceStart"]))
            self.assertAlmostEqual(gap, 0.25, delta=1.0/25)

    def test_unsplit_segment_preserves_id(self):
        """SEC-08: Segment without pause cuts retains its original ID instead of being renamed to _p1."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {"src": {"path": "dummy.wav", "duration": 3.0}},
                "timeline": [
                    {
                        "id": "original-stable-id",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 0.0,
                        "sourceEnd": 2.0,
                        "targetStart": 0.0,
                        "text": "没有任何长停顿的句子",
                    }
                ],
                "reviewQueue": []
            }
            words_per_segment = {
                "original-stable-id": [
                    {"word": "任何", "text": "任何", "start": 0.1, "end": 0.8},
                    {"word": "停顿", "text": "停顿", "start": 1.0, "end": 1.8},  # 0.2s gap < 0.35s
                ]
            }
            tightened_plan, report = tighten_pauses(
                plan,
                threshold=0.35,
                keep=0.25,
                words_per_segment=words_per_segment,
                verify_audio_energy=False,
            )
            keeps = [x for x in tightened_plan["timeline"] if x["op"] == "keep"]
            self.assertEqual(len(keeps), 1)
            self.assertEqual(keeps[0]["id"], "original-stable-id")


def plan_duration_frames(plan, fps):
    ends = 0
    for item in plan["timeline"]:
        if item["op"] == "keep":
            t = frame(item["targetStart"], fps)
            dur = frame(item["sourceEnd"], fps) - frame(item["sourceStart"], fps)
            ends = max(ends, t + dur)
    return ends


if __name__ == "__main__":
    unittest.main()
