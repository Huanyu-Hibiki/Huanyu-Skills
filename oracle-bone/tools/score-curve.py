#!/usr/bin/env python3
"""oracle-bone score-curve — 预测精度收敛曲线。

扫描项目内所有作品的 prediction 文件，提取 (predicted_composite, bucket, 中枢, 实绩)
配对，按轨道分组输出收敛表 + 简单文本曲线。供 oracle-bump / oracle-status 参考。

用法:
  python score-curve.py <project_root> [--track <id>] [--json]

输出:
  - 每轨: 样本数 / 平均绝对偏差 / 偏差方向序列 / bucket 命中率
  - JSON 模式输出结构化数据（供看板/工具消费）
"""

import argparse
import json
import re
import sys
from pathlib import Path


def find_predictions(root: Path):
    """作品目录布局: <NNN>_<标题>/predictions/*.md"""
    for pred_dir in root.glob("[0-9][0-9][0-9]_*/predictions"):
        for f in pred_dir.glob("*.md"):
            yield f
    # 兼容平铺布局（历史项目）
    flat = root / "predictions"
    if flat.is_dir():
        for f in flat.glob("*.md"):
            if not any(p.parent == f.parent for p in []):
                yield f


HEADER_RE = {
    "track": re.compile(r"^\*\*Track\*\*:\s*(.+)$", re.M),
    "composite": re.compile(r"composite=\*{0,2}([\d.]+)", re.M),
    "central": re.compile(r"中枢\s*~?\s*([\d.]+)", re.M),
    "published": re.compile(r"^\*\*Published at\*\*:\s*(.+)$", re.M),
}

PRED_SECTION_RE = re.compile(r"^## 预测(?: v\d+)?\s*$", re.M)


def parse_prediction(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    out = {"file": str(path)}
    for key, rx in HEADER_RE.items():
        m = rx.search(text)
        out[key] = m.group(1).strip() if m else None
    # 提取复盘段实绩（首行 "播放：X" 或轨道指标）
    retro = text.split("## 复盘", 1)
    out["has_retro"] = len(retro) > 1 and len(retro[1].strip()) > 20
    m = re.search(r"播放[：:]\s*([\d.]+)\s*([w万k千]?)", text)
    if m:
        num = float(m.group(1))
        unit = m.group(2)
        mult = {"w": 10000, "万": 10000, "k": 1000, "千": 1000}.get(unit, 1)
        out["actual_views"] = int(num * mult)
    else:
        out["actual_views"] = None
    out["reconstructed"] = "Reconstructed" in text
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="项目根（.oracle-state.json 所在目录）")
    ap.add_argument("--track", help="只看某轨道")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    root = Path(args.root)
    if not (root / ".oracle-state.json").exists():
        print(f"❌ {root} 不是 oracle-bone 项目（缺 .oracle-state.json）", file=sys.stderr)
        sys.exit(1)

    samples = []
    for f in find_predictions(root):
        try:
            s = parse_prediction(f)
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ 解析失败 {f}: {e}", file=sys.stderr)
            continue
        if s.get("reconstructed") or not s.get("has_retro"):
            continue  # 校准样本 only
        if args.track and s.get("track") != args.track:
            continue
        if s.get("composite") and s.get("actual_views"):
            samples.append(s)

    if not samples:
        print("无有效校准样本（需完整复盘 + 实绩数据）")
        return

    by_track = {}
    for s in samples:
        by_track.setdefault(s["track"] or "unknown", []).append(s)

    if args.as_json:
        print(json.dumps({"samples": samples}, ensure_ascii=False, indent=2))
        return

    print(f"📈 score-curve — {len(samples)} 个校准样本，{len(by_track)} 轨\n")
    for track, items in sorted(by_track.items()):
        n = len(items)
        deviations = []
        directions = []
        hits = 0
        for it in items:
            comp = float(it["composite"])
            actual = it["actual_views"]
            # 有中枢才算偏差
            if it.get("central"):
                central_v = float(it["central"])
                m = re.search(r"([w万k千]?)$", it["central"])
                unit = m.group(1) if m else ""
                mult = {"w": 10000, "万": 10000, "k": 1000, "千": 1000}.get(unit, 1)
                central_abs = central_v * mult
                if central_abs > 0:
                    dev = (actual - central_abs) / central_abs
                    deviations.append(abs(dev))
                    directions.append("low" if actual > central_abs else "high")
            # bucket 粗命中：预测 bucket 与实绩档位（信息有限，仅参考）
        avg_dev = sum(deviations) / len(deviations) if deviations else None
        streak = 0
        if directions:
            from collections import Counter
            c = Counter(directions)
            streak = c.most_common(1)[0][1]
        print(f"─ 轨道 {track}: {n} 样本")
        if avg_dev is not None:
            print(f"    平均绝对偏差: {avg_dev:.0%}（基于 {len(deviations)} 个有中枢样本）")
        if directions:
            print(f"    方向分布: {'/'.join(directions)}")
            if streak >= 3:
                print(f"    ⚠️ 同向偏差 {streak} 次 → 建议跑 /oracle-bump --track {track}")
        print()

    print("注：中枢单位解析有限，精确偏差请以 prediction 复盘段为准。")


if __name__ == "__main__":
    main()
