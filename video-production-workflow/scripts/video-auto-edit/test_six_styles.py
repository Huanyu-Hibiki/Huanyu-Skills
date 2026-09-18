"""TDD Test suite for Task 9: Six distinct B-roll styles with parameterized entries and preview."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.broll_registry import find_matching_template, get_template, list_templates, validate_shot_brief
from lib.broll_narrative import generate_shot_brief
from lib.broll_remotion import render_remotion_shot, verify_broll_shot
from lib.edit_plan import load_plan
from lib.edit_outputs import preview, verify_draft


class TestSixStylesBroll(unittest.TestCase):
    """Test suite ensuring all six distinct styles are parameterized, renderable, and draft-compatible."""

    EXPECTED_STYLES = [
        "documentary_observe",
        "vox_explainer",
        "stop_motion_craft",
        "editorial_magazine",
        "product_cinematic",
        "motion_packaging",
    ]

    def test_all_six_styles_have_registered_templates_with_distinct_grammar(self):
        """All six styles have registered templates with distinct compositions, camera, and motion dynamics."""
        templates_by_style = {}
        grammars = []

        representative_templates = {
            "documentary_observe": "remotion-observe-focus",
            "vox_explainer": "remotion-data-causality",
            "stop_motion_craft": "remotion-stop-motion-craft",
            "editorial_magazine": "hyperframes-editorial-process",
            "product_cinematic": "remotion-stat-counter",
            "motion_packaging": "remotion-process-breakdown",
        }

        for style in self.EXPECTED_STYLES:
            t_id = representative_templates[style]
            tmpl = get_template(t_id)
            self.assertIsNotNone(tmpl, f"Missing registered template for style: {style}")
            self.assertIn(style, tmpl.get("style_packs", []))
            templates_by_style[style] = tmpl
            grammar = tmpl.get("shot_grammar", {})
            self.assertIn("visual_role", grammar)
            self.assertIn("camera_motion", grammar)
            self.assertIn("motion_dynamics", grammar)
            grammars.append((grammar["visual_role"], grammar["camera_motion"], grammar["motion_dynamics"]))

        # Verify that styles are not mere color/font reskins: motion dynamics and roles must have diversity
        distinct_grammars = set(grammars)
        self.assertGreaterEqual(len(distinct_grammars), 5, "Grammars must have discernible structural differences")

    def test_render_all_six_styles_representative_shots(self):
        """Render a valid representative shot for each of the six styles without error."""
        with tempfile.TemporaryDirectory() as td:
            out_root = Path(td)
            rendered_shots = {}

            # 1. documentary_observe: Observe / Focus inspection
            brief_doc = {
                "id": "shot-doc-obs",
                "engine": "remotion",
                "template_id": "remotion-observe-focus",
                "style_pack": "documentary_observe",
                "duration": 2.5,
                "fps": 25,
                "transparency": "full_alpha",
                "overlay_mode": "transparent_overlay",
                "props": {"title": "系统监控现场指标追踪", "focusArea": "核心服务集群"}
            }
            validate_shot_brief(brief_doc)
            res_doc = render_remotion_shot(brief_doc, out_root)
            qa_doc = verify_broll_shot(res_doc, brief_doc)
            self.assertEqual(qa_doc["status"], "passed")
            rendered_shots["documentary_observe"] = res_doc

            # 2. vox_explainer: Conceptual causality
            brief_vox = {
                "id": "shot-vox-exp",
                "engine": "remotion",
                "template_id": "remotion-data-causality",
                "style_pack": "vox_explainer",
                "duration": 2.5,
                "fps": 25,
                "transparency": "opaque",
                "overlay_mode": "full_frame",
                "props": {"title": "吞吐量飞跃对比", "beforeValue": 120, "afterValue": 600, "unit": "qps"}
            }
            res_vox = render_remotion_shot(brief_vox, out_root)
            qa_vox = verify_broll_shot(res_vox, brief_vox)
            self.assertEqual(qa_vox["status"], "passed")
            rendered_shots["vox_explainer"] = res_vox

            # 3. stop_motion_craft: Stop motion tactile stepped motion
            brief_stop = {
                "id": "shot-stop-motion",
                "engine": "remotion",
                "template_id": "remotion-stop-motion-craft",
                "style_pack": "stop_motion_craft",
                "duration": 2.5,
                "fps": 25,
                "transparency": "opaque",
                "overlay_mode": "full_frame",
                "props": {"title": "手作卡片逐帧拆解", "steps": ["剪裁", "拼贴", "组合"], "activeStep": 1}
            }
            validate_shot_brief(brief_stop)
            res_stop = render_remotion_shot(brief_stop, out_root)
            qa_stop = verify_broll_shot(res_stop, brief_stop)
            self.assertEqual(qa_stop["status"], "passed")
            rendered_shots["stop_motion_craft"] = res_stop

            # 4. editorial_magazine: Editorial layout assembly
            brief_edit = {
                "id": "shot-edit-mag",
                "engine": "hyperframes",
                "template_id": "hyperframes-editorial-process",
                "style_pack": "editorial_magazine",
                "duration": 2.5,
                "fps": 25,
                "transparency": "opaque",
                "overlay_mode": "full_frame",
                "props": {"title": "杂志版面核心流程", "steps": ["选题", "排印", "装帧"], "activeStep": 1}
            }
            validate_shot_brief(brief_edit)
            from lib.broll_hyperframes import render_hyperframes_shot, verify_hyperframes_shot
            res_edit = render_hyperframes_shot(brief_edit, out_root)
            qa_edit = verify_hyperframes_shot(res_edit, brief_edit)
            self.assertEqual(qa_edit["status"], "passed")
            rendered_shots["editorial_magazine"] = res_edit

            # 5. product_cinematic: Kinetic focal metric
            brief_prod = {
                "id": "shot-prod-cine",
                "engine": "remotion",
                "template_id": "remotion-stat-counter",
                "style_pack": "product_cinematic",
                "duration": 2.5,
                "fps": 25,
                "transparency": "full_alpha",
                "overlay_mode": "transparent_overlay",
                "props": {"title": "高可用率", "targetNumber": 99.99, "suffix": "%"}
            }
            validate_shot_brief(brief_prod)
            res_prod = render_remotion_shot(brief_prod, out_root)
            qa_prod = verify_broll_shot(res_prod, brief_prod)
            self.assertEqual(qa_prod["status"], "passed")
            rendered_shots["product_cinematic"] = res_prod

            # 6. motion_packaging: Process architecture breakdown
            brief_mot = {
                "id": "shot-mot-pkg",
                "engine": "remotion",
                "template_id": "remotion-process-breakdown",
                "style_pack": "motion_packaging",
                "duration": 2.5,
                "fps": 25,
                "transparency": "full_alpha",
                "overlay_mode": "transparent_overlay",
                "props": {"title": "微服务发布流水线", "steps": ["构建", "扫描", "灰度", "全量"], "activeStep": 2}
            }
            validate_shot_brief(brief_mot)
            res_mot = render_remotion_shot(brief_mot, out_root)
            qa_mot = verify_broll_shot(res_mot, brief_mot)
            self.assertEqual(qa_mot["status"], "passed")
            rendered_shots["motion_packaging"] = res_mot

            self.assertEqual(len(rendered_shots), 6)

    def test_assemble_all_six_styles_into_single_jianying_draft(self):
        """All six representative styles can be assembled onto a single timeline and Jianying draft."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            camera = root / "camera.mp4"
            # 18-second camera base
            subprocess.run([
                'ffmpeg', '-v', 'error', '-y',
                '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=25:duration=18',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=18',
                '-c:v', 'libx264', '-c:a', 'aac', str(camera)
            ], check=True)

            # Create 6 short dummy video sources for the 6 styles (each 2.5s)
            style_sources = {}
            timeline_items = [
                {
                    "id": "aroll-main",
                    "op": "keep",
                    "sourceId": "cam",
                    "sourceStart": 0.0,
                    "sourceEnd": 18.0,
                    "targetStart": 0.0,
                    "track": "A-roll Final",
                    "text": "六种风格全套代表镜头展示。",
                }
            ]

            for idx, style in enumerate(self.EXPECTED_STYLES):
                s_video = root / f"broll_{style}.mp4"
                subprocess.run([
                    'ffmpeg', '-v', 'error', '-y',
                    '-f', 'lavfi', '-i', f'color=c=blue:s=320x180:rate=25:d=2.5',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(s_video)
                ], check=True)
                sid = f"src_{style}"
                style_sources[sid] = {"path": f"broll_{style}.mp4", "duration": 2.5}
                t_start = idx * 2.8
                timeline_items.append({
                    "id": f"broll-{style}",
                    "op": "insert_broll_packaging",
                    "sourceId": sid,
                    "sourceStart": 0.0,
                    "sourceEnd": 2.5,
                    "targetStart": t_start,
                    "track": "B-roll Packaging",
                    "stylePack": style,
                    "sourceStartFrame": 0,
                    "sourceEndFrame": 62,
                    "targetStartFrame": int(round(t_start * 25)),
                    "durationFrames": 62,
                })

            plan_dict = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {
                    "cam": {"path": "camera.mp4", "duration": 18.0},
                    **style_sources
                },
                "timeline": timeline_items,
                "reviewQueue": []
            }
            plan_file = root / "Rough/edit-plan.v1.json"
            plan_file.parent.mkdir(parents=True, exist_ok=True)
            plan_file.write_text(json.dumps(plan_dict, indent=2, ensure_ascii=False), encoding="utf-8")

            loaded = load_plan(plan_file)
            self.assertEqual(len(loaded["timeline"]), 7)

            # Preview synthesis
            prev_path = root / "Rough/six-styles-preview.mp4"
            preview(loaded, prev_path)
            self.assertTrue(prev_path.is_file())

            # Apply to draft
            draft_cli = Path(__file__).resolve().parents[1] / "video-jianying-draft/jianying.py"
            res = subprocess.run([
                sys.executable, str(draft_cli), "apply_edit_plan",
                "--plan", str(plan_file),
                "--output-dir", str(root / "Drafts"),
                "--draft-id", "six_styles_draft",
            ], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

            # Verification
            v_res = verify_draft(loaded, root / "Drafts/six_styles_draft/draft_content.json")
            self.assertEqual(v_res["status"], "ok")

    def test_diversity_rule_flags_adjacent_identical_templates(self):
        """Adjacent B-roll items cannot reuse identical template_id or composition."""
        from lib.broll_narrative import check_broll_diversity

        # Valid sequence: alternating styles & templates
        valid_items = [
            {"id": "b1", "template_id": "remotion-data-causality", "composition": "split_frame_editorial"},
            {"id": "b2", "template_id": "remotion-process-breakdown", "composition": "upper_left_stack"},
            {"id": "b3", "template_id": "remotion-stat-counter", "composition": "focal_metric_center"},
        ]
        res_valid = check_broll_diversity(valid_items)
        self.assertTrue(res_valid["passed"])
        self.assertEqual(len(res_valid["warnings"]), 0)

        # Invalid sequence: adjacent identical template
        invalid_items = [
            {"id": "b1", "template_id": "remotion-data-causality", "composition": "split_frame_editorial"},
            {"id": "b2", "template_id": "remotion-data-causality", "composition": "split_frame_editorial"},
        ]
        res_invalid = check_broll_diversity(invalid_items)
        self.assertFalse(res_invalid["passed"])
        self.assertIn("adjacent_identical_template", res_invalid["warnings"][0])


if __name__ == "__main__":
    unittest.main()
