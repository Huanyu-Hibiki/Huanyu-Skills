"""End-to-end integration acceptance tests for Task 11: full pipeline from raw to draft."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).with_name("auto_edit.py")
DRAFT_CLI = Path(__file__).resolve().parents[1] / "video-jianying-draft" / "jianying.py"


class TestE2EPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / "Project"
        self.project.mkdir(parents=True, exist_ok=True)
        self.rough = self.project / "Rough"
        self.rough.mkdir(parents=True, exist_ok=True)

        # Generate standard test video files with ffmpeg
        self.raw_a_roll = self.project / "Raw" / "a_roll.mp4"
        self.raw_a_roll.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", "color=c=blue:s=320x180:r=25:d=8",
            "-f", "lavfi", "-i", "sine=f=440:r=44100:d=8",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(self.raw_a_roll)
        ], check=True)

        self.raw_screen = self.project / "Raw" / "screen.mp4"
        subprocess.run([
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", "color=c=green:s=320x180:r=25:d=10",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", "-t", "10", str(self.raw_screen)
        ], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_e2e_use_case_1_standard_spoken(self):
        """Use Case 1: Standard A-roll speech cuts, draft generation, subtitles, and preview consistency."""
        plan_req = {
            "version": "1",
            "fps": 25,
            "sources": {
                "raw_video": str(self.raw_a_roll)
            },
            "timeline": [
                {
                    "id": "intro",
                    "op": "keep",
                    "sourceId": "raw_video",
                    "sourceStart": 0.5,
                    "sourceEnd": 2.5,
                    "targetStart": 0.0,
                    "text": "欢迎大家收看本期技术讲解",
                    "speaker": "host"
                },
                {
                    "id": "concept",
                    "op": "keep",
                    "sourceId": "raw_video",
                    "sourceStart": 3.0,
                    "sourceEnd": 5.5,
                    "targetStart": 2.0,
                    "text": "今天我们要探讨完整的视频自动剪辑管线",
                    "speaker": "host"
                },
                {
                    "id": "discarded_gap",
                    "op": "remove",
                    "sourceId": "raw_video",
                    "sourceStart": 2.5,
                    "sourceEnd": 3.0,
                    "reason": "pause_tightening"
                }
            ]
        }
        input_plan_path = self.rough / "input_plan.json"
        input_plan_path.write_text(json.dumps(plan_req, indent=2, ensure_ascii=False), encoding="utf-8")

        # 1. auto_edit.py plan
        res = subprocess.run([
            sys.executable, str(CLI), "plan", str(self.project), "--input", str(input_plan_path)
        ], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

        # 2. auto_edit.py validate
        res = subprocess.run([
            sys.executable, str(CLI), "validate", str(self.project)
        ], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

        # 3. subtitles & preview
        for cmd in ("subtitles", "preview"):
            res = subprocess.run([
                sys.executable, str(CLI), cmd, str(self.project)
            ], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

        # Verify subtitles has timelineVersion
        srt_file = self.rough / "auto-cut.srt"
        self.assertTrue(srt_file.is_file())
        self.assertIn("timelineVersion:", srt_file.read_text(encoding="utf-8"))

        # Verify preview duration matches plan
        preview_file = self.rough / "auto-cut-preview.mp4"
        self.assertTrue(preview_file.is_file())
        preview_meta = json.loads(preview_file.with_suffix(".json").read_text(encoding="utf-8"))
        # 2.0s + 2.5s = 4.5s (112 or 113 frames at 25fps)
        self.assertAlmostEqual(preview_meta["duration"], 4.5, delta=0.08)

        # 4. Generate JianYing draft
        draft_dir = self.project / "Drafts"
        res = subprocess.run([
            sys.executable, str(DRAFT_CLI), "apply_edit_plan",
            "--plan", str(self.rough / "edit-plan.v1.json"),
            "--output-dir", str(draft_dir),
            "--draft-id", "standard-cut"
        ], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

        draft_content_path = draft_dir / "standard-cut" / "draft_content.json"
        self.assertTrue(draft_content_path.is_file())
        draft_content = json.loads(draft_content_path.read_text(encoding="utf-8"))

        # Check recovery track is muted
        recovery_tracks = [t for t in draft_content.get("tracks", []) if t.get("name") == "A-roll Recovery"]
        if recovery_tracks:
            self.assertEqual(recovery_tracks[0].get("attribute"), 1)

    def test_e2e_use_case_2_takes_selection_and_pauses(self):
        """Use Case 2: Multi-take retry selection, pause tightening, and circuit breaker."""
        takes_data = {
            "version": "1.0",
            "algorithm": "takes_selection",
            "sources": {
                "raw_video": {
                    "path": str(self.raw_a_roll),
                    "duration": 8.0
                }
            },
            "sentences": [
                {
                    "idx": 0,
                    "text": "大家好欢迎来到频道",
                    "takes": [
                        {
                            "id": "s1_take1",
                            "start": 0.5,
                            "end": 2.5,
                            "completeness": 0.5,
                            "match": 0.6,
                            "speed": 1.2
                        },
                        {
                            "id": "s1_take2",
                            "start": 2.8,
                            "end": 4.8,
                            "completeness": 1.0,
                            "match": 0.95,
                            "speed": 1.0
                        }
                    ]
                },
                {
                    "idx": 1,
                    "text": "今天介绍核心技术方案",
                    "takes": [
                        {
                            "id": "s2_take1",
                            "start": 5.5,
                            "end": 7.5,
                            "completeness": 1.0,
                            "match": 0.95,
                            "speed": 1.0
                        }
                    ]
                }
            ]
        }
        takes_file = self.rough / "takes_decision.json"
        takes_file.write_text(json.dumps(takes_data, indent=2, ensure_ascii=False), encoding="utf-8")

        # 1. select-takes with --apply
        res = subprocess.run([
            sys.executable, str(CLI), "select-takes", str(self.project),
            "--takes", str(takes_file),
            "--apply"
        ], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

        plan = json.loads((self.rough / "edit-plan.v1.json").read_text(encoding="utf-8"))
        self.assertEqual(len([x for x in plan["timeline"] if x["op"] == "keep"]), 2)
        self.assertEqual(len([x for x in plan["timeline"] if x["op"] == "remove"]), 1)

        # 2. validate with circuit breaker checks
        res = subprocess.run([
            sys.executable, str(CLI), "validate", str(self.project)
        ], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        val_data = json.loads((self.rough / "auto-cut-validation.json").read_text(encoding="utf-8"))
        self.assertFalse(val_data["circuitBreaker"]["circuit_broken"])

    def test_e2e_use_case_3_screen_demo_and_reconcile(self):
        """Use Case 3: Silent screen recording markers, multi-track assemble, and draft reconciliation."""
        plan_req = {
            "version": "1",
            "fps": 25,
            "sources": {
                "raw_video": str(self.raw_a_roll)
            },
            "timeline": [
                {
                    "id": "sec1",
                    "op": "keep",
                    "sourceId": "raw_video",
                    "sourceStart": 0.5,
                    "sourceEnd": 3.0,
                    "targetStart": 0.0,
                    "text": "第一部分是系统初始化",
                    "speaker": "host"
                },
                {
                    "id": "sec2",
                    "op": "keep",
                    "sourceId": "raw_video",
                    "sourceStart": 3.5,
                    "sourceEnd": 6.5,
                    "targetStart": 2.5,
                    "text": "第二部分我们展示录屏演示功能",
                    "speaker": "host"
                }
            ]
        }
        input_plan_path = self.rough / "edit-plan.v1.json"
        input_plan_path.write_text(json.dumps(plan_req, indent=2, ensure_ascii=False), encoding="utf-8")
        subprocess.run([sys.executable, str(CLI), "plan", str(self.project), "--input", str(input_plan_path)], check=True)

        markers_data = [
            {
                "id": "demo_screen_01",
                "anchor": "录屏演示",
                "start": 1.0,
                "end": 3.5,
                "min_required_duration": 1.0
            }
        ]
        markers_file = self.rough / "screen_markers.json"
        markers_file.write_text(json.dumps(markers_data, indent=2, ensure_ascii=False), encoding="utf-8")

        res = subprocess.run([
            sys.executable, str(CLI), "insert-screen-demo", str(self.project),
            "--screen", str(self.raw_screen),
            "--markers", str(markers_file),
            "--apply"
        ], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

        manifest_file = self.project / "Polished" / "broll-manifest.v1.json"
        self.assertTrue(manifest_file.is_file())
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["items"]), 1)
        orig_target_start = manifest["items"][0]["target_start"]
        self.assertAlmostEqual(orig_target_start, 2.72, delta=0.05)

        # Generate draft
        draft_dir = self.project / "Drafts"
        res = subprocess.run([
            sys.executable, str(DRAFT_CLI), "apply_edit_plan",
            "--plan", str(self.rough / "edit-plan.v1.json"),
            "--output-dir", str(draft_dir),
            "--draft-id", "multitrack-draft"
        ], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

        draft_content_path = draft_dir / "multitrack-draft" / "draft_content.json"
        self.assertTrue(draft_content_path.is_file())

        # Check Screen Demo track is muted in draft
        draft_content = json.loads(draft_content_path.read_text(encoding="utf-8"))
        screen_track = next((t for t in draft_content["tracks"] if t.get("name") == "Screen Demo"), None)
        self.assertIsNotNone(screen_track)
        self.assertEqual(screen_track.get("attribute"), 1)

        # Now simulate manual adjustment in JianYing: user trims sec1 from 2.5s down to 1.5s
        # (shifting sec2 from 2.5s to 1.5s, which is a -1.0s shift)
        sec1_seg = next(s for s in draft_content["tracks"][0]["segments"] if s.get("id") == "sec1")
        sec2_seg = next(s for s in draft_content["tracks"][0]["segments"] if s.get("id") == "sec2")
        sec1_seg["target_timerange"]["duration"] = 1500000
        sec1_seg["source_timerange"]["duration"] = 1500000
        sec2_seg["target_timerange"]["start"] = 1500000

        draft_content_path.write_text(json.dumps(draft_content, indent=2, ensure_ascii=False), encoding="utf-8")

        # Execute auto_edit.py reconcile
        res = subprocess.run([
            sys.executable, str(CLI), "reconcile", str(self.project),
            "--draft", str(draft_content_path),
            "--apply"
        ], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

        reconciled_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        # Target start must shift by exactly 1.0s!
        self.assertAlmostEqual(reconciled_manifest["items"][0]["target_start"], orig_target_start - 1.0, delta=0.05)

    def test_e2e_use_case_4_three_way_broll_and_recovery_safety(self):
        """Use Case 4: Full assembly of three-way B-roll (Screen Demo, Packaging, AI Visual) and silent recovery track."""
        broll_pkg_video = self.project / "Raw" / "broll_pkg.mp4"
        subprocess.run([
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", "color=c=red:s=320x180:r=25:d=2",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", "-t", "2", str(broll_pkg_video)
        ], check=True)

        broll_ai_video = self.project / "Raw" / "broll_ai.mp4"
        subprocess.run([
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", "color=c=yellow:s=320x180:r=25:d=2",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", "-t", "2", str(broll_ai_video)
        ], check=True)

        plan_req = {
            "version": "1",
            "fps": 25,
            "sources": {
                "raw_video": str(self.raw_a_roll),
                "screen_vid": str(self.raw_screen),
                "pkg_vid": str(broll_pkg_video),
                "ai_vid": str(broll_ai_video),
            },
            "timeline": [
                {
                    "id": "a_roll_1",
                    "op": "keep",
                    "sourceId": "raw_video",
                    "sourceStart": 0.0,
                    "sourceEnd": 3.0,
                    "targetStart": 0.0,
                    "track": "A-roll Final",
                    "text": "第一段主干口播",
                    "speaker": "host"
                },
                {
                    "id": "a_roll_2",
                    "op": "keep",
                    "sourceId": "raw_video",
                    "sourceStart": 4.0,
                    "sourceEnd": 7.0,
                    "targetStart": 3.0,
                    "track": "A-roll Final",
                    "text": "第二段主干口播演示",
                    "speaker": "host"
                },
                {
                    "id": "a_roll_removed_gap",
                    "op": "remove",
                    "sourceId": "raw_video",
                    "sourceStart": 3.0,
                    "sourceEnd": 4.0,
                    "reason": "pause_cut"
                },
                {
                    "id": "broll_screen_1",
                    "op": "insert_screen_demo",
                    "sourceId": "screen_vid",
                    "sourceStart": 0.0,
                    "sourceEnd": 2.0,
                    "targetStart": 0.5,
                    "track": "Screen Demo",
                    "anchor": "主干口播",
                },
                {
                    "id": "broll_pkg_1",
                    "op": "insert_broll_packaging",
                    "sourceId": "pkg_vid",
                    "sourceStart": 0.0,
                    "sourceEnd": 1.5,
                    "targetStart": 3.2,
                    "track": "B-roll Packaging",
                    "anchor": "演示",
                },
                {
                    "id": "broll_ai_1",
                    "op": "insert_broll_ai_visual",
                    "sourceId": "ai_vid",
                    "sourceStart": 0.0,
                    "sourceEnd": 1.5,
                    "targetStart": 4.5,
                    "track": "B-roll AI Visual",
                    "anchor": "演示",
                }
            ]
        }
        input_plan_path = self.rough / "edit-plan.v1.json"
        input_plan_path.write_text(json.dumps(plan_req, indent=2, ensure_ascii=False), encoding="utf-8")

        # 1. auto_edit.py plan & validate
        subprocess.run([sys.executable, str(CLI), "plan", str(self.project), "--input", str(input_plan_path)], check=True)
        res = subprocess.run([sys.executable, str(CLI), "validate", str(self.project)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

        # 2. preview rendering check
        res = subprocess.run([sys.executable, str(CLI), "preview", str(self.project)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        prev_file = self.rough / "auto-cut-preview.mp4"
        self.assertTrue(prev_file.is_file())

        # 3. Draft generation & verify_draft
        draft_dir = self.project / "Drafts"
        res = subprocess.run([
            sys.executable, str(DRAFT_CLI), "apply_edit_plan",
            "--plan", str(self.rough / "edit-plan.v1.json"),
            "--output-dir", str(draft_dir),
            "--draft-id", "all-tracks-draft"
        ], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

        draft_content_path = draft_dir / "all-tracks-draft" / "draft_content.json"
        self.assertTrue(draft_content_path.is_file())
        draft_content = json.loads(draft_content_path.read_text(encoding="utf-8"))

        tracks_by_name = {t.get("name"): t for t in draft_content.get("tracks", []) if "name" in t}
        # Check all three B-roll tracks are present and MUTED (attribute=1)
        for broll_track_name in ("Screen Demo", "B-roll Packaging", "B-roll AI Visual"):
            self.assertIn(broll_track_name, tracks_by_name)
            self.assertEqual(tracks_by_name[broll_track_name].get("attribute"), 1, f"{broll_track_name} must be muted")

        # Check recovery track is MUTED and present
        self.assertIn("A-roll Recovery", tracks_by_name)
        self.assertEqual(tracks_by_name["A-roll Recovery"].get("attribute"), 1)

        # 4. verify-draft CLI command
        res = subprocess.run([
            sys.executable, str(CLI), "verify-draft", str(self.project),
            "--draft", str(draft_content_path)
        ], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn('"status": "ok"', res.stdout)


if __name__ == "__main__":
    unittest.main()
