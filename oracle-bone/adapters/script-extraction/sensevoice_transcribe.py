#!/usr/bin/env python3
"""oracle-bone script-extraction — SenseVoiceSmall 本地转写（FunASR 管线）。

oracle-voice 路径 B 的中文快线：SenseVoiceSmall + FSMN-VAD（阿里 FunAudioLLM 开源，Apache-2.0）。
模型仅 ~234M，中文转写速度比 whisper-large 快一个量级；输出无标点——标点由 oracle-voice 文字轮恢复。
whisper（transcribe.py）仍是多语种/兜底默认，本脚本面向纯中文口播的快速转写。

模型解析：首次运行自动从 ModelScope 下载到 <adapter>/models/funasr/（已 gitignore，国内直连稳）。

依赖（一次性，装进本 adapter 自带 .venv——见 README「SenseVoice 安装」节）:
  uv pip install --python .venv/Scripts/python.exe -r requirements-sensevoice.txt

输出契约（与 transcribe.py 一致）：transcript.md = 来源 + 时长 + 转录方式标注 + 段落版全文
"""
import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CACHE_DIR = HERE / "models" / "funasr"

INSTALL_HINT = (
    "SenseVoice 依赖未安装。一次性安装（装进本 adapter 自带 .venv，不换系统 python）：\n"
    "  cd adapters/script-extraction\n"
    "  uv pip install --python .venv/Scripts/python.exe -r requirements-sensevoice.txt\n"
    "（无 uv 则用 .venv/Scripts/python.exe -m pip install -r requirements-sensevoice.txt）"
)


def fmt_dur(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}m{s:02d}s"


def ffprobe_duration(path: Path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        return float(out.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def to_paragraphs(text: str, target: int = 180) -> list[str]:
    """按句读粗分段——不做任何内容改写（原话保真，标点恢复归 oracle-voice 文字轮）。"""
    import re

    sentences = [s for s in re.split(r"(?<=[。！？；!?;])\s*", text.strip()) if s]
    paras, buf = [], ""
    for sentence in sentences:
        if buf and len(buf) + len(sentence) > target:
            paras.append(buf)
            buf = sentence
        else:
            buf += sentence
    if buf:
        paras.append(buf)
    return paras or ([text.strip()] if text.strip() else [])


def write_transcript(out_path: Path, source: str, duration, method: str, paras: list[str]):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        f"# transcript — {source.stem}",
        "",
        f"- **来源**：{source.name}",
        f"- **时长**：{fmt_dur(duration) if duration else '未知'}",
        f"- **转录方式**：{method}",
        f"- **转录时间**：{datetime.now().isoformat(timespec='seconds')}",
        "",
        "---",
        "",
    ]
    body = paras if paras else ["（未检测到语音内容）"]
    out_path.write_text("\n".join(header + body) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="SenseVoiceSmall 本地转写（中文快线）")
    ap.add_argument("input", help="音频/视频本地文件路径")
    ap.add_argument("--out", default=".", help="输出目录（transcript.md 落这里）")
    ap.add_argument("--language", default="auto", help="auto/zh/yue/en/ja/ko（默认 auto）")
    ap.add_argument("--device", default="cpu", help="cpu / cuda:0")
    ap.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR),
                    help="模型缓存目录（默认 models/funasr/，已 gitignore）")
    args = ap.parse_args()

    try:
        from funasr import AutoModel
        from funasr.utils.postprocess_utils import rich_transcription_postprocess
    except ImportError:
        print(INSTALL_HINT, file=sys.stderr)
        return 3

    audio = Path(args.input).expanduser()
    if not audio.exists():
        print(f"输入文件不存在: {audio}", file=sys.stderr)
        return 2

    duration = ffprobe_duration(audio)

    t0 = time.time()
    model = AutoModel(
        model="iic/SenseVoiceSmall",
        vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        vad_kwargs={"max_single_segment_time": 30000},
        device=args.device,
        disable_update=True,
        cache_dir=args.cache_dir,
    )
    load_s = time.time() - t0

    t1 = time.time()
    res = model.generate(
        input=str(audio),
        cache={},
        language=args.language,
        use_itn=True,
        batch_size_s=60,
        merge_vad=True,
        merge_length_s=15,
    )
    asr_s = time.time() - t1

    text = rich_transcription_postprocess(res[0]["text"]) if res else ""
    paras = to_paragraphs(text)
    out_path = Path(args.out).expanduser() / "transcript.md"
    write_transcript(out_path, audio, duration,
                     f"SenseVoiceSmall (local, {args.device}, funasr)", paras)

    rtf = f"，RTF≈{asr_s / duration:.2f}" if duration and duration > 0 else ""
    print(f"✅ 转写完成 → {out_path}")
    print(f"   加载 {load_s:.1f}s / 转写 {asr_s:.1f}s{rtf} / 字数 {len(text)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
