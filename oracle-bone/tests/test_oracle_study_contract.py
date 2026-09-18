#!/usr/bin/env python3
"""oracle-study 的可观察行为契约测试。

这些测试只读取 skill 公共说明，验证模式边界、证据约束和兼容路由；
不耦合文档内部的章节顺序或实现细节。
"""

import re
import unittest
from pathlib import Path


PKG_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = PKG_ROOT / "skills" / "oracle-study" / "SKILL.md"


class TestOracleStudyContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL_PATH.read_text(encoding="utf-8")

    def test_declares_single_entry_and_three_modes(self):
        self.assertRegex(self.skill, r"(?m)^name:\s*oracle-study\s*$")
        for mode in ("benchmark", "practice", "dual"):
            self.assertRegex(self.skill, rf"(?m)^#{{2,3}}\s+{mode}\b")

    def test_benchmark_keeps_qualitative_evidence_without_weight_mutation(self):
        self.assertRegex(self.skill, r"3[–-]10 个样本")
        for marker in ("表现数据", "用户印象", "定性"):
            self.assertIn(marker, self.skill)
        self.assertRegex(self.skill, r"不能直接.*rubric.*权重|不直接.*rubric.*权重")

    def test_practice_requires_user_learning_loop_and_three_gates(self):
        for marker in ("复述", "质疑", "迁移", "最小实践", "知识卡片"):
            self.assertIn(marker, self.skill)
        for gate in ("V1", "V2", "V3"):
            self.assertIn(gate, self.skill)
        self.assertRegex(self.skill, r"落到用户.*轨道|用户.*轨道.*落点")

    def test_dual_shares_archive_but_keeps_evidence_chains_separate(self):
        self.assertIn("study/<对象>/samples/<content-id>/", self.skill)
        self.assertRegex(self.skill, r"推荐.*深拆.*用户确认|用户确认.*深拆")
        self.assertRegex(self.skill, r"统计关联.*不.*复制|不.*复制.*统计关联")
        self.assertRegex(
            self.skill,
            re.compile(r"benchmark.*practice|practice.*benchmark", re.S),
        )

    def test_packaging_and_motion_requests_delegate_to_vpw(self):
        self.assertIn("video-production-workflow", self.skill)
        self.assertRegex(self.skill, r"包装.*动效.*(?:交给|路由).*video-production-workflow")
        self.assertRegex(self.skill, r"不属于.*oracle-study|不在.*oracle-study")

    def test_legacy_learning_names_are_read_only_compatibility_aliases(self):
        for legacy_name in ("oracle-learn-from", "oracle-apprentice"):
            self.assertIn(legacy_name, self.skill)
        self.assertRegex(self.skill, r"旧.*(?:只读|可读).*兼容")
        self.assertRegex(self.skill, r"迁移.*确认|确认.*迁移")

    def test_legacy_entries_are_not_installable_skills(self):
        aliases = {"oracle-learn-from", "oracle-apprentice", "oracle-cover-analyze"}
        skill_dirs = {
            path.parent.name
            for path in (PKG_ROOT / "skills").glob("*/SKILL.md")
            if path.parent.name not in aliases
        }
        self.assertEqual(len(skill_dirs), 26)
        self.assertIn("oracle-study", skill_dirs)
        for legacy_name in ("oracle-learn-from", "oracle-apprentice"):
            self.assertTrue((PKG_ROOT / "skills" / legacy_name / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
