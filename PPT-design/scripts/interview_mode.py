"""Stateful topic-interview seam for the ppt-design skill.

The class in this module is intentionally small and dependency-free.  The
skill instructions provide the conversational policy; this module makes the
two important invariants executable: one question per turn and an explicit
confirmation gate before PPTX generation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import re
from typing import Final

from common import (
    atomic_write_text,
    clean_text,
    is_explicit_confirmation,
    markdown_inline,
    persist_design_status,
    safe_output_dir,
)


class SessionStatus(str, Enum):
    WAITING_FOR_ANSWER = "waiting_for_answer"
    READY_TO_DRAFT = "ready_to_draft"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"


@dataclass(frozen=True)
class InterviewTurn:
    """One public conversational turn.

    ``questions`` contains zero or one item by contract.  ``field`` identifies
    the answer slot without exposing the session's mutable implementation.
    """

    field: str | None
    questions: tuple[str, ...]
    answer_required: bool


_QUESTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("goal", "这份 PPT 最希望观众理解或采取的一个行动是什么？"),
    ("audience", "这份 PPT 的主要观众是谁？"),
    ("context", "PPT 将在什么场景使用？"),
    ("duration", "你预计用多长时间讲完这份 PPT？"),
    ("message", "你希望整份 PPT 留下的核心观点是什么？"),
    ("evidence", "哪些事实、数据、案例或素材必须保留？"),
    ("length", "你希望大约制作多少页？"),
    ("style", "你偏好的视觉方向是什么？"),
)

class InterviewSession:
    """Topic interview with a one-question-at-a-time confirmation gate."""

    def __init__(self, topic: str) -> None:
        if not isinstance(topic, str):
            raise TypeError("topic must be a string")
        topic = clean_text(topic, "topic", 200)
        if not topic:
            raise ValueError("topic must not be blank")
        self.topic = topic
        self._answers: dict[str, str] = {}
        self._index = 0
        self._design_path: Path | None = None
        self.status = SessionStatus.WAITING_FOR_ANSWER

    @classmethod
    def start(cls, topic: str) -> "InterviewSession":
        return cls(topic)

    @property
    def current_field(self) -> str | None:
        if self._index >= len(_QUESTIONS):
            return None
        return _QUESTIONS[self._index][0]

    @property
    def can_generate_pptx(self) -> bool:
        return self.status is SessionStatus.CONFIRMED

    def next_turn(self) -> InterviewTurn:
        """Return the current question without advancing state."""

        if self.status is SessionStatus.WAITING_FOR_ANSWER:
            field, question = _QUESTIONS[self._index]
            return InterviewTurn(field, (question,), True)
        return InterviewTurn(None, (), False)

    def answer(self, answer: str) -> InterviewTurn:
        """Record one answer; blank input leaves the same question active."""

        if self.status is not SessionStatus.WAITING_FOR_ANSWER:
            raise RuntimeError("the interview is not waiting for an answer")
        if not isinstance(answer, str):
            raise TypeError("answer must be a string")
        cleaned = answer.strip()
        if not cleaned:
            field = self.current_field
            assert field is not None
            return InterviewTurn(
                field,
                (f"为了继续，请只回答一个信息点：{_QUESTIONS[self._index][1]}",),
                True,
            )
        cleaned = clean_text(cleaned, "answer", 5000)

        field = self.current_field
        assert field is not None  # guarded by WAITING_FOR_ANSWER
        self._answers[field] = cleaned
        self._index += 1
        if self._index == len(_QUESTIONS):
            self.status = SessionStatus.READY_TO_DRAFT
        return self.next_turn()

    def write_design(self, output_dir: Path) -> Path:
        """Write the confirmable ``PPTDESIGN.md`` contract."""

        if self.status not in {SessionStatus.READY_TO_DRAFT, SessionStatus.AWAITING_CONFIRMATION}:
            raise RuntimeError("complete the interview before writing the design")
        output_dir = safe_output_dir(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / "PPTDESIGN.md"
        if target.is_symlink():
            raise ValueError("PPTDESIGN.md must not be a symbolic link")
        atomic_write_text(target, self._render_design())
        self._design_path = target
        self.status = SessionStatus.AWAITING_CONFIRMATION
        return target

    def confirm(self, message: str) -> None:
        """Open the PPTX gate only on explicit confirmation language."""

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

    def _render_design(self) -> str:
        answer_lines = "\n".join(
            f"- **{field}**：{markdown_inline(self._answers.get(field, '待补充'))}"
            for field, _ in _QUESTIONS
        )
        outline = "\n".join(
            "### 第 {number} 页\n"
            "- 标题：待确认\n"
            "- 核心结论：根据“{message}”展开\n"
            "- 内容：待根据来源与证据填充\n"
            "- 版式：待确认\n"
            "- 可编辑对象：文本框和形状\n"
            "- 素材槽位：待确认\n"
            "- 演讲备注：待确认\n".format(
                number=number,
                message=markdown_inline(self._answers["message"]),
            )
            for number in range(1, self._slide_count() + 1)
        )
        topic = json.dumps(self.topic, ensure_ascii=False)
        topic_markdown = markdown_inline(self.topic)
        return f"""---
name: {topic}
mode: topic-interview
status: awaiting-user-confirmation
editable_output: true
---

# PPTDESIGN: {topic_markdown}

## 叙事

- 主题：{topic_markdown}
- 采访回答：
{answer_lines}

## 视觉 tokens

- 画幅：16:9（默认，可在确认时调整）
- 网格：12 列；外边距与间距采用 8px 基准
- 颜色：待从主题、品牌或材料中确认主色、辅色与中性色
- 字体：优先使用覆盖全部目标语言的可用字体
- 间距：8px 基准，标题、正文和图表采用一致的垂直节奏
- 形状：待确认圆角、描边和装饰形状规则
- 图表规则：数据优先使用可编辑图表或表格，标明单位和来源
- 页脚规则：页码、来源和备注位置待确认，不能压住内容
- 对象规则：文字、表格、图表和形状保持 PowerPoint 原生可编辑

## 来源

- 用户访谈回答：以上访谈字段
- 外部来源：待 Agent 在缺少事实或素材时检索并记录来源、日期与用途
- 许可状态：待确认

## 逐页大纲

{outline}

## 待确认项

- 上述叙事、视觉 tokens 与逐页大纲需待用户确认
- 外部检索事实与素材来源需在生成前补齐
- 确认前不得生成 PPTX
"""

    def _slide_count(self) -> int:
        raw = self._answers.get("length", "")
        match = re.search(r"(?<!\d)(\d{1,2})(?!\d)", raw)
        count = int(match.group(1)) if match else 8
        return max(3, min(count, 30))
