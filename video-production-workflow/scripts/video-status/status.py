#!/usr/bin/env python3
"""Render a read-only status summary for a video project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_state(project: Path) -> dict:
    path = project / ".video-workflow-state.json"
    if not path.exists():
        raise SystemExit(f"state file not found: {path}; run init_project.py first")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid state file: {path}: {exc}") from exc


def artifact_status(project: Path, relative: str) -> bool:
    return (project / relative).exists()


def build_report(project: Path, state: dict) -> dict:
    phase_status = state.get("phase_status", {})
    checks = {
        "storyboard": artifact_status(project, "video scripts/storyboard.json"),
        "rough_cut": artifact_status(project, "Rough/edl.json"),
        "caption": artifact_status(project, "Sub/caption_corrected.srt"),
        "fine_cut": artifact_status(project, "Sub/master.srt"),
        "asset_manifest": artifact_status(project, "assets/licenses/media_asset_manifest.json"),
        "broll_plan": artifact_status(project, "video scripts/broll-opportunity-analysis.md"),
        "broll_manifest": artifact_status(project, "Polished/broll-manifest.md"),
        "final": artifact_status(project, "Final/video_final.mp4"),
    }
    return {
        "project": str(project),
        "title": state.get("title", project.name),
        "current_phase": state.get("current_phase", "unknown"),
        "phase_status": phase_status,
        "approval_pending": state.get("approval_pending"),
        "checks": checks,
        "broll": state.get("broll", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Show video production status")
    parser.add_argument("project", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    project = args.project.resolve()
    report = build_report(project, load_state(project))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"视频制作状态：{report['title']}")
    print(f"项目：{report['project']}")
    print(f"当前阶段：{report['current_phase']}")
    print("\n阶段：")
    for name, status in report["phase_status"].items():
        print(f"  {name}: {status}")
    print("\n交接文件：")
    for name, present in report["checks"].items():
        print(f"  {'✅' if present else '⬜'} {name}")
    if report["approval_pending"]:
        print(f"\n等待审批：{report['approval_pending']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
