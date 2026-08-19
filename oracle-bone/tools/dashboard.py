#!/usr/bin/env python3
"""oracle-bone dashboard — 分析引擎：五维指标提取 + 快照 diff + quantile 规则建议。

供 oracle-compass-retro（五维闸门 + A/B 分类 + 下一期动作）和 oracle-status 消费。
设计参考 data-scientist-community（AGPL-3.0）的 quantile 规则思路，clean-room 重写，
建议措辞与 oracle-bone 体系（轨道 / review skill / derivative）对齐。

用法:
  python dashboard.py --db content-analytics.db [--markdown]
"""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from snapshot_store import latest_diff, _num  # noqa: E402

FIVE_DIM_KEYS = ["封面点击率", "平均播放时长", "完播率", "跳出率", "5s完播率"]


def extract_five_dim(unified_rows):
    """从归一行提取五维增量指标（值保留原文：'45%' / '12s'）。"""
    out = []
    for r in unified_rows:
        item = {"平台作品键": r.get("平台作品键", ""), "标题": r.get("标题", ""), "平台": r.get("平台", "")}
        for k in FIVE_DIM_KEYS:
            item[k] = str(r.get(k, "") or "")
        item["跳出率口径"] = str(r.get("跳出率口径", "") or "")
        out.append(item)
    return out


def _pct(v):
    try:
        return float(str(v).replace("%", ""))
    except (ValueError, TypeError):
        return None


def quantile_recommendations(diff_rows, top_n=3):
    """在 plays>0 样本上算分位阈值 → 规则建议（每条带 why + actions + 证据作品）。"""

    def valid_plays(r):
        p = _num(r.get("有效播放"))
        return p if p > 0 else _num(r.get("播放量")) or _num(r.get("阅读量"))

    nonzero = [r for r in diff_rows if valid_plays(r) > 0]
    if len(nonzero) < 4:
        return [], {"note": f"样本 {len(nonzero)} 条 <4，分位阈值不稳定，暂不给规则建议"}

    plays = sorted(valid_plays(r) for r in nonzero)
    ers = sorted(r.get("互动率", 0) for r in nonzero)

    def pct(series, q):
        idx = min(int(q * len(series)), len(series) - 1)
        return series[idx]

    thresholds = {
        "median_plays": pct(plays, 0.5), "p90_plays": pct(plays, 0.9),
        "p25_engagement_rate": round(pct(ers, 0.25), 4), "p75_engagement_rate": round(pct(ers, 0.75), 4),
        "zero_plays_works": sum(1 for r in diff_rows if valid_plays(r) <= 0),
    }

    def brief(r):
        return {"标题": r.get("标题", ""), "平台": r.get("平台", ""), "播放": valid_plays(r), "互动率": r.get("互动率", 0)}

    recs = []

    high_eng_low_play = [r for r in nonzero
                         if valid_plays(r) <= thresholds["median_plays"]
                         and r.get("互动率", 0) >= thresholds["p75_engagement_rate"]]
    high_eng_low_play.sort(key=lambda r: r.get("互动率", 0), reverse=True)
    if high_eng_low_play:
        recs.append({
            "id": "high_engagement_low_play",
            "title": "高互动但低播放：内容共鸣在，分发/包装拖后腿",
            "why": f"互动率 ≥ p75（{thresholds['p75_engagement_rate']:.1%}）但播放 ≤ 中位数（{thresholds['median_plays']}）——观众爱看但没被送进去，问题多半在标题/封面/分发时机，不在内容质量。",
            "actions": [
                "跑 /oracle-title 换标题结构再发一次变体（同内容不同包装）",
                "跑 /oracle-derivative 把高互动作品拆成图文形态二次分发",
                "检查封面点击率（五维闸门）——低则先改封面再谈内容",
            ],
            "examples": [brief(r) for r in high_eng_low_play[:top_n]],
        })

    low_eng_high_play = [r for r in nonzero
                         if valid_plays(r) >= thresholds["p90_plays"]
                         and r.get("互动率", 0) <= thresholds["p25_engagement_rate"]]
    low_eng_high_play.sort(key=valid_plays, reverse=True)
    if low_eng_high_play:
        recs.append({
            "id": "high_play_low_engagement",
            "title": "高播放但低互动：有流量没转化",
            "why": f"播放进前 10%（≥{thresholds['p90_plays']}）但互动率落后 25%（≤{thresholds['p25_engagement_rate']:.1%}）——算法给了量，观众没开口，缺互动触发器或价值兑现。",
            "actions": [
                "下一条 draft 的 ## 互动设计 段必选评论触发器（选择题优先，门槛最低）",
                "跑 /oracle-who-for 检查价值主张是否对得上受众（Q4 价值虚是最常见根因）",
                "发布后 5 分钟内置顶评论（/oracle-pinned-comment）先撑起评论氛围",
            ],
            "examples": [brief(r) for r in low_eng_high_play[:top_n]],
        })

    gainers = [r for r in diff_rows if not r.get("is_new") and _num(r.get("播放增量")) > 0]
    gainers.sort(key=lambda r: _num(r.get("播放增量")), reverse=True)
    if gainers:
        recs.append({
            "id": "top_gainers",
            "title": "两次采集间增长最快的旧作品：正在被算法重新推荐",
            "why": "这些旧作品的播放增量最高——平台在二次分发或外部流量带动，拆解它们比做新选题性价比高。",
            "actions": [
                "逐条拆解标题结构 / 开头 3 秒 / 节奏点（/oracle-apprentice 拜师自己的爆款）",
                "同主题做系列（合集 + 固定栏目名），承接二推流量",
            ],
            "examples": [brief(r) | {"播放增量": _num(r.get("播放增量"))} for r in gainers[:top_n]],
        })

    return recs, thresholds


def classify_ab(five_dim_rows):
    """五维指标 → A 类（选题）/ B 类（表达）粗分类（数据缺失的维度跳过）。"""
    out = []
    for r in five_dim_rows:
        click = _pct(r.get("封面点击率"))
        bounce = _pct(r.get("跳出率"))
        cls = []
        if click is not None and click < 5.0:
            cls.append("A 类信号：封面点击率偏低")
        if bounce is not None and bounce > 60.0:
            cls.append("A 类信号：跳出率高，开头没留住")
        if not cls:
            cls.append("五维数据不足或正常（后台无该指标则跳过 A/B 粗分）")
        out.append({**r, "粗分类": cls})
    return out


def render_markdown(result):
    lines = ["# 数据看板（oracle-bone dashboard）", ""]
    meta = result.get("latest_run") or {}
    lines.append(f"- 最新采集：run {meta.get('run_id')} @ {meta.get('run_at')}")
    if result.get("prev_run"):
        lines.append(f"- 对比基线：run {result['prev_run'].get('run_id')} @ {result['prev_run'].get('run_at')}")
    else:
        lines.append("- ⚠️ 首次采集（无对比基线，只有当期快照）")
    lines.append("")

    recs = result.get("recommendations", [])
    if not recs:
        lines.append(result.get("thresholds", {}).get("note", "暂无规则建议。"))
    for rec in recs:
        lines += [f"## {rec['title']}", "", rec["why"], ""]
        for a in rec["actions"]:
            lines.append(f"- {a}")
        lines.append("")
        if rec.get("examples"):
            lines.append("| 标题 | 平台 | 播放 | 互动率 |")
            lines.append("|---|---|---|---|")
            for e in rec["examples"]:
                lines.append(f"| {e.get('标题','')[:30]} | {e.get('平台','')} | {e.get('播放',0)} | {e.get('互动率',0):.1%} |")
            lines.append("")

    th = result.get("thresholds") or {}
    if th.get("median_plays") is not None and recs:
        lines += ["## 分位阈值", "",
                  f"- 播放中位数: {th.get('median_plays')} · p90: {th.get('p90_plays')}",
                  f"- 互动率 p25: {th.get('p25_engagement_rate', 0):.1%} · p75: {th.get('p75_engagement_rate', 0):.1%}",
                  f"- 零播放作品（隐藏/异常）: {th.get('zero_plays_works', 0)} 条", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="content-analytics.db 路径")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--unified", default="", help="最新 unified.json（可选：附加五维指标提取）")
    args = ap.parse_args()

    diff = latest_diff(args.db)
    if not diff.get("ok"):
        print(json.dumps(diff, ensure_ascii=False))
        return

    recs, thresholds = quantile_recommendations(diff.get("rows", []))
    result = {**diff, "recommendations": recs, "thresholds": thresholds}

    if args.unified:
        payload = json.loads(Path(args.unified).read_text(encoding="utf-8"))
        result["five_dim"] = extract_five_dim(payload.get("rows", []))
        result["ab_classification"] = classify_ab(result["five_dim"])

    if args.markdown:
        print(render_markdown(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
