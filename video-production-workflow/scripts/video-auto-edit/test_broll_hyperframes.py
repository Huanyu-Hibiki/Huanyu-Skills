"""Integration coverage for Task 7 HyperFrames packaging routing."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class TestHyperFramesPackaging(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
