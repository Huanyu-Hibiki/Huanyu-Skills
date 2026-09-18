"""Source-materials discovery seam for the ppt-design skill."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from interview_mode import InterviewTurn, SessionStatus
from common import (
    atomic_write_text,
    clean_text,
    is_explicit_confirmation,
    markdown_inline,
    persist_design_status,
    safe_output_dir,
)


class SourceMaterialsSession:
    """Turn a material inventory into a confirmable design document.

    At most one high-value follow-up is asked. It prefers the goal, then a
    missing audience or usage context. Other missing fields remain explicit
    gaps in the design document instead of triggering a chain of questions.
    """

    def __init__(
        self,
        topic: str,
        materials: list[dict[str, Any]],
        *,
        goal: str | None = None,
        audience: str | None = None,
        context: str | None = None,
        core_message: str | None = None,
        external_sources: list[dict[str, Any]] | None = None,
    ) -> None:
        if not isinstance(topic, str):
            raise TypeError("topic must be a string")
        self.topic = clean_text(topic, "topic", 200)
        if not isinstance(materials, list) or not materials:
            raise ValueError("materials must be a non-empty list")
        if len(materials) > 100:
            raise ValueError("materials contains too many entries")
        self.materials = [self._validate_material(item) for item in materials]
        self.goal = clean_text(goal, "goal", 5000) if goal is not None else None
        self.audience = clean_text(audience, "audience", 500) if audience is not None else None
        self.context = clean_text(context, "context", 500) if context is not None else None
        self.core_message = (
            clean_text(core_message, "core_message", 2000)
            if core_message is not None
            else None
        )
        if external_sources is not None and not isinstance(external_sources, list):
            raise ValueError("external_sources must be a list")
        if external_sources is not None and len(external_sources) > 100:
            raise ValueError("external_sources contains too many entries")
        self.external_sources = [
            self._validate_external_source(item)
            for item in (external_sources or [])
        ]
        self._design_path: Path | None = None
        self.status = SessionStatus.WAITING_FOR_ANSWER if self._missing_follow_up() else SessionStatus.READY_TO_DRAFT

    @classmethod
    def start(
        cls,
        topic: str,
        materials: list[dict[str, Any]],
        *,
        goal: str | None = None,
        audience: str | None = None,
        context: str | None = None,
        core_message: str | None = None,
        external_sources: list[dict[str, Any]] | None = None,
    ) -> "SourceMaterialsSession":
        return cls(
            topic,
            materials,
            goal=goal,
            audience=audience,
            context=context,
            core_message=core_message,
            external_sources=external_sources,
        )

    def next_turn(self) -> InterviewTurn:
        if self.status is SessionStatus.WAITING_FOR_ANSWER:
            field, question = self._follow_up_question()
            return InterviewTurn(
                field,
                (question,),
                True,
            )
        return InterviewTurn(None, (), False)

    @property
    def can_generate_pptx(self) -> bool:
        return self.status is SessionStatus.CONFIRMED

    def confirm(self, message: str) -> None:
        if self.status is not SessionStatus.AWAITING_CONFIRMATION:
            raise RuntimeError("write and display PPTDESIGN.md before confirming it")
        if is_explicit_confirmation(message):
            assert self._design_path is not None
            persist_design_status(self._design_path, "confirmed")
            self.status = SessionStatus.CONFIRMED

    def request_changes(self) -> None:
        """Reopen the design contract so edits require confirmation again."""

        if self.status is not SessionStatus.CONFIRMED or self._design_path is None:
            raise RuntimeError("only a confirmed design can be reopened")
        persist_design_status(self._design_path, "awaiting-user-confirmation")
        self.status = SessionStatus.AWAITING_CONFIRMATION

    def answer(self, answer: str) -> InterviewTurn:
        if self.status is not SessionStatus.WAITING_FOR_ANSWER:
            raise RuntimeError("source materials are not waiting for an answer")
        if not isinstance(answer, str):
            raise TypeError("answer must be a string")
        if not answer.strip():
            field, question = self._follow_up_question()
            return InterviewTurn(field, (f"为了继续，请只回答一个信息点：{question}",), True)
        field, _ = self._follow_up_question()
        value = clean_text(answer, field, 5000)
        if field == "goal":
            self.goal = value
        elif field == "audience":
            self.audience = value
        else:
            self.context = value
        self.status = SessionStatus.READY_TO_DRAFT
        return self.next_turn()

    def _missing_follow_up(self) -> bool:
        return not bool(self.goal) or (bool(self.goal) and not self.audience and not self.context)

    def _follow_up_question(self) -> tuple[str, str]:
        if not self.goal:
            return "goal", "这份 PPT 最希望帮助观众理解或决定什么？"
        if not self.audience:
            return "audience", "这份 PPT 的主要观众是谁？"
        return "context", "PPT 将在什么场景使用？"

    def write_design(self, output_dir: Path, *, allowed_root: Path | None = None) -> Path:
        if self.status not in {
            SessionStatus.READY_TO_DRAFT,
            SessionStatus.AWAITING_CONFIRMATION,
        }:
            raise RuntimeError("answer the source-material question first")
        output_dir = safe_output_dir(output_dir, allowed_root=allowed_root)
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / "PPTDESIGN.md"
        if target.is_symlink():
            raise ValueError("PPTDESIGN.md must not be a symbolic link")
        atomic_write_text(target, self._render_design())
        self._design_path = target
        self.status = SessionStatus.AWAITING_CONFIRMATION
        return target

    def _render_design(self) -> str:
        topic = markdown_inline(self.topic)
        topic_yaml = json.dumps(self.topic, ensure_ascii=False)
        materials = "\n".join(self._render_material(item) for item in self.materials)
        external = "\n".join(self._render_external(item) for item in self.external_sources)
        if not external:
            external = "- 暂无外部来源；如需补充事实，Agent 必须记录来源、日期与用途"
        pages = "\n".join(
            f"### 第 {number} 页\n"
            "- 标题：待确认\n"
            f"- 核心结论：围绕“{markdown_inline(self.goal or '待补充')}”展开\n"
            "- 内容：从用户材料中提取并核对\n"
            "- 版式：待确认\n"
            "- 可编辑对象：文本框和形状\n"
            "- 素材槽位：使用已列出的用户素材或明确标记缺口\n"
            "- 演讲备注：待确认\n"
            for number in range(1, 9)
        )
        gaps = self._gaps()
        return f"""---
name: {topic_yaml}
mode: source-materials
status: awaiting-user-confirmation
editable_output: true
---

# PPTDESIGN: {topic}

## 叙事

- 主题：{topic}
- 目标：{markdown_inline(self.goal or '待用户补充')}
- 受众：{markdown_inline(self.audience or '待用户补充')}
- 使用场景：{markdown_inline(self.context or '待用户补充')}
- 核心信息：{markdown_inline(self.core_message or self.goal or '待用户补充')}
- 证据：来自用户材料中已列出的事实，缺失项在逐页设计前标记为待提取或待核对
- 用户提供材料（主来源）：{len(self.materials)} 项

## 视觉 tokens

- 画幅：16:9（默认，可在确认时调整）
- 网格：12 列；外边距与间距采用 8px 基准
- 颜色：待从品牌规范或材料中确认主色、辅色与中性色
- 字体：选择覆盖目标语言的可用字体
- 间距：8px 基准，标题、正文和图表采用一致的垂直节奏
- 形状：待确认圆角、描边和装饰形状规则
- 图表规则：数据优先使用可编辑图表或表格，标明单位和来源
- 页脚规则：页码、来源和备注位置待确认，不能压住内容

## 来源

### 用户提供材料（主来源）

{materials}

### 外部来源与补充

{external}

## 逐页大纲

{pages}

## 可访问性与验证

- 可访问性：正文保持可读字号与对比度；图片补充替代文字或图注；图表标注单位、来源和关键结论
- 可编辑性：文字、表格、图表和形状必须保持原生对象；照片和插图单独作为图片资产
- 验证清单：检查文字溢出、对象重叠、网格对齐、来源完整性、图片裁切，并打开输出 PPTX 验证

## 待确认项

{gaps}
- 用户必须确认叙事、视觉 tokens 与逐页大纲
- 确认前不得生成 PPTX
"""

    def _gaps(self) -> str:
        gaps: list[str] = []
        if not self.audience:
            gaps.append("- 受众未提供")
        if not self.context:
            gaps.append("- 使用场景未提供")
        if not self.core_message:
            gaps.append("- 核心信息未单独提供，将先以目标作为工作假设")
        if any(not item.get("facts") for item in self.materials):
            gaps.append("- 部分材料没有结构化事实，需要 Agent 阅读并核对")
        if not any(item.get("assets") for item in self.materials):
            gaps.append("- 可用视觉素材未提供")
        if any(
            not all(item.get(key) for key in ("date", "use", "license_status", "uncertainty"))
            for item in self.external_sources
        ):
            gaps.append("- 部分外部来源缺少日期、用途、许可或不确定性记录")
        if not gaps:
            gaps.append("- 无新增材料缺口；仍需用户确认设计")
        return "\n".join(gaps)

    @staticmethod
    def _validate_material(item: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise ValueError("each material must be an object")
        kind = clean_text(item.get("kind", ""), "kind", 50)
        name = clean_text(item.get("name", ""), "name", 200)
        reference = clean_text(item.get("reference", ""), "reference", 2000)
        _validate_reference(reference, "reference")
        for key in ("facts", "assets"):
            value = item.get(key, [])
            if value is None:
                value = []
            if not isinstance(value, list):
                raise ValueError(f"{key} must be a list")
            if len(value) > 100:
                raise ValueError(f"{key} contains too many entries")
            for entry in value:
                clean_text(entry, key, 1000)
        for key, limit in (
            ("summary", 5000),
            ("license_status", 500),
        ):
            if key in item and item[key] is not None:
                clean_text(item[key], key, limit)
        result = copy.deepcopy(dict(item))
        result.update(kind=kind, name=name, reference=reference)
        result["facts"] = list(item.get("facts") or [])
        result["assets"] = list(item.get("assets") or [])
        if item.get("content") and not item.get("summary"):
            result["summary"] = str(item["content"])[:500]
        return result

    @staticmethod
    def _validate_external_source(item: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise ValueError("each external source must be an object")
        source = clean_text(item.get("source", ""), "source", 2000)
        _validate_reference(source, "source", require_http=True)
        for key, limit in (
            ("date", 100),
            ("use", 1000),
            ("license_status", 500),
            ("uncertainty", 1000),
        ):
            if key in item and item[key] is not None:
                clean_text(item[key], key, limit)
        result = copy.deepcopy(dict(item))
        result["source"] = source
        return result

    @staticmethod
    def _render_material(item: dict[str, Any]) -> str:
        facts = ", ".join(markdown_inline(str(fact)) for fact in item.get("facts", []))
        assets = ", ".join(markdown_inline(str(asset)) for asset in item.get("assets", []))
        return (
            f"- **{markdown_inline(item['name'])}** ({markdown_inline(item['kind'])})\n"
            f"  - 位置：{markdown_inline(item['reference'])}\n"
            f"  - 摘要：{markdown_inline(str(item.get('summary', '待读取')))}\n"
            f"  - 事实：{facts or '待提取'}\n"
            f"  - 可用视觉素材：{assets or '无'}\n"
            f"  - 许可：{markdown_inline(str(item.get('license_status', '待确认')))}"
        )

    @staticmethod
    def _render_external(item: dict[str, Any]) -> str:
        return (
            f"- 来源：{markdown_inline(item['source'])}；"
            f"日期：{markdown_inline(str(item.get('date', '待记录')))}；"
            f"用途：{markdown_inline(str(item.get('use', '待记录')))}；"
            f"许可：{markdown_inline(str(item.get('license_status', '待确认')))}；"
            f"不确定性：{markdown_inline(str(item.get('uncertainty', '待用户确认')))}"
        )


def _validate_reference(reference: str, label: str, *, require_http: bool = False) -> None:
    scheme_match = re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", reference)
    if not scheme_match or re.match(r"^[A-Za-z]:[\\/]", reference):
        if require_http:
            raise ValueError(f"{label} must be an HTTP(S) URL")
        return
    parsed = urlsplit(reference)
    if parsed.scheme.lower() not in {"http", "https"} or (require_http and not parsed.netloc):
        raise ValueError(f"{label} has an unsupported URL scheme")
    if parsed.username or parsed.password:
        raise ValueError(f"{label} must not contain URL credentials")
    sensitive = {
        "token", "access_token", "password", "passwd", "secret", "client_secret",
        "key", "api_key", "auth", "authorization", "signature", "credential", "session",
    }
    query_keys = parse_qsl(parsed.query, keep_blank_values=True)
    fragment_keys = parse_qsl(parsed.fragment, keep_blank_values=True)
    if any(key.lower() in sensitive for key, _ in (*query_keys, *fragment_keys)):
        raise ValueError(f"{label} must not contain credential query parameters")
