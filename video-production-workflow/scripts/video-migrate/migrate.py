#!/usr/bin/env python3
"""Migrate or bootstrap the workflow state without deleting project files."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


LATEST = "0.1"
ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "templates"
PHASES = [
    "init", "plan", "record", "rough_cut", "caption_correct", "jianying_draft",
    "assets", "fine_cut", "broll_plan", "broll_generate", "polish", "delivery",
]
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


def has_file(project: Path, relative: str) -> bool:
    return (project / relative).is_file()


def has_any_file(project: Path, relative_dir: str) -> bool:
    directory = project / relative_dir
    return directory.is_dir() and any(path.is_file() for path in directory.rglob("*"))


def detect_phase_status(project: Path) -> tuple[dict[str, str], list[str]]:
    """Infer only evidence-backed states; never treat an empty directory as complete."""
    evidence = {
        "plan": [
            "video scripts/storyboard.md",
            "video scripts/storyboard.json",
        ],
        "rough_cut": [
            "Rough/edl.json",
            "Rough/rough_cut_manifest.md",
            "Rough/preview.mp4",
        ],
        "caption_correct": [
            "Sub/caption_corrected.srt",
        ],
        "jianying_draft": [
            "Jianying-draft/draft_content.json",
            "Rough/jianying_draft_manifest.md",
        ],
        "assets": [
            "assets/licenses/media_asset_manifest.json",
        ],
        "fine_cut": [
            "Polished/fine_cut.mp4",
            "Sub/master.srt",
        ],
        "broll_plan": [
            "video scripts/broll-opportunity-analysis.md",
            "video scripts/broll-segment-plan.md",
            "video scripts/broll-style-decision.md",
        ],
        "broll_generate": [
            "Polished/broll-manifest.md",
        ],
        "polish": [
            "Polished/preview.mp4",
            "Polished/final_timeline_manifest.md",
        ],
        "delivery": [
            "Final/video_final.mp4",
            "Final/qa-report.md",
        ],
    }
    statuses = {phase: "not_started" for phase in PHASES}
    statuses["init"] = "completed"
    detected: list[str] = []

    for phase, files in evidence.items():
        present = [relative for relative in files if has_file(project, relative)]
        detected.extend(present)
        if len(present) == len(files):
            statuses[phase] = "completed"
        elif present:
            statuses[phase] = "in_progress"

    if has_any_file(project, "Raw"):
        statuses["record"] = "in_progress"
        detected.append("Raw/*")

    return statuses, detected


def timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate video workflow state")
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    project.mkdir(parents=True, exist_ok=True)
    for relative in PROJECT_DIRS:
        (project / relative).mkdir(parents=True, exist_ok=True)
    state_path = project / ".video-workflow-state.json"

    had_state = state_path.exists()
    if had_state:
        backup = state_path.with_name(f".video-workflow-state.json.bak-{timestamp()}")
        shutil.copy2(state_path, backup)
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid state file: {state_path}: {exc}") from exc
    else:
        backup = None
        state = {
            "schema_version": LATEST,
            "skill_version": "0.1.0",
            "project_path": str(project),
            "project_id": project.name,
            "title": project.name,
            "format": {"width": 1920, "height": 1080, "fps": 30, "aspect_ratio": "16:9"},
            "current_phase": "init",
            "phase_status": {},
            "approval_pending": None,
            "artifacts": {},
            "broll": {},
        }

    detected_status, detected_artifacts = detect_phase_status(project)
    phase_status = state.setdefault("phase_status", {})
    for phase in PHASES:
        current = phase_status.get(phase)
        if current in (None, "not_started"):
            phase_status[phase] = detected_status[phase]
    state.setdefault("schema_version", LATEST)
    state.setdefault("skill_version", "0.1.0")
    state.setdefault("project_path", str(project))
    state.setdefault("project_id", project.name)
    state.setdefault("title", project.name)
    state.setdefault(
        "format",
        {"width": 1920, "height": 1080, "fps": 30, "aspect_ratio": "16:9"},
    )
    state.setdefault("approval_pending", None)
    state.setdefault("artifacts", {})
    state.setdefault("broll", {})
    state["artifacts"]["migration_detected"] = detected_artifacts
    state["schema_version"] = LATEST
    if not had_state or state.get("current_phase") in (None, "init"):
        state["current_phase"] = next(
            (phase for phase in PHASES if phase_status[phase] != "completed"),
            "delivery",
        )
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status_path = project / "STATUS.md"
    if not status_path.exists():
        template = TEMPLATES / "status.template.md"
        if template.exists():
            shutil.copy2(template, status_path)
    workflow_path = project / "WORKFLOW.md"
    if not workflow_path.exists():
        template = TEMPLATES / "workflow.template.md"
        if template.exists():
            shutil.copy2(template, workflow_path)

    report = project / "Rough" / "migrations" / f"migration-{timestamp()}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "# Workflow Migration\n\n"
        f"- Project: `{project}`\n"
        f"- Target schema: `{LATEST}`\n"
        f"- State backup: `{backup or 'created from directory scan'}`\n\n"
        "Detected artifacts:\n"
        + "\n".join(f"- `{item}`" for item in detected_artifacts)
        + "\n\n目录和已有媒体未删除。请运行 `scripts/video-status/status.py` 检查阶段状态。\n",
        encoding="utf-8",
    )
    print(json.dumps({"state": str(state_path), "report": str(report)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
