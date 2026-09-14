"""交付承诺校验：分镜声明的运动比承诺 vs 装配清单实际兑现。

video-plan 在 storyboard.json 写入 delivery_promise（mode + min_motion_ratio，
口播+剪映管线默认 hybrid / 0.2）；video-polish 装配前运行本脚本核对
Polished/broll-compose.json：已批准 B-roll 里静帧/文字卡兜底占比过高、
或已批准条目文件缺失 = 违约——降级必须显式批准并记入决策日志，不许静默。

运动单元口径：底片（fine_cut，真实口播素材）恒为运动；B-roll beat 按
文件后缀分类（mp4/mov/webm/mkv/avi=运动，png/jpg=静帧）。

用法:
    python check_delivery_promise.py <项目根> [--min-motion 0.2] [--mode hybrid]
输出: JSON 摘要 + 结论
退出码: 0=pass 3=尚未装配 2=degraded（需批准降级） 1=fail（条目丢失）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}
STILL_EXT = {".png", ".jpg", ".jpeg", ".webp"}

DEFAULT_MODE = "hybrid"
DEFAULT_MIN_MOTION = 0.2


def load_promise(storyboard_json: Path, args_min: float | None, args_mode: str | None):
    mode, min_motion = args_mode or DEFAULT_MODE, args_min or DEFAULT_MIN_MOTION
    if storyboard_json.exists():
        data = json.loads(storyboard_json.read_text(encoding="utf-8"))
        p = data.get("delivery_promise") or {}
        mode = args_mode or p.get("mode", mode)
        min_motion = args_min or float(p.get("min_motion_ratio", min_motion))
    return {"mode": mode, "min_motion_ratio": min_motion}


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        sys.exit(0)
    project = Path(sys.argv[1])
    args = sys.argv[2:]
    min_motion = mode = None
    for i, a in enumerate(args):
        if a == "--min-motion" and i + 1 < len(args):
            min_motion = float(args[i + 1])
        elif a == "--mode" and i + 1 < len(args):
            mode = args[i + 1]

    promise = load_promise(project / "video scripts" / "storyboard.json", min_motion, mode)

    compose_path = project / "Polished" / "broll-compose.json"
    fine_cut = project / "Polished" / "fine_cut.mp4"
    if not compose_path.exists():
        print(json.dumps({"status": "no_assembly", "promise": promise,
                          "note": "尚未装配（无 broll-compose.json）"}, ensure_ascii=False))
        sys.exit(3)

    compose = json.loads(compose_path.read_text(encoding="utf-8"))
    beats = compose.get("beats", [])

    motion = 1 if fine_cut.exists() else 0   # 底片=真实口播素材，恒为运动单元
    stills, lost = [], []
    for b in beats:
        f = (project / b.get("file", "")) if not Path(b.get("file", "")).is_absolute() \
            else Path(b["file"])
        if not f.exists():
            lost.append({"id": b.get("id"), "file": b.get("file")})
            continue
        ext = f.suffix.lower()
        if ext in VIDEO_EXT:
            motion += 1
        elif ext in STILL_EXT:
            stills.append(b.get("id"))
        else:
            motion += 1  # 未知后缀按视频处理，不冤枉

    total = motion + len(stills)
    ratio = round(motion / total, 3) if total else 0.0
    result = {
        "status": None, "promise": promise,
        "motion_units": motion, "still_units": len(stills),
        "still_beat_ids": stills, "missing_beats": lost,
        "motion_ratio": ratio,
    }
    if lost:
        result["status"] = "fail"
        result["note"] = "已批准 B-roll 文件缺失——装配禁止静默丢条目，先回 /b-roll-generate 重做"
        code = 1
    elif ratio < promise["min_motion_ratio"]:
        result["status"] = "degraded"
        result["note"] = (f"运动比 {ratio} < 承诺 {promise['min_motion_ratio']}——"
                          "静帧兜底需用户显式批准并记入 decision_log（category=promise_change）")
        code = 2
    else:
        result["status"] = "pass"
        result["note"] = "交付承诺兑现"
        code = 0

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(code)


if __name__ == "__main__":
    main()
