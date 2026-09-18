import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np
import scipy.io.wavfile as wavfile

# Add lib to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.boundary_protect import (
    analyze_cut_boundary,
    verify_sentence_boundary,
    generate_boundary_report,
)


def create_synthetic_audio(path: Path, segments: list[tuple[float, float, float]], total_duration: float, sr: int = 16000):
    """
    Generate synthetic WAV audio:
    segments: list of (start_s, end_s, amplitude) where amplitude > 0 is tone (speech proxy), 0 is silence.
    """
    n_samples = int(total_duration * sr)
    audio = np.zeros(n_samples, dtype=np.float32)
    for start, end, amp in segments:
        s_idx = int(start * sr)
        e_idx = int(end * sr)
        if amp > 0:
            t = np.linspace(0, end - start, e_idx - s_idx, endpoint=False)
            # 220Hz tone with slight harmonic to mimic voice formant
            tone = amp * 0.7 * np.sin(2 * np.pi * 220 * t) + amp * 0.3 * np.sin(2 * np.pi * 440 * t)
            # apply 10ms smooth ramp at head and tail
            ramp_len = min(int(0.01 * sr), len(tone) // 2)
            if ramp_len > 0:
                tone[:ramp_len] *= np.linspace(0, 1, ramp_len)
                tone[-ramp_len:] *= np.linspace(1, 0, ramp_len)
            audio[s_idx:e_idx] = tone
    # Normalize and convert to int16
    int16_audio = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    wavfile.write(str(path), sr, int16_audio)


class TestBoundaryProtection(unittest.TestCase):

    def test_asr_early_cutoff_extended_to_silence(self):
        """When ASR ends early while speech continues, cut point must extend to stable silence."""
        with tempfile.TemporaryDirectory() as td:
            wav_path = Path(td) / "speech.wav"
            # Speech from 0.5s to 2.4s (tail syllable lasts until 2.4s), silence 2.4s to 3.5s
            create_synthetic_audio(wav_path, [(0.5, 2.4, 0.8)], total_duration=3.5)

            # ASR mistakenly reported speech ending early at 2.0s
            decision = analyze_cut_boundary(
                audio_path=wav_path,
                candidate_end=2.0,
                sentence_text="当畜五牸，意思就是养母畜。",
                manuscript_text="当畜五牸，意思就是养母畜。",
                tail_chars=3,
                max_search_window=1.0,
            )

            # The cut point must NOT be at 2.0s or before 2.4s (which would truncate "畜")
            self.assertGreaterEqual(decision["safe_end"], 2.40,
                                    f"Cut point {decision['safe_end']} truncated tail phoneme before 2.40s")
            self.assertTrue(decision["tail_preserved"])
            self.assertEqual(decision["status"], "approved")

    def test_tail_word_missing_in_asr_routes_to_review(self):
        """When manuscript tail characters are absent from ASR transcript, refuse blind cut."""
        with tempfile.TemporaryDirectory() as td:
            wav_path = Path(td) / "speech.wav"
            create_synthetic_audio(wav_path, [(0.5, 2.0, 0.8)], total_duration=3.0)

            # ASR missing the last word "畜"
            decision = analyze_cut_boundary(
                audio_path=wav_path,
                candidate_end=2.0,
                sentence_text="当畜五牸，意思就是养母",
                manuscript_text="当畜五牸，意思就是养母畜。",
                tail_chars=3,
            )

            self.assertFalse(decision["tail_preserved"])
            self.assertEqual(decision["status"], "review_required")
            self.assertIn("tail_mismatch", decision["reason"])
            self.assertIsNotNone(decision.get("reviewQueueItem"))

    def test_local_tail_verification_immune_to_other_sentences(self):
        """Tail verification must be strictly local, not fooled by same tail words elsewhere."""
        sentence_1_manuscript = "今天的天气很好"
        sentence_1_transcript = "今天的天气"  # Missing "很好"
        full_text_containing_other = "今天的天气我们在外面玩这个设计很好"  # "很好" appears in other sentence

        # Verify sentence 1 locally
        result = verify_sentence_boundary(
            sentence_transcript=sentence_1_transcript,
            manuscript_sentence=sentence_1_manuscript,
            full_context_text=full_text_containing_other,
            tail_chars=2,
        )

        self.assertFalse(result["tail_matched"], "Local check must fail even if tail chars exist elsewhere")
        self.assertEqual(result["missing_tail"], "很好")

    def test_bounded_search_does_not_swallow_next_speech(self):
        """Search window must be constrained by next speech start time."""
        with tempfile.TemporaryDirectory() as td:
            wav_path = Path(td) / "speech.wav"
            # Sentence 1: 0.5s - 2.0s; Sentence 2: 2.3s - 3.5s (gap is only 0.3s)
            create_synthetic_audio(wav_path, [(0.5, 2.0, 0.8), (2.3, 3.5, 0.8)], total_duration=4.0)

            decision = analyze_cut_boundary(
                audio_path=wav_path,
                candidate_end=1.9,
                sentence_text="第一句话结束",
                manuscript_text="第一句话结束",
                next_speech_start=2.3,
            )

            # Safe end must not swallow into next speech >= 2.3s
            self.assertLess(decision["safe_end"], 2.30)

    def test_boundary_report_generation(self):
        """Boundary report structure must conform to Rough/cut-boundary-report.json."""
        with tempfile.TemporaryDirectory() as td:
            wav_path = Path(td) / "speech.wav"
            create_synthetic_audio(wav_path, [(0.5, 1.8, 0.8)], total_duration=2.5)

            decisions = [
                analyze_cut_boundary(
                    audio_path=wav_path,
                    candidate_end=1.7,
                    sentence_text="当畜五牸，意思就是养母畜。",
                    manuscript_text="当畜五牸，意思就是养母畜。",
                )
            ]
            report_path = Path(td) / "cut-boundary-report.json"
            generate_boundary_report(decisions, report_path)

            self.assertTrue(report_path.is_file())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertIn("boundaries", report)
            self.assertIn("summary", report)
            self.assertEqual(report["summary"]["total_checked"], 1)

    def test_head_word_missing_in_asr_routes_to_review(self):
        """When manuscript head characters are absent from ASR transcript, route to review."""
        with tempfile.TemporaryDirectory() as td:
            wav_path = Path(td) / "speech.wav"
            create_synthetic_audio(wav_path, [(0.5, 2.0, 0.8)], total_duration=3.0)

            decision = analyze_cut_boundary(
                audio_path=wav_path,
                candidate_end=2.0,
                sentence_text="意思就是养母畜。",
                manuscript_text="当畜五牸，意思就是养母畜。",
                head_chars=3,
            )

            self.assertFalse(decision["head_preserved"])
            self.assertEqual(decision["status"], "review_required")
            self.assertIn("head_mismatch", decision["reason"])
            self.assertIsNotNone(decision.get("reviewQueueItem"))

    def test_cli_boundary_check_apply_and_strict_validate(self):
        """Test boundary-check --apply updates plan sourceEnd and validate --strict blocks unreviewed items."""
        cli = Path(__file__).resolve().parent / "auto_edit.py"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wav_path = root / "raw.wav"
            # Audio speech from 0.5 to 2.4s, silence 2.4 to 3.5s
            create_synthetic_audio(wav_path, [(0.5, 2.4, 0.8)], total_duration=3.5)

            # Create an edit plan with candidate_end at 2.0s (ASR premature cutoff)
            plan_data = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {"raw": "raw.wav"},
                "timeline": [
                    {
                        "id": "seg-1",
                        "op": "keep",
                        "sourceId": "raw",
                        "sourceStart": 0.5,
                        "sourceEnd": 2.0,
                        "targetStart": 0.0,
                        "text": "当畜五牸，意思就是养母畜。",
                        "manuscript": "当畜五牸，意思就是养母畜。",
                    },
                    {
                        "id": "seg-2",
                        "op": "keep",
                        "sourceId": "raw",
                        "sourceStart": 2.5,
                        "sourceEnd": 3.2,
                        "targetStart": 1.5,
                        "text": "第二句继续说话。",
                        "manuscript": "第二句继续说话。",
                    }
                ],
                "reviewQueue": []
            }
            plan_dir = root / "Rough"
            plan_dir.mkdir(parents=True, exist_ok=True)
            plan_file = plan_dir / "edit-plan.v1.json"
            plan_file.write_text(json.dumps(plan_data, indent=2, ensure_ascii=False), encoding="utf-8")

            # 1. Run boundary-check --apply
            res = subprocess.run([sys.executable, str(cli), "boundary-check", str(root), "--apply"],
                                 capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

            # Check that plan was updated: seg-1 sourceEnd extended to >= 2.4s
            updated_plan = json.loads(plan_file.read_text(encoding="utf-8"))
            seg1 = [x for x in updated_plan["timeline"] if x["id"] == "seg-1"][0]
            self.assertGreaterEqual(seg1["sourceEnd"], 2.40)

            # Check that seg-2 targetStart was ripple-shifted
            seg2 = [x for x in updated_plan["timeline"] if x["id"] == "seg-2"][0]
            self.assertGreater(seg2["targetStart"], 1.5)

            # 2. Run validate --strict: since text matches and speech snapped cleanly, should exit 0
            val_res = subprocess.run([sys.executable, str(cli), "validate", str(root), "--strict"],
                                     capture_output=True, text=True)
            self.assertEqual(val_res.returncode, 0, val_res.stderr)
            val_json = json.loads((plan_dir / "auto-cut-validation.json").read_text(encoding="utf-8"))
            self.assertEqual(val_json["status"], "ok")

            # 3. Now corrupt seg-1 text to cause mismatch and test validate --strict blocking
            updated_plan["timeline"][0]["text"] = "篡改截断的句子"
            plan_file.write_text(json.dumps(updated_plan, indent=2, ensure_ascii=False), encoding="utf-8")

            fail_res = subprocess.run([sys.executable, str(cli), "validate", str(root), "--strict"],
                                      capture_output=True, text=True)
            self.assertNotEqual(fail_res.returncode, 0)
            fail_val = json.loads((plan_dir / "auto-cut-validation.json").read_text(encoding="utf-8"))
            self.assertEqual(fail_val["status"], "review_required")
            self.assertGreater(fail_val["boundaryCheck"]["review_required"], 0)

    def test_speech_continues_at_window_boundary_marked_ambiguous(self):
        """When voice activity persists right up to the search window boundary, mark review_required."""
        with tempfile.TemporaryDirectory() as td:
            wav_path = Path(td) / "speech.wav"
            # Speech continuous from 0.5s to 3.0s, candidate_end at 2.0s, search window max 0.5s (up to 2.5s)
            create_synthetic_audio(wav_path, [(0.5, 3.0, 0.8)], total_duration=3.5)

            decision = analyze_cut_boundary(
                audio_path=wav_path,
                candidate_end=2.0,
                sentence_text="持续长句发音未结束",
                manuscript_text="持续长句发音未结束",
                max_search_window=0.5,
            )

            self.assertEqual(decision["status"], "review_required")
            self.assertIn("speech_continues_at_search_boundary", decision["reason"])
            self.assertIsNotNone(decision.get("reviewQueueItem"))

    def test_speech_collides_with_next_speech_marked_ambiguous(self):
        """When speech continues right into next speech (< 50ms gap), mark review_required."""
        with tempfile.TemporaryDirectory() as td:
            wav_path = Path(td) / "speech.wav"
            # Sentence 1 speech ends at 2.28s; Sentence 2 starts at 2.30s (gap is only 20ms < silence_margin 50ms)
            create_synthetic_audio(wav_path, [(0.5, 2.28, 0.8), (2.30, 3.5, 0.8)], total_duration=4.0)

            decision = analyze_cut_boundary(
                audio_path=wav_path,
                candidate_end=2.0,
                sentence_text="紧凑口播第一句",
                manuscript_text="紧凑口播第一句",
                next_speech_start=2.30,
            )

            self.assertEqual(decision["status"], "review_required")
            self.assertIsNotNone(decision.get("reviewQueueItem"))
            self.assertEqual(decision["reviewQueueItem"]["type"], "cut_boundary_ambiguous")

    def test_frame_domain_quantization_ripple_shift(self):
        """Ripple shifting downstream clips must use frame math to prevent ValueError: overlap or nonmonotonic timeline."""
        cli = Path(__file__).resolve().parent / "auto_edit.py"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wav_path = root / "raw.wav"
            # Audio speech from 0.0 to 1.025s (at 25 fps, 1.018s -> frame 25; 1.025s -> frame 26)
            create_synthetic_audio(wav_path, [(0.0, 1.025, 0.8)], total_duration=2.0)

            # Construct edge case: seg-1 sourceEnd is 1.018s (frame 25), safe_end will extend to > 1.02s (frame 26).
            # seg-2 targetStart is 1.00s (frame 25).
            plan_data = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {"raw": "raw.wav"},
                "timeline": [
                    {
                        "id": "seg-1",
                        "op": "keep",
                        "sourceId": "raw",
                        "sourceStart": 0.0,
                        "sourceEnd": 1.018,
                        "targetStart": 0.0,
                        "text": "测试毫秒量化进位第一段",
                        "manuscript": "测试毫秒量化进位第一段",
                    },
                    {
                        "id": "seg-2",
                        "op": "keep",
                        "sourceId": "raw",
                        "sourceStart": 1.2,
                        "sourceEnd": 1.8,
                        "targetStart": 1.00,
                        "text": "测试毫秒量化进位第二段",
                        "manuscript": "测试毫秒量化进位第二段",
                    }
                ],
                "reviewQueue": []
            }
            plan_dir = root / "Rough"
            plan_dir.mkdir(parents=True, exist_ok=True)
            plan_file = plan_dir / "edit-plan.v1.json"
            plan_file.write_text(json.dumps(plan_data, indent=2, ensure_ascii=False), encoding="utf-8")

            res = subprocess.run([sys.executable, str(cli), "boundary-check", str(root), "--apply"],
                                 capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)


if __name__ == "__main__":
    unittest.main()
