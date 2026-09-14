"""旁白-画面对齐断言：每句字幕的 ±窗口内必须有画面事件（切点或 B-roll 起点）。

装配 QA 用。数据全部来自既有产物：Sub/master.srt 的句级 cue ×
Rough/edl.json 的剪辑点 + Polished/broll-compose.json 的 B-roll 起点。
「这句话说到时画面上有没有对应的东西」由机械检查回答，不靠人眼。

用法:
    python check_cue_alignment.py <项目根> [--window 1.0] [--max-uncovered 0.15]
退出码: 0=通过 1=未覆盖率超阈值 2=找不到输入（advisory，不阻塞）
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def parse_srt(path: Path) -> list:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    cues = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [l for l in block.splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        m = re.search(
            r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", block
        )
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        cues.append({"start": start, "end": end,
                     "text": " ".join(lines[2:])[:40]})
    return cues


def collect_events(project: Path) -> list:
    events = []
    edl_path = project / "Rough" / "edl.json"
    if edl_path.exists():
        edl = json.loads(edl_path.read_text(encoding="utf-8"))
        for key in ("clips", "segments", "cuts"):
            for e in edl.get(key, []) or []:
                t = e.get("target-start", e.get("target_start", e.get("start")))
                if isinstance(t, (int, float)) and t >= 0:
                    events.append(round(float(t), 3))
    compose_path = project / "Polished" / "broll-compose.json"
    if compose_path.exists():
        for b in json.loads(compose_path.read_text(encoding="utf-8")).get("beats", []):
            if isinstance(b.get("start"), (int, float)):
                events.append(round(float(b["start"]), 3))
    return sorted(set(events))


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    project = Path(sys.argv[1])
    window, max_uncovered = 1.0, 0.15
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a == "--window" and i + 1 < len(args):
            window = float(args[i + 1])
        elif a == "--max-uncovered" and i + 1 < len(args):
            max_uncovered = float(args[i + 1])

    srt = project / "Sub" / "master.srt"
    if not srt.exists():
        print(json.dumps({"status": "no_input", "note": "找不到 Sub/master.srt"}, ensure_ascii=False))
        sys.exit(2)
    cues = parse_srt(srt)
    events = collect_events(project)
    if not events:
        print(json.dumps({"status": "no_input", "note": "edl.json / broll-compose.json 都没有画面事件"},
                         ensure_ascii=False))
        sys.exit(2)

    uncovered = []
    for c in cues:
        if not any(c["start"] - window <= t <= c["end"] + window for t in events):
            uncovered.append(c)

    ratio = round(len(uncovered) / len(cues), 3) if cues else 0.0
    result = {
        "status": "pass" if ratio <= max_uncovered else "fail",
        "cues": len(cues), "events": len(events),
        "window_s": window, "uncovered_ratio": ratio,
        "uncovered": uncovered[:20],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
