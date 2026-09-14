"""成片技术探针：发布前的最低完备性机检（结构化输出，评审材料之一）。

检查项（全部可判定，缺数据本身算失败）：
  1. 容器可读、时长与预期差 ≤5%（--expect-duration 传入粗剪/装配目标时长）
  2. 音轨存在；峰值电平（volumedetect max_volume）>-0.5dBFS 判逼近削波
  3. 四点抽帧（10%/35%/65%/90%）成功落盘，供人工/独立评审拼图用

用法:
    python final_probe.py <成片.mp4> [--expect-duration 95.2] [--frames-dir 目录]
输出: Polished/final_probe.json + 抽帧文件
退出码: 0=pass 1=fail
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


def ffprobe_json(video: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", str(video)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if out.returncode != 0:
        raise RuntimeError(f"ffprobe 失败: {out.stderr[:200]}")
    return json.loads(out.stdout or "{}")


def volumedetect(video: Path) -> dict | None:
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(video),
         "-map", "0:a:0", "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    m = re.search(r"max_volume:\s*(-?[\d.]+)\s*dB", out.stderr)
    n = re.search(r"mean_volume:\s*(-?[\d.]+)\s*dB", out.stderr)
    if not m:
        return None
    return {"max_volume_db": float(m.group(1)),
            "mean_volume_db": float(n.group(1)) if n else None}


def grab_frame(video: Path, t: float, dest: Path) -> bool:
    r = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(video),
         "-frames:v", "1", str(dest)],
        capture_output=True,
    )
    return r.returncode == 0 and dest.exists()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = [a for a in sys.argv[1:]]
    if not args or args[0] in ("--help", "-h"):
        print(__doc__)
        sys.exit(0)
    video = Path(args[0])
    if not video.exists():
        print(f"[X] 找不到 {video}")
        sys.exit(1)

    expect = None
    frames_dir = video.parent / "verify" / "final-probe"
    for i, a in enumerate(args):
        if a == "--expect-duration" and i + 1 < len(args):
            expect = float(args[i + 1])
        elif a == "--frames-dir" and i + 1 < len(args):
            frames_dir = Path(args[i + 1])
    frames_dir.mkdir(parents=True, exist_ok=True)

    checks, ok = [], True
    try:
        probe = ffprobe_json(video)
    except RuntimeError as e:
        print(json.dumps({"status": "fail", "error": str(e)}, ensure_ascii=False))
        sys.exit(1)

    v = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), None)
    duration = float(probe.get("format", {}).get("duration", 0) or 0)

    checks.append({"check": "视频流存在", "ok": v is not None,
                   "detail": f"{v.get('codec_name')} {v.get('width')}x{v.get('height')}" if v else "缺失"})
    ok &= v is not None

    checks.append({"check": "音轨存在", "ok": a is not None,
                   "detail": f"{a.get('codec_name')} {a.get('sample_rate')}Hz" if a else "缺失（成片必须有声）"})
    ok &= a is not None

    if expect and duration:
        drift = abs(duration - expect) / expect
        passed = drift <= 0.05
        checks.append({"check": "时长核对", "ok": passed,
                       "detail": f"实际 {duration:.2f}s vs 预期 {expect:.2f}s（差 {drift:.1%}）"})
        ok &= passed
    elif expect:
        checks.append({"check": "时长核对", "ok": False, "detail": "容器读不到时长"})
        ok = False

    vol = volumedetect(video) if a else None
    if a:
        peak_ok = vol is not None and vol["max_volume_db"] <= -0.5
        checks.append({"check": "峰值电平", "ok": peak_ok,
                       "detail": (f"max {vol['max_volume_db']}dB / mean {vol['mean_volume_db']}dB"
                                  if vol else "volumedetect 无输出") + ("" if peak_ok else " ——逼近削波，回查混音")})
        ok &= peak_ok

    frames = []
    if v and duration:
        for tag, pct in (("p10", 0.10), ("p35", 0.35), ("p65", 0.65), ("p90", 0.90)):
            dest = frames_dir / f"{video.stem}-probe-{tag}.png"
            got = grab_frame(video, duration * pct, dest)
            frames.append({"tag": tag, "at_s": round(duration * pct, 2),
                           "file": str(dest) if got else None})
            ok &= got
        checks.append({"check": "四点抽帧", "ok": all(f["file"] for f in frames),
                       "detail": f"{sum(1 for f in frames if f['file'])}/4 → {frames_dir}"})
    else:
        checks.append({"check": "四点抽帧", "ok": False, "detail": "无视频流/时长，跳过"})
        ok = False

    result = {"status": "pass" if ok else "fail", "video": str(video),
              "duration_s": duration, "checks": checks, "frames": frames}
    out_path = video.parent / "final_probe.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    for c in checks:
        print(f"  {'✅' if c['ok'] else '❌'} {c['check']}: {c['detail']}")
    print(f"探针报告: {out_path}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
