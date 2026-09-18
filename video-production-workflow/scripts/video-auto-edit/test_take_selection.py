"""Unit and integration tests for Task 4: Multi-take selection and recovery tracks."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.edit_plan import load_plan, frame
from lib.take_selection import (
    convert_takes_to_plan,
    evaluate_circuit_breaker,
    restore_take_in_plan,
)
from lib.edit_outputs import subtitles, verify_draft
import lib.edit_draft as edit_draft


class TestTakeSelection(unittest.TestCase):

    def test_completeness_hard_gate_overrules_speed_and_pause(self):
        """Hard gate: Complete sentence take MUST win over partial take even if partial take has better speed/pause."""
        takes_decision = {
            "summary": {"sentences": 1, "matched": 1, "unmatched": 0},
            "sentences": [
                {
                    "idx": 0,
                    "text": "我们今天来探讨视频自动剪辑的技术方案与实现路径。",
                    "takes": [
                        {
                            "id": "take-partial",
                            "start": 1.0,
                            "end": 3.0,
                            "match": 0.45,
                            "completeness": 0.40,  # Incomplete!
                            "pause_ratio": 0.0,
                            "rate_score": 1.0,  # Fast speech
                            "total": 0.85,
                            "sourceId": "src",
                        },
                        {
                            "id": "take-complete",
                            "start": 5.0,
                            "end": 10.0,
                            "match": 1.0,
                            "completeness": 1.0,  # Complete!
                            "pause_ratio": 0.20,
                            "rate_score": 0.80,
                            "total": 0.80,  # Total score slightly lower due to pause
                            "sourceId": "src",
                        }
                    ]
                }
            ]
        }
        sources = {"src": {"path": "dummy.mp4", "duration": 20.0}}
        plan, report = convert_takes_to_plan(takes_decision, sources, fps=25)

        keeps = [x for x in plan["timeline"] if x["op"] == "keep"]
        removes = [x for x in plan["timeline"] if x["op"] == "remove"]

        self.assertEqual(len(keeps), 1)
        self.assertEqual(keeps[0]["sourceStart"], 5.0)
        self.assertEqual(keeps[0]["sourceEnd"], 10.0)
        self.assertEqual(keeps[0]["undoGroup"], "sentence-0")

        self.assertEqual(len(removes), 1)
        self.assertEqual(removes[0]["sourceStart"], 1.0)
        self.assertEqual(removes[0]["sourceEnd"], 3.0)
        self.assertEqual(removes[0]["undoGroup"], "sentence-0")
        self.assertIn("partial_take", removes[0]["reason"])

    def test_low_confidence_candidate_routes_to_review(self):
        """Takes with high low-confidence ratio (>0.35) or low match are routed to reviewQueue."""
        takes_decision = {
            "summary": {"sentences": 1, "matched": 1, "unmatched": 0},
            "sentences": [
                {
                    "idx": 0,
                    "text": "这段话转录置信度极低可能是幻觉。",
                    "takes": [
                        {
                            "id": "take-hallucination",
                            "start": 2.0,
                            "end": 6.0,
                            "match": 0.80,
                            "completeness": 0.90,
                            "lowconf_ratio": 0.55,  # > 0.35
                            "total": 0.60,
                            "sourceId": "src",
                        }
                    ]
                }
            ]
        }
        sources = {"src": {"path": "dummy.mp4", "duration": 10.0}}
        plan, report = convert_takes_to_plan(takes_decision, sources, fps=25)

        # Must route to reviewQueue
        self.assertGreaterEqual(len(plan["reviewQueue"]), 1)
        self.assertEqual(plan["reviewQueue"][0]["type"], "low_confidence_take")
        self.assertEqual(plan["reviewQueue"][0]["action"], "hold_and_review")

    def test_rhetorical_parallelism_keeps_both_sentences(self):
        """Parallel sentences in manuscript are preserved as distinct sentences and takes."""
        takes_decision = {
            "summary": {"sentences": 2, "matched": 2, "unmatched": 0},
            "sentences": [
                {
                    "idx": 0,
                    "text": "因为有你，我们才能前行。",
                    "takes": [
                        {"id": "take-1", "start": 1.0, "end": 4.0, "match": 1.0, "completeness": 1.0, "sourceId": "src"}
                    ]
                },
                {
                    "idx": 1,
                    "text": "因为有你，我们才能前行。",  # Parallelism (identical text, different sentence index)
                    "takes": [
                        {"id": "take-2", "start": 5.0, "end": 8.0, "match": 1.0, "completeness": 1.0, "sourceId": "src"}
                    ]
                }
            ]
        }
        sources = {"src": {"path": "dummy.mp4", "duration": 10.0}}
        plan, report = convert_takes_to_plan(takes_decision, sources, fps=25)

        keeps = [x for x in plan["timeline"] if x["op"] == "keep"]
        self.assertEqual(len(keeps), 2)
        self.assertEqual(keeps[0]["undoGroup"], "sentence-0")
        self.assertEqual(keeps[1]["undoGroup"], "sentence-1")
        self.assertEqual(keeps[0]["targetStart"], 0.0)
        self.assertAlmostEqual(keeps[1]["targetStart"], 3.0, delta=1.0/25)

    def test_order_conflict_maintains_manuscript_sequence(self):
        """Retakes recorded out of order (e.g. S0 retake recorded after S1) are ordered by manuscript."""
        takes_decision = {
            "summary": {"sentences": 2, "matched": 2, "unmatched": 0},
            "sentences": [
                {
                    "idx": 0,
                    "text": "第一句话最后才重录成功。",
                    "takes": [
                        {"id": "take-0-bad", "start": 0.0, "end": 3.0, "match": 0.6, "completeness": 0.5, "sourceId": "src"},
                        {"id": "take-0-good", "start": 20.0, "end": 23.0, "match": 1.0, "completeness": 1.0, "sourceId": "src"},
                    ]
                },
                {
                    "idx": 1,
                    "text": "第二句话正常录制。",
                    "takes": [
                        {"id": "take-1", "start": 5.0, "end": 8.0, "match": 1.0, "completeness": 1.0, "sourceId": "src"}
                    ]
                }
            ]
        }
        sources = {"src": {"path": "dummy.mp4", "duration": 30.0}}
        plan, report = convert_takes_to_plan(takes_decision, sources, fps=25)

        keeps = [x for x in plan["timeline"] if x["op"] == "keep"]
        # Sentence 0 (retake at 20.0) MUST come first on targetStart!
        self.assertEqual(keeps[0]["undoGroup"], "sentence-0")
        self.assertEqual(keeps[0]["sourceStart"], 20.0)
        self.assertEqual(keeps[0]["targetStart"], 0.0)

        # Sentence 1 comes second on targetStart
        self.assertEqual(keeps[1]["undoGroup"], "sentence-1")
        self.assertEqual(keeps[1]["sourceStart"], 5.0)
        self.assertAlmostEqual(keeps[1]["targetStart"], 3.0, delta=1.0/25)

    def test_circuit_breaker_triggers_with_denominators(self):
        """Circuit breaker triggers on >35% deletion, >5% unmatched manuscript, or >3 high-risk items."""
        # 1. Test deletion ratio trigger (>35%)
        plan = {
            "version": "1",
            "fps": 25,
            "sources": {"src": {"duration": 100.0}},
            "timeline": [
                {"id": "k1", "op": "keep", "sourceId": "src", "sourceStart": 0.0, "sourceEnd": 55.0, "targetStart": 0.0},
                {"id": "r1", "op": "remove", "sourceId": "src", "sourceStart": 55.0, "sourceEnd": 95.0}, # 40s removed = 40% > 35%
            ],
            "reviewQueue": []
        }
        cb = evaluate_circuit_breaker(plan, total_sentences=10, unmatched_sentences=0)
        self.assertTrue(cb["circuit_broken"])
        self.assertIn("deletion_limit_exceeded", cb["triggers"])
        self.assertAlmostEqual(cb["metrics"]["deletion"]["actual"], 0.40, places=2)
        self.assertEqual(cb["metrics"]["deletion"]["source_s"], 100.0)
        self.assertEqual(cb["metrics"]["deletion"]["removed_s"], 40.0)

        # 2. Test unmatched manuscript trigger (>5%)
        plan2 = {
            "version": "1",
            "fps": 25,
            "sources": {"src": {"duration": 100.0}},
            "timeline": [
                {"id": "k1", "op": "keep", "sourceId": "src", "sourceStart": 0.0, "sourceEnd": 80.0, "targetStart": 0.0},
            ],
            "reviewQueue": []
        }
        cb2 = evaluate_circuit_breaker(plan2, total_sentences=10, unmatched_sentences=1) # 1/10 = 10% > 5%
        self.assertTrue(cb2["circuit_broken"])
        self.assertIn("unmatched_manuscript_exceeded", cb2["triggers"])
        self.assertAlmostEqual(cb2["metrics"]["unmatched_manuscript"]["actual"], 0.10, places=2)

        # 3. Test high risk items trigger (>3 items)
        plan3 = {
            "version": "1",
            "fps": 25,
            "sources": {"src": {"duration": 100.0}},
            "timeline": [
                {"id": "k1", "op": "keep", "sourceId": "src", "sourceStart": 0.0, "sourceEnd": 80.0, "targetStart": 0.0},
            ],
            "reviewQueue": [{"id": f"q{i}"} for i in range(4)] # 4 > 3
        }
        cb3 = evaluate_circuit_breaker(plan3, total_sentences=10, unmatched_sentences=0)
        self.assertTrue(cb3["circuit_broken"])
        self.assertIn("high_risk_items_exceeded", cb3["triggers"])
        self.assertEqual(cb3["metrics"]["high_risk"]["actual"], 4)

    def test_restore_take_recomputes_timeline_and_subtitles(self):
        """Restoring a removed take updates targetStart and subtitles monotonically."""
        plan = {
            "version": "1",
            "fps": 25,
            "projectRoot": ".",
            "sources": {"src": {"path": "dummy.mp4", "duration": 50.0}},
            "timeline": [
                {
                    "id": "take-0",
                    "op": "keep",
                    "sourceId": "src",
                    "sourceStart": 0.0,
                    "sourceEnd": 2.0,
                    "targetStart": 0.0,
                    "text": "第一句当前版本",
                    "undoGroup": "sentence-0",
                },
                {
                    "id": "take-0-alt",
                    "op": "remove",
                    "sourceId": "src",
                    "sourceStart": 5.0,
                    "sourceEnd": 9.0,  # 4s duration (longer than current 2s)
                    "text": "第一句备用重录版本更长",
                    "undoGroup": "sentence-0",
                },
                {
                    "id": "take-1",
                    "op": "keep",
                    "sourceId": "src",
                    "sourceStart": 15.0,
                    "sourceEnd": 18.0,
                    "targetStart": 2.0,  # Initially placed after take-0 at 2.0s
                    "text": "第二句",
                    "undoGroup": "sentence-1",
                }
            ],
            "reviewQueue": []
        }

        restored_plan, receipt = restore_take_in_plan(plan, item_id="take-0-alt")
        keeps = [x for x in restored_plan["timeline"] if x["op"] == "keep"]
        removes = [x for x in restored_plan["timeline"] if x["op"] == "remove"]

        self.assertEqual(len(keeps), 2)
        # take-0-alt is now kept
        self.assertEqual(keeps[0]["id"], "take-0-alt")
        self.assertEqual(keeps[0]["sourceStart"], 5.0)
        self.assertEqual(keeps[0]["sourceEnd"], 9.0)
        self.assertEqual(keeps[0]["targetStart"], 0.0)

        # take-1 targetStart shifted from 2.0s to 4.0s (because restored take is 4s long!)
        self.assertEqual(keeps[1]["id"], "take-1")
        self.assertAlmostEqual(keeps[1]["targetStart"], 4.0, delta=1.0/25)

        # Old take-0 is now remove
        self.assertEqual(len(removes), 1)
        self.assertEqual(removes[0]["id"], "take-0")

    def test_recovery_track_and_independent_recovery_draft(self):
        """apply_edit_plan creates muted/hidden A-roll Recovery and independent recovery draft."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            media = root / "video.mp4"
            subprocess.run([
                'ffmpeg', '-v', 'error', '-y',
                '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=25:duration=10',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=10',
                '-c:v', 'libx264', '-c:a', 'aac', str(media)
            ], check=True)

            plan_data = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {"src": {"path": "video.mp4", "duration": 10.0}},
                "timeline": [
                    {
                        "id": "take-0",
                        "op": "keep",
                        "sourceId": "src",
                        "sourceStart": 0.0,
                        "sourceEnd": 2.0,
                        "targetStart": 0.0,
                        "text": "主成片第一句",
                        "undoGroup": "sentence-0",
                    },
                    {
                        "id": "take-0-del",
                        "op": "remove",
                        "sourceId": "src",
                        "sourceStart": 3.0,
                        "sourceEnd": 6.0,
                        "reason": ["duplicate_take"],
                        "undoGroup": "sentence-0",
                    }
                ],
                "reviewQueue": []
            }
            plan_file = root / "edit-plan.v1.json"
            plan_file.write_text(json.dumps(plan_data, indent=2, ensure_ascii=False), encoding="utf-8")

            # Run jianying.py apply_edit_plan via CLI
            draft_cli = Path(__file__).resolve().parents[1] / "video-jianying-draft/jianying.py"
            cmd = [
                sys.executable, str(draft_cli), "apply_edit_plan",
                "--plan", str(plan_file),
                "--output-dir", str(root / "Drafts"),
                "--draft-id", "test_recovery_draft",
            ]
            run_res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(run_res.returncode, 0, run_res.stderr)

            draft_path = root / "Drafts/test_recovery_draft/draft_content.json"
            draft_content = json.loads(draft_path.read_text(encoding="utf-8"))

            # 1. Check A-roll Recovery track in main draft
            rec_tracks = [t for t in draft_content["tracks"] if t.get("name") == "A-roll Recovery"]
            self.assertEqual(len(rec_tracks), 1)
            rec_track = rec_tracks[0]
            # Must be muted
            self.assertEqual(rec_track["attribute"], 1)
            self.assertEqual(len(rec_track["segments"]), 1)
            seg = rec_track["segments"][0]
            # Must not extend beyond project duration (target duration matches)
            self.assertLessEqual(seg["target_timerange"]["start"] + seg["target_timerange"]["duration"],
                                 draft_content["duration"] if "duration" in draft_content else 10_000_000)

            # 2. Check independent recovery draft existence
            recovery_draft_dir = root / "Drafts/test_recovery_draft-recovery"
            self.assertTrue(recovery_draft_dir.is_dir())
            self.assertTrue((recovery_draft_dir / "draft_content.json").is_file())

    def test_auto_edit_select_takes_and_restore_cli(self):
        """Test auto_edit.py select-takes, restore, and circuit breaker in validate."""
        cli = Path(__file__).resolve().parents[0] / "auto_edit.py"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            media = root / "video.mp4"
            subprocess.run([
                'ffmpeg', '-v', 'error', '-y',
                '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=25:duration=10',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=10',
                '-c:v', 'libx264', '-c:a', 'aac', str(media)
            ], check=True)

            takes_decision = {
                "summary": {"sentences": 1, "matched": 1, "unmatched": 0},
                "sources": {"src": {"path": "video.mp4", "duration": 10.0}},
                "sentences": [
                    {
                        "idx": 0,
                        "text": "我们开始进行多遍录制选优和恢复测试。",
                        "takes": [
                            {
                                "id": "take-bad",
                                "start": 0.0,
                                "end": 2.0,
                                "match": 0.5,
                                "completeness": 0.5,
                                "pause_ratio": 0.0,
                                "rate_score": 1.0,
                                "total": 0.6,
                                "sourceId": "src",
                            },
                            {
                                "id": "take-good",
                                "start": 3.0,
                                "end": 6.0,
                                "match": 1.0,
                                "completeness": 1.0,
                                "pause_ratio": 0.1,
                                "rate_score": 0.9,
                                "total": 0.95,
                                "sourceId": "src",
                            }
                        ]
                    }
                ]
            }
            takes_file = root / "takes_decision.json"
            takes_file.write_text(json.dumps(takes_decision, indent=2, ensure_ascii=False), encoding="utf-8")

            # 1. Run select-takes CLI
            cmd_select = [
                sys.executable, str(cli), "select-takes", str(root),
                "--takes", str(takes_file), "--apply"
            ]
            res_sel = subprocess.run(cmd_select, capture_output=True, text=True)
            self.assertEqual(res_sel.returncode, 0, res_sel.stderr)
            self.assertTrue((root / "Rough/edit-plan.v1.json").is_file())
            self.assertTrue((root / "Rough/takes-selection-report.json").is_file())
            self.assertTrue((root / "Rough/circuit-breaker.json").is_file())

            plan_after_select = json.loads((root / "Rough/edit-plan.v1.json").read_text(encoding="utf-8"))
            keeps = [x for x in plan_after_select["timeline"] if x["op"] == "keep"]
            removes = [x for x in plan_after_select["timeline"] if x["op"] == "remove"]
            self.assertEqual(len(keeps), 1)
            self.assertEqual(keeps[0]["id"], "take-good")
            self.assertEqual(len(removes), 1)
            self.assertEqual(removes[0]["id"], "take-bad")

            # 2. Run restore CLI
            cmd_restore = [
                sys.executable, str(cli), "restore", str(root),
                "--item", "take-bad", "--apply"
            ]
            res_res = subprocess.run(cmd_restore, capture_output=True, text=True)
            self.assertEqual(res_res.returncode, 0, res_res.stderr)

            plan_after_restore = json.loads((root / "Rough/edit-plan.v1.json").read_text(encoding="utf-8"))
            keeps2 = [x for x in plan_after_restore["timeline"] if x["op"] == "keep"]
            removes2 = [x for x in plan_after_restore["timeline"] if x["op"] == "remove"]
            self.assertEqual(len(keeps2), 1)
            self.assertEqual(keeps2[0]["id"], "take-bad")
            self.assertEqual(len(removes2), 1)
            self.assertEqual(removes2[0]["id"], "take-good")

            # 3. Run validate CLI without --strict
            cmd_val = [
                sys.executable, str(cli), "validate", str(root)
            ]
            res_val = subprocess.run(cmd_val, capture_output=True, text=True)
            self.assertEqual(res_val.returncode, 0, res_val.stderr)
            self.assertTrue((root / "Rough/auto-cut-validation.json").is_file())
            self.assertTrue((root / "Rough/auto-cut-report.md").is_file())
            val_json = json.loads((root / "Rough/auto-cut-validation.json").read_text(encoding="utf-8"))
            self.assertIn("circuitBreaker", val_json)
            self.assertFalse(val_json["circuitBreaker"]["circuit_broken"])

            # 4. Trigger circuit breaker by marking large deletion (>35%)
            cb_plan = copy.deepcopy(plan_after_restore)
            cb_plan["timeline"].append({
                "id": "massive-cut",
                "op": "remove",
                "sourceId": "src",
                "sourceStart": 5.0,
                "sourceEnd": 9.5,
                "reason": ["manual_cut"],
                "undoGroup": "manual",
                "durationFrames": 112,
                "sourceStartFrame": 125,
                "sourceEndFrame": 237,
            })
            (root / "Rough/edit-plan.v1.json").write_text(json.dumps(cb_plan, indent=2, ensure_ascii=False), encoding="utf-8")
            if (root / "Rough/circuit-breaker.json").is_file():
                (root / "Rough/circuit-breaker.json").unlink()

            cmd_strict = [
                sys.executable, str(cli), "validate", str(root), "--strict"
            ]
            res_strict = subprocess.run(cmd_strict, capture_output=True, text=True)
            self.assertEqual(res_strict.returncode, 1)
            val_json_strict = json.loads((root / "Rough/auto-cut-validation.json").read_text(encoding="utf-8"))
            self.assertTrue(val_json_strict["circuitBreaker"]["circuit_broken"])
            self.assertIn("deletion_limit_exceeded", val_json_strict["circuitBreaker"]["triggers"])

    def test_restore_without_undo_group_does_not_evict_unrelated_items(self):
        """SEC-01: Restoring a remove item without an undoGroup MUST NOT swap with unrelated items that also lack undoGroup."""
        plan = {
            "version": "1",
            "fps": 25,
            "projectRoot": ".",
            "sources": {"src": {"path": "dummy.mp4", "duration": 20.0}},
            "timeline": [
                {
                    "id": "unrelated-keep",
                    "op": "keep",
                    "sourceId": "src",
                    "sourceStart": 0.0,
                    "sourceEnd": 2.0,
                    "targetStart": 0.0,
                    # No undoGroup
                },
                {
                    "id": "standalone-remove",
                    "op": "remove",
                    "sourceId": "src",
                    "sourceStart": 3.0,
                    "sourceEnd": 5.0,
                    "reason": ["cut"],
                    # No undoGroup
                }
            ]
        }
        restored_plan, receipt = restore_take_in_plan(plan, item_id="standalone-remove")
        keeps = [x for x in restored_plan["timeline"] if x["op"] == "keep"]
        removes = [x for x in restored_plan["timeline"] if x["op"] == "remove"]

        # Both items should now be keep! unrelated-keep was NOT evicted!
        self.assertEqual(len(keeps), 2)
        self.assertEqual(len(removes), 0)
        keep_ids = [x["id"] for x in keeps]
        self.assertIn("unrelated-keep", keep_ids)
        self.assertIn("standalone-remove", keep_ids)


if __name__ == "__main__":
    unittest.main()
