"""Unit and integration tests for Task 8: AI visual B-roll generation pipeline."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.broll_ai_visual import (
    resolve_ai_visual_budget,
    generate_ai_visual_shot,
    verify_ai_visual_shot,
    AIProviderClient,
)
from lib.broll_registry import validate_shot_brief
from lib.edit_plan import load_plan
from lib.edit_draft import apply_edit_plan
from lib.edit_outputs import preview, verify_draft


def _sample_brief(shot_id: str = "broll-ai-01") -> dict:
    return {
        "id": shot_id,
        "route": "ai_visual",
        "engine": "gemini_veo",
        "template_id": "ai-visual-vox-metaphor",
        "style_pack": "vox_explainer",
        "duration": 3.0,
        "fps": 25,
        "width": 1280,
        "height": 720,
        "transparency": "opaque",
        "overlay_mode": "full_frame",
        "target_start": 1.5,
        "prompt": "vintage paper cutout collage depicting data flowing into cloud infrastructure",
        "first_frame_prompt": "empty rustic desk workspace with blank parchment",
        "last_frame_prompt": "assembled complex network diagram made of torn paper cutouts",
        "props": {"style": "paper_collage", "max_cost_usd": 0.50},
    }


class TestAIVisualBroll(unittest.TestCase):

    def test_credential_isolation_and_secret_redaction(self):
        """API keys must NEVER be leaked into logs, plans, prompt artifacts, or receipts."""
        brief = _sample_brief("shot-secret-leak-test")
        env_config = {
            "GEMINI_API_KEY": "test-gemini-key-placeholder",
            "GOOGLE_CLOUD_PROJECT": "secret-project-id",
        }
        spec = resolve_ai_visual_budget(brief, env_config=env_config)
        self.assertTrue(spec["has_credentials"])
        # Stringify the entire resolved spec and verify raw key is strictly absent
        spec_dump = json.dumps(spec)
        self.assertNotIn("test-gemini-key-placeholder", spec_dump)
        self.assertEqual(spec["gemini_key_hash"], hashlib.sha256(b"test-gemini-key-placeholder").hexdigest()[:12])

    def test_missing_credentials_routes_to_review_queue_without_mocking(self):
        """When credentials are absent, generation halts with status pending_credentials and does NOT fake a video."""
        brief = _sample_brief("shot-no-key")
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            # Empty environment - no credentials
            spec = resolve_ai_visual_budget(brief, env_config={})
            self.assertFalse(spec["has_credentials"])
            res = generate_ai_visual_shot(brief, out_dir=out_dir, budget_spec=spec)
            self.assertEqual(res["status"], "pending_credentials")
            self.assertEqual(res["action"], "route_to_review_queue")
            self.assertFalse((out_dir / "shot-no-key/final.mp4").exists())

    def test_factual_or_evidence_prompts_redirected_to_screen_demo(self):
        """Requests attempting to hallucinate factual UI, real contracts, or news must be rejected and redirected to screen_demo."""
        bad_brief = _sample_brief("shot-fake-evidence")
        bad_brief["prompt"] = "Show the exact bank balance screenshot and customer legal contract"
        with self.assertRaisesRegex(ValueError, "factual_evidence_requires_screen_demo"):
            resolve_ai_visual_budget(bad_brief, env_config={})

    def test_async_job_persistence_and_resumption(self):
        """An asynchronous generation job records operation ID and can resume without re-submitting."""
        brief = _sample_brief("shot-async-resume")
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            mock_client = MagicMock(spec=AIProviderClient)
            mock_client.submit_job.return_value = {
                "operation_id": "operations/generate-12345",
                "status": "running",
            }
            spec = {"has_credentials": True, "engine": "gemini_veo", "model": "veo-3.1-fast"}

            # First run: job submitted, status running
            res1 = generate_ai_visual_shot(brief, out_dir=out_dir, budget_spec=spec, provider_client=mock_client)
            self.assertEqual(res1["status"], "running")
            self.assertEqual(res1["operation_id"], "operations/generate-12345")
            self.assertEqual(mock_client.submit_job.call_count, 1)

            # Check manifest/job checkpoint saved to disk
            op_file = out_dir / "shot-async-resume/operation.json"
            self.assertTrue(op_file.is_file())

            # Second run: resumes existing job without calling submit_job again
            mock_client.check_job_status.return_value = {
                "status": "running",
                "operation_id": "operations/generate-12345",
            }
            res2 = generate_ai_visual_shot(brief, out_dir=out_dir, budget_spec=spec, provider_client=mock_client)
            self.assertEqual(mock_client.submit_job.call_count, 1)  # NOT called again!
            self.assertEqual(mock_client.check_job_status.call_count, 1)

    def test_video_qa_validates_audio_free_and_duration_tolerance(self):
        """QA gate enforces zero audio streams, exact duration within 1 frame, and receipt binding."""
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / "shot-qa-gate"
            folder.mkdir()
            video_path = folder / "final.mp4"
            # Generate a 3.0s silent synthetic video (scale 640x360 at 25 fps)
            cmd = [
                "ffmpeg", "-v", "error", "-y",
                "-f", "lavfi", "-i", "color=c=navy:s=640x360:r=25:d=3.0",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                str(video_path)
            ]
            subprocess.run(cmd, check=True)

            brief = _sample_brief("shot-qa-gate")
            result = {
                "status": "rendered",
                "shot_id": "shot-qa-gate",
                "video_path": str(video_path),
                "duration": 3.0,
                "fps": 25,
            }

            # Missing receipt must be rejected
            qa1 = verify_ai_visual_shot(result, brief)
            self.assertEqual(qa1["status"], "rejected")
            self.assertEqual(qa1["reason"], "receipt_missing_or_invalid")

            # Write valid signed receipt
            from lib.broll_ai_visual import create_ai_visual_receipt
            receipt_path = create_ai_visual_receipt(result, brief, provider_name="mock_provider", model="mock-veo")
            result["receipt_path"] = str(receipt_path)

            qa2 = verify_ai_visual_shot(result, brief)
            self.assertEqual(qa2["status"], "passed")
            self.assertTrue(qa2["is_silent"])

    def test_ai_visual_draft_track_and_preview_integration(self):
        """AI visual shot integrates into edit-plan timeline, draft 'B-roll AI Visual' track, and preview overlay."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Create synthetic A-roll video (4.0s)
            aroll_path = root / "a_roll.mp4"
            subprocess.run([
                "ffmpeg", "-v", "error", "-y",
                "-f", "lavfi", "-i", "color=c=black:s=640x360:r=25:d=4.0",
                "-f", "lavfi", "-i", "sine=f=440:r=48000:d=4.0",
                "-c:v", "libx264", "-c:a", "aac", str(aroll_path)
            ], check=True)

            # Create synthetic B-roll AI visual video (2.0s)
            ai_vis_path = root / "broll_ai.mp4"
            subprocess.run([
                "ffmpeg", "-v", "error", "-y",
                "-f", "lavfi", "-i", "color=c=purple:s=640x360:r=25:d=2.0",
                "-c:v", "libx264", str(ai_vis_path)
            ], check=True)

            plan = {
                "version": "1",
                "fps": 25,
                "projectRoot": str(root),
                "sources": {
                    "src_aroll": {"path": str(aroll_path), "duration": 4.0},
                    "src_ai_broll": {"path": str(ai_vis_path), "duration": 2.0},
                },
                "timeline": [
                    {
                        "id": "aroll_seg_01",
                        "op": "keep",
                        "sourceId": "src_aroll",
                        "sourceStart": 0.0,
                        "sourceEnd": 4.0,
                        "targetStart": 0.0,
                        "track": "A-roll Final",
                        "sourceStartFrame": 0,
                        "sourceEndFrame": 100,
                        "targetStartFrame": 0,
                        "durationFrames": 100,
                    },
                    {
                        "id": "ai_broll_seg_01",
                        "op": "insert_broll_ai_visual",
                        "sourceId": "src_ai_broll",
                        "sourceStart": 0.0,
                        "sourceEnd": 2.0,
                        "targetStart": 1.0,
                        "track": "B-roll AI Visual",
                        "sourceStartFrame": 0,
                        "sourceEndFrame": 50,
                        "targetStartFrame": 25,
                        "durationFrames": 50,
                    }
                ],
                "reviewQueue": []
            }
            plan_file = root / "Rough/edit-plan.v1.json"
            plan_file.parent.mkdir(parents=True, exist_ok=True)
            plan_file.write_text(json.dumps(plan), encoding="utf-8")

            # Test load_plan validation
            loaded = load_plan(plan_file)
            self.assertEqual(len(loaded["timeline"]), 2)

            # Test preview with B-roll AI Visual overlay
            prev_path = root / "Rough/auto-cut-preview.mp4"
            preview(loaded, prev_path)
            self.assertTrue(prev_path.is_file())

            # Test draft creation with B-roll AI Visual track
            draft_cli = Path(__file__).resolve().parents[1] / "video-jianying-draft/jianying.py"
            res = subprocess.run([
                sys.executable, str(draft_cli), "apply_edit_plan",
                "--plan", str(plan_file),
                "--output-dir", str(root / "Drafts"),
                "--draft-id", "my_ai_draft",
            ], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)

            draft_content = json.loads((root / "Drafts/my_ai_draft/draft_content.json").read_text(encoding="utf-8"))
            ai_tracks = [t for t in draft_content["tracks"] if t.get("name") == "B-roll AI Visual"]
            self.assertEqual(len(ai_tracks), 1)
            # B-roll AI Visual must be muted so A-roll narration is unperturbed
            self.assertEqual(ai_tracks[0].get("attribute"), 1)

            v_res = verify_draft(loaded, root / "Drafts/my_ai_draft/draft_content.json")
            self.assertEqual(v_res["status"], "ok")

    def test_auto_edit_insert_broll_ai_visual_cli(self):
        """auto_edit.py insert-broll-ai-visual CLI command handles pending credentials and dry-run."""
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
                        "text": "我们用深度网络生成高维概念特征空间。",
                    }
                ],
                "reviewQueue": []
            }
            plan_file = root / "Rough/edit-plan.v1.json"
            plan_file.parent.mkdir(parents=True, exist_ok=True)
            plan_file.write_text(json.dumps(plan_dict, indent=2, ensure_ascii=False), encoding="utf-8")

            # Run insert-broll-ai-visual without credentials -> routes to pending_credentials in reviewQueue
            cmd = [
                sys.executable, str(cli), "insert-broll-ai-visual", str(root),
                "--sentence", "take-1",
                "--style-pack", "vox_explainer",
                "--apply"
            ]
            env = os.environ.copy()
            env.pop("GEMINI_API_KEY", None)
            env.pop("GOOGLE_CLOUD_PROJECT", None)
            res = subprocess.run(cmd, capture_output=True, text=True, env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            out_json = json.loads(res.stdout.strip())
            self.assertEqual(out_json["status"], "pending_credentials")

            # Check reviewQueue in updated plan
            updated_plan = json.loads(plan_file.read_text(encoding="utf-8"))
            self.assertTrue(any(rq.get("type") == "ai_visual_pending_credentials" for rq in updated_plan["reviewQueue"]))


if __name__ == "__main__":
    unittest.main()
