#!/usr/bin/env python3
"""oracle-bone context —— 任务状态摘要器（只读）。

从项目根的 .oracle-state.json 提取与当前任务相关的最小状态摘要（默认 ≤6000 字节），
替代"每个子 skill 各自全量解读 state"——各 skill 拿到的是同一份口径。
本脚本**只读**：绝不写任何文件、不改 state。

用法:
  python tools/context.py <project_root> [--task <task>] [--track <id>]

task 取子 skill 后缀（predict / retro / seed / status ...）；未知 task 回退为基础摘要。
--track 只看某一轨（predict / retro / bump 按轨干活时用）。

退出码: 0 正常（含警告） / 2 未初始化 / 3 state 损坏
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LATEST_SCHEMA = "1.0"  # 与 migrations/registry.md 保持一致
SUMMARY_BUDGET_BYTES = 6000
MAX_LIST_ITEMS = 8

# 各任务建议读取清单（文件名与 shared-references 既有协议，不新增事实源）
TASK_READLIST = {
    "score": ["rubric_notes.md（该轨节）", "shared-references/scoring-procedure.md（打分规程）"],
    "predict": [
        "rubric_notes.md（该轨节）",
        "shared-references/scoring-procedure.md（打分规程）",
        "同轨 predictions/*.md header（锚点，排除 reconstructed）",
        "shared-references/prediction-anatomy.md + blind-prediction-protocol.md",
    ],
    "retro": [
        "目标作品 predictions/*.md（## 复盘 段追加）",
        "rubric_notes.md（观察入 notes，违反即删）",
        "采集: adapters/perf-data（NEEDS_AUTH → --auth-only，缺失不估算）",
    ],
    "bump": [
        "shared-references/bump-validation-protocol.md（全量重打 + 跨模型审）",
        "tools/score-curve.py --json（偏差方向 / bucket 命中率）",
    ],
    "compass-retro": [
        "tools/dashboard.py（五维 + quantile 建议）",
        "meta-retros/product-feedback.md（如有）",
        "content-plan.md（规划修订候选，只建议不改）",
    ],
    "recommend": ["candidates.md（tier != skip）", "content-plan.md（占比过滤）"],
    "seed": ["user-profile.md（风格 / 红线）", "content-plan.md（track 分流）", "references/hook-prototypes.md"],
    "voice": ["candidates.md 该 entry（track / 立意 / 受众）", "seed 录音聊天卡（如刚跑完 seed）", "voice-lexicon.md（个人词典，可选）", "转写: App 自带转写粘贴（推荐）或 adapters/script-extraction"],
    "trends": ["adapters/trend-sources/（已启用源）", "shared-references/candidate-schema.md", "shared-references/scoring-procedure.md（粗打分规程）"],
    "title": ["目标作品 scripts/*.md（draft）", "标题候选列表（评审模式；生成模式自产）"],
    "description": ["目标作品 scripts/*.md（定稿，append 发布文案段）", "state.platforms（平台集）"],
    "cover": ["目标作品 scripts/*.md（定稿）", "user-profile.md（形象三词 / 风格）", "cover-patterns.md（如有，对标视觉配方）"],
    "no-ai-slop": ["目标作品 scripts/*.md（预测前必跑）"],
    "who-for": ["audience-profiles.md（init 基线画像 → 逐稿深化）"],
    "open-source": ["references/conversion-track-playbook.md（转化轨专用）"],
    "simulate-audience": ["audience-profiles.md（核心受众 / 一般关注两类）"],
    "compliance": ["目标作品 scripts/*.md（发布前 gate）"],
    "shoot": ["对应 prediction 文件（diff ≥30% → predict v2）"],
    "publish": ["对应 prediction 文件（登记 URL）", "oracle-compliance gate 先过"],
    "pinned-comment": ["已发布作品 scripts/*.md（置顶评论段 append）"],
    "derivative": ["已发布作品 scripts/*.md（T+1 裂变）"],
    "learn-from": ["benchmark.md / script_patterns.md（--append 增量）"],
    "apprentice": ["study/<博主>/（拆解档案）"],
    "status": ["本摘要即基线；可选 tools/score-curve.py --json / tools/dashboard.py"],
    "migrate": ["migrations/registry.md（版本链单一来源）"],
}


def confidence_label(n: int) -> str:
    """state-management.md Confidence 派生表（单一真值）的代码化。"""
    if n <= 0:
        return "🔴 极低"
    if n <= 2:
        return "🟠 低"
    if n <= 5:
        return "🟡 偏低"
    if n <= 10:
        return "🟢 中"
    if n <= 20:
        return "🟢 较高"
    return "🔵 高"


def load_state(root: Path):
    """返回 (state, error_exit_code)。state 不存在 → 2；解析失败 → 3。"""
    path = root / ".oracle-state.json"
    if not path.exists():
        return None, 2
    try:
        # utf-8-sig 兼容带 BOM 的文件（Windows 记事本/PowerShell 写出）与无 BOM 两种形态
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f), 0
    except (json.JSONDecodeError, OSError):
        return None, 3


def fmt_track(t: dict, state: dict) -> str:
    tid = t.get("id", "?")
    n = state.get("calibration_samples_by_track", {}).get(tid, 0)
    name = t.get("name") or tid
    layer = t.get("funnel_layer") or "-"
    ratio = t.get("mix_ratio")
    ratio_s = f" {ratio:.0%}" if isinstance(ratio, (int, float)) else ""
    windows = "/".join(str(d) for d in t.get("retro_windows_days", [])) or "-"
    ver = t.get("rubric_version", "?")
    return f"  - {name}({tid}·{layer}){ratio_s} rubric {ver} · 窗口 T+{windows} · 样本 {n} {confidence_label(n)}"


def pending_retro_lines(state: dict, now: datetime) -> list:
    lines = []
    for pr in state.get("pending_retros", [])[:MAX_LIST_ITEMS]:
        track = pr.get("track", "?")
        file = Path(pr.get("file", "?")).name
        due_open = [
            w for w in pr.get("due_windows", [])
            if not w.get("done") and _parse_iso(w.get("due_at")) and _parse_iso(w.get("due_at")) <= now
        ]
        if due_open:
            days = ",".join(str(w.get("days", "?")) for w in due_open)
            lines.append(f"  - 🚨 {file}（{track}）T+{days} 已到期")
        else:
            undone = [w for w in pr.get("due_windows", []) if not w.get("done")]
            if undone:
                nearest = min((_parse_iso(w.get("due_at")) for w in undone if _parse_iso(w.get("due_at"))), default=None)
                when = nearest.date().isoformat() if nearest else "?"
                lines.append(f"  - {file}（{track}）最近窗口 {when}")
    return lines


def _parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def build_summary(state: dict, task: str, track_filter: str | None) -> str:
    now = datetime.now(timezone.utc).astimezone()
    lines = ["# oracle-bone 任务摘要", ""]

    schema = state.get("schema_version", "?")
    lines.append(f"state: v{schema} · {state.get('mode', '?')} · {state.get('content_form', '?')}")
    lines.append(f"平台: {' / '.join(state.get('platforms', []) ) or '未配置'}")
    cadence = state.get("target_publish_cadence_days")
    lines.append(f"cadence: {'每 %s 天' % cadence if cadence else '灵活（buffer 颜色禁用）'}")
    lines.append("")

    tracks = state.get("tracks", {}).get("definitions", [])
    if track_filter:
        tracks = [t for t in tracks if t.get("id") == track_filter]
        if not tracks:
            lines.append(f"⚠ 轨道 {track_filter} 未注册（plan_type={state.get('plan_type', '?')}）")
    if tracks:
        ratios = " / ".join(f"{t.get('name') or t.get('id')} {t.get('mix_ratio', 0):.0%}" for t in tracks)
        lines.append(f"规划: {state.get('plan_type', '?')}（{ratios}）")
        lines.append("分轨校准池:")
        lines.extend(fmt_track(t, state) for t in tracks)
    total = state.get("calibration_samples_total")
    if total is None:
        total = sum(state.get("calibration_samples_by_track", {}).values())
    lines.append(f"总样本: {total}")
    lines.append("")

    sc = state.get("stage_constraint") or {}
    val = sc.get("value", "none")
    if val and val != "none":
        basis = sc.get("basis", "")
        at = (sc.get("updated_at") or "")[:10]
        lines.append(f"当前约束: {val}（{basis}{'，' + at if at else ''}）")
    else:
        lines.append("当前约束: none（无显著约束即好状态，不硬贴标签）")

    shoots = state.get("shoots", [])
    stock = f"，按 cadence 存量≈{len(shoots) * cadence} 天" if shoots and cadence else ""
    lines.append(f"Buffer: {len(shoots)} 篇在途（拍了未发）{stock}")
    if shoots:
        earliest = min((_parse_iso(s.get("shot_at")) for s in shoots if _parse_iso(s.get("shot_at"))), default=None)
        if earliest:
            days = (now - earliest).days
            if days >= 14:
                lines.append(f"  ⚠ 最早一拍已 {days} 天未发——时效流失风险")

    due = pending_retro_lines(state, now)
    queued = len(state.get("pending_retros", []))
    lines.append(f"待复盘: 排队 {queued} 条" + ("" if due else "，无到期窗口"))
    lines.extend(due[:MAX_LIST_ITEMS])

    bm = state.get("benchmark_status", "none")
    if bm == "imported":
        lines.append(f"对标: {state.get('benchmark_name', '?')}（样本 {state.get('benchmark_sample_count', 0)}）")
    else:
        lines.append(f"对标: {bm}")
    lines.append(f"hooks: {'已装' if state.get('hooks_installed') else '未装（immutability 靠流程纪律 + predict Phase 0 自检）'}")
    lines.append("")

    if schema != LATEST_SCHEMA:
        lines.append(f"⚠ schema v{schema} ≠ v{LATEST_SCHEMA} → 先跑 /oracle-migrate 再继续本任务")
        lines.append("")

    readlist = TASK_READLIST.get(task)
    if readlist:
        lines.append(f"本任务（{task}）建议读取:")
        lines.extend(f"  - {item}" for item in readlist)
        lines.append("  - 其余文件按需，不默认全量加载")
    elif task:
        lines.append(f"（task={task} 无专属读取清单，按该子 skill 的 Inputs 段执行）")

    return "\n".join(lines)


def enforce_budget(text: str) -> str:
    data = text.encode("utf-8")
    if len(data) <= SUMMARY_BUDGET_BYTES:
        return text
    cut = data[: SUMMARY_BUDGET_BYTES - 32].decode("utf-8", errors="ignore")
    return cut + "\n\n…（摘要超 6KB 已截断——这是异常信号，检查 state 是否膨胀）"


def main() -> int:
    parser = argparse.ArgumentParser(description="oracle-bone 任务状态摘要（只读）")
    parser.add_argument("project_root", help="用户内容项目根目录")
    parser.add_argument("--task", default="", help="子 skill 后缀，如 predict / retro / status")
    parser.add_argument("--track", default=None, help="只看某一轨（按轨任务用）")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows GBK 控制台防 emoji 乱码
    except AttributeError:
        pass

    root = Path(args.project_root).expanduser()
    if not root.is_dir():
        print(f"项目根不存在: {root}", file=sys.stderr)
        return 3

    state, code = load_state(root)
    if state is None:
        if code == 2:
            print("state 不存在——用户未初始化。路由 /oracle-init，本脚本不代建。")
        else:
            print("state file 损坏（JSON 解析失败）。建议备份后重跑 /oracle-init。")
        return code

    summary = enforce_budget(build_summary(state, args.task, args.track))
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
