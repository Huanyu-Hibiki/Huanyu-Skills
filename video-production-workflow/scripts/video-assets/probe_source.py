"""素材源技术准入探针：下载完成后、进管线前先 ffprobe 实测，不信任标称。

实战里 stock 平台的「large / HD」档经常是放大档（实际 640×360）或长关键帧
间隔（渲染时 seek 冻结）。本探针实测：最小边分辨率、帧率、时长、关键帧
最大间隔（扫描前 120 秒）。不达标的素材进「未完成清单」或走升级链，
不进渲染队列。

用法:
    python probe_source.py <素材1> [素材2 ...] [--min-side 1080] [--min-duration 3] [--max-kf-gap 5.0]
退出码: 0=全部通过 1=存在 fail
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def ffprobe_stream(video: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
         "-show_streams", str(video)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr[:200])
    return json.loads(out.stdout or "{}")


def keyframe_gap(video: Path, scan_s: int = 120) -> float | None:
    """只读关键帧时间戳（skip_frame nokey），返回前 scan_s 秒内的最大间隔。"""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-skip_frame", "nokey",
         "-show_entries", "frame=pts_time", "-of", "csv=p=0",
         "-read_intervals", f"%+{scan_s}", str(video)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    ts = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ts.append(float(line))
        except ValueError:
            continue
    if len(ts) < 2:
        return None
    gaps = [b - a for a, b in zip(ts, ts[1:])]
    return round(max(gaps), 3)


def probe_one(video: Path, min_side: float, min_dur: float, max_gap: float) -> dict:
    r = {"file": video.name, "checks": [], "verdict": "pass"}
    try:
        data = ffprobe_stream(video)
    except RuntimeError as e:
        r["verdict"] = "fail"
        r["checks"].append({"check": "容器可读", "ok": False, "detail": str(e)})
        return r
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if not v:
        r["verdict"] = "fail"
        r["checks"].append({"check": "视频流", "ok": False, "detail": "无视频流"})
        return r

    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    side = min(w, h)
    ok = side >= min_side
    r["checks"].append({
        "check": "实测分辨率", "ok": ok,
        "detail": f"{w}x{h}（最小边 {side}px vs 要求 ≥{int(min_side)}px）"
                  + ("" if ok or side >= 720 else " ——疑似放大假高清") ,
    })
    if not ok:
        r["verdict"] = "fail"

    num, den = (v.get("r_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den) if float(den) else 0.0
    dur = float(data.get("format", {}).get("duration", 0) or 0)
    ok = dur >= min_dur
    r["checks"].append({"check": "时长", "ok": ok,
                        "detail": f"{dur:.1f}s vs 要求 ≥{min_dur}s" + ("" if ok else "（不够剪）")})
    if not ok:
        r["verdict"] = "fail"

    r["fps"] = round(fps, 3)
    gap = keyframe_gap(video)
    if gap is None:
        r["checks"].append({"check": "关键帧间隔", "ok": True, "detail": "关键帧过少/无法测量（短素材），跳过"})
    else:
        ok = gap <= max_gap
        r["checks"].append({
            "check": "关键帧间隔", "ok": ok,
            "detail": f"max {gap}s vs ≤{max_gap}s"
                      + ("" if ok else " ——渲染 seek 易冻结，重编码："
                         "ffmpeg -i IN -c:v libx264 -r 30 -g 30 -keyint_min 30 -sc_threshold 0 -movflags +faststart OUT"),
        })
        if not ok and r["verdict"] == "pass":
            r["verdict"] = "warn"
    return r


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    files, min_side, min_dur, max_gap = [], 1080.0, 3.0, 5.0
    args = sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        print(__doc__)
        sys.exit(0)
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--min-side" and i + 1 < len(args):
            min_side = float(args[i + 1]); i += 2
        elif a == "--min-duration" and i + 1 < len(args):
            min_dur = float(args[i + 1]); i += 2
        elif a == "--max-kf-gap" and i + 1 < len(args):
            max_gap = float(args[i + 1]); i += 2
        else:
            files.append(Path(a)); i += 1

    any_fail = False
    for f in files:
        if not f.exists():
            print(json.dumps({"file": f.name, "verdict": "fail",
                              "checks": [{"check": "文件存在", "ok": False, "detail": str(f)}]},
                             ensure_ascii=False))
            any_fail = True
            continue
        r = probe_one(f, min_side, min_dur, max_gap)
        any_fail |= r["verdict"] == "fail"
        mark = {"pass": "✅", "warn": "⚠️ ", "fail": "❌"}[r["verdict"]]
        print(f"{mark} {r['file']}")
        for c in r["checks"]:
            print(f"    {'✅' if c['ok'] else '❌'} {c['check']}: {c['detail']}")
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
