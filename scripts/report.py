#!/usr/bin/env python3
"""skill-master HTML report renderer (task 14).

Renders ``templates/report.html`` by pure string replacement — the frozen
contract lives in the template's header comment (lines 2-57):

  CLI: python scripts/report.py --draft <analysis.md> --findings <findings.json>
           --out <report.html> [--timestamp "2026-08-28 12:00"]

  - 6 placeholders: {{TITLE}} {{SCORE}} {{OVERVIEW}} {{SECTIONS}}
    {{FINDINGS_TABLE}} {{GENERATED_AT}}
  - score tier is swapped via the quoted full class attribute value
    ``"card score-card score-mid"`` (never a bare ``score-mid`` substring,
    which would corrupt the stylesheet).
  - a small markdown subset (h2/h3/h4, paragraphs, ul/ol, fenced code,
    inline code, bold) is hand-rolled with stdlib only; every text node is
    html.escape'd so hostile evidence/draft content cannot inject markup.

Output is self-contained (inline CSS, zero external resources, zero JS).
Newlines are normalized to LF and written as raw bytes so the golden-file
test stays byte-identical regardless of git's autocrlf setting.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = PROJECT_ROOT / "templates" / "report.html"

SEVERITIES = ("critical", "high", "medium", "low")
DEFAULT_TITLE = "Skill 分析报告"
SCORE_CLASS_ANCHOR = '"card score-card score-mid"'  # unique in template body
_RE_CONTRACT_COMMENT = re.compile(r"<!--.*?-->\n?", re.DOTALL)

# ordered (pattern, tag) for list items; unordered first
_RE_UL_ITEM = re.compile(r"^[-*+]\s+(.*)$")
_RE_OL_ITEM = re.compile(r"^\d+[.)]\s+(.*)$")
_RE_H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


# --------------------------------------------------------------------------
# severity helpers
# --------------------------------------------------------------------------


def normalize_severity(value: object) -> str:
    """Map arbitrary severity values onto the four known classes.

    Unknown/missing values fall back to ``low`` so a hostile string can
    never land inside a class attribute.
    """
    s = str(value if value is not None else "").strip().lower()
    return s if s in SEVERITIES else "low"


def score_tier(score: int) -> str:
    """Map a 0-100 score onto the template's four-tier color scale."""
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 25:
        return "mid"
    return "low"


# --------------------------------------------------------------------------
# markdown subset -> HTML
# --------------------------------------------------------------------------


def slugify(text: str) -> str:
    """Slug for section ids: lowercase, whitespace collapsed to '-'."""
    s = re.sub(r"[^\w\s-]", "", text.strip().lower())
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s or "section"


def render_inline(text: str) -> str:
    """Escape, then apply inline markdown: `` `code` `` (protected) and **bold**."""
    stash: list[str] = []

    def _stash_code(m: re.Match[str]) -> str:
        stash.append(f"<code>{html.escape(m.group(1), quote=False)}</code>")
        return f"\x00{len(stash) - 1}\x00"

    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", _stash_code, out)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    return re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], out)


def _parse_score(data: dict) -> int:
    try:
        return int(data.get("score", 0))
    except (TypeError, ValueError):
        return 0


def render_markdown(text: str) -> str:
    """Render the markdown subset into ``<section>`` structures."""
    lines = text.replace("\r\n", "\n").split("\n")
    n = len(lines)
    sections: list[str] = []
    section_id: str | None = None
    body: list[str] = []
    para: list[str] = []
    in_section = False

    def flush_para() -> None:
        if para:
            body.append(f"<p>{render_inline(' '.join(para))}</p>")
            para.clear()

    def flush_section() -> None:
        nonlocal section_id, in_section
        if in_section:
            id_attr = f' id="{section_id}"' if section_id else ""
            sections.append(f"<section{id_attr}>\n" + "\n".join(body) + "\n</section>")
        section_id = None
        body.clear()
        in_section = False

    def ensure_section() -> None:
        nonlocal in_section
        if not in_section:  # implicit section for content before any ## heading
            in_section = True

    i = 0
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_para()
            ensure_section()
            code_lines: list[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # consume the closing fence (or run past EOF)
            body.append("<pre><code>" + html.escape("\n".join(code_lines), quote=False) + "</code></pre>")
            continue

        m2 = re.match(r"^##\s+(.*)$", line)
        m3 = re.match(r"^###\s+(.*)$", line)
        m4 = re.match(r"^####\s+(.*)$", line)
        if m2:
            flush_para()
            flush_section()
            in_section = True
            title = m2.group(1).strip()
            section_id = slugify(title)
            body.append(f'<h2 id="{section_id}">{render_inline(title)}</h2>')
        elif m3:
            flush_para()
            ensure_section()
            body.append(f"<h3>{render_inline(m3.group(1).strip())}</h3>")
        elif m4:
            flush_para()
            ensure_section()
            body.append(f"<h4>{render_inline(m4.group(1).strip())}</h4>")
        elif not stripped:
            flush_para()
        elif (ul := _RE_UL_ITEM.match(stripped)) or (ol := _RE_OL_ITEM.match(stripped)):
            flush_para()
            ensure_section()
            is_ul = ul is not None
            item_re = _RE_UL_ITEM if is_ul else _RE_OL_ITEM
            tag = "ul" if is_ul else "ol"
            items: list[str] = []
            while i < n and (m := item_re.match(lines[i].strip())):
                items.append(f"<li>{render_inline(m.group(1).strip())}</li>")
                i += 1
            body.append(f"<{tag}>\n" + "\n".join(items) + f"\n</{tag}>")
            continue
        else:
            para.append(stripped)
        i += 1

    flush_para()
    flush_section()
    return "\n\n".join(sections)


# --------------------------------------------------------------------------
# report fragments
# --------------------------------------------------------------------------


def render_overview(findings: list) -> str:
    """Four severity count cards injected at {{OVERVIEW}}."""
    counts = {sev: 0 for sev in SEVERITIES}
    for f in findings:
        if isinstance(f, dict):
            counts[normalize_severity(f.get("severity"))] += 1
    cards = [
        f'<div class="card sev-{sev}">\n'
        f'          <p class="card-label">{sev.capitalize()}</p>\n'
        f'          <p class="card-value">{counts[sev]}</p>\n'
        f'        </div>'
        for sev in SEVERITIES
    ]
    return "\n          ".join(cards)


def render_findings_table(findings: list) -> str:
    """``<tr>`` rows at {{FINDINGS_TABLE}}; columns: severity/rule/file/line/note."""
    if not findings:
        return '<tr><td colspan="5" class="empty">未发现安全风险</td></tr>'
    rows = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        sev = normalize_severity(f.get("severity"))
        raw_sev = str(f.get("severity", "") or "").strip()
        badge = html.escape(raw_sev if raw_sev else sev, quote=False)
        line = f.get("line")
        if isinstance(line, bool) or not isinstance(line, int):
            line_text = html.escape(str(line if line is not None else ""), quote=False)
        else:
            line_text = str(line)
        note = f.get("explanation") or f.get("evidence") or ""
        rows.append(
            f'<tr class="sev-{sev}">\n'
            f'            <td><span class="sev sev-{sev}">{badge}</span></td>\n'
            f'            <td>{html.escape(str(f.get("rule_id", "")), quote=False)}</td>\n'
            f'            <td>{html.escape(str(f.get("file", "")), quote=False)}</td>\n'
            f'            <td>{line_text}</td>\n'
            f'            <td>{html.escape(str(note), quote=False)}</td>\n'
            f'          </tr>'
        )
    return "\n          ".join(rows)


def strip_contract_comment(template: str) -> str:
    """Drop the template's leading contract comment before rendering.

    The template header (lines 2-62) documents placeholders with literal
    examples (``{{TITLE}}``, ``<tr class="sev-critical">`` …) that would
    otherwise be hit by the plain-string replacements. The template
    explicitly allows removing this block ("可选，非契约要求").
    """
    return _RE_CONTRACT_COMMENT.sub("", template, count=1)


def extract_title(draft_text: str) -> tuple[str, str]:
    """Use the draft's first H1 as the report title; strip it from the body."""
    m = _RE_H1.search(draft_text)
    if m:
        return m.group(1), draft_text.replace(m.group(0), "", 1)
    return DEFAULT_TITLE, draft_text


def render_report(draft_text: str, findings_data: dict, timestamp: str) -> str:
    """Render the template with all six placeholders filled."""
    title, body_text = extract_title(draft_text.replace("\r\n", "\n"))
    findings = findings_data.get("findings") or []
    if not isinstance(findings, list):
        findings = []
    score = _parse_score(findings_data)

    template = strip_contract_comment(
        TEMPLATE_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
    )
    rendered = template
    rendered = rendered.replace("{{TITLE}}", html.escape(title, quote=False))
    rendered = rendered.replace("{{SCORE}}", str(score))
    rendered = rendered.replace("{{OVERVIEW}}", render_overview(findings))
    rendered = rendered.replace("{{SECTIONS}}", render_markdown(body_text))
    rendered = rendered.replace("{{FINDINGS_TABLE}}", render_findings_table(findings))
    rendered = rendered.replace("{{GENERATED_AT}}", html.escape(timestamp, quote=False))
    rendered = rendered.replace(
        SCORE_CLASS_ANCHOR, f'"card score-card score-{score_tier(score)}"'
    )
    return rendered


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the skill-master HTML report.")
    parser.add_argument("--draft", required=True, help="analysis markdown draft (.md)")
    parser.add_argument("--findings", required=True, help="scanner findings JSON")
    parser.add_argument("--out", required=True, help="output HTML path")
    parser.add_argument("--timestamp", default=None, help="generated-at override (deterministic tests)")
    args = parser.parse_args(argv)

    draft_path = Path(args.draft)
    findings_path = Path(args.findings)
    out_path = Path(args.out)

    if not draft_path.is_file():
        print(f"error: draft file not found: {draft_path}", file=sys.stderr)
        return 1
    if not findings_path.is_file():
        print(f"error: findings file not found: {findings_path}", file=sys.stderr)
        return 1
    if not TEMPLATE_PATH.is_file():
        print(f"error: report template not found: {TEMPLATE_PATH}", file=sys.stderr)
        return 1
    try:
        draft_text = draft_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: cannot read draft: {exc}", file=sys.stderr)
        return 1
    try:
        findings_data = json.loads(findings_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"error: cannot read findings JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(findings_data, dict):
        print("error: findings JSON root must be an object", file=sys.stderr)
        return 1

    timestamp = args.timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rendered = render_report(draft_text, findings_data, timestamp)

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(rendered.encode("utf-8"))
    except OSError as exc:
        print(f"error: cannot write output: {exc}", file=sys.stderr)
        return 1
    print(str(out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
