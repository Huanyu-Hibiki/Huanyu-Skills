#!/usr/bin/env python3
"""Initialize a video project without overwriting existing files."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "templates"

PROJECT_DIRS = [
    "video scripts",
    "Raw",
    "Rough/transcripts",
    "Rough/clips_graded",
    "Rough/animations",
    "Rough/verify",
    "Sub",
    "Jianying-draft",
    "Polished/B-roll",
    "Polished/Remotion",
    "Polished/HyperFrames",
    "assets/requests",
    "assets/raw/audio",
    "assets/raw/video",
    "assets/raw/image",
    "assets/audio/music",
    "assets/audio/sfx",
    "assets/video/stock",
    "assets/image/stock",
    "assets/licenses",
    "assets/logs",
    "prompt/video",
    "prompt/image",
    "prompt/animation",
    "prompt/audio",
    "Thumb",
    "Final",
    "ProjectFolder",
]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def copy_if_missing(source: Path, target: Path) -> bool:
    if target.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


def build_state(project: Path, title: str, width: int, height: int, fps: int) -> dict:
    aspect = "9:16" if height > width else "1:1" if width == height else "16:9"
    return {
        "schema_version": "0.1",
        "skill_version": "0.1.0",
        "project_path": str(project.resolve()),
        "project_id": project.name,
        "title": title,
        "format": {"width": width, "height": height, "fps": fps, "aspect_ratio": aspect},
        "current_phase": "init",
        "phase_status": {
            "init": "completed",
            "plan": "not_started",
            "record": "not_started",
            "rough_cut": "not_started",
            "caption_correct": "not_started",
            "jianying_draft": "not_started",
            "assets": "not_started",
            "fine_cut": "not_started",
            "broll_plan": "not_started",
            "broll_generate": "not_started",
            "polish": "not_started",
            "delivery": "not_started",
        },
        "approval_pending": None,
        "artifacts": {},
        "broll": {
            "profile_confirmed": False,
            "opportunity_count": 0,
            "approved_count": 0,
            "generated_count": 0,
            "qa_passed_count": 0,
            "deferred_count": 0,
            "manifest_path": "Polished/broll-manifest.md",
        },
        "last_action_at": now_iso(),
        "initialized_at": now_iso(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a video production project")
    parser.add_argument("project", type=Path)
    parser.add_argument("--title", default=None)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--manuscript", type=Path, default=None)
    args = parser.parse_args()

    project = args.project.resolve()
    project.mkdir(parents=True, exist_ok=True)
    for relative in PROJECT_DIRS:
        (project / relative).mkdir(parents=True, exist_ok=True)

    state_path = project / ".video-workflow-state.json"
    if not state_path.exists():
        state = build_state(project, args.title or project.name, args.width, args.height, args.fps)
        if args.manuscript:
            state["artifacts"]["manuscript_source"] = str(args.manuscript.resolve())
        state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )

    copy_if_missing(TEMPLATES / "workflow.template.md", project / "WORKFLOW.md")
    copy_if_missing(TEMPLATES / "status.template.md", project / "STATUS.md")
    if args.manuscript:
        manuscript = args.manuscript.resolve()
        copy_if_missing(manuscript, project / "video scripts" / "manuscript.md")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.setdefault("artifacts", {})["manuscript_source"] = str(manuscript)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"project": str(project), "state": str(state_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
