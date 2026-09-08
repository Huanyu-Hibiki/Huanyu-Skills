#!/usr/bin/env python3
"""上下文预算棘轮 + tools/context.py 行为回归。

预算数字定义在 BUDGETS（见 MAINTENANCE.md）：**棘轮语义——只许收紧，不许放松**。
放松任何预算都必须在 MAINTENANCE.md 记录理由，否则本测试红。

运行（无需 pytest，纯 stdlib）:
  python -m unittest discover -s tests -v
或直接:
  python tests/test_context_budget.py
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent
TOOLS = PKG_ROOT / "tools" / "context.py"

# ── 预算棘轮（bytes）。基线 = 2026-09-07 现状最大值 + 少量余量 ──
BUDGETS = {
    "main_skill": 31_000,      # 当前 SKILL.md ≈ 30,057
    "sub_skill": 18_000,       # 当前最大 oracle-init ≈ 17,455
    "protocol": 15_000,        # 当前最大 state-management ≈ 13,743
    "runtime_session": 78_000, # 主 SKILL + 最大子 skill + 两份最大协议 ≈ 73.7K
}


def size(path: Path) -> int:
    return path.stat().st_size


class TestBudgetRatchet(unittest.TestCase):
    def test_main_skill_budget(self):
        self.assertLessEqual(size(PKG_ROOT / "SKILL.md"), BUDGETS["main_skill"])

    def test_sub_skill_budgets(self):
        offenders = [
            f"{p.parent.name}={size(p)}B"
            for p in sorted((PKG_ROOT / "skills").glob("*/SKILL.md"))
            if size(p) > BUDGETS["sub_skill"]
        ]
        self.assertEqual(offenders, [], f"超预算子 skill: {offenders}")

    def test_protocol_budgets(self):
        offenders = [
            f"{p.name}={size(p)}B"
            for p in sorted((PKG_ROOT / "shared-references").glob("*.md"))
            if size(p) > BUDGETS["protocol"]
        ]
        self.assertEqual(offenders, [], f"超预算协议: {offenders}")

    def test_runtime_session_budget(self):
        main = size(PKG_ROOT / "SKILL.md")
        max_sub = max(size(p) for p in (PKG_ROOT / "skills").glob("*/SKILL.md"))
        protocols = sorted(
            (size(p) for p in (PKG_ROOT / "shared-references").glob("*.md")), reverse=True
        )
        worst = main + max_sub + sum(protocols[:2])  # 单任务最多读两份协议
        self.assertLessEqual(
            worst, BUDGETS["runtime_session"],
            f"运行时最坏读取 {worst}B（主 {main} + 子 {max_sub} + 协议 {protocols[:2]}）",
        )


def run_context(root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOLS), str(root), *extra],
        capture_output=True, encoding="utf-8",
    )


def write_state(root: Path, state: dict) -> None:
    (root / ".oracle-state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fixture_state(schema: str = "1.0") -> dict:
    return {
        "schema_version": schema,
        "mode": "cold-start",
        "content_form": "opinion-video",
        "project_root": "<tmp>",
        "platforms": ["bilibili", "douyin"],
        "target_publish_cadence_days": 2,
        "plan_type": "dual",
        "tracks": {"definitions": [
            {"id": "reach", "funnel_layer": "破圈", "name": "破圈轨",
             "rubric_section": "rubric_notes.md#track-reach", "rubric_version": "v0",
             "review_skill": "oracle-who-for", "success_metrics": ["播放"],
             "retro_windows_days": [3], "mix_ratio": 0.4},
            {"id": "convert", "funnel_layer": "转化", "name": "转化轨",
             "rubric_section": "rubric_notes.md#track-convert", "rubric_version": "v0",
             "review_skill": "oracle-open-source", "success_metrics": ["咨询"],
             "retro_windows_days": [3, 7, 30], "mix_ratio": 0.6},
        ], "mix_ratio_note": ""},
        "calibration_samples_by_track": {"reach": 2, "convert": 0},
        "shoots": [],
        "pending_retros": [],
    }


class TestContextTool(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_needs_init_exit_code(self):
        proc = run_context(self.root)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("oracle-init", proc.stdout)

    def test_corrupt_state_exit_code(self):
        (self.root / ".oracle-state.json").write_text("{not json", encoding="utf-8")
        proc = run_context(self.root)
        self.assertEqual(proc.returncode, 3)

    def test_utf8_bom_state_accepted(self):
        # Windows 记事本 / PowerShell 写出的带 BOM 文件不算损坏
        path = self.root / ".oracle-state.json"
        path.write_bytes(b"\xef\xbb\xbf" + json.dumps(fixture_state(), ensure_ascii=False).encode("utf-8"))
        proc = run_context(self.root, "--task", "status")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("破圈轨", proc.stdout)

    def test_summary_within_budget(self):
        write_state(self.root, fixture_state())
        proc = run_context(self.root, "--task", "predict", "--track", "reach")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.encode("utf-8")
        self.assertLessEqual(len(out), 6000)
        self.assertIn("破圈轨", proc.stdout)
        self.assertIn("🟠 低", proc.stdout)          # reach 样本 2 → 派生表
        self.assertIn("当前约束: none", proc.stdout)  # 缺字段兜底，不崩
        self.assertIn("prediction-anatomy", proc.stdout)

    def test_schema_mismatch_warns(self):
        write_state(self.root, fixture_state(schema="0.9"))
        proc = run_context(self.root, "--task", "status")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("oracle-migrate", proc.stdout)

    def test_stage_constraint_shown(self):
        state = fixture_state()
        state["stage_constraint"] = {"value": "capacity_limited", "basis": "cadence 目标与可投入差距大", "updated_at": "2026-09-01T00:00:00+08:00"}
        write_state(self.root, state)
        proc = run_context(self.root, "--task", "seed")
        self.assertIn("capacity_limited", proc.stdout)
        self.assertIn("cadence 目标与可投入差距大", proc.stdout)

    def test_unknown_task_falls_back(self):
        write_state(self.root, fixture_state())
        proc = run_context(self.root, "--task", "nonexistent")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("无专属读取清单", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
