"""Public-behavior tests for the PPT design source-materials seam."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from interview_mode import SessionStatus  # noqa: E402
from source_materials import SourceMaterialsSession  # noqa: E402


def test_source_materials_asks_at_most_one_high_value_question() -> None:
    session = SourceMaterialsSession.start(
        "季度业务复盘",
        [
            {
                "kind": "document",
                "name": "业务复盘文档",
                "reference": "materials/review.md",
                "summary": "记录了本季度的业务变化。",
                "facts": ["收入增长 20%"],
                "assets": ["收入趋势图"],
            },
            {
                "kind": "spreadsheet",
                "name": "指标表",
                "reference": "materials/metrics.xlsx",
                "facts": ["转化率 8%"],
            },
        ],
    )

    first = session.next_turn()

    assert session.status is SessionStatus.WAITING_FOR_ANSWER
    assert len(first.questions) == 1
    assert first.field == "goal"

    answered = session.answer("帮助管理层决定下季度资源投入")

    assert answered.questions == ()
    assert session.status is SessionStatus.READY_TO_DRAFT


def test_source_materials_render_inventory_primary_sources_and_gaps(tmp_path: Path) -> None:
    session = SourceMaterialsSession.start(
        "季度业务复盘",
        [
            {
                "kind": "document",
                "name": "业务复盘文档",
                "reference": "materials/review.md",
                "summary": "记录了本季度的业务变化。",
                "facts": ["收入增长 20%"],
            },
            {
                "kind": "link",
                "name": "产品公告",
                "reference": "https://example.com/announcement",
                "summary": "公开的产品变更说明。",
                "license_status": "用户授权引用",
            },
        ],
        goal="帮助管理层决定下季度资源投入",
        audience="管理层",
        external_sources=[
            {
                "source": "https://example.com/metrics",
                "date": "2026-09-18",
                "use": "核对行业指标",
                "uncertainty": "待用户确认",
            }
        ],
    )

    assert session.next_turn().questions == ()
    output = session.write_design(tmp_path)
    markdown = output.read_text(encoding="utf-8")
    frontmatter = markdown.split("---", 2)[1]
    assert "mode: source-materials" in frontmatter
    assert 'name: "季度业务复盘"' in frontmatter

    assert session.status is SessionStatus.AWAITING_CONFIRMATION
    for heading in (
        "## 叙事",
        "## 视觉 tokens",
        "## 来源",
        "## 逐页大纲",
        "## 待确认项",
    ):
        assert heading in markdown
    assert "mode: source-materials" in markdown
    assert "用户提供材料（主来源）" in markdown
    assert "业务复盘文档" in markdown
    assert "materials/review.md" in markdown
    assert "产品公告" in markdown
    assert "收入增长 20%" in markdown
    assert "可用视觉素材" in markdown
    assert "https://example.com/metrics" in markdown
    assert "2026-09-18" in markdown
    assert "核对行业指标" in markdown
    assert "待用户确认" in markdown
    assert "确认前不得生成 PPTX" in markdown


def test_source_materials_confirmation_gate_is_shared_with_interview_mode(
    tmp_path: Path,
) -> None:
    session = SourceMaterialsSession.start(
        "产品路线图",
        [
            {
                "kind": "outline",
                "name": "路线图提纲",
                "reference": "materials/roadmap.md",
                "facts": ["三项重点工作"],
                "assets": ["路线图图标"],
            }
        ],
        goal="让团队对齐优先级",
        audience="产品与工程团队",
    )
    session.write_design(tmp_path)

    session.confirm("我想再改一页")
    assert session.can_generate_pptx is False

    session.confirm("确认设计")
    assert session.status is SessionStatus.CONFIRMED
    assert session.can_generate_pptx is True
    assert "status: confirmed" in (tmp_path / "PPTDESIGN.md").read_text(encoding="utf-8")

    session.request_changes()
    assert session.status is SessionStatus.AWAITING_CONFIRMATION
    assert session.can_generate_pptx is False
    assert "status: awaiting-user-confirmation" in (tmp_path / "PPTDESIGN.md").read_text(encoding="utf-8")


def test_source_materials_asks_one_missing_design_discriminator() -> None:
    session = SourceMaterialsSession.start(
        "产品路线图",
        [{"kind": "outline", "name": "提纲", "reference": "roadmap.md"}],
        goal="让团队对齐优先级",
    )

    turn = session.next_turn()
    assert len(turn.questions) == 1
    assert turn.field == "audience"

    session.answer("产品与工程团队")
    assert session.next_turn().questions == ()


def test_invalid_materials_are_rejected() -> None:
    with pytest.raises(ValueError, match="reference"):
        SourceMaterialsSession.start(
            "缺少来源",
            [{"kind": "document", "name": "文档", "reference": ""}],
        )

    with pytest.raises(ValueError, match="scheme"):
        SourceMaterialsSession.start(
            "不安全来源",
            [{"kind": "link", "name": "链接", "reference": "javascript:alert(1)"}],
        )
