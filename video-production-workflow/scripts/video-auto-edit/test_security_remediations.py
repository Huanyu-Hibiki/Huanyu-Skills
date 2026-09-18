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
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.broll_hyperframes import _brief_hash, render_hyperframes_shot, verify_hyperframes_shot
from lib.broll_registry import validate_shot_brief
from lib.broll_remotion import render_remotion_shot
from auto_edit import _publish_plan_and_manifest


def _hyperframes_brief(shot_id: str = "safe-shot") -> dict:
    return {
        "id": shot_id,
        "engine": "hyperframes",
        "template_id": "hyperframes-editorial-process",
        "style_pack": "vox_explainer",
        "duration": 3,
        "fps": 25,
        "transparency": "opaque",
        "overlay_mode": "full_frame",
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

    def test_remotion_rejects_preexisting_artifact_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            folder = root / "safe-shot"
            folder.mkdir()
            victim = root / "victim.tsx"
            victim.write_text("unchanged", encoding="utf-8")
            try:
                (folder / "Composition.tsx").symlink_to(victim)
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

    def test_hyperframes_rejects_symlinked_ancestor(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            real_parent = root / "real-parent"
            real_parent.mkdir()
            linked_parent = root / "linked-parent"
            try:
                linked_parent.symlink_to(real_parent, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlinks unavailable: {error}")
            with self.assertRaisesRegex(ValueError, "symlink"):
                render_hyperframes_shot(_hyperframes_brief(), linked_parent / "nested")

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

    def test_hyperframes_rejects_preexisting_artifact_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            folder = root / "safe-shot"
            folder.mkdir()
            victim = root / "victim.html"
            victim.write_text("unchanged", encoding="utf-8")
            try:
                (folder / "composition.html").symlink_to(victim)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlinks unavailable: {error}")

            def fake_run(command, **kwargs):
                if "--version" in command:
                    return subprocess.CompletedProcess(command, 0, stdout=b"0.6.98", stderr=b"")
                return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

            with patch("lib.broll_hyperframes.subprocess.run", side_effect=fake_run):
                with self.assertRaisesRegex(ValueError, "symlink"):
                    render_hyperframes_shot(_hyperframes_brief(), root)

    def test_hyperframes_rejects_dangling_artifact_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            folder = root / "safe-shot"
            folder.mkdir()
            try:
                (folder / "composition.html").symlink_to(root / "missing-target.html")
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlinks unavailable: {error}")

            def fake_run(command, **kwargs):
                if "--version" in command:
                    return subprocess.CompletedProcess(command, 0, stdout=b"0.6.98", stderr=b"")
                return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

            with patch("lib.broll_hyperframes.subprocess.run", side_effect=fake_run):
                with self.assertRaisesRegex(ValueError, "symlink"):
                    render_hyperframes_shot(_hyperframes_brief(), root)

    def test_remotion_rejects_dangling_artifact_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            folder = root / "safe-shot"
            folder.mkdir()
            try:
                (folder / "Composition.tsx").symlink_to(root / "missing-target.tsx")
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlinks unavailable: {error}")
            with patch("lib.broll_remotion.subprocess.run"):
                with self.assertRaisesRegex(ValueError, "symlink"):
                    render_remotion_shot({"id": "safe-shot", "duration": 2.5}, root)

    def test_remotion_rejects_excessive_pixel_frame_budget(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, "pixel-frame"):
                render_remotion_shot({"id": "budget-shot", "duration": 60, "width": 3840, "height": 2160, "fps": 60}, td)

    def test_plan_manifest_transaction_rolls_back_on_manifest_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan_path = root / "Rough" / "edit-plan.v1.json"
            manifest_path = root / "Polished" / "broll-manifest.v1.json"
            plan_path.parent.mkdir()
            manifest_path.parent.mkdir()
            old_plan = b'{"version":"1","timeline":[]}'
            old_manifest = b'{"version":"1","items":[]}'
            plan_path.write_bytes(old_plan)
            manifest_path.write_bytes(old_manifest)
            with patch("auto_edit.load_plan", return_value={"planHash": "normalized"}), \
                 patch("auto_edit.write_broll_manifest", side_effect=OSError("manifest unavailable")):
                with self.assertRaises(OSError):
                    _publish_plan_and_manifest(plan_path, {"version": "1"}, manifest_path, {"items": ["new"]})
            self.assertEqual(plan_path.read_bytes(), old_plan)
            self.assertEqual(manifest_path.read_bytes(), old_manifest)

    def test_hyperframes_report_tamper_cannot_pass_without_receipt_update(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / "safe-shot"
            folder.mkdir(parents=True)
            video = folder / "safe-shot.mp4"
            video.write_bytes(b"encoded-video")
            composition = folder / "composition.html"
            composition.write_text("<main></main>", encoding="utf-8")
            from lib.broll_hyperframes import GSAP_ASSET
            gsap_asset = folder / "gsap-3.14.2.min.js"
            gsap_asset.write_bytes(GSAP_ASSET.read_bytes())
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
            report = {"passed": True, "renderer": "hyperframes-v0.6.98", "frames": frames,
                      "seek_order": [1, 0, 2, 1], "seek_consistent": True, "distinct_frames": True}
            report_path.write_text(json.dumps(report), encoding="utf-8")
            from lib.broll_registry import get_template
            tmpl = get_template("hyperframes-editorial-process")
            receipt = {
                "engine": "hyperframes",
                "engine_version": "0.6.98",
                "shot_id": "safe-shot",
                "brief_sha256": _brief_hash(_hyperframes_brief()),
                "video_path": str(video.resolve()),
                "duration": 3.0,
                "fps": 25,
                "composition": str(composition.resolve()),
                "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                "seek_report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
                "samples": frames,
                "composition_sha256": hashlib.sha256(composition.read_bytes()).hexdigest(),
                "composition_source": str(composition.resolve()),
                "composition_source_sha256": hashlib.sha256(composition.read_bytes()).hexdigest(),
                "gsap_version": "3.14.2",
                "gsap_sha256": hashlib.sha256(gsap_asset.read_bytes()).hexdigest(),
                "template_source": tmpl["source"],
                "composition_source_ref": tmpl.get("composition_source"),
                "registry_source": tmpl.get("registry_source"),
                "design_tokens_source": tmpl.get("design_tokens_source"),
                "seek_safe_source": tmpl.get("seek_safe_source"),
                "design_tokens": tmpl.get("design_tokens"),
                "adoption_scope": tmpl.get("adoption_scope"),
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

            failed_report = dict(report, passed=False, seek_consistent=False)
            report_path.write_text(json.dumps(failed_report), encoding="utf-8")
            receipt["seek_report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            self.assertEqual(verify_hyperframes_shot(result, _hyperframes_brief())["reason"], "hyperframes_seek_safety_failed")

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

    def test_shot_brief_requires_template_capability_fields(self):
        brief = _hyperframes_brief()
        brief.pop("transparency")
        with self.assertRaisesRegex(ValueError, "transparency"):
            validate_shot_brief(brief, engine="hyperframes")


if __name__ == "__main__":
    unittest.main()
