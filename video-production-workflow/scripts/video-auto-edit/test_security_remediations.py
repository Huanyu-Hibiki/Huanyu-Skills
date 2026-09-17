from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.broll_hyperframes import render_hyperframes_shot, verify_hyperframes_shot
from lib.broll_registry import validate_shot_brief
from lib.broll_remotion import render_remotion_shot


def _hyperframes_brief(shot_id: str = "safe-shot") -> dict:
    return {
        "id": shot_id,
        "engine": "hyperframes",
        "template_id": "hyperframes-editorial-process",
        "style_pack": "vox_explainer",
        "duration": 3,
        "fps": 25,
        "props": {"steps": ["one", "two"]},
    }


class TestSecurityRemediations(unittest.TestCase):
    def test_remotion_rejects_symlinked_output_root(self):
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
                render_remotion_shot({"id": "safe-shot", "duration": 2.5}, linked_output)

    def test_remotion_rejects_symlinked_shot_folder(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root.mkdir(exist_ok=True)
            target = root / "target"
            target.mkdir()
            linked_folder = root / "safe-shot"
            try:
                linked_folder.symlink_to(target, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlinks unavailable: {error}")

            with patch("lib.broll_remotion.subprocess.run"):
                with self.assertRaisesRegex(ValueError, "symlink"):
                    render_remotion_shot({"id": "safe-shot", "duration": 2.5}, root)

    def test_hyperframes_rejects_artifact_folder_symlink_before_resolve(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "target"
            target.mkdir()
            linked_folder = root / "safe-shot"
            try:
                linked_folder.symlink_to(target, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlinks unavailable: {error}")

            with patch("lib.broll_hyperframes.subprocess.run") as run:
                run.return_value = subprocess.CompletedProcess([], 1, stderr=b"should not render")
                with self.assertRaisesRegex(ValueError, "symlink"):
                    render_hyperframes_shot(_hyperframes_brief(), root)
                run.assert_not_called()

    def test_hyperframes_dependency_mismatch_fails_before_render(self):
        with tempfile.TemporaryDirectory() as td:
            calls = []

            def fake_run(command, **kwargs):
                calls.append(command)
                return subprocess.CompletedProcess(command, 0, stdout=b"0.8.46\n", stderr=b"")

            with patch("lib.broll_hyperframes.subprocess.run", side_effect=fake_run):
                with self.assertRaisesRegex(ValueError, "version mismatch"):
                    render_hyperframes_shot(_hyperframes_brief(), Path(td))

            self.assertEqual(len(calls), 1)
            self.assertIn("--no-install", calls[0])

    def test_hyperframes_dependency_offline_fails_before_render(self):
        with tempfile.TemporaryDirectory() as td:
            calls = []

            def fake_run(command, **kwargs):
                calls.append(command)
                return subprocess.CompletedProcess(command, 1, stdout=b"", stderr=b"offline")

            with patch("lib.broll_hyperframes.subprocess.run", side_effect=fake_run):
                with self.assertRaisesRegex(ValueError, "dependency.*offline"):
                    render_hyperframes_shot(_hyperframes_brief(), Path(td))

            self.assertEqual(len(calls), 1)

    def test_hyperframes_report_tamper_cannot_pass_without_receipt_update(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / "safe-shot"
            folder.mkdir(parents=True)
            video = folder / "safe-shot.mp4"
            video.write_bytes(b"encoded-video")
            composition = folder / "composition.html"
            composition.write_text("<main></main>", encoding="utf-8")
            sample_paths = []
            frames = []
            for index, timestamp in enumerate((0.0, 1.5, 2.96)):
                sample = folder / f"output-sample-{index}.png"
                sample.write_bytes(f"sample-{index}".encode())
                sample_paths.append(sample)
                frames.append({
                    "timestamp": timestamp,
                    "artifact": str(sample),
                    "actual_output_hash": hashlib.sha256(sample.read_bytes()).hexdigest(),
                })
            report_path = folder / "seek-safe-report.json"
            report = {"passed": True, "renderer": "local-html-v1", "frames": frames}
            report_path.write_text(json.dumps(report), encoding="utf-8")
            receipt = {
                "engine": "hyperframes",
                "engine_version": "local-html-v1",
                "shot_id": "safe-shot",
                "video_path": str(video.resolve()),
                "duration": 3.0,
                "fps": 25,
                "composition": str(composition.resolve()),
                "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                "seek_report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
                "samples": frames,
            }
            receipt_path = folder / "receipt.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            result = {
                "source_path": str(folder),
                "video_path": str(video),
                "seek_report_path": str(report_path),
                "receipt_path": str(receipt_path),
            }
            self.assertEqual(verify_hyperframes_shot(result, _hyperframes_brief())["status"], "passed")

            tampered = dict(report)
            tampered["frames"] = list(frames)
            tampered["frames"][0] = dict(frames[0], actual_output_hash="0" * 64)
            report_path.write_text(json.dumps(tampered), encoding="utf-8")
            self.assertEqual(verify_hyperframes_shot(result, _hyperframes_brief())["status"], "rejected")

    def test_shot_brief_limit_counts_utf8_bytes(self):
        brief = {
            "id": "safe-shot",
            "engine": "hyperframes",
            "template_id": "hyperframes-editorial-process",
            "style_pack": "vox_explainer",
            "duration": 3,
            "props": {"title": "汉" * 11_000},
        }
        with self.assertRaisesRegex(ValueError, "32KiB"):
            validate_shot_brief(brief, engine="hyperframes")


if __name__ == "__main__":
    unittest.main()
