"""Integration coverage for Task 7 HyperFrames packaging routing."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.broll_registry import validate_shot_brief
from auto_edit import write_broll_manifest
from lib.broll_hyperframes import render_hyperframes_shot, verify_hyperframes_shot


class TestHyperFramesPackaging(unittest.TestCase):
    def _project_with_camera(self, root: Path, *, existing_packaging: bool = False) -> Path:
        camera = root / "camera.mp4"
        subprocess.run([
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=size=320x180:rate=25:duration=5",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
            "-c:v", "libx264", "-c:a", "aac", str(camera),
        ], check=True)
        timeline = [{
            "id": "sentence-1", "op": "keep", "sourceId": "camera",
            "sourceStart": 0.0, "sourceEnd": 5.0, "targetStart": 0.0,
            "track": "A-roll Final", "text": "把复杂流程拆成三个可验证步骤。",
        }]
        if existing_packaging:
            timeline.append({
                "id": "replace-me", "op": "insert_broll_packaging", "sourceId": "camera",
                "sourceStart": 0.0, "sourceEnd": 3.0, "targetStart": 1.0,
                "track": "B-roll Packaging", "stylePack": "vox_explainer",
            })
        plan = {"version": "1", "fps": 25, "projectRoot": str(root),
                "sources": {"camera": {"path": "camera.mp4", "duration": 5.0}},
                "timeline": timeline, "reviewQueue": []}
        plan_path = root / "Rough" / "edit-plan.v1.json"
        plan_path.parent.mkdir(parents=True)
        plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        return plan_path

    @staticmethod
    def _hyperframes_brief(shot_id: str) -> dict:
        return {
            "id": shot_id, "engine": "hyperframes",
            "template_id": "hyperframes-editorial-process", "style_pack": "vox_explainer",
            "duration": 3, "target_start": 1, "props": {"steps": ["one", "two"]},
        }

    def test_corrupt_manifest_is_not_overwritten(self):
        """A render command refuses corrupt state before it can publish a replacement."""
        cli = Path(__file__).resolve().parent / "auto_edit.py"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._project_with_camera(root)
            manifest_path = root / "Polished" / "broll-manifest.v1.json"
            manifest_path.parent.mkdir()
            corrupt = b'{"items": [not valid json'
            manifest_path.write_bytes(corrupt)
            result = subprocess.run([sys.executable, str(cli), "insert-broll-packaging", str(root),
                                     "--engine", "hyperframes", "--apply"], text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cannot safely read B-roll manifest", result.stderr)
            self.assertEqual(manifest_path.read_bytes(), corrupt)

    def test_manifest_write_does_not_follow_a_predictable_temp_symlink(self):
        """Atomic state publishing must not write through an attacker-created temp link."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_path = root / "broll-manifest.v1.json"
            victim = root / "victim.json"
            victim.write_text("unchanged", encoding="utf-8")
            temp_path = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
            try:
                temp_path.symlink_to(victim)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlinks unavailable: {error}")
            write_broll_manifest(manifest_path, {"version": "1", "items": [], "summary": {}})
            self.assertEqual(victim.read_text(encoding="utf-8"), "unchanged")

    def test_retry_updates_only_the_failed_item_and_preserves_other_entries(self):
        """Retry is a targeted state transition, not a manifest-wide rewrite."""
        cli = Path(__file__).resolve().parent / "auto_edit.py"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._project_with_camera(root)
            retry_id = "retry-me"
            other = {"id": "leave-me", "route": "screen_demo", "status": "approved", "attempt": 7,
                     "metadata": {"must": "remain byte-for-byte equivalent"}}
            manifest_path = root / "Polished" / "broll-manifest.v1.json"
            manifest_path.parent.mkdir()
            manifest_path.write_text(json.dumps({"version": "1", "items": [
                dict(self._hyperframes_brief(retry_id), route="packaging", status="failed", attempt=2,
                     shot_brief=self._hyperframes_brief(retry_id), error="prior render failure"), other],
                "summary": {"total_items": 2}}, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(cli), "retry-broll-item", str(root),
                                     "--retry-item", retry_id, "--apply"], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            items = json.loads(manifest_path.read_text(encoding="utf-8"))["items"]
            retried = next(item for item in items if item["id"] == retry_id)
            unchanged = next(item for item in items if item["id"] == other["id"])
            self.assertEqual(retried["status"], "approved")
            self.assertEqual(retried["attempt"], 3)
            self.assertEqual(unchanged, other)

    def test_replacement_creates_one_jianying_packaging_segment_readback(self):
        """A replacement leaves one actual Jianying B-roll segment on its native track."""
        cli = Path(__file__).resolve().parent / "auto_edit.py"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan_path = self._project_with_camera(root, existing_packaging=True)
            brief_path = root / "brief.json"
            brief_path.write_text(json.dumps(self._hyperframes_brief("replace-me")), encoding="utf-8")
            result = subprocess.run([sys.executable, str(cli), "insert-broll-packaging", str(root),
                                     "--brief", str(brief_path), "--engine", "hyperframes", "--apply"],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            updated = json.loads(plan_path.read_text(encoding="utf-8"))
            packaging = [item for item in updated["timeline"] if item.get("track") == "B-roll Packaging"]
            self.assertEqual([item["id"] for item in packaging], ["replace-me"])
            draft_cli = cli.parents[1] / "video-jianying-draft" / "jianying.py"
            draft_result = subprocess.run([sys.executable, str(draft_cli), "apply_edit_plan", "--plan", str(plan_path),
                                           "--output-dir", str(root / "Drafts"), "--draft-id", "replace-readback"],
                                          text=True, capture_output=True)
            self.assertEqual(draft_result.returncode, 0, draft_result.stderr)
            draft = json.loads((root / "Drafts" / "replace-readback" / "draft_content.json").read_text(encoding="utf-8"))
            track = next(item for item in draft["tracks"] if item.get("name") == "B-roll Packaging")
            self.assertEqual(len(track["segments"]), 1)

    def test_rejects_symlinked_output_and_oversized_or_deep_briefs(self):
        """The render boundary rejects links and hostile JSON before creating artifacts."""
        brief = {
            "id": "safe-shot", "engine": "hyperframes",
            "template_id": "hyperframes-editorial-process", "style_pack": "vox_explainer",
            "duration": 3, "props": {"steps": ["one"]},
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            real_output = root / "real-output"
            real_output.mkdir()
            linked_output = root / "linked-output"
            try:
                linked_output.symlink_to(real_output, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlinks unavailable: {error}")
            with self.assertRaisesRegex(ValueError, "symlink"):
                render_hyperframes_shot(brief, linked_output)

        with self.assertRaises(ValueError):
            validate_shot_brief(dict(brief, props={"text": "x" * 40_000}))
        deeply_nested = {}
        nested = deeply_nested
        for _ in range(1_100):
            child = {}
            nested["child"] = child
            nested = child
        with self.assertRaises(ValueError):
            validate_shot_brief(dict(brief, props=deeply_nested))

    def test_shared_brief_routes_to_seek_safe_hyperframes_packaging_track(self):
        """The public CLI produces a safe, deterministic HTML artifact and packaging item."""
        cli = Path(__file__).resolve().parent / "auto_edit.py"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            camera = root / "camera.mp4"
            subprocess.run([
                "ffmpeg", "-v", "error", "-y",
                "-f", "lavfi", "-i", "testsrc=size=320x180:rate=25:duration=5",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
                "-c:v", "libx264", "-c:a", "aac", str(camera),
            ], check=True)
            plan = {
                "version": "1", "fps": 25, "projectRoot": str(root),
                "sources": {"camera": {"path": "camera.mp4", "duration": 5.0}},
                "timeline": [{
                    "id": "sentence-1", "op": "keep", "sourceId": "camera",
                    "sourceStart": 0.0, "sourceEnd": 5.0, "targetStart": 0.0,
                    "track": "A-roll Final", "text": "把复杂流程拆成三个可验证步骤。",
                }], "reviewQueue": [],
            }
            plan_path = root / "Rough" / "edit-plan.v1.json"
            plan_path.parent.mkdir(parents=True)
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

            result = subprocess.run([
                sys.executable, str(cli), "insert-broll-packaging", str(root),
                "--sentence", "sentence-1", "--engine", "hyperframes", "--apply",
            ], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)

            manifest_path = root / "Polished" / "broll-manifest.v1.json"
            self.assertTrue(manifest_path.is_file(), result.stdout)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            item = manifest["items"][0]
            self.assertEqual(item["engine"], "hyperframes")
            artifact_dir = Path(item["source_path"])
            self.assertTrue((artifact_dir / "composition.html").is_file())
            self.assertTrue((artifact_dir / "seek-safe-report.json").is_file())
            html = (artifact_dir / "composition.html").read_text(encoding="utf-8")
            self.assertNotIn("http://", html)
            self.assertNotIn("https://", html)

            seek_report = json.loads((artifact_dir / "seek-safe-report.json").read_text(encoding="utf-8"))
            self.assertTrue(seek_report["passed"])
            self.assertEqual(len(seek_report["frames"]), 3)
            # The samples must come from the encoded HyperFrames output, not a
            # second Python/Pillow implementation of the scene.
            self.assertTrue(all("actual_output_hash" in sample for sample in seek_report["frames"]))
            receipt = json.loads((artifact_dir / "receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["renderer"]["command"][0:3], ["npx", "hyperframes", "render"])

            # QA reads samples decoded from the rendered video and rejects a
            # missing or altered sample rather than trusting the manifest.
            first_sample = Path(seek_report["frames"][0]["artifact"])
            first_sample.unlink()
            self.assertEqual(
                verify_hyperframes_shot({
                    "source_path": str(artifact_dir), "video_path": item["video_path"],
                    "seek_report_path": str(artifact_dir / "seek-safe-report.json"),
                }, item["shot_brief"])["status"],
                "rejected",
            )

            updated = json.loads(plan_path.read_text(encoding="utf-8"))
            packaging = [entry for entry in updated["timeline"] if entry.get("track") == "B-roll Packaging"]
            self.assertEqual(len(packaging), 1)
            self.assertEqual(packaging[0]["engine"], "hyperframes")

            preview_result = subprocess.run(
                [sys.executable, str(cli), "preview", str(root)], text=True, capture_output=True
            )
            self.assertEqual(preview_result.returncode, 0, preview_result.stderr)
            self.assertTrue((root / "Rough" / "auto-cut-preview.mp4").is_file())

            draft_cli = cli.parents[1] / "video-jianying-draft" / "jianying.py"
            draft_result = subprocess.run([
                sys.executable, str(draft_cli), "apply_edit_plan", "--plan", str(plan_path),
                "--output-dir", str(root / "Drafts"), "--draft-id", "hyperframes-packaging",
            ], text=True, capture_output=True)
            self.assertEqual(draft_result.returncode, 0, draft_result.stderr)
            draft = json.loads((root / "Drafts" / "hyperframes-packaging" / "draft_content.json").read_text(encoding="utf-8"))
            track = next(item for item in draft["tracks"] if item.get("name") == "B-roll Packaging")
            self.assertEqual(track["attribute"], 1)

    def test_registry_rejects_unsupported_style_before_render(self):
        with self.assertRaisesRegex(ValueError, "style_pack"):
            validate_shot_brief({
                "id": "shot", "engine": "hyperframes",
                "template_id": "hyperframes-editorial-process",
                "style_pack": "not-supported", "duration": 3,
                "props": {"steps": ["one"]},
            })


if __name__ == "__main__":
    unittest.main()
