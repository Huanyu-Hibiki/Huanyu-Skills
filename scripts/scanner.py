"""scanner.py — static security rule engine for skill directories (tasks 10-11).

CLI: python scripts/scanner.py <target-path> [--json] [--max-files N]
stdout is always a single JSON object {"score": ..., "findings": [...],
"truncated": ...}; exit code 0 on success, non-zero with an {"error": "..."}
JSON body on failure.

Rule source of truth: shared-references/security-taxonomy.md §2 — 25 rules
(INJ×5 / EXFIL×6 / DEST×4 / OBF×6 / PERM×4); every id and severity is copied
verbatim from the taxonomy tables, never improvised here.

Pattern-writing discipline (references/security/pattern-examples.md §1):
all regexes compile with a single re.IGNORECASE | re.MULTILINE flag pair, no
nested quantifiers, command names anchored with \\b, bounded [^\\n] windows.
Where pattern-examples shows a leading \\b directly before a flag token
(`\\b-d\\b`) the implementation drops it — a boundary between two non-word
characters never matches; the trailing \\b is kept (scanner.py is the final
authority per that document's header note).

Co-occurrence ("chain") rules: EXFIL-002 (credential read + network call in
the same file) and PERM-004 (read-only allowed-tools declaration + write
instruction in the same file) are implemented as scanner-level same-file
co-occurrence per pattern-examples §1.3 — each regex stays single-line.
"""

from __future__ import annotations

import argparse
import bisect
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

MARKDOWN_EXTS = {".md"}
CODE_EXTS = {
    ".py", ".sh", ".ps1", ".psm1", ".js", ".bat", ".cmd", ".reg", ".vbs",
    ".vbe", ".pl", ".rb", ".bash", ".zsh", ".fish", ".ts", ".lua", ".r",
}

RULE_FLAGS = re.IGNORECASE | re.MULTILINE

EVIDENCE_MAX = 200  # pattern-examples §3.2: clip long lines to a 200-char window

# taxonomy §4 评分约定 (frozen): weights per finding, ×1.3 multiplier when the
# scanned target contains executable scripts, hard cap at 100.
SEVERITY_WEIGHTS = {"critical": 50, "high": 25, "medium": 10, "low": 5}
EXECUTABLE_EXTS = {".sh", ".py", ".ps1", ".bat", ".cmd", ".exe", ".js"}
SCORE_CAP = 100

# per-file content read cap and enumeration cap (truncation) — module-level
# constants so tests can monkeypatch them.
SIZE_CAP_BYTES = 50 * 1024 * 1024
DEFAULT_MAX_FILES = 500


class ScannerError(Exception):
    """Unrecoverable scan failure (target path missing, ...)."""


@dataclass(frozen=True)
class Rule:
    """One taxonomy §2 rule row; field contract per taxonomy §5 (6 fields)."""

    id: str
    severity: str
    pattern: str
    target: str  # markdown | code | frontmatter | filename | all
    explanation: str
    false_positive_note: str


RULES: tuple[Rule, ...] = (
    # --- INJ 提示注入（taxonomy §2.1）------------------------------------
    Rule(
        id="INJ-001",
        severity="high",
        target="all",
        pattern=r"\b(?:ignore|disregard|forget)\b[^.\n]{0,40}\b(?:previous|prior|above|all)\b[^.\n]{0,40}\b(?:instructions?|prompts?|rules?)\b",
        explanation="指令覆盖类注入：企图让宿主 agent 抛弃既有指令（ignore/disregard/forget previous instructions 变体）。",
        false_positive_note="重构文档指代旧测试规则（如“忽略先前所有规则”）、安全教学示例代码块会命中，复核看语境。",
    ),
    Rule(
        id="INJ-002",
        severity="high",
        target="all",
        pattern=r"\byour\s+new\s+system\s+prompt\b|(?:reveal|print|show|dump|leak|repeat)\b[^.\n]{0,40}\bsystem\s+prompt\b|输出你.{0,10}系统提示",
        explanation="系统提示覆盖或套取指令（your new system prompt / 输出完整系统提示）。",
        false_positive_note="讨论系统提示机制的科普文档、教学示例会引用这些短语，复核看是否处于示例与讲解语境。",
    ),
    Rule(
        id="INJ-003",
        severity="high",
        target="all",
        pattern=r"\b(?:no\s+restrictions?|without\s+any\s+restrictions?|never\s+refuse|do\s+anything\s+now)\b",
        explanation="越权与反拒答诱导：解除安全限制、要求永不拒绝（no restrictions / never refuse 类）。",
        false_positive_note="安全教学 skill 在代码块内展示恶意特征原文会命中，复核看是否有教学语境。",
    ),
    Rule(
        id="INJ-004",
        severity="high",
        target="all",
        pattern=r"<!--[^>\n]{0,200}?\b(?:ignore|system|override|execute|send|upload)\b",
        explanation="HTML 注释等不可见载体中夹带命令式指令。",
        false_positive_note="普通文档导航注释（如 <!-- see system docs -->）含 system 等词会命中，属良性。",
    ),
    Rule(
        id="INJ-005",
        severity="medium",
        target="all",
        pattern=r"\btreat\s+the\s+following\s+as\s+trusted\b|\balways\s+comply\b|\bcomply\s+without\s+questioning\b",
        explanation="行为操纵类弱注入（treat as trusted / always comply without questioning）。",
        false_positive_note="信任模型讨论、评审指南可能合法使用这些短语，单独出现不足以定罪。",
    ),
    # --- EXFIL 数据外泄（taxonomy §2.2）----------------------------------
    Rule(
        id="EXFIL-001",
        severity="critical",
        target="code",
        pattern=r"\b(?:curl|wget)\b[^|;\n]{0,80}(?:-d\b|--data\b|--post-data\b)[^|;\n]{0,120}(?:\$\{?[A-Z_][A-Z0-9_]{2,}\}?|%[A-Z_]+%|\.env\b)",
        explanation="curl/wget POST 携带环境变量外传，凭据出网证据链完整。",
        false_positive_note="CI 内网上报构建号（大写变量 + POST 但端点为内部地址）会命中，复核时降级。",
    ),
    Rule(
        id="EXFIL-002",
        severity="critical",
        target="code",
        pattern=r"\b(?:id_rsa|id_ed25519|id_ecdsa)\b|[\"']\.ssh[\"']|\.aws[/\\]credentials|\.gnupg\b|\.env\b|~/?\.ssh\b",
        explanation="同文件内先读凭据（.ssh/.env 等）再联网，链式共现指向凭据外传（联网特征由伴随条件校验）。",
        false_positive_note="备份/迁移类 skill 读密钥并上传到用户配置端点属正常功能，复核看端点是否可配置且已明示。",
    ),
    Rule(
        id="EXFIL-003",
        severity="high",
        target="code",
        pattern=r"\b(?:webhook\.site|pastebin\.com|ngrok\.(?:io|com)|requestbin\.com|pipedream\.net|beeceptor\.com|oast\.(?:fun|pro|live|site)|burpcollaborator\.net|interact\.sh)\b",
        explanation="向 webhook.site/pastebin/ngrok 等临时接收端点外传数据。",
        false_positive_note="使用这些服务做合法集成或 webhook 调试演示会命中，复核看传输的数据内容。",
    ),
    Rule(
        id="EXFIL-004",
        severity="high",
        target="code",
        pattern=r"os\.environ\.(?:items|copy)\(\)|\benv\s*\|\s*base64\b|\bprintenv\b|\bGet-ChildItem\s+env:",
        explanation="环境变量全量枚举/收割（os.environ.items / env|base64 / printenv）。",
        false_positive_note="就地复制环境变量传给子进程（继承 PATH）不外传时属正常用法，复核时降级。",
    ),
    Rule(
        id="EXFIL-005",
        severity="medium",
        target="code",
        pattern=r"~/?\.(?:ssh|aws|gnupg)\b|/(?:home|Users)/[^/'\"\s]+/\.(?:ssh|aws|gnupg)\b",
        explanation="枚举 .ssh/.aws/.gnupg 敏感目录。",
        false_positive_note="备份类 skill 的功能声明行（备份范围含 ~/.ssh）会命中，属该类工具的正常行为。",
    ),
    Rule(
        id="EXFIL-006",
        severity="high",
        target="markdown",
        pattern=r"\b(?:upload|send|post|transmit|exfiltrate|ship)\b[^.\n]{0,80}\b(?:session|conversation|transcript|system\s+prompt|chat\s+history|context)\b|\b(?:session|conversation|transcript|system\s+prompt)\b[^.\n]{0,80}\b(?:upload|外传|上传)\b",
        explanation="指示打包会话上下文/系统提示并上传外传。",
        false_positive_note="用户明确要求的会话导出/归档功能会命中，复核看是否有用户显式授权语境。",
    ),
    # --- DEST 破坏命令（taxonomy §2.3）------------------------------------
    Rule(
        id="DEST-001",
        severity="critical",
        target="code",
        pattern=(
            r"\brm\s+(?:-\w*[rR]\w*[fF]\w*|-\w*[fF]\w*[rR]\w*)\s+[\"']?(?!\.)\s*(?:/|~)\s*[/\s\"']?$"
            r"|\brm\s+(?:-\w*[rR]\w*[fF]\w*|-\w*[fF]\w*[rR]\w*)\s+[\"']?(?!\.)(?:/|~/)(?:etc|usr|home|var|root|bin|sbin|boot|lib|opt)\b"
            r"|\brd\s+/s\b[^.\n]{0,40}/q\b"
            r"|\bRemove-Item\b[^.\n]{0,60}-Recurse\b"
        ),
        explanation="递归强删指向根目录或用户主目录（rm -rf / 、rd /s /q C:\\ 等）。",
        false_positive_note=r"指向明确子目录的清理脚本（rm -rf ./build）已被 (?!\.) 边界排除；文档引用命令原文会命中。",
    ),
    Rule(
        id="DEST-002",
        severity="critical",
        target="code",
        pattern=r"\bmkfs(?:\.\w+)?\b|\bdd\s+if=/dev/(?:zero|random|null)\b|\bdiskpart\b[^.\n]{0,40}\bclean\b|\bformat\s+[a-zA-Z]:",
        explanation="磁盘格式化或覆写命令（mkfs / dd if=/dev/zero / diskpart clean / format C:）。",
        false_positive_note="取证/运维文档中的禁止性说明（“严禁执行 mkfs”）会命中，复核看语境。",
    ),
    Rule(
        id="DEST-003",
        severity="high",
        target="code",
        pattern=r"\breg\s+add\b[^.\n]{0,80}\b(?:HKLM|HKCU|HKEY_LOCAL_MACHINE|HKEY_CURRENT_USER|HKEY_USERS)\b|\[(?:HKEY_LOCAL_MACHINE|HKEY_CURRENT_USER|HKEY_USERS)[^\]\n]{0,140}\bRun(?:Once)?\s*\]",
        explanation="注册表或启动项写入（reg add HKLM…\\Run）。",
        false_positive_note="安装器写自启动项属常见行为，需结合 skill 声明的功能判断。",
    ),
    Rule(
        id="DEST-004",
        severity="high",
        target="code",
        pattern=r"\btaskkill\b[^.\n]{0,40}\b(?:svchost|lsass|csrss|wininit|winlogon|services)\.exe\b|\bshutdown\s+/[sr]\b|\bkill\s+-9\s+1\b|\bStop-Process\b[^.\n]{0,40}-Force\b",
        explanation="杀系统关键进程或强制关机重启（taskkill svchost / shutdown / kill -9 1）。",
        false_positive_note="部署脚本装完驱动后重启（shutdown /r）是发布流程常规动作，复核时降级并注明。",
    ),
    # --- OBF 混淆隐藏（taxonomy §2.4）------------------------------------
    Rule(
        id="OBF-001",
        severity="high",
        target="code",
        pattern=r"[A-Za-z0-9+/]{80,}={0,2}[^.\n]{0,40}(?:base64\s+(?:-d|--decode)|\bb64decode\b|FromBase64String|\bIEX\b)",
        explanation="超长 base64 串（≥80 字符）解码后直接执行。",
        false_positive_note="解码内嵌证书公钥后落盘校验（不执行）会命中，复核看解码结果的去向。",
    ),
    Rule(
        id="OBF-002",
        severity="high",
        target="code",
        pattern=r"\beval\s*\(|\bexec\s*\(|\bIEX\b|\bInvoke-Expression\b",
        explanation="eval/exec/IEX 类动态执行拼接字符串。",
        false_positive_note="计算器类 skill eval 字面量表达式无外部数据流，命中后在报告中注明无污点输入。",
    ),
    Rule(
        id="OBF-003",
        severity="medium",
        target="all",
        pattern="[\u200b\u200c\u200d\u2060\ufeff]",
        explanation="零宽/不可见字符（U+200B/U+200C/U+200D/U+2060/U+FEFF）。",
        false_positive_note="从网页复制粘贴残留的 U+FEFF（BOM）是最大误报源，可能只是编码残留。",
    ),
    Rule(
        id="OBF-004",
        severity="low",
        target="code",
        pattern=r">>\s*~/?\.\w+|\btee\s+-a\s+~/?\.\w+|/(?:home|Users)/[^/\s]+/\.(?:bashrc|profile|zshrc|bash_profile)\b",
        explanation="向 .bashrc/.profile 等 dotfile 追加写入，实现隐藏与持久化。",
        false_positive_note="大量正常配置以 . 开头，shell 集成安装脚本写 ~/.bashrc 属常见行为。",
    ),
    Rule(
        id="OBF-005",
        severity="high",
        target="filename",
        pattern=r"\.(?:pdf|docx?|xlsx?|pptx?|txt|csv|md|jpe?g|png|gif|html?|zip|rar|7z|svg)\.(?:exe|sh|ps1|bat|cmd|js|jse|vbs|vbe|wsf|scf|scr|com|pif|msi|jar|py|pl|rb|hta)$",
        explanation="双扩展名可执行伪装（invoice.pdf.exe / notes.md.ps1 类文件名）。",
        false_positive_note="暂无已知误报场景，可直接报告；确有同名合法文件时复核确认内容。",
    ),
    Rule(
        id="OBF-006",
        severity="high",
        target="code",
        pattern=r"\b(?:curl|wget)\b[^|\n]{0,120}\|\s*(?:ba|z|da)?sh\b|\b(?:xxd|unhex)\s+-r\b|\brot13\b[^|\n]{0,40}\|",
        explanation="编码管道执行：curl|bash 远程代码直接落地、hex/rot13 解码后执行。",
        false_positive_note="官方安装脚本的 curl … | bash 惯用写法会命中，复核看 URL 域名是否可信。",
    ),
    # --- PERM 过度权限（taxonomy §2.5）------------------------------------
    Rule(
        id="PERM-001",
        severity="high",
        target="frontmatter",
        pattern=r"allowed-tools:\s*[^\n]{0,10}\bBash\(\*\)",
        explanation="frontmatter 声明 Bash(*) 高危通配工具权限。",
        false_positive_note="写作指南以反面教材形式引用 Bash(*) 会命中，复核看语境。",
    ),
    Rule(
        id="PERM-002",
        severity="high",
        target="code",
        pattern=r"\bsudo\s+(?:-n\b|--non-interactive\b)|#Requires\s+-RunAsAdministrator\b|\brunas\b",
        explanation="自动 sudo/root 静默提权（sudo -n / #Requires -RunAsAdministrator / runas）。",
        false_positive_note="教程教用户自查免密配置的说明行（sudo -n true）会命中，非脚本内静默提权。",
    ),
    Rule(
        id="PERM-003",
        severity="medium",
        target="code",
        pattern=r"\brm\s+-(?![a-zA-Z]*r)[a-zA-Z]*f[a-zA-Z]*\s|--yes\b|\bRemove-Item\b[^.\n]{0,40}\b-Force\b|\bgit\s+push\s+--force\b(?!-with-lease)|2>\s*/dev/null",
        explanation="静默删除/绕过确认门槛标志（rm -f / --yes / -Force / 2>/dev/null）。",
        false_positive_note="无人值守安装脚本使用 --yes 属常规自动化做法，需结合其他命中综合判断；含 r 的删除标志（rm -rf）归 DEST-001，本规则不重复计分。",
    ),
    Rule(
        id="PERM-004",
        severity="medium",
        target="markdown",
        pattern=r"\b(?:Write|Edit)\b[^.\n]{0,80}(?:\btool\b|\bfile\b|\bto\b)|\b写(?:入|出|文件)\b",
        explanation="声明权限与实际行为不符：frontmatter 只声明只读工具（伴随条件），正文却指示写文件。",
        false_positive_note="声明行列举不全（漏写 Write）但功能无害时会命中，复核看实际写操作的范围。",
    ),
)

# Same-file co-occurrence companions (pattern-examples §1.3: the regex stays
# single-line, the scanner performs the chain check). A rule listed here only
# reports when BOTH its own pattern and the companion pattern hit the file.
CHAIN_REQUIREMENTS: dict[str, str] = {
    # EXFIL-002: credential read must co-occur with an outbound network call
    "EXFIL-002": (
        r"requests\.(?:post|put)|urllib\.request|urlopen\b|httpx\.(?:post|put)|"
        r"\bcurl\b[^|\n]{0,120}(?:-d\b|--data\b|\bPOST\b)|\bwget\b[^|\n]{0,80}--post-data|"
        r"Invoke-WebRequest|Invoke-RestMethod|socket\.connect"
    ),
    # PERM-004: write instruction must co-occur with a read-only allowed-tools line
    "PERM-004": r"allowed-tools:(?![^\n]*\b(?:Write|Bash|Edit|MultiEdit|NotebookEdit)\b)[^\n]*",
}

_COMPILED: dict[str, re.Pattern[str]] = {
    rule.id: re.compile(rule.pattern, RULE_FLAGS) for rule in RULES
}
_CHAIN_COMPILED: dict[str, re.Pattern[str]] = {
    rule_id: re.compile(pattern, RULE_FLAGS)
    for rule_id, pattern in CHAIN_REQUIREMENTS.items()
}
_FILENAME_RULES = [rule for rule in RULES if rule.target == "filename"]
_CONTENT_RULES = [rule for rule in RULES if rule.target != "filename"]

_FM_CLOSE = re.compile(r"^---\s*$", re.MULTILINE)


def _kind(path: Path) -> str:
    """Classify a file for target filtering: markdown / code / other."""
    ext = path.suffix.lower()
    if ext in MARKDOWN_EXTS:
        return "markdown"
    if ext in CODE_EXTS:
        return "code"
    return "other"


def _frontmatter_span(text: str) -> tuple[int, int] | None:
    """Return the [start, end) offsets of the leading YAML frontmatter block
    (--- fenced head of a markdown file), or None when absent."""
    if not text.startswith("---"):
        return None
    first_nl = text.find("\n")
    if first_nl == -1 or text[:first_nl].rstrip("\r") != "---":
        return None
    closing = _FM_CLOSE.search(text, first_nl + 1)
    if closing is None:
        return None
    return (first_nl + 1, closing.start())


def _clip_evidence(line_text: str, col: int) -> str:
    """pattern-examples §3: evidence is the full matched line; lines longer
    than 200 chars are clipped to a 200-char window centered on the hit with
    "…" on both ends (boundaries relaxed to the nearest whitespace)."""
    if len(line_text) <= EVIDENCE_MAX:
        return line_text
    start = max(0, min(col - EVIDENCE_MAX // 2, len(line_text) - EVIDENCE_MAX))
    end = start + EVIDENCE_MAX
    if start > 0:
        relaxed = line_text.find(" ", start, start + 24)
        if relaxed != -1:
            start = relaxed + 1
    if end < len(line_text):
        relaxed = line_text.rfind(" ", end - 24, end)
        if relaxed >= start:
            end = relaxed
    return "…" + line_text[start:end] + "…"


def _target_applies(rule: Rule, kind: str, fm_span: tuple[int, int] | None) -> bool:
    if rule.target == "all":
        return True
    if rule.target == "markdown":
        return kind == "markdown"
    if rule.target == "code":
        return kind == "code"
    if rule.target == "frontmatter":
        return kind == "markdown" and fm_span is not None
    return False


def _scan_text(rel: str, text: str, kind: str, findings: list[dict]) -> None:
    """Apply every applicable content rule to one decoded file; one finding
    per (rule, line), evidence = matched line clipped per §3."""
    fm_span = _frontmatter_span(text)
    line_starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            line_starts.append(i + 1)

    for rule in _CONTENT_RULES:
        if not _target_applies(rule, kind, fm_span):
            continue
        chain = _CHAIN_COMPILED.get(rule.id)
        if chain is not None and chain.search(text) is None:
            continue
        reported_lines: set[int] = set()
        for m in _COMPILED[rule.id].finditer(text):
            if rule.target == "frontmatter" and not (
                fm_span[0] <= m.start() < fm_span[1]  # type: ignore[index]
            ):
                continue
            lineno = bisect.bisect_right(line_starts, m.start())
            if lineno in reported_lines:
                continue
            reported_lines.add(lineno)
            line_begin = line_starts[lineno - 1]
            line_end = text.find("\n", line_begin)
            if line_end == -1:
                line_end = len(text)
            line_text = text[line_begin:line_end].rstrip("\r")
            findings.append(
                {
                    "rule_id": rule.id,
                    "severity": rule.severity,
                    "file": rel,
                    "line": lineno,
                    "evidence": _clip_evidence(line_text, m.start() - line_begin),
                    "explanation": rule.explanation,
                }
            )


def _scan_file(path: Path, rel: str, findings: list[dict]) -> None:
    """Scan one file: filename rules against the name, content rules against
    the decoded text. Binary files (NUL byte) and files over SIZE_CAP_BYTES
    are skipped for content scanning (filename rules still apply)."""
    for rule in _FILENAME_RULES:
        if _COMPILED[rule.id].search(path.name):
            findings.append(
                {
                    "rule_id": rule.id,
                    "severity": rule.severity,
                    "file": rel,
                    "line": 0,  # filename match: no line to point at
                    "evidence": path.name,
                    "explanation": rule.explanation,
                }
            )

    if path.stat().st_size > SIZE_CAP_BYTES:
        return  # oversized: skip content scan
    data = path.read_bytes()
    if b"\x00" in data:
        return  # binary per contract
    text = data.decode("utf-8", errors="replace")
    if text.startswith("\ufeff"):
        text = text[1:]  # leading BOM is an encoding marker, not content
    _scan_text(rel, text, _kind(path), findings)


def compute_score(findings: list[dict], has_executable: bool) -> int:
    """taxonomy §4 frozen scoring: critical +50 / high +25 / medium +10 /
    low +5 summed over findings; ×1.3 when the target contains executable
    scripts; capped at 100."""
    total = sum(SEVERITY_WEIGHTS[f["severity"]] for f in findings)
    if has_executable:
        total *= 1.3
    return min(SCORE_CAP, int(round(total)))


def scan(target: str | Path, max_files: int = DEFAULT_MAX_FILES) -> dict:
    """Scan a directory (recursive) or a single file; returns the JSON-ready
    result object {"score": ..., "findings": [...], "truncated": ...}.

    Directory scans stop after ``max_files`` files (enumerated in sorted
    path order) and flag "truncated": true when the limit was hit.
    """
    if max_files < 0:
        raise ScannerError(f"--max-files must be >= 0, got {max_files}")
    target = Path(target)
    if not target.exists():
        raise ScannerError(f"target path does not exist: {target}")
    if not (target.is_file() or target.is_dir()):
        raise ScannerError(f"target path is neither a file nor a directory: {target}")

    if target.is_file():
        entries = [(target, target.name)]
        truncated = False
    else:
        all_files = sorted(target.rglob("*"), key=lambda p: p.as_posix())
        all_files = [p for p in all_files if p.is_file()]
        entries = [
            (p, p.relative_to(target).as_posix()) for p in all_files[:max_files]
        ]
        truncated = len(all_files) > max_files

    findings: list[dict] = []
    has_executable = False
    for path, rel in entries:
        if path.suffix.lower() in EXECUTABLE_EXTS:
            has_executable = True
        _scan_file(path, rel, findings)

    findings.sort(key=lambda f: (f["file"], f["line"], f["rule_id"]))
    return {
        "score": compute_score(findings, has_executable),
        "findings": findings,
        "truncated": truncated,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scanner.py",
        description="Scan a skill directory or file against the security taxonomy rules.",
    )
    parser.add_argument("target", help="skill directory or single file to scan")
    parser.add_argument(
        "--json",
        action="store_true",
        help="output JSON on stdout (always on; accepted for compatibility)",
    )
    parser.add_argument(
        "--max-files",
        dest="max_files",
        type=int,
        default=DEFAULT_MAX_FILES,
        help=f"stop scanning after N files (default {DEFAULT_MAX_FILES}); "
        "the result is flagged truncated",
    )
    args = parser.parse_args(argv)

    try:
        result = scan(args.target, max_files=args.max_files)
    except ScannerError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
