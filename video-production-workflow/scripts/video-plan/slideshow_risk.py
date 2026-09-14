"""分镜「幻灯片感」风险闸：给 storyboard.md 主表打 PPT 感分数。

在 /video-plan 结束状态（用户审批）之前运行。判定 reject 的分镜不得进入
审批闸——先按 findings 重排。打分维度为方法论事实，实现为本合集原生编写。

检查项（0-10 分，越高越像 PPT）：
  c1 意图缺失    「画面」列过短（<8 字），说明这镜没想清楚让观众明白什么
  c2 文字卡过载  动效条目里文字卡/标题卡占比过高（>40% 重罚）
  c3 节奏盲区    「剪辑/声音」列空白 = 没设计镜头怎么动、声音怎么接
  c4 同类连排    连续 ≥3 镜同拍摄形式+同覆盖模式，无节奏变化
  c5 泛化词      震撼/惊艳/未来感/丝滑…这类词没法翻译成可执行画面
  c6 B-roll 极端 完全没有（全口播干讲）或过半（画面堆积）

判定：score <3 pass / 3-5.5 warn / >5.5 reject

用法:
    python slideshow_risk.py <项目根>
输出:
    video scripts/slideshow_risk_report.json + 控制台报告
退出码: 0=pass 2=warn 1=reject
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BUZZWORDS = re.compile(
    r"震撼|惊艳|炫酷|高级感|大气|未来感|丝滑|沉浸式|革命性|颠覆|史诗级|完美呈现|极致"
)
TEXT_CARD_WORDS = ("文字卡", "标题卡", "关键词强调", "纯文字", "金句卡")
GEN_TYPES = ("Remotion", "HyperFrames", "动画设计", "Stock", "AI 图", "AI 视频")

C1_MAX, C2_MAX, C3_MAX, C4_MAX, C5_MAX = 3.0, 3.0, 1.5, 2.5, 2.0


def _cells(line: str) -> list:
    parts = [c.strip() for c in line.strip().strip("|").split("|")]
    return parts


def parse_storyboard(md_path: Path) -> list:
    """解析主表 markdown 表格 → [{镜号,时间,画面,旁白,字幕,剪辑,形式,覆盖}]。"""
    rows, in_table, header_seen = [], False, False
    for line in md_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("## ") and in_table:
            break
        if not s.startswith("|"):
            if in_table and not s.startswith("#"):
                continue
            in_table = False
            continue
        cells = _cells(s)
        if len(cells) < 8:
            continue
        if not header_seen:
            header_seen = "镜号" in cells[0]
            in_table = header_seen
            continue
        if set(cells[0]) <= {"-", ":", " "}:
            continue
        in_table = True
        rows.append({
            "shot": cells[0], "time": cells[1], "visual": cells[2],
            "narration": cells[3], "subtitle": cells[4], "edit": cells[5],
            "format": cells[6], "coverage": cells[7] if len(cells) > 7 else "",
        })
    return rows


def score(rows: list) -> dict:
    n = len(rows)
    findings = []
    total = 0.0

    # c1 意图缺失
    weak = [r for r in rows if len(r["visual"]) < 8]
    if n:
        ratio = len(weak) / n
        s = min(ratio * 4, C1_MAX)
        total += s
        if weak:
            findings.append({
                "check": "意图缺失", "score": round(s, 2),
                "detail": f"{len(weak)}/{n} 镜画面描述过短，没想清楚让观众明白什么",
                "shots": [r["shot"] for r in weak][:12],
            })

    # c2 文字卡过载（只统计生成类条目）
    gen = [r for r in rows if any(k in r["format"] for k in GEN_TYPES)]
    cards = [r for r in gen if any(k in (r["visual"] + r["subtitle"]) for k in TEXT_CARD_WORDS)]
    if gen:
        ratio = len(cards) / len(gen)
        s = min(ratio * 5, C2_MAX)
        total += s
        if cards:
            findings.append({
                "check": "文字卡过载", "score": round(s, 2),
                "detail": f"生成类条目 {len(cards)}/{len(gen)} 是文字卡/标题卡——抽象关键词不落通用文字卡",
                "shots": [r["shot"] for r in cards][:12],
            })

    # c3 节奏盲区
    blind = [r for r in rows if not r["edit"]]
    if n:
        ratio = len(blind) / n
        s = min(ratio * 2, C3_MAX)
        total += s
        if blind:
            findings.append({
                "check": "节奏盲区", "score": round(s, 2),
                "detail": f"{len(blind)}/{n} 镜「剪辑/声音」列空白——镜头怎么动、声音怎么接没有设计",
                "shots": [r["shot"] for r in blind][:12],
            })

    # c4 同类连排（连续 ≥3 同形式+同覆盖）
    runs = []
    i = 0
    while i < len(rows):
        j = i
        while j + 1 < len(rows) and rows[j + 1]["format"] == rows[i]["format"] \
                and rows[j + 1]["coverage"] == rows[i]["coverage"]:
            j += 1
        if j - i + 1 >= 3:
            runs.append((rows[i]["shot"], rows[j]["shot"], rows[i]["format"], j - i + 1))
        i = j + 1
    s = min(len(runs) * 0.7, C4_MAX)
    total += s
    if runs:
        findings.append({
            "check": "同类连排", "score": round(s, 2),
            "detail": "连续 ≥3 镜同形式同覆盖，无节奏变化",
            "runs": [f"{a}~{b}（{c}×{d}）" for a, b, c, d in runs][:8],
        })

    # c5 泛化词
    buzz = [(r["shot"], BUZZWORDS.findall(r["visual"] + r["narration"])) for r in rows]
    buzz = [(shot, ws) for shot, ws in buzz if ws]
    hit_count = sum(len(ws) for _, ws in buzz)
    s = min(hit_count * 0.4, C5_MAX)
    total += s
    if buzz:
        findings.append({
            "check": "泛化词", "score": round(s, 2),
            "detail": "情绪词没法翻译成可执行画面——改写成动作因果（谁、动什么、观众看到什么）",
            "hits": [f"{shot}: {'、'.join(ws)}" for shot, ws in buzz][:10],
        })

    # c6 B-roll 极端
    if n:
        gen_ratio = len(gen) / n
        if gen_ratio == 0:
            total += 2.5
            findings.append({
                "check": "B-roll 极端（缺失）", "score": 2.5,
                "detail": "全片没有任何 B-roll/动效条目——纯口播干讲，先过 /b-roll-finder 机会分析",
                "shots": [],
            })
        elif gen_ratio > 0.5:
            total += 1.5
            findings.append({
                "check": "B-roll 极端（堆积）", "score": 1.5,
                "detail": f"超过半数镜头（{len(gen)}/{n}）是生成/B-roll 条目——口播主导被画面堆积淹没",
                "shots": [],
            })

    total = round(min(total, 10.0), 2)
    verdict = "reject" if total > 5.5 else ("warn" if total >= 3.0 else "pass")
    return {
        "score": total, "verdict": verdict,
        "shots_total": n, "findings": findings,
    }


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        sys.exit(0)
    project = Path(sys.argv[1])
    md = project / "video scripts" / "storyboard.md"
    if not md.exists():
        print(f"[X] 找不到 {md}")
        sys.exit(1)

    rows = parse_storyboard(md)
    if not rows:
        print("[X] 主表没有解析到镜头行——检查 storyboard.md 的「## 主表」表格格式")
        sys.exit(1)

    result = score(rows)
    report_path = project / "video scripts" / "slideshow_risk_report.json"
    report_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    tag = {"pass": "✅", "warn": "⚠️ ", "reject": "❌"}[result["verdict"]]
    print(f"{tag} 幻灯片风险分: {result['score']}/10 → {result['verdict']}（{result['shots_total']} 镜）")
    for f in result["findings"]:
        print(f"  [{f['check']}] +{f['score']} {f['detail']}")
    print(f"报告: {report_path}")
    sys.exit({"pass": 0, "warn": 2, "reject": 1}[result["verdict"]])


if __name__ == "__main__":
    main()
