#!/usr/bin/env python3
"""oracle-bone script-extraction — 视频/音频 → transcript.md。

管线：URL → yt-dlp 下载（字幕轨优先，无字幕走 whisper）→ ffmpeg 抽音频 → faster-whisper 转录。
本地文件跳过 yt-dlp。

模型解析顺序：
  1. --model-dir <path> 显式指定
  2. 本目录 models/faster-whisper-<size>/ 存在（README 预下载方案）
  3. 交给 faster-whisper 在线下载（HF cache，国内网络常失败 → 见 README 模型下载节）

输出契约（与 adapters/script-extraction/README.md 一致）：
  transcript.md = 来源 + 时长 + 转录方式标注 + 段落版全文
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_MODEL = "medium"
LOCAL_MODELS_DIR = HERE / "models"
SUB_LANGS = "zh-Hans,zh-Hant,zh-CN,zh,zh-Hans_orig,en,en-US,en-GB"
LANG_PRIORITY = ["zh-Hans", "zh-Hans_orig", "zh-Hant", "zh-CN", "zh", "en-US", "en-GB", "en"]

# 五大平台档案（反爬要点移植自 data-scientist-community 的拟人化思路：真实登录态复用 +
# TLS 指纹拟真 + 请求间隔 + 退避重试 [3s,8s]）。impersonate=None 表示平台不挑指纹。
PLATFORM_PROFILES = {
    "douyin": {
        "domains": ["douyin.com", "iesdouyin.com"],
        "impersonate": "chrome",       # 抖音校验 TLS/JA3 指纹，必须像真浏览器
        "sleep_requests": 1.5,          # 请求间隔（秒）——别机器枪式连发
        "cookies_hint": "网页版登录后 --cookies-from-browser chrome 复用登录态，成功率最高",
    },
    "xiaohongshu": {
        "domains": ["xiaohongshu.com", "xhslink.com"],
        "impersonate": "chrome",
        "sleep_requests": 1.5,
        "cookies_hint": "未登录常拿不到流地址；--cookies-from-browser chrome + 已登录浏览器",
    },
    "bilibili": {
        "domains": ["bilibili.com", "b23.tv", "bilivideo.com"],
        "impersonate": None,
        "sleep_requests": 0,
        "cookies_hint": "下载一般免登录；字幕轨必须 cookie（--cookies-from-browser chrome）",
    },
    "zhihu": {
        "domains": ["zhihu.com"],
        "impersonate": None,
        "sleep_requests": 1,
        "cookies_hint": "视频回答可提取；纯文字回答无需转录——直接复制文本学习表达",
    },
    "wechat-channels": {
        "domains": ["channels.weixin.qq.com"],
        "impersonate": None,
        "sleep_requests": 0,
        "unsupported": True,            # 无公开网页播放器，yt-dlp 无提取器
        "cookies_hint": "不支持 URL——手机导出/录屏得本地文件后走本地路径，或手动粘稿",
    },
}

# yt-dlp 全局拟人化配置（main 里按平台档案 + 用户参数装配）
YT = {"impersonate": None, "sleep_requests": 0, "cookies_file": None,
      "cookies_browser": None, "warned_impersonate": False}


def curl_cffi_ok() -> bool:
    try:
        import curl_cffi  # noqa: F401
        return True
    except ImportError:
        return False


def detect_platform(url: str):
    low = url.lower()
    for key, prof in PLATFORM_PROFILES.items():
        if any(d in low for d in prof["domains"]):
            return key
    return None


def die(msg: str, code: int = 1):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(code)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


def fmt_dur(seconds):
    if seconds is None:
        return "unknown"
    seconds = int(round(seconds))
    h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def ffmpeg_ok():
    return bool(shutil.which("ffmpeg")) and bool(shutil.which("ffprobe"))


def media_duration(path: Path):
    r = run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def ytdlp(args):
    """统一 yt-dlp 调用：注入拟人化参数（登录态 cookie + TLS 指纹 + 请求间隔 + 退避重试）。"""
    cmd = [sys.executable, "-m", "yt_dlp", "--no-playlist",
           "--retries", "3", "--retry-sleep", "http:linear=3:8"]  # 退避重试 3s→8s，节奏同 data-scientist-community
    if YT["impersonate"]:
        if curl_cffi_ok():
            cmd += ["--impersonate", YT["impersonate"]]
        elif not YT["warned_impersonate"]:
            YT["warned_impersonate"] = True
            print("⚠️ curl-cffi 未安装，跳过 TLS 指纹拟真——"
                  "反爬严格的平台（抖音/小红书）可能失败。装法：--pre 装 'yt-dlp[curl-cffi]'", file=sys.stderr)
    if YT["sleep_requests"] > 0:
        cmd += ["--sleep-requests", str(YT["sleep_requests"])]
    if YT["cookies_file"]:
        cmd += ["--cookies", YT["cookies_file"]]
    if YT["cookies_browser"]:
        cmd += ["--cookies-from-browser", YT["cookies_browser"]]
    return run(cmd + args)


def fetch_url_meta(url: str):
    r = ytdlp(["-J", "--skip-download", url])
    if r.returncode != 0:
        die(f"yt-dlp 拉取信息失败：{r.stderr.strip()[:500]}")
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        die("yt-dlp 返回的元数据不是合法 JSON（可能遇到反爬/登录墙，试 --cookies-from-browser chrome 或手动粘稿）")


def download_media(url: str, tmpdir: Path) -> Path:
    out_tpl = str(tmpdir / "src.%(ext)s")
    r = ytdlp(["-f", "bv*+ba/b", "--merge-output-format", "mp4", "-o", out_tpl, url])
    if r.returncode != 0:
        die(f"yt-dlp 下载失败：{r.stderr.strip()[:500]}（反爬平台先试 --cookies-from-browser chrome）")
    files = sorted(tmpdir.glob("src.*"), key=lambda p: p.stat().st_size, reverse=True)
    if not files:
        die("yt-dlp 报成功但找不到下载文件")
    return files[0]


def try_subtitles(url: str, tmpdir: Path):
    sub_dir = tmpdir / "subs"
    sub_dir.mkdir()
    cmd = [
        "--skip-download", "--write-subs", "--write-auto-subs",
        "--sub-langs", SUB_LANGS, "--sub-format", "vtt/srt/best",
        "-o", str(sub_dir / "cap"),
        url,
    ]
    r = ytdlp(cmd)
    caps = list(sub_dir.glob("cap*.vtt")) + list(sub_dir.glob("cap*.srt"))
    if not caps:
        return None
    ranked = sorted(caps, key=lambda p: next(
        (LANG_PRIORITY.index(l) for l in LANG_PRIORITY if p.name.lower().startswith(f"cap.{l}")), 99))
    picked = ranked[0]
    is_auto = ".auto." in picked.name or bool(re.search(r"\.zh[^.]*\.vtt$", picked.name))
    lang_tag = next((l for l in LANG_PRIORITY if l in picked.name.lower()), "?")
    return picked, lang_tag, is_auto


def clean_cue_text(line: str) -> str:
    line = re.sub(r"<[^>]+>", "", line)
    line = re.sub(r"&nbsp;", " ", line)
    return line.strip()


def subs_to_paragraphs(cap_file: Path) -> list[str]:
    raw = cap_file.read_text(encoding="utf-8", errors="replace")
    lines: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE", "\ufeff")):
            continue
        if "-->" in line or re.fullmatch(r"\d+", line):
            continue
        text = clean_cue_text(line)
        if not text:
            continue
        if lines and (lines[-1] in text or text in lines[-1]):
            lines[-1] = lines[-1] if len(lines[-1]) >= len(text) else text
            continue
        lines.append(text)
    body = "".join(lines) if any(re.match(r"[\u4e00-\u9fff]", l) for l in lines) else " ".join(lines)
    sentences = re.split(r"(?<=[。！？!?.])\s*", body)
    sentences = [s for s in sentences if s.strip()]
    paras, buf = [], []
    for s in sentences:
        buf.append(s.strip())
        if len(buf) >= 4:
            paras.append("".join(buf) if any(re.match(r"[\u4e00-\u9fff]", c) for c in buf) else " ".join(buf))
            buf = []
    if buf:
        paras.append("".join(buf) if any(re.match(r"[\u4e00-\u9fff]", c) for c in buf) else " ".join(buf))
    return paras


def resolve_model(size: str, model_dir: str | None):
    if model_dir:
        p = Path(model_dir)
        if not (p / "model.bin").exists():
            die(f"--model-dir 无效：{p} 下没有 model.bin（CTranslate2 模型目录应含 model.bin/config.json/tokenizer.json）")
        return str(p), f"whisper-{size}(local: {p})"
    local = LOCAL_MODELS_DIR / f"faster-whisper-{size}"
    if (local / "model.bin").exists():
        return str(local), f"whisper-{size}(local: models/{local.name})"
    return size, None


def whisper_paragraphs(audio: Path, model_spec: str, label: str, lang: str | None, device: str, compute_type: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        die("faster-whisper 未安装——先跑 README 的 uv venv 三步 setup，或走手动粘稿")
    try:
        model = WhisperModel(model_spec, device=device, compute_type=compute_type)
    except Exception as e:
        die(
            f"模型加载失败：{type(e).__name__}: {str(e)[:300]}\n"
            f"  大概率是在线下载被墙/无网。解决：按 README「模型下载」节，从 ModelScope 或 HuggingFace\n"
            f"  预下载 faster-whisper-{DEFAULT_MODEL} 到 {LOCAL_MODELS_DIR / ('faster-whisper-' + DEFAULT_MODEL)}，\n"
            f"  或用 --model-dir 指向已下载目录。"
        )
    seg_iter, info = model.transcribe(str(audio), language=lang, vad_filter=True, beam_size=5)
    segs = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in seg_iter]
    if not segs:
        return [], getattr(info, "language", "?"), label
    paras, buf, last_end = [], [], None
    for s in segs:
        gap = (s["start"] - last_end) if last_end is not None else 0
        if buf and gap > 2.0:
            paras.append("".join(buf))
            buf = []
        buf.append(s["text"])
        last_end = s["end"]
    if buf:
        paras.append("".join(buf))
    return paras, getattr(info, "language", "?"), label


def extract_audio(media: Path, tmpdir: Path) -> Path:
    audio = tmpdir / "audio.wav"
    r = run(["ffmpeg", "-y", "-i", str(media), "-vn", "-ac", "1", "-ar", "16000", str(audio)])
    if r.returncode != 0 or not audio.exists():
        die(f"ffmpeg 抽音频失败：{r.stderr.strip()[:300]}")
    return audio


def write_transcript(out_path: Path, source: str, title: str, duration, method: str, paras: list[str]):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        f"# transcript — {title}",
        "",
        f"- **来源**：{source}",
        f"- **时长**：{fmt_dur(duration)}",
        f"- **转录方式**：{method}",
        f"- **转录时间**：{datetime.now().isoformat(timespec='seconds')}",
        "",
        "---",
        "",
    ]
    out_path.write_text("\n".join(header + paras) + "\n", encoding="utf-8")


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="oracle-bone script-extraction：视频/音频 → transcript.md（字幕轨优先，whisper 兜底）")
    ap.add_argument("input", help="视频/音频 URL 或本地文件路径")
    ap.add_argument("--out", default=".", help="输出目录（transcript.md 落这里；建议传 study/<博主>-apprentice/<标题>/）")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"faster-whisper 模型档位（默认 {DEFAULT_MODEL}：tiny/base/small/medium/large-v3/large-v3-turbo）")
    ap.add_argument("--model-dir", default=None, help="本地模型目录（含 model.bin）；默认自动找本目录 models/faster-whisper-<size>/")
    ap.add_argument("--lang", default=None, help="强制语言（如 zh / en）；默认自动检测")
    ap.add_argument("--device", default="auto", help="cpu / cuda / auto（默认 auto）")
    ap.add_argument("--compute-type", default="auto", help="int8 / float16 / auto（默认 auto：cpu→int8, gpu→float16）")
    ap.add_argument("--cookies", default=None, help="yt-dlp cookies.txt 文件（B站等需登录的字幕源）")
    ap.add_argument("--cookies-from-browser", default=None,
                    help="直接复用本机浏览器登录态（chrome/edge/firefox；反爬平台首选，需浏览器已登录）")
    ap.add_argument("--impersonate", default="auto",
                    help="TLS 指纹拟真目标（chrome/safari/off/auto=按平台档案；抖音/小红书自动启用 chrome）")
    ap.add_argument("--sleep-requests", type=float, default=-1,
                    help="每次请求间隔秒数（-1=按平台档案默认；抖音/小红书 1.5s 拟人节奏）")
    ap.add_argument("--force-whisper", action="store_true", help="跳过字幕轨，强制走 whisper 转录")
    args = ap.parse_args()

    if not ffmpeg_ok():
        die("ffmpeg/ffprobe 不在 PATH——whisper 路径必需（字幕轨路径可以无，但建议装）")

    is_url = bool(re.match(r"https?://", args.input))
    platform = detect_platform(args.input) if is_url else None
    if platform == "wechat-channels":
        die("视频号没有公开网页播放器，yt-dlp 无提取器。改用：\n"
            "  a) 手机导出/录屏拿到本地视频文件 → transcribe.py <本地文件>\n"
            "  b) 手动粘稿（apprentice 零依赖主路径）")

    # 装配拟人化配置：平台档案打底，用户参数覆盖
    prof = PLATFORM_PROFILES.get(platform, {})
    YT["cookies_file"] = args.cookies
    YT["cookies_browser"] = getattr(args, "cookies_from_browser")
    if args.impersonate == "off":
        YT["impersonate"] = None
    elif args.impersonate != "auto":
        YT["impersonate"] = args.impersonate
    else:
        YT["impersonate"] = prof.get("impersonate")
    if args.sleep_requests >= 0:
        YT["sleep_requests"] = args.sleep_requests
    else:
        YT["sleep_requests"] = prof.get("sleep_requests", 0)

    out_path = Path(args.out).resolve() / "transcript.md"
    tmpdir = Path(tempfile.mkdtemp(prefix="oracle-se-"))
    try:
        if is_url:
            plat_tag = platform or "generic"
            extras = []
            if YT["impersonate"]:
                extras.append(f"impersonate={YT['impersonate']}")
            if YT["sleep_requests"] > 0:
                extras.append(f"sleep={YT['sleep_requests']}s")
            if YT["cookies_browser"] or YT["cookies_file"]:
                extras.append("cookies=on")
            print(f"▶ 平台：{plat_tag}{'｜' + '｜'.join(extras) if extras else ''}")
            meta = fetch_url_meta(args.input)
            title = meta.get("title") or "untitled"
            duration = meta.get("duration")
            source = args.input
            sub = None if args.force_whisper else try_subtitles(args.input, tmpdir)
            if sub:
                cap_file, lang_tag, is_auto = sub
                paras = subs_to_paragraphs(cap_file)
                if paras:
                    method = f"字幕轨 {lang_tag}({'auto-ASR' if is_auto else 'manual'})"
                    write_transcript(out_path, source, title, duration, method, paras)
                    print(f"✅ [字幕轨 {lang_tag}] transcript: {out_path}")
                    print(f"   时长 {fmt_dur(duration)}｜段落 {len(paras)}｜来源 {source}")
                    return
                print("⚠️ 字幕轨下载到了但清洗后为空，转 whisper", file=sys.stderr)
            media = download_media(args.input, tmpdir)
        else:
            media = Path(args.input).expanduser().resolve()
            if not media.exists():
                die(f"本地文件不存在：{media}")
            title = media.stem
            source = media.name
            duration = None

        if duration is None:
            duration = media_duration(media)
        audio = extract_audio(media, tmpdir)
        model_spec, label = resolve_model(args.model, args.model_dir)
        if label is None:
            label = f"whisper-{args.model}({args.device}, {args.compute_type})"
        ct = args.compute_type
        if ct == "auto":
            ct = "int8" if args.device in ("cpu", "auto") else "float16"
        dev = "cpu" if args.device == "auto" else args.device
        t0 = time.time()
        paras, detected, label = whisper_paragraphs(audio, model_spec, label, args.lang, dev, ct)
        method = f"{label}｜语言 {detected}｜耗时 {time.time() - t0:.0f}s"
        write_transcript(out_path, source, title, duration, method, paras)
        print(f"✅ [whisper] transcript: {out_path}")
        print(f"   时长 {fmt_dur(duration)}｜段落 {len(paras)}｜{method}")
        if not paras:
            print("⚠️ whisper 输出为空——检查音轨是否存在人声", file=sys.stderr)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
