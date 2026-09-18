"""Tests for Task 10: Reconciliation, timeline realignment, and invalidation."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import sys
import unittest
import unittest.mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.draft_reconcile import (
    reconcile_plan_from_draft,
    realign_broll_manifest,
    rebuild_subtitles_for_plan,
    check_subtitles_compatible,
    audit_broll_manifest,
    evaluate_broll_cache_invalidation,
)
from lib.edit_draft import apply_edit_plan
from lib.edit_outputs import micros
from lib.edit_plan import load_plan


class MockJianYing:
    """Mock script file and materials for draft testing."""
    class Track_type:
        video = "video"
        text = "text"

    class Clip_settings:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class Timerange:
        def __init__(self, start, duration):
            self.start = start
            self.duration = duration

    class Video_material:
        def __init__(self, material_type, path, material_name, duration, width, height):
            self.id = "mat-" + hashlib.sha256(path.encode()).hexdigest()[:8]
            self.path = path
            self.duration = duration
            self.width = width
            self.height = height

    class Video_segment:
        def __init__(self, material, target_timerange, source_timerange, volume=1.0, clip_settings=None):
            self.material = material
            self.target_timerange = target_timerange
            self.source_timerange = source_timerange
            self.volume = volume
            self.clip_settings = clip_settings
            self.segment_id = ""

    class Text_segment:
        def __init__(self, text, target_timerange):
            self.text = text
            self.target_timerange = target_timerange
            self.segment_id = ""

    class Script_file:
        def __init__(self, width, height, fps=30):
            self.width = width
            self.height = height
            self.fps = fps
            self.tracks = {}
            self.materials = {"videos": [], "texts": []}

        def add_track(self, track_type, name, mute=False):
            self.tracks[name] = {
                "type": track_type,
                "name": name,
                "attribute": 1 if mute else 0,
                "segments": []
            }

        def add_segment(self, segment, track_name):
            if track_name not in self.tracks:
                self.add_track("video", track_name)
            if hasattr(segment, "material"):
                if not any(m["id"] == segment.material.id for m in self.materials["videos"]):
                    self.materials["videos"].append({
                        "id": segment.material.id,
                        "path": segment.material.path,
                        "duration": segment.material.duration
                    })
                seg_dict = {
                    "id": segment.segment_id or "seg-" + hashlib.sha256(str(segment.target_timerange.start).encode()).hexdigest()[:8],
                    "material_id": segment.material.id,
                    "target_timerange": {"start": segment.target_timerange.start, "duration": segment.target_timerange.duration},
                    "source_timerange": {"start": segment.source_timerange.start, "duration": segment.source_timerange.duration},
                    "volume": segment.volume,
                }
            else:
                mat_id = "text-mat-" + hashlib.sha256(segment.text.encode()).hexdigest()[:8]
                self.materials["texts"].append({"id": mat_id, "content": segment.text})
                seg_dict = {
                    "id": segment.segment_id or "seg-text",
                    "material_id": mat_id,
                    "target_timerange": {"start": segment.target_timerange.start, "duration": segment.target_timerange.duration}
                }
            self.tracks[track_name]["segments"].append(seg_dict)

        def dump(self, path):
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "fps": self.fps,
                "materials": self.materials,
                "tracks": list(self.tracks.values()),
            }
            p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class TestDraftReconcile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.video_file = self.root / "a_roll.mp4"
        self.video_file.write_bytes(b"dummy video content")

        self.fps = 30
        self.base_plan = {
            "version": "1",
            "fps": self.fps,
            "durationFrames": 210,
            "sources": {
                "src_main": {
                    "path": str(self.video_file),
                    "duration": 15.0
                }
            },
            "timeline": [
                {
                    "id": "item-1",
                    "op": "keep",
                    "sourceId": "src_main",
                    "sourceStart": 0.0,
                    "sourceEnd": 2.0,
                    "sourceStartFrame": 0,
                    "sourceEndFrame": 60,
                    "durationFrames": 60,
                    "targetStart": 0.0,
                    "targetStartFrame": 0,
                    "track": "A-roll Final",
                    "text": "欢迎来到技术分享",
                    "speaker": "host"
                },
                {
                    "id": "item-2",
                    "op": "keep",
                    "sourceId": "src_main",
                    "sourceStart": 2.0,
                    "sourceEnd": 4.0,
                    "sourceStartFrame": 60,
                    "sourceEndFrame": 120,
                    "durationFrames": 60,
                    "targetStart": 2.0,
                    "targetStartFrame": 60,
                    "track": "A-roll Final",
                    "text": "今天深入讲解系统架构",
                    "speaker": "host"
                },
                {
                    "id": "item-3",
                    "op": "keep",
                    "sourceId": "src_main",
                    "sourceStart": 4.0,
                    "sourceEnd": 7.0,
                    "sourceStartFrame": 120,
                    "sourceEndFrame": 210,
                    "durationFrames": 90,
                    "targetStart": 4.0,
                    "targetStartFrame": 120,
                    "track": "A-roll Final",
                    "text": "我们来看这个操作演示",
                    "speaker": "host"
                }
            ],
            "reviewQueue": []
        }
        p_bytes = json.dumps(self.base_plan, sort_keys=True).encode()
        self.base_plan["planHash"] = hashlib.sha256(p_bytes).hexdigest()

    def tearDown(self):
        self.tmp.cleanup()

    def _create_mock_draft(self, segments, path):
        mat_id = "mat_vid_01"
        draft_data = {
            "fps": self.fps,
            "materials": {
                "videos": [
                    {
                        "id": mat_id,
                        "path": str(self.video_file),
                        "duration": 15000000
                    }
                ],
                "texts": []
            },
            "tracks": [
                {
                    "name": "A-roll Final",
                    "type": "video",
                    "attribute": 0,
                    "segments": []
                }
            ]
        }
        for seg in segments:
            draft_data["tracks"][0]["segments"].append({
                "id": seg.get("id", "seg-test"),
                "material_id": mat_id,
                "target_timerange": {
                    "start": seg["target_start_us"],
                    "duration": seg["duration_us"]
                },
                "source_timerange": {
                    "start": seg["source_start_us"],
                    "duration": seg["duration_us"]
                }
            })
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(draft_data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def test_reconcile_draft_timeline_shift_updates_broll_anchors(self):
        draft_path = self.root / "draft" / "draft_content.json"
        self._create_mock_draft([
            {
                "id": "item-2",
                "source_start_us": micros(60, self.fps),
                "duration_us": micros(60, self.fps),
                "target_start_us": 0
            },
            {
                "id": "item-3",
                "source_start_us": micros(120, self.fps),
                "duration_us": micros(90, self.fps),
                "target_start_us": micros(60, self.fps)
            }
        ], draft_path)

        broll_vid = self.root / "broll.mp4"
        broll_vid.write_bytes(b"broll mock")
        manifest = {
            "version": "1",
            "items": [
                {
                    "id": "demo-01",
                    "route": "screen_demo",
                    "anchor": "操作演示",
                    "target_start": 4.0,
                    "duration": 2.5,
                    "status": "approved",
                    "video_path": str(broll_vid),
                    "shot_brief": {"id": "demo-01", "style_pack": "documentary_observe"}
                }
            ]
        }

        reconciled_plan = reconcile_plan_from_draft(self.base_plan, draft_path)
        self.assertEqual(reconciled_plan["durationFrames"], 150)
        self.assertEqual(len(reconciled_plan["timeline"]), 2)
        self.assertEqual(reconciled_plan["timeline"][0]["id"], "item-2")
        self.assertEqual(reconciled_plan["timeline"][0]["targetStartFrame"], 0)
        self.assertEqual(reconciled_plan["timeline"][1]["id"], "item-3")
        self.assertEqual(reconciled_plan["timeline"][1]["targetStartFrame"], 60)
        self.assertEqual(reconciled_plan["timeline"][1]["targetStart"], 2.0)

        realigned_manifest, updated_plan = realign_broll_manifest(manifest, reconciled_plan)
        realigned_item = realigned_manifest["items"][0]

        self.assertEqual(realigned_item["target_start"], 2.0)
        self.assertEqual(realigned_item["status"], "approved")
        self.assertEqual(realigned_item["video_path"], str(broll_vid))
        self.assertEqual(len(updated_plan.get("reviewQueue", [])), 0)

    def test_reconcile_draft_orphaned_anchor_sent_to_review_queue(self):
        draft_path = self.root / "draft" / "draft_content.json"
        self._create_mock_draft([
            {
                "id": "item-1",
                "source_start_us": 0,
                "duration_us": micros(60, self.fps),
                "target_start_us": 0
            },
            {
                "id": "item-2",
                "source_start_us": micros(60, self.fps),
                "duration_us": micros(60, self.fps),
                "target_start_us": micros(60, self.fps)
            }
        ], draft_path)

        broll_vid = self.root / "broll.mp4"
        broll_vid.write_bytes(b"broll mock")
        manifest = {
            "version": "1",
            "items": [
                {
                    "id": "demo-01",
                    "route": "screen_demo",
                    "anchor": "操作演示",
                    "target_start": 4.0,
                    "duration": 2.5,
                    "status": "approved",
                    "video_path": str(broll_vid)
                }
            ]
        }

        reconciled_plan = reconcile_plan_from_draft(self.base_plan, draft_path)
        realigned_manifest, updated_plan = realign_broll_manifest(manifest, reconciled_plan)

        realigned_item = realigned_manifest["items"][0]
        self.assertIn(realigned_item["status"], ("orphaned", "pending_review"))
        self.assertEqual(realigned_item["reason"], "anchor_deleted_in_draft")

        rq = updated_plan.get("reviewQueue", [])
        self.assertTrue(any(item.get("type") == "broll_anchor_orphaned" and item.get("broll_id") == "demo-01" for item in rq))

    def test_subtitles_rebuilt_with_version_binding_and_rejects_stale_master(self):
        srt_file = self.root / "auto-cut.srt"
        rebuild_subtitles_for_plan(self.base_plan, srt_file)
        self.assertTrue(srt_file.exists())
        content = srt_file.read_text(encoding="utf-8")
        self.assertIn("timelineVersion: " + self.base_plan["planHash"], content)

        is_compat, _ = check_subtitles_compatible(srt_file, self.base_plan)
        self.assertTrue(is_compat)

        modified_plan = copy.deepcopy(self.base_plan)
        modified_plan["planHash"] = "different_hash_999"
        modified_plan["durationFrames"] = 120
        is_compat, reason = check_subtitles_compatible(srt_file, modified_plan)
        self.assertFalse(is_compat)
        self.assertIn("stale", reason.lower())

    def test_apply_edit_plan_protects_manually_modified_draft(self):
        dy = MockJianYing()
        output_dir = self.root / "jianying_drafts"

        probe_dict = {
            "streams": [{"codec_type": "video", "width": 1920, "height": 1080}],
            "format": {"duration": "15.0"}
        }
        with unittest.mock.patch("lib.edit_plan.probe", return_value=probe_dict):
            with unittest.mock.patch("lib.edit_draft.probe", return_value=probe_dict):
                with unittest.mock.patch("lib.edit_draft.verify_draft", return_value={"status": "ok"}):
                    plan_file = self.root / "plan.json"
                    plan_file.write_text(json.dumps(self.base_plan, indent=2), encoding="utf-8")

                    draft_path1 = apply_edit_plan(plan_file, output_dir, dy, draft_id="test-draft")
                    self.assertTrue(Path(draft_path1).exists())

                    Path(draft_path1).write_text(json.dumps({"modified_by_user": True}), encoding="utf-8")

                    draft_path2 = apply_edit_plan(plan_file, output_dir, dy, draft_id="test-draft")
                    self.assertNotEqual(draft_path1, draft_path2)
                    self.assertIn("modified_by_user", Path(draft_path1).read_text(encoding="utf-8"))

    def test_intercept_completed_status_when_video_missing(self):
        manifest = {
            "version": "1",
            "items": [
                {
                    "id": "shot-01",
                    "status": "completed",
                    "video_path": str(self.root / "non_existent_file.mp4")
                }
            ]
        }
        audited, issues = audit_broll_manifest(manifest)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["type"], "missing_output_file")
        self.assertEqual(audited["items"][0]["status"], "failed")

    def test_cache_invalidation_granularity(self):
        item = {
            "id": "pack-01",
            "status": "approved",
            "video_path": str(self.video_file),
            "shot_brief": {
                "id": "pack-01",
                "template_id": "remotion-process-breakdown",
                "style_pack": "motion_packaging",
                "text": "步骤一：初始化系统",
                "theme": "dark"
            }
        }
        same_brief = copy.deepcopy(item["shot_brief"])
        is_valid, reason = evaluate_broll_cache_invalidation(item, same_brief)
        self.assertTrue(is_valid)

        changed_brief = copy.deepcopy(item["shot_brief"])
        changed_brief["text"] = "步骤一：启动网关服务"
        is_valid, reason = evaluate_broll_cache_invalidation(item, changed_brief)
        self.assertFalse(is_valid)
        self.assertIn("text", reason)

        changed_style = copy.deepcopy(item["shot_brief"])
        changed_style["style_pack"] = "vox_explainer"
        is_valid, reason = evaluate_broll_cache_invalidation(item, changed_style)
        self.assertFalse(is_valid)
        self.assertIn("style_pack", reason)

    def test_cli_reconcile_end_to_end(self):
        """Integration test for CLI 'auto_edit.py reconcile'."""
        project = self.root / "Project"
        rough = project / "Rough"
        rough.mkdir(parents=True, exist_ok=True)

        plan_file = rough / "edit-plan.v1.json"
        plan_file.write_text(json.dumps(self.base_plan, indent=2), encoding="utf-8")

        broll_vid = project / "broll.mp4"
        broll_vid.write_bytes(b"dummy broll")
        manifest_file = rough / "broll-manifest.json"
        manifest_data = {
            "version": "1",
            "items": [
                {
                    "id": "demo-01",
                    "route": "screen_demo",
                    "anchor": "操作演示",
                    "target_start": 4.0,
                    "duration": 2.5,
                    "status": "approved",
                    "video_path": str(broll_vid),
                }
            ]
        }
        manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        # Mock draft with item-1 deleted
        draft_path = project / "draft" / "draft_content.json"
        self._create_mock_draft([
            {
                "id": "item-2",
                "source_start_us": micros(60, self.fps),
                "duration_us": micros(60, self.fps),
                "target_start_us": 0
            },
            {
                "id": "item-3",
                "source_start_us": micros(120, self.fps),
                "duration_us": micros(90, self.fps),
                "target_start_us": micros(60, self.fps)
            }
        ], draft_path)

        # Execute auto_edit.py reconcile CLI
        import auto_edit
        test_argv = [
            "auto_edit.py", "reconcile", str(project),
            "--draft", str(draft_path),
            "--apply"
        ]
        probe_dict = {
            "streams": [{"codec_type": "video", "width": 1920, "height": 1080}],
            "format": {"duration": "15.0"}
        }
        with unittest.mock.patch("lib.edit_plan.probe", return_value=probe_dict):
            with unittest.mock.patch("sys.argv", test_argv):
                ret = auto_edit.main()
                self.assertEqual(ret, 0)

        # Verify applied plan
        updated_plan = json.loads(plan_file.read_text(encoding="utf-8"))
        self.assertEqual(updated_plan["durationFrames"], 150)
        self.assertEqual(len(updated_plan["timeline"]), 2)

        # Verify realigned manifest
        updated_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        self.assertEqual(updated_manifest["items"][0]["target_start"], 2.0)

        # Verify rebuilt subtitle
        srt_file = rough / "auto-cut.srt"
        self.assertTrue(srt_file.exists())
        self.assertIn("timelineVersion: " + updated_plan["planHash"], srt_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
