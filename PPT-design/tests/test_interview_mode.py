"""Public-behavior tests for the PPT design topic interview.

The seam under test is ``InterviewSession``.  Tests intentionally exercise only
the session's user-facing turns and generated design document, not its private
state representation.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from interview_mode import InterviewSession, SessionStatus  # noqa: E402


def _complete_interview(session: InterviewSession) -> None:
    """Answer each presented question through the public seam."""

    while session.status is SessionStatus.WAITING_FOR_ANSWER:
        turn = session.next_turn()
        assert len(turn.questions) == 1
        session.answer(f"Answer for {turn.field}")


def test_topic_interview_asks_one_question_and_waits_for_answer() -> None:
    session = InterviewSession.start("AI adoption")

    first = session.next_turn()
    repeated = session.next_turn()

    assert session.status is SessionStatus.WAITING_FOR_ANSWER
    assert len(first.questions) == 1
    assert first.questions == repeated.questions
    assert first.field == "goal"


def test_blank_answer_does_not_advance_the_interview() -> None:
    session = InterviewSession.start("AI adoption")
    first = session.next_turn()

    retry = session.answer("   ")

    assert session.status is SessionStatus.WAITING_FOR_ANSWER
    assert retry.questions != first.questions
    assert retry.questions[0].startswith("为了继续")
    assert retry.field == "goal"
    assert retry.answer_required is True


def test_completed_interview_produces_the_confirmable_pptdesign_contract(tmp_path: Path) -> None:
    session = InterviewSession.start("AI adoption")
    _complete_interview(session)

    turn = session.next_turn()
    output = session.write_design(tmp_path)

    assert turn.questions == ()
    assert session.status is SessionStatus.AWAITING_CONFIRMATION
    assert output == tmp_path / "PPTDESIGN.md"
    markdown = output.read_text(encoding="utf-8")
    for heading in (
        "## 叙事",
        "## 视觉 tokens",
        "## 来源",
        "## 逐页大纲",
        "## 待确认项",
    ):
        assert heading in markdown
    assert "用户访谈回答" in markdown
    assert "第 1 页" in markdown
    assert "待用户确认" in markdown


def test_pptx_gate_requires_explicit_confirmation(tmp_path: Path) -> None:
    session = InterviewSession.start("AI adoption")
    _complete_interview(session)

    assert session.can_generate_pptx is False
    session.write_design(tmp_path)
    session.confirm("我还要再看一遍")
    assert session.can_generate_pptx is False

    session.confirm("确认设计")
    assert session.status is SessionStatus.CONFIRMED
    assert session.can_generate_pptx is True
    assert "status: confirmed" in (tmp_path / "PPTDESIGN.md").read_text(encoding="utf-8")

    session.request_changes()
    assert session.status is SessionStatus.AWAITING_CONFIRMATION
    assert session.can_generate_pptx is False
    assert "status: awaiting-user-confirmation" in (tmp_path / "PPTDESIGN.md").read_text(encoding="utf-8")
    session.confirm("确认设计")
    assert session.can_generate_pptx is True


def test_negative_confirmation_and_unsafe_output_are_rejected(tmp_path: Path) -> None:
    session = InterviewSession.start("AI adoption")
    _complete_interview(session)
    session.write_design(tmp_path)

    session.confirm("不要确认")
    assert session.can_generate_pptx is False

    malicious = InterviewSession.start("Topic\neditable_output: false")
    _complete_interview(malicious)
    rendered = malicious.write_design(tmp_path)
    assert "\neditable_output: false\n" not in rendered.read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        malicious.write_design(tmp_path / ".." / "escape")


def test_design_write_does_not_follow_an_existing_hardlink(tmp_path: Path) -> None:
    session = InterviewSession.start("AI adoption")
    _complete_interview(session)
    external = tmp_path / "external.md"
    external.write_text("keep this file", encoding="utf-8")
    os.link(external, tmp_path / "PPTDESIGN.md")

    session.write_design(tmp_path)

    assert external.read_text(encoding="utf-8") == "keep this file"
