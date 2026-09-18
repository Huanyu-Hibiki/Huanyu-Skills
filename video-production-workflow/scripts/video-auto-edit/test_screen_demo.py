"""Unit and integration tests for Task 5: Screen Demo on independent track."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.edit_plan import load_plan
from lib.screen_demo import match_screen_anchors
from lib.edit_outputs import preview, verify_draft


class TestScreenDemo(unittest.TestCase):

    def test_anchor_to_target_time_not_source_time(self):
        """Anchor matching resolves to targetStart on the edited timeline, NOT sourceStart in raw footage."""
        plan = {
            "version": "1",
            "fps": 25,
            "projectRoot": ".",
            "sources": {
                "camera": {"path": "camera.mp4", "duration": 100.0},
                "screen": {"path": "screen.mp4", "duration": 50.0}
            },
            "timeline": [
                {
                    "id": "take-1",
                    "op": "keep",
                    "sourceId": "camera",
                    "sourceStart": 60.0,  # Raw source is at 60s
                    "sourceEnd": 70.0,
                    "targetStart": 0.0,   # Target timeline starts at 0s!
                    "text": "我们首先点击发布按钮，系统将自动进入审核流程。",
                    "track": "A-roll Final",
                }
            ],
            "reviewQueue": []
        }
        markers = [
            {
                "id": "m-publish",
                "anchor": "点击发布按钮",
                "start": 5.0,
                "end": 9.0,
            }
        ]

        updated_plan, manifest = match_screen_anchors(
            plan=plan,
            screen_source_id="screen",
            markers=markers,
        )

        screen_items = [x for x in updated_plan["timeline"] if x.get("track") == "Screen Demo"]
        self.assertEqual(len(screen_items), 1)
        item = screen_items[0]
        # targetStart must be near 0.0 (A-roll target time), NOT 60.0 (camera source time)!
        self.assertLess(item["targetStart"], 5.0)
        self.assertEqual(item["sourceId"], "screen")
        self.assertEqual(item["sourceStart"], 5.0)
        self.assertEqual(item["sourceEnd"], 9.0)
        self.assertEqual(item["track"], "Screen Demo")

    def test_multiple_ambiguous_anchors_routed_to_review(self):
        """When multiple spoken sentences match the same anchor without 1:1 pairing, route to reviewQueue."""
        plan = {
            "version": "1",
            "fps": 25,
            "projectRoot": ".",
            "sources": {
                "camera": {"path": "camera.mp4", "duration": 50.0},
                "screen": {"path": "screen.mp4", "duration": 30.0}
            },
            "timeline": [
                {
                    "id": "take-1",
                    "op": "keep",
                    "sourceId": "camera",
                    "sourceStart": 10.0,
                    "sourceEnd": 15.0,
                    "targetStart": 0.0,
                    "text": "大家看这里，点击进入设置界面。",
                    "track": "A-roll Final",
                },
                {
                    "id": "take-2",
                    "op": "keep",
                    "sourceId": "camera",
                    "sourceStart": 20.0,
                    "sourceEnd": 25.0,
                    "targetStart": 5.0,
                    "text": "完成之后，再次点击进入设置界面核对。",
                    "track": "A-roll Final",
                }
            ],
            "reviewQueue": []
        }
        markers = [
            {
                "id": "m-settings",
                "anchor": "点击进入设置界面",  # Appears twice in manuscript!
                "start": 2.0,
                "end": 6.0,
            }
        ]

        updated_plan, manifest = match_screen_anchors(
            plan=plan,
            screen_source_id="screen",
            markers=markers,
        )

        screen_items = [x for x in updated_plan["timeline"] if x.get("track") == "Screen Demo"]
        # Ambiguous anchor must NOT be guessed onto the track
        self.assertEqual(len(screen_items), 0)
        # Must be in reviewQueue
        rq = updated_plan.get("reviewQueue", [])
        self.assertTrue(any(x.get("type") == "ambiguous_anchor_match" for x in rq))

    def test_missing_marker_and_insufficient_duration_handling(self):
        """Missing markers or insufficient screen demo duration route to review without silent trimming."""
        plan = {
            "version": "1",
            "fps": 25,
            "projectRoot": ".",
            "sources": {
                "camera": {"path": "camera.mp4", "duration": 30.0},
                "screen": {"path": "screen.mp4", "duration": 10.0}
            },
            "timeline": [
                {
                    "id": "take-1",
                    "op": "keep",
                    "sourceId": "camera",
                    "sourceStart": 0.0,
                    "sourceEnd": 10.0,
                    "targetStart": 0.0,
                    "text": "我们演示完整的数据导入全过程，需要持续展示操作步骤。",
                    "track": "A-roll Final",
                }
            ],
            "reviewQueue": []
        }
        markers = [
            {
                "id": "m-short",
                "anchor": "数据导入全过程",
                "start": 0.0,
                "end": 0.5,  # Too short! 0.5s for a 10s step cannot convey the key operation
                "min_required_duration": 2.0,
            },
            {
                "id": "m-nonexistent",
                "anchor": "找不到这个锚点",
                "start": 1.0,
                "end": 5.0,
            }
        ]

        updated_plan, manifest = match_screen_anchors(
            plan=plan,
            screen_source_id="screen",
            markers=markers,
        )

        screen_items = [x for x in updated_plan["timeline"] if x.get("track") == "Screen Demo"]
        self.assertEqual(len(screen_items), 0)

        rq = updated_plan.get("reviewQueue", [])
        self.assertTrue(any(x.get("type") == "insufficient_marker_duration" for x in rq))
        self.assertTrue(any(x.get("type") == "unmatched_spoken_anchor" for x in rq))

    def test_screen_demo_muted_and_audio_unchanged_in_draft_and_preview(self):
        """Screen Demo track is completely silent and does not alter A-roll audio in draft or preview."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            camera = root / "camera.mp4"
            screen = root / "screen.mp4"

            # Create camera with 440Hz tone
            subprocess.run([
                'ffmpeg', '-v', 'error', '-y',
                '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=25:duration=4',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=4',
                '-c:v', 'libx264', '-c:a', 'aac', str(camera)
            ], check=True)

            # Create screen recording with 880Hz tone (should NOT be heard!)
            subprocess.run([
                'ffmpeg', '-v', 'error', '-y',
                '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=25:duration=4',
                '-f', 'lavfi', '-i', 'sine=frequency=880:duration=4',
                '-c:v', 'libx264', '-c:a', 'aac', str(screen)
            ], check=True)

            plan_dict = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {
                    "cam": {"path": "camera.mp4", "duration": 4.0},
                    "scr": {"path": "screen.mp4", "duration": 4.0},
                },
                "timeline": [
                    {
                        "id": "a-roll-1",
                        "op": "keep",
                        "sourceId": "cam",
                        "sourceStart": 0.0,
                        "sourceEnd": 4.0,
                        "targetStart": 0.0,
                        "track": "A-roll Final",
                        "text": "点击播放测试录屏效果",
                    },
                    {
                        "id": "screen-1",
                        "op": "insert_screen_demo",
                        "sourceId": "scr",
                        "sourceStart": 1.0,
                        "sourceEnd": 3.0,
                        "targetStart": 1.0,
                        "track": "Screen Demo",
                        "anchor": "测试录屏效果",
                    }
                ],
                "reviewQueue": []
            }
            plan_file = root / "plan.json"
            plan_file.write_text(json.dumps(plan_dict, indent=2, ensure_ascii=False), encoding="utf-8")

            norm_plan = load_plan(plan_file)
            preview_video = root / "preview.mp4"
            preview(norm_plan, preview_video)
            self.assertTrue(preview_video.is_file())

            # Verify draft creation
            draft_cli = Path(__file__).resolve().parents[1] / "video-jianying-draft/jianying.py"
            cmd = [
                sys.executable, str(draft_cli), "apply_edit_plan",
                "--plan", str(plan_file),
                "--output-dir", str(root / "Drafts"),
                "--draft-id", "test_screen_draft",
            ]
            run_res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(run_res.returncode, 0, run_res.stderr)

            draft_content = json.loads((root / "Drafts/test_screen_draft/draft_content.json").read_text(encoding="utf-8"))
            scr_tracks = [t for t in draft_content["tracks"] if t.get("name") == "Screen Demo"]
            self.assertEqual(len(scr_tracks), 1)
            # Screen Demo track must be muted!
            self.assertEqual(scr_tracks[0].get("attribute"), 1)

            # verify_draft consistency
            v_res = verify_draft(norm_plan, root / "Drafts/test_screen_draft/draft_content.json")
            self.assertEqual(v_res["status"], "ok")

    def test_pending_markers_do_not_enter_preview(self):
        """Pending markers do NOT enter delivery preview as completed B-roll."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            camera = root / "camera.mp4"
            subprocess.run([
                'ffmpeg', '-v', 'error', '-y',
                '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=25:duration=3',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3',
                '-c:v', 'libx264', '-c:a', 'aac', str(camera)
            ], check=True)

            plan_dict = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {
                    "cam": {"path": "camera.mp4", "duration": 3.0},
                },
                "timeline": [
                    {
                        "id": "a-1",
                        "op": "keep",
                        "sourceId": "cam",
                        "sourceStart": 0.0,
                        "sourceEnd": 3.0,
                        "targetStart": 0.0,
                        "track": "A-roll Final",
                        "text": "测试未放置标记",
                    }
                ],
                "reviewQueue": [
                    {
                        "id": "pending-screen-marker-1",
                        "type": "unmatched_screen_marker",
                        "anchor": "未匹配标记",
                        "action": "hold_and_review",
                    }
                ]
            }
            plan_file = root / "plan.json"
            plan_file.write_text(json.dumps(plan_dict, indent=2, ensure_ascii=False), encoding="utf-8")
            norm_plan = load_plan(plan_file)
            preview_video = root / "preview.mp4"
            preview(norm_plan, preview_video)
            self.assertTrue(preview_video.is_file())
            # Output duration must equal A-roll only (3.0s)
            probe_out = subprocess.run([
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', str(preview_video)
            ], capture_output=True, text=True)
            self.assertAlmostEqual(float(probe_out.stdout.strip()), 3.0, delta=0.1)

    def test_idempotent_draft_and_manifest_readback(self):
        """Re-executing apply_edit_plan does not duplicate Screen Demo tracks or clips."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            camera = root / "camera.mp4"
            screen = root / "screen.mp4"
            for p in (camera, screen):
                subprocess.run([
                    'ffmpeg', '-v', 'error', '-y',
                    '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=25:duration=3',
                    '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3',
                    '-c:v', 'libx264', '-c:a', 'aac', str(p)
                ], check=True)

            plan_dict = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {
                    "cam": {"path": "camera.mp4", "duration": 3.0},
                    "scr": {"path": "screen.mp4", "duration": 3.0},
                },
                "timeline": [
                    {
                        "id": "a-1",
                        "op": "keep",
                        "sourceId": "cam",
                        "sourceStart": 0.0,
                        "sourceEnd": 3.0,
                        "targetStart": 0.0,
                        "track": "A-roll Final",
                        "text": "测试幂等上轨",
                    },
                    {
                        "id": "screen-1",
                        "op": "insert_screen_demo",
                        "sourceId": "scr",
                        "sourceStart": 0.5,
                        "sourceEnd": 2.5,
                        "targetStart": 0.5,
                        "track": "Screen Demo",
                        "anchor": "测试幂等上轨",
                    }
                ],
                "reviewQueue": []
            }
            plan_file = root / "plan.json"
            plan_file.write_text(json.dumps(plan_dict, indent=2, ensure_ascii=False), encoding="utf-8")
            norm_plan = load_plan(plan_file)

            draft_cli = Path(__file__).resolve().parents[1] / "video-jianying-draft/jianying.py"
            # Apply draft once
            res1 = subprocess.run([
                sys.executable, str(draft_cli), "apply_edit_plan",
                "--plan", str(plan_file),
                "--output-dir", str(root / "Drafts"),
                "--draft-id", "idempotent_screen_draft",
            ], capture_output=True, text=True)
            self.assertEqual(res1.returncode, 0)

            # Apply draft twice
            res2 = subprocess.run([
                sys.executable, str(draft_cli), "apply_edit_plan",
                "--plan", str(plan_file),
                "--output-dir", str(root / "Drafts"),
                "--draft-id", "idempotent_screen_draft",
            ], capture_output=True, text=True)
            self.assertEqual(res2.returncode, 0)

            draft_content = json.loads((root / "Drafts/idempotent_screen_draft/draft_content.json").read_text(encoding="utf-8"))
            scr_tracks = [t for t in draft_content["tracks"] if t.get("name") == "Screen Demo"]
            self.assertEqual(len(scr_tracks), 1)
            self.assertEqual(len(scr_tracks[0]["segments"]), 1)

            # Verify draft
            v_res = verify_draft(norm_plan, root / "Drafts/idempotent_screen_draft/draft_content.json")
            self.assertEqual(v_res["status"], "ok")

    def test_auto_edit_insert_screen_demo_cli(self):
        """Test auto_edit.py insert-screen-demo CLI end-to-end with manifest generation."""
        cli = Path(__file__).resolve().parents[0] / "auto_edit.py"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            camera = root / "camera.mp4"
            screen = root / "screen.mp4"
            for p in (camera, screen):
                subprocess.run([
                    'ffmpeg', '-v', 'error', '-y',
                    '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=25:duration=5',
                    '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5',
                    '-c:v', 'libx264', '-c:a', 'aac', str(p)
                ], check=True)

            plan_dict = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {
                    "cam": {"path": "camera.mp4", "duration": 5.0},
                },
                "timeline": [
                    {
                        "id": "a-1",
                        "op": "keep",
                        "sourceId": "cam",
                        "sourceStart": 0.0,
                        "sourceEnd": 5.0,
                        "targetStart": 0.0,
                        "track": "A-roll Final",
                        "text": "请大家仔细看屏幕，点击确认提交按钮完成操作。",
                    }
                ],
                "reviewQueue": []
            }
            plan_file = root / "Rough/edit-plan.v1.json"
            plan_file.parent.mkdir(parents=True, exist_ok=True)
            plan_file.write_text(json.dumps(plan_dict, indent=2, ensure_ascii=False), encoding="utf-8")

            markers_data = [
                {
                    "id": "m-submit",
                    "anchor": "点击确认提交按钮",
                    "start": 1.0,
                    "end": 4.0,
                }
            ]
            markers_file = root / "Rough/screen_markers.json"
            markers_file.write_text(json.dumps(markers_data, indent=2, ensure_ascii=False), encoding="utf-8")

            # Run insert-screen-demo
            cmd = [
                sys.executable, str(cli), "insert-screen-demo", str(root),
                "--screen", str(screen),
                "--markers", str(markers_file),
                "--apply"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

            # Check outputs
            manifest_file = root / "Polished/broll-manifest.v1.json"
            self.assertTrue(manifest_file.is_file())
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            self.assertEqual(manifest["summary"]["approved_count"], 1)

            # Verify plan has Screen Demo item
            updated_plan = json.loads(plan_file.read_text(encoding="utf-8"))
            scr_items = [x for x in updated_plan["timeline"] if x.get("track") == "Screen Demo"]
            self.assertEqual(len(scr_items), 1)

            # Validate pipeline commands
            for subcmd in ("validate", "subtitles", "preview"):
                sub_res = subprocess.run([sys.executable, str(cli), subcmd, str(root)], capture_output=True, text=True)
                self.assertEqual(sub_res.returncode, 0, sub_res.stderr)

            # Test repeat execution idempotence (CRITICAL-01 fix)
            cmd_repeat = [
                sys.executable, str(cli), "insert-screen-demo", str(root),
                "--screen", str(screen),
                "--markers", str(markers_file),
                "--apply"
            ]
            res_repeat = subprocess.run(cmd_repeat, capture_output=True, text=True)
            self.assertEqual(res_repeat.returncode, 0, res_repeat.stderr)

            reloaded_plan = json.loads(plan_file.read_text(encoding="utf-8"))
            reloaded_scr_items = [x for x in reloaded_plan["timeline"] if x.get("track") == "Screen Demo"]
            self.assertEqual(len(reloaded_scr_items), 1, "Repeated execution must not duplicate screen demo timeline items")

            # Validate pipeline still passes without track monotonicity or collision errors
            val_res = subprocess.run([sys.executable, str(cli), "validate", str(root)], capture_output=True, text=True)
            self.assertEqual(val_res.returncode, 0, val_res.stderr)

    def test_screen_demo_collision_routed_to_review_queue(self):
        """When multiple screen demo markers overlap on target timeline, route collision to reviewQueue."""
        plan = {
            "version": "1",
            "fps": 25,
            "projectRoot": ".",
            "sources": {
                "camera": {"path": "camera.mp4", "duration": 50.0},
                "screen": {"path": "screen.mp4", "duration": 30.0}
            },
            "timeline": [
                {
                    "id": "take-1",
                    "op": "keep",
                    "sourceId": "camera",
                    "sourceStart": 0.0,
                    "sourceEnd": 10.0,
                    "targetStart": 0.0,
                    "text": "第一步点击保存，第二步点击提交按钮。",
                    "track": "A-roll Final",
                }
            ],
            "reviewQueue": []
        }
        # Two markers matching the same sentence that overlap on the timeline
        markers = [
            {
                "id": "m-save",
                "anchor": "点击保存",
                "start": 0.0,
                "end": 6.0,  # 6 seconds
            },
            {
                "id": "m-submit",
                "anchor": "点击提交按钮",
                "start": 2.0,
                "end": 7.0,  # Starts before m-save ends -> collision!
            }
        ]

        updated_plan, manifest = match_screen_anchors(
            plan=plan,
            screen_source_id="screen",
            markers=markers,
        )

        screen_items = [x for x in updated_plan["timeline"] if x.get("track") == "Screen Demo"]
        # Only the first non-colliding marker should be placed
        self.assertEqual(len(screen_items), 1)
        self.assertEqual(screen_items[0]["id"], "m-save")

        # The colliding one must be routed to reviewQueue
        rq = updated_plan.get("reviewQueue", [])
        collisions = [x for x in rq if x.get("type") == "overlapping_screen_demo"]
        self.assertEqual(len(collisions), 1)
        self.assertEqual(collisions[0]["marker_id"], "m-submit")

    def test_screen_demo_out_of_bounds_markers(self):
        """Markers with start >= end or out-of-bounds duration are routed to reviewQueue."""
        plan = {
            "version": "1",
            "fps": 25,
            "projectRoot": ".",
            "sources": {
                "camera": {"path": "camera.mp4", "duration": 50.0},
                "screen": {"path": "screen.mp4", "duration": 10.0}
            },
            "timeline": [
                {
                    "id": "take-1",
                    "op": "keep",
                    "sourceId": "camera",
                    "sourceStart": 0.0,
                    "sourceEnd": 10.0,
                    "targetStart": 0.0,
                    "text": "测试边界非法标记处理逻辑。",
                    "track": "A-roll Final",
                }
            ],
            "reviewQueue": []
        }
        markers = [
            {
                "id": "m-inverted",
                "anchor": "非法标记",
                "start": 5.0,
                "end": 3.0,  # start > end
            },
            {
                "id": "m-overrun",
                "anchor": "处理逻辑",
                "start": 15.0,  # > screen duration (10.0)
                "end": 18.0,
            }
        ]

        updated_plan, manifest = match_screen_anchors(
            plan=plan,
            screen_source_id="screen",
            markers=markers,
        )

        screen_items = [x for x in updated_plan["timeline"] if x.get("track") == "Screen Demo"]
        self.assertEqual(len(screen_items), 0)

        rq = updated_plan.get("reviewQueue", [])
        oob_items = [x for x in rq if x.get("type") == "marker_out_of_bounds"]
        self.assertEqual(len(oob_items), 2)

    def test_screen_demo_draft_zoom_settings(self):
        """When timeline item specifies zoom, Jianying draft segment applies scale_x and scale_y."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            camera = root / "camera.mp4"
            screen = root / "screen.mp4"
            for p in (camera, screen):
                subprocess.run([
                    'ffmpeg', '-v', 'error', '-y',
                    '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=25:duration=3',
                    '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3',
                    '-c:v', 'libx264', '-c:a', 'aac', str(p)
                ], check=True)

            plan_dict = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {
                    "cam": {"path": "camera.mp4", "duration": 3.0},
                    "scr": {"path": "screen.mp4", "duration": 3.0},
                },
                "timeline": [
                    {
                        "id": "a-1",
                        "op": "keep",
                        "sourceId": "cam",
                        "sourceStart": 0.0,
                        "sourceEnd": 3.0,
                        "targetStart": 0.0,
                        "track": "A-roll Final",
                        "text": "测试缩放效果",
                    },
                    {
                        "id": "screen-zoom",
                        "op": "insert_screen_demo",
                        "sourceId": "scr",
                        "sourceStart": 0.5,
                        "sourceEnd": 2.5,
                        "targetStart": 0.5,
                        "track": "Screen Demo",
                        "zoom": 1.25,
                    }
                ],
                "reviewQueue": []
            }
            plan_file = root / "plan.json"
            plan_file.write_text(json.dumps(plan_dict, indent=2, ensure_ascii=False), encoding="utf-8")

            draft_cli = Path(__file__).resolve().parents[1] / "video-jianying-draft/jianying.py"
            cmd = [
                sys.executable, str(draft_cli), "apply_edit_plan",
                "--plan", str(plan_file),
                "--output-dir", str(root / "Drafts"),
                "--draft-id", "zoom_screen_draft",
            ]
            run_res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(run_res.returncode, 0, run_res.stderr)

            draft_content = json.loads((root / "Drafts/zoom_screen_draft/draft_content.json").read_text(encoding="utf-8"))
            scr_tracks = [t for t in draft_content["tracks"] if t.get("name") == "Screen Demo"]
            self.assertEqual(len(scr_tracks), 1)

            # Check materials.videos or clip settings
            # In pyJianYingDraft, clip_settings are attached to segment or material
            # Let's inspect segment details
            seg_obj = scr_tracks[0]["segments"][0]
            clip_cfg = seg_obj.get("clip")
            self.assertIsNotNone(clip_cfg, "Segment should have clip settings")
            self.assertAlmostEqual(clip_cfg.get("scale", {}).get("x", 1.0), 1.25, places=2)
            self.assertAlmostEqual(clip_cfg.get("scale", {}).get("y", 1.0), 1.25, places=2)

    def test_screen_demo_word_level_alignment(self):
        """When words_per_segment is provided, targetStart aligns to the matched word start offset."""
        plan = {
            "version": "1",
            "fps": 25,
            "projectRoot": ".",
            "sources": {
                "camera": {"path": "camera.mp4", "duration": 50.0},
                "screen": {"path": "screen.mp4", "duration": 30.0}
            },
            "timeline": [
                {
                    "id": "take-1",
                    "op": "keep",
                    "sourceId": "camera",
                    "sourceStart": 10.0,
                    "sourceEnd": 20.0,
                    "targetStart": 0.0,
                    "text": "欢迎大家来到本教程，现在点击提交表单完成配置。",
                    "track": "A-roll Final",
                }
            ],
            "reviewQueue": []
        }
        markers = [
            {
                "id": "m-submit",
                "anchor": "点击提交表单",
                "start": 1.0,
                "end": 4.0,
            }
        ]
        words_per_segment = {
            "take-1": [
                {"word": "欢迎大家", "start": 10.0, "end": 11.5},
                {"word": "来到本教程", "start": 11.5, "end": 13.0},
                {"word": "现在", "start": 13.0, "end": 14.0},
                {"word": "点击提交表单", "start": 14.0, "end": 16.5},  # offset = 14.0 - 10.0 = 4.0s
                {"word": "完成配置", "start": 16.5, "end": 19.5},
            ]
        }

        updated_plan, manifest = match_screen_anchors(
            plan=plan,
            screen_source_id="screen",
            markers=markers,
            words_per_segment=words_per_segment,
        )

        screen_items = [x for x in updated_plan["timeline"] if x.get("track") == "Screen Demo"]
        self.assertEqual(len(screen_items), 1)
        item = screen_items[0]
        # Target start should be shifted by word offset ~4.0s
        self.assertAlmostEqual(item["targetStart"], 4.0, delta=0.1)


if __name__ == "__main__":
    unittest.main()
