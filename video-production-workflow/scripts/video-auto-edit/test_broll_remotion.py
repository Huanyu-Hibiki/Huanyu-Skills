"""Unit and integration tests for Task 6: Remotion narrative scene B-roll."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.broll_registry import list_templates, get_template, find_matching_template
from lib.broll_narrative import generate_shot_brief
from lib.broll_remotion import render_remotion_shot, verify_broll_shot
from lib.edit_plan import load_plan
from lib.edit_outputs import preview, verify_draft
import lib.edit_draft as edit_draft


class TestRemotionBroll(unittest.TestCase):

    def test_remotion_rejects_symlinked_shot_folder_before_writing(self):
        """A valid shot id may not redirect artifacts outside the output root."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output = root / "out"
            output.mkdir()
            outside = root / "outside"
            outside.mkdir()
            redirected = output / "safe-shot"
            try:
                redirected.symlink_to(outside, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlinks unavailable: {error}")
            with self.assertRaisesRegex(ValueError, "symlink"):
                render_remotion_shot({"id": "safe-shot", "duration": 0.0}, output)

    def test_remotion_template_registry_completeness(self):
        """Registry must contain template parameters, engine, aspect ratios, duration, transparency, style, grammar, and license."""
        templates = list_templates()
        self.assertGreaterEqual(len(templates), 2, "Must provide multiple narrative templates")

        for t in templates:
            self.assertTrue(t.get("id"), "Template must have an id")
            self.assertEqual(t.get("engine"), "remotion")
            self.assertTrue(t.get("engine_version"))
            self.assertTrue(t.get("source"))
            self.assertIn(t.get("license"), ("MIT", "Apache-2.0"))
            self.assertIn("16:9", t.get("aspect_ratios", []))
            d_range = t.get("duration_range")
            self.assertIsInstance(d_range, list)
            self.assertEqual(len(d_range), 2)
            self.assertLess(d_range[0], d_range[1])

            self.assertIn(t.get("transparency"), ("full_alpha", "opaque"))
            self.assertIn(t.get("overlay_mode"), ("full_frame", "transparent_overlay"))
            self.assertGreaterEqual(len(t.get("style_packs", [])), 1)

            grammar = t.get("shot_grammar", {})
            self.assertTrue(grammar.get("visual_role"))
            self.assertTrue(grammar.get("camera_motion"))
            self.assertTrue(grammar.get("motion_dynamics"))

            props = t.get("props_schema", {})
            self.assertIsInstance(props, dict)
            self.assertIn("title", props)

        # Query matching
        matched = find_matching_template(visual_role="data_causality", style_pack="vox_explainer")
        self.assertIsNotNone(matched)
        self.assertEqual(matched["id"], "remotion-data-causality")

        matched_proc = find_matching_template(visual_role="process_breakdown", style_pack="documentary_observe")
        self.assertIsNotNone(matched_proc)
        self.assertEqual(matched_proc["id"], "remotion-process-breakdown")

    def test_registry_does_not_silently_fallback_unsupported_style(self):
        self.assertIsNone(find_matching_template(
            visual_role="data_causality", style_pack="unsupported-style", engine="remotion"
        ))

    def test_narrative_shot_brief_generation_from_explanation(self):
        """Explanatory sentence automatically forms a structured shot brief with genuine narrative motion."""
        sentence = {
            "id": "sent-001",
            "text": "通过引入底层缓存机制，系统响应时间从 1200ms 骤降至 85ms，性能提升近 14 倍。",
            "targetStart": 10.0,
            "duration": 5.0,
        }

        brief = generate_shot_brief(
            sentence=sentence,
            style_pack="vox_explainer",
            talking_head_zone={"x": 0.65, "y": 0.50, "w": 0.35, "h": 0.50}
        )

        self.assertEqual(brief["route"], "packaging")
        self.assertEqual(brief["engine"], "remotion")
        self.assertEqual(brief["shot_grammar"]["visual_role"], "data_causality")
        self.assertEqual(brief["template_id"], "remotion-data-causality")
        self.assertGreaterEqual(brief["duration"], 3.0)
        for field in ("main_visual", "composition", "entrance", "exit", "acceptance_frames", "source", "provenance", "layer", "start", "end", "stylePack"):
            self.assertIn(field, brief)

        # Props must contain explanatory causal parameters, NOT merely subtitle copy
        props = brief["props"]
        self.assertTrue(props.get("beforeValue"))
        self.assertTrue(props.get("afterValue"))
        self.assertTrue(props.get("deltaLabel") or props.get("callout"))

        # Talking head avoidance zone must be respected
        self.assertEqual(brief["face_avoidance_zone"]["x"], 0.65)

    def test_render_data_causality_full_frame_mp4(self):
        """Renders an explanatory data causality scene to full-frame MP4 with deterministic frame QA."""
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            shot_brief = {
                "id": "shot-data-01",
                "template_id": "remotion-data-causality",
                "overlay_mode": "full_frame",
                "transparency": "opaque",
                "style_pack": "vox_explainer",
                "duration": 3.0,
                "fps": 25,
                "width": 640,
                "height": 360,
                "props": {
                    "title": "系统性能对比",
                    "beforeLabel": "重构前",
                    "beforeValue": 1200,
                    "afterLabel": "重构后",
                    "afterValue": 85,
                    "unit": "ms",
                    "callout": "14x 加速",
                },
                "face_avoidance_zone": None,
            }

            result = render_remotion_shot(shot_brief, out_dir=out_dir)
            self.assertEqual(result["status"], "rendered")
            video_path = Path(result["video_path"])
            self.assertTrue(video_path.is_file())
            self.assertTrue(video_path.name.endswith(".mp4"))

            # Check deterministic frame artifacts
            qa_res = verify_broll_shot(result, shot_brief)
            self.assertEqual(qa_res["status"], "passed")
            self.assertTrue(Path(qa_res["in_frame"]).is_file())
            self.assertTrue(Path(qa_res["mid_frame"]).is_file())
            self.assertTrue(Path(qa_res["out_frame"]).is_file())
            self.assertFalse(qa_res["is_blank"])

            # Verify source files preserved for re-rendering
            self.assertTrue((out_dir / "shot-data-01/Composition.tsx").is_file())
            self.assertTrue((out_dir / "shot-data-01/props.json").is_file())
            self.assertTrue((out_dir / "shot-data-01/shot_brief.json").is_file())
            self.assertTrue((out_dir / "shot-data-01/receipt.json").is_file())

    def test_render_transparent_overlay_prores4444_mov(self):
        """Transparent overlay must be ProRes 4444 with valid alpha channel (yuva444p10le)."""
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            shot_brief = {
                "id": "shot-process-01",
                "template_id": "remotion-process-breakdown",
                "overlay_mode": "transparent_overlay",
                "transparency": "full_alpha",
                "style_pack": "documentary_observe",
                "duration": 3.0,
                "fps": 25,
                "width": 640,
                "height": 360,
                "props": {
                    "title": "执行流水线",
                    "steps": ["代码审计", "单元测试", "草稿合成", "合规验证"],
                    "activeStep": 2,
                },
                "face_avoidance_zone": {"x": 0.65, "y": 0.50, "w": 0.35, "h": 0.50},
            }

            result = render_remotion_shot(shot_brief, out_dir=out_dir)
            self.assertEqual(result["status"], "rendered")
            video_path = Path(result["video_path"])
            self.assertTrue(video_path.is_file())
            self.assertTrue(video_path.name.endswith(".mov"))

            # Probe for alpha channel in video
            probe_out = subprocess.run([
                'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_name,pix_fmt',
                '-of', 'json', str(video_path)
            ], capture_output=True, text=True, check=True)
            p_data = json.loads(probe_out.stdout)
            stream = p_data["streams"][0]
            self.assertIn("prores", stream["codec_name"].lower())
            self.assertIn(stream["pix_fmt"], ("yuva444p10le", "yuva444p12le"))

            qa_res = verify_broll_shot(result, shot_brief)
            self.assertEqual(qa_res["status"], "passed")
            self.assertTrue(qa_res["has_alpha"])

    def test_reject_opaque_fallback_for_transparent_request(self):
        """If opaque video is falsely provided for transparent overlay, QA gate rejects to reviewQueue."""
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            opaque_video = out_dir / "fake_transparent.mp4"
            # Create opaque MP4 (yuv420p, no alpha)
            subprocess.run([
                'ffmpeg', '-v', 'error', '-y',
                '-f', 'lavfi', '-i', 'color=c=black:size=640x360:duration=2:rate=25',
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(opaque_video)
            ], check=True)

            shot_brief = {
                "id": "shot-fake-01",
                "overlay_mode": "transparent_overlay",
                "transparency": "full_alpha",
                "duration": 2.0,
                "fps": 25,
            }
            fake_result = {
                "status": "rendered",
                "video_path": str(opaque_video),
                "in_frame": str(out_dir / "in.png"),
                "mid_frame": str(out_dir / "mid.png"),
                "out_frame": str(out_dir / "out.png"),
            }
            qa_res = verify_broll_shot(fake_result, shot_brief)
            self.assertEqual(qa_res["status"], "rejected")
            self.assertEqual(qa_res["reason"], "transparency_not_supported_opaque_fallback_rejected")

    def test_face_avoidance_safety_zone(self):
        """B-roll graphics must stay clear of the designated facecam talking-head zone."""
        shot_brief = {
            "id": "shot-face-test",
            "template_id": "remotion-data-causality",
            "overlay_mode": "transparent_overlay",
            "face_avoidance_zone": {"x": 0.60, "y": 0.40, "w": 0.40, "h": 0.60},
        }
        # Content placed safely on the left: x: 0.05, y: 0.10, w: 0.50, h: 0.80
        safe_content_box = {"x": 0.05, "y": 0.10, "w": 0.50, "h": 0.80}
        self.assertTrue(verify_broll_shot.check_face_avoidance(safe_content_box, shot_brief["face_avoidance_zone"]))

        # Content overlapping facecam on the right: x: 0.55, y: 0.45, w: 0.40, h: 0.50
        colliding_content_box = {"x": 0.55, "y": 0.45, "w": 0.40, "h": 0.50}
        self.assertFalse(verify_broll_shot.check_face_avoidance(colliding_content_box, shot_brief["face_avoidance_zone"]))

    def test_broll_packaging_draft_and_preview_integration(self):
        """B-roll Packaging track in Jianying draft is muted (volume=0) and preview overlays cleanly."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            camera = root / "camera.mp4"
            broll_video = root / "broll.mp4"

            # Camera with 440Hz tone
            subprocess.run([
                'ffmpeg', '-v', 'error', '-y',
                '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=25:duration=5',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=5',
                '-c:v', 'libx264', '-c:a', 'aac', str(camera)
            ], check=True)

            # B-roll with 1000Hz tone (should be muted in draft & preview!)
            subprocess.run([
                'ffmpeg', '-v', 'error', '-y',
                '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=25:duration=3',
                '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=3',
                '-c:v', 'libx264', '-c:a', 'aac', str(broll_video)
            ], check=True)

            plan_dict = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {
                    "cam": {"path": "camera.mp4", "duration": 5.0},
                    "broll_pkg": {"path": "broll.mp4", "duration": 3.0},
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
                        "text": "测试 Remotion 包装镜头进入时间线",
                    },
                    {
                        "id": "broll-shot-1",
                        "op": "insert_broll_packaging",
                        "sourceId": "broll_pkg",
                        "sourceStart": 0.0,
                        "sourceEnd": 3.0,
                        "targetStart": 1.0,
                        "track": "B-roll Packaging",
                        "stylePack": "vox_explainer",
                        "overlayMode": "full_frame",
                    }
                ],
                "reviewQueue": []
            }
            plan_file = root / "plan.json"
            plan_file.write_text(json.dumps(plan_dict, indent=2, ensure_ascii=False), encoding="utf-8")
            norm_plan = load_plan(plan_file)

            # Check preview generation
            prev_out = root / "preview.mp4"
            preview(norm_plan, prev_out)
            self.assertTrue(prev_out.is_file())

            # Apply to Jianying draft
            draft_cli = Path(__file__).resolve().parents[1] / "video-jianying-draft/jianying.py"
            res = subprocess.run([
                sys.executable, str(draft_cli), "apply_edit_plan",
                "--plan", str(plan_file),
                "--output-dir", str(root / "Drafts"),
                "--draft-id", "broll_pkg_draft",
            ], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

            draft_content = json.loads((root / "Drafts/broll_pkg_draft/draft_content.json").read_text(encoding="utf-8"))
            pkg_tracks = [t for t in draft_content["tracks"] if t.get("name") == "B-roll Packaging"]
            self.assertEqual(len(pkg_tracks), 1)
            # B-roll Packaging must be muted so A-roll narration is unperturbed
            self.assertEqual(pkg_tracks[0].get("attribute"), 1)

            # verify_draft consistency check
            v_res = verify_draft(norm_plan, root / "Drafts/broll_pkg_draft/draft_content.json")
            self.assertEqual(v_res["status"], "ok")

    def test_auto_edit_insert_broll_packaging_cli(self):
        """auto_edit.py insert-broll-packaging CLI command works end-to-end."""
        cli = Path(__file__).resolve().parents[0] / "auto_edit.py"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            camera = root / "camera.mp4"
            subprocess.run([
                'ffmpeg', '-v', 'error', '-y',
                '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=25:duration=6',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=6',
                '-c:v', 'libx264', '-c:a', 'aac', str(camera)
            ], check=True)

            plan_dict = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {
                    "cam": {"path": "camera.mp4", "duration": 6.0},
                },
                "timeline": [
                    {
                        "id": "take-1",
                        "op": "keep",
                        "sourceId": "cam",
                        "sourceStart": 0.0,
                        "sourceEnd": 6.0,
                        "targetStart": 0.0,
                        "track": "A-roll Final",
                        "text": "我们重构了缓存架构，系统性能提升了 10 倍以上。",
                    }
                ],
                "reviewQueue": []
            }
            plan_file = root / "Rough/edit-plan.v1.json"
            plan_file.parent.mkdir(parents=True, exist_ok=True)
            plan_file.write_text(json.dumps(plan_dict, indent=2, ensure_ascii=False), encoding="utf-8")

            # Run insert-broll-packaging
            cmd = [
                sys.executable, str(cli), "insert-broll-packaging", str(root),
                "--sentence", "take-1",
                "--style-pack", "vox_explainer",
                "--apply"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

            # Check outputs
            manifest_file = root / "Polished/broll-manifest.v1.json"
            self.assertTrue(manifest_file.is_file())
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(manifest.get("items", [])), 1)
            broll_item = manifest["items"][0]
            self.assertEqual(broll_item["route"], "packaging")
            self.assertEqual(broll_item["engine"], "remotion")

            # Verify plan has B-roll Packaging item
            updated_plan = json.loads(plan_file.read_text(encoding="utf-8"))
            pkg_items = [x for x in updated_plan["timeline"] if x.get("track") == "B-roll Packaging"]
            self.assertEqual(len(pkg_items), 1)

            # Test CLI-01: Reject nonexistent sentence explicitly
            cmd_bad = [
                sys.executable, str(cli), "insert-broll-packaging", str(root),
                "--sentence", "nonexistent-sentence-999",
            ]
            res_bad = subprocess.run(cmd_bad, capture_output=True, text=True)
            self.assertNotEqual(res_bad.returncode, 0)
            self.assertIn("not found in plan timeline", res_bad.stderr)

    def test_render_stat_counter_template(self):
        """Render kinetic stat counter template successfully (LOGIC-01 fix)."""
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            shot_brief = {
                "id": "shot-stat-01",
                "template_id": "remotion-stat-counter",
                "overlay_mode": "full_frame",
                "transparency": "opaque",
                "style_pack": "motion_packaging",
                "duration": 2.5,
                "fps": 25,
                "width": 640,
                "height": 360,
                "props": {
                    "title": "全年吞吐量",
                    "targetNumber": 99.8,
                    "prefix": "",
                    "suffix": "%",
                },
                "face_avoidance_zone": None,
            }
            res = render_remotion_shot(shot_brief, out_dir=out_dir)
            self.assertEqual(res["status"], "rendered")
            qa = verify_broll_shot(res, shot_brief)
            self.assertEqual(qa["status"], "passed")

    def test_path_traversal_attack_rejected(self):
        """Path traversal in shot_id is rejected with ValueError (SEC-01 fix)."""
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            bad_brief = {
                "id": "../../escape_dir",
                "template_id": "remotion-data-causality",
                "duration": 2.5,
            }
            with self.assertRaises(ValueError):
                render_remotion_shot(bad_brief, out_dir=out_dir)

    def test_face_avoidance_gate_enforced_in_qa(self):
        """When face avoidance zone collides with content, QA rejects the shot (GATE-01 fix)."""
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            shot_brief = {
                "id": "shot-face-qa-test",
                "template_id": "remotion-data-causality",
                "overlay_mode": "transparent_overlay",
                "transparency": "full_alpha",
                "duration": 2.5,
                "fps": 25,
                "width": 640,
                "height": 360,
                # Place facecam in upper left right where the graphic box is located!
                "face_avoidance_zone": {"x": 0.05, "y": 0.10, "w": 0.50, "h": 0.70},
            }
            res = render_remotion_shot(shot_brief, out_dir=out_dir)
            qa = verify_broll_shot(res, shot_brief)
            self.assertEqual(qa["status"], "rejected")
            self.assertEqual(qa["reason"], "content_penetrates_face_avoidance_zone")


if __name__ == "__main__":
    unittest.main()
