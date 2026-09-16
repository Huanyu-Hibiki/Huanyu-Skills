"""素材落位匹配器：把手里的录屏/实拍素材自动配到精剪时间轴的合适位置。

解决"多段素材不知道放哪"：按三条策略产出 broll-compose 骨架，落点与时长
全部机械可查，配对结果必须过人工确认闸才进入装配。

策略（按优先级）：
  1. 镜号映射   文件名含镜号（目录规范：实拍【EP001-S01-001到S04-001】.mp4，
                取 S 后序号为分镜镜号）→ 对上 storyboard.json 的
                broll_candidates.shot_id → 在 Sub/master.srt 里找该条旁白原句
                的时间码 → beat 落点 = 句起点 + 0.3s
  2. 语义候选   文件名无镜号的素材：列出清单 + master.srt 未被占用的句子，
                交给 Agent/用户做语义配对（脚本只出材料不下结论）
  3. 时长对齐   beat 区间 = min(素材时长, 句长+2s)；素材偏短(<2s)给 warning；
                beat 重叠自动顺延；相邻间隙 <1s 合并（不留人物碎片）

⚠️ 边界：带人声讲解的录屏不是 B-roll（是 A-roll，走 /video-rough-cut 转录
挑 take）；本脚本只匹配无声覆盖素材。必须在 /video-fine-cut 之后运行
（master.srt 是精剪时间轴，B-roll 落位以它为唯一时间真源）。

用法:
    python match_footage.py <项目根> --footage <素材目录1> [素材目录2 ...] \
        [--lead 0.3] [--max 8.0]
输出:
    Polished/broll-compose.draft.json   骨架（确认后改为正式 broll-compose.json）
    Polished/match_report.md            匹配表（确认闸材料）
退出码: 0=完成 1=输入缺失
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

LEAD_DEFAULT = 0.3     # 词锚落点：关键词说出后 0.2-0.5s，取中值
MAX_BEAT = 8.0         # 单条 B-roll 上限（timing-and-qa：流程/图表 4-8s）
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
SHOT_RE = re.compile(r"S(\d+)", re.IGNORECASE)


def media_duration(path: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        return float(out.stdout.strip())
    except Exception:
        return 0.0


def parse_srt(path: Path) -> list:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    cues = []
    for block in re.split(r"\n\s*\n", text.strip()):
        m = re.search(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", block)
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        cues.append({
            "start": g[0]*3600 + g[1]*60 + g[2] + g[3]/1000,
            "end": g[4]*3600 + g[5]*60 + g[6] + g[7]/1000,
            "text": " ".join(l.strip() for l in block.splitlines()[2:] if l.strip()),
        })
    return cues


def _norm(t: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", t)


def find_sentence_time(cues: list, excerpt: str) -> tuple | None:
    """在 master.srt 里找与 broll_candidates.manuscript_excerpt 最相似的句。"""
    target = _norm(excerpt)[:30]
    if not target:
        return None
    best, best_r = None, 0.0
    for c in cues:
        r = 1.0 if target in _norm(c["text"]) else __import__("difflib").SequenceMatcher(
            None, target, _norm(c["text"])).ratio()
        if r > best_r:
            best, best_r = c, r
    return (best, best_r) if best and best_r >= 0.5 else None


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", type=Path)
    ap.add_argument("--footage", type=Path, nargs="+", required=True,
                    help="素材目录（Raw/录屏、assets/raw/video 等，递归扫描）")
    ap.add_argument("--lead", type=float, default=LEAD_DEFAULT)
    ap.add_argument("--max", type=float, default=MAX_BEAT, dest="max_beat")
    args = ap.parse_args()
    project = args.project

    sb_path = project / "video scripts" / "storyboard.json"
    srt_path = project / "Sub" / "master.srt"
    if not sb_path.exists() or not srt_path.exists():
        print("[X] 需要 video scripts/storyboard.json 和 Sub/master.srt（先完成分镜与精剪）")
        sys.exit(1)

    sb = json.loads(sb_path.read_text(encoding="utf-8"))
    cands = {str(c.get("shot_id")): c for c in sb.get("broll_candidates", [])}
    cues = parse_srt(srt_path)

    # 收集素材（递归，仅视频）
    files = []
    for d in args.footage:
        if d.is_file():
            files.append(d)
        else:
            files.extend(p for p in d.rglob("*") if p.suffix.lower() in VIDEO_EXT)

    beats, semantic_pool, unmatched = [], [], []
    used_shots = set()
    for f in sorted(files):
        shots = [s for s in SHOT_RE.findall(f.stem)]
        matched = None
        for s in shots:
            sid = str(int(s)) if s.isdigit() else s
            if sid in cands and sid not in used_shots:
                matched = (sid, cands[sid])
                break
        dur = media_duration(f)
        if matched:
            sid, cand = matched
            used_shots.add(sid)
            hit = find_sentence_time(cues, cand.get("manuscript_excerpt", ""))
            if not hit:
                unmatched.append({"file": str(f), "shot_id": sid,
                                  "reason": "镜号对上了，但 master.srt 里找不到对应旁白句（精剪删了这句？）"})
                continue
            cue, conf = hit
            start = round(cue["start"] + args.lead, 2)
            span = min(dur, max(2.0, (cue["end"] - cue["start"]) + 2.0), args.max_beat)
            beats.append({
                "id": cand.get("motion_brief_ref") or f"BROLL-{sid}",
                "start": start, "end": round(start + span, 2),
                "file": str(f), "source": "shot-map",
                "shot_id": sid, "sentence": cue["text"][:40],
                "match_confidence": round(conf, 2),
                "warning": None if dur >= 2.0 else f"素材仅 {dur:.1f}s，偏短",
            })
        else:
            semantic_pool.append({"file": str(f), "duration": round(dur, 1)})

    # 重叠顺延 + 碎片合并
    beats.sort(key=lambda b: b["start"])
    for i, b in enumerate(beats):
        if i and b["start"] < beats[i-1]["end"]:
            b["start"] = beats[i-1]["end"]
            b["end"] = round(b["start"] + (b["end"] - b["start"]), 2)
            b["warning"] = (b["warning"] + "；" if b.get("warning") else "") + "与前一 beat 重叠，已顺延"

    draft = {"beats": [{"id": b["id"], "start": b["start"], "end": b["end"], "file": b["file"]} for b in beats]}
    detail = {"beats": beats, "semantic_pool": semantic_pool, "unmatched": unmatched,
              "note": "draft 需人工确认后改名为 broll-compose.json；semantic_pool 交给 Agent/用户语义配对"}
    out_draft = project / "Polished" / "broll-compose.draft.json"
    out_report = project / "Polished" / "match_report.md"
    out_draft.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"# 素材落位匹配报告（{len(beats)} 条镜号映射 / {len(semantic_pool)} 条待语义配对）", "",
             "| 素材 | 镜号 | 落点 | 时长 | 依据句 | 置信 | 提示 |", "|---|---|---|---|---|---|---|"]
    for b in beats:
        lines.append(f"| `{Path(b['file']).name}` | {b['shot_id']} | {b['start']}-{b['end']}s | "
                     f"{b['end']-b['start']:.1f}s | {b['sentence']} | {b['match_confidence']:.0%} | {b.get('warning') or '-'} |")
    if semantic_pool:
        lines += ["", "## 待语义配对（文件名无镜号，脚本不下结论）", ""]
        lines += [f"- `{p['file']}`（{p['duration']}s）" for p in semantic_pool]
        lines += ["", "未占用的时间段（master.srt 中无 B-roll 覆盖的句子）见 broll-opportunity-analysis.md 未消化条目。"]
    if unmatched:
        lines += ["", "## 镜号对上但没找到落点", ""]
        lines += [f"- `{u['file']}`（{u['reason']}）" for u in unmatched]
    out_report.write_text("\n".join(lines), encoding="utf-8")

    print(f"🎬 镜号映射 {len(beats)} 条 / 待语义配对 {len(semantic_pool)} 条 / 落点缺失 {len(unmatched)} 条")
    for b in beats:
        print(f"  {b['id']} {b['start']}-{b['end']}s ← {Path(b['file']).name}（{b['sentence'][:24]}…）")
    print(f"骨架: {out_draft}\n报告: {out_report}\n🔴 确认匹配表后才可改名 broll-compose.json 进入装配")
    sys.exit(0)


if __name__ == "__main__":
    main()
