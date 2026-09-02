"""One-click AI model downloader for video-production-workflow.

Default: only the faster-whisper large-v3 model (best Windows support:
CPU int8 / CUDA both work out of the box).

Optional extras:
  --include whisper   also download the openai-whisper large-v3 .pt file
                     (keep this engine with --engine whisper)
  --include funasr   also download Fun-ASR-Nano (legacy; needs
                     `uv sync --extra funasr` to be usable)

Sources:
  --source auto        detect network: overseas -> huggingface, CN -> modelscope
  --source modelscope  魔搭社区（国内推荐）
  --source huggingface HuggingFace（国外推荐；不可达时自动切 hf-mirror.com）
  --source direct      only official direct URLs (no mirrors)

All models land under <skill>/models/ by default:
  models/faster-whisper/large-v3/       (CTranslate2 format directory)
  models/whisper/large-v3.pt            (openai-whisper PyTorch checkpoint)
  models/funasr/FunAudioLLM/Fun-ASR-Nano-2512/

Usage (run from the skill root):
  uv run python scripts/setup/download_models.py
  uv run python scripts/setup/download_models.py --source modelscope
  uv run python scripts/setup/download_models.py --source huggingface --include whisper
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import urllib.request
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
MODELS_ROOT = Path(os.environ.get("VIDEO_MODELS_DIR", "")) if os.environ.get("VIDEO_MODELS_DIR") else SKILL_ROOT / "models"

FW_MODEL = "large-v3"
WHISPER_MODEL = "large-v3"
FUNASR_MODEL = "FunAudioLLM/Fun-ASR-Nano-2512"

# Canonical CTranslate2 repos for faster-whisper models.
FW_HF_REPO = "Systran/faster-whisper-large-v3"
# ModelScope mirrors, tried in order (verified 2026-09: Systran 官方同步存在).
FW_MS_REPOS = [
    "Systran/faster-whisper-large-v3",
    "pengzhendong/faster-whisper-large-v3",
    "keepitsimple/faster-whisper-large-v3",
]
FUNASR_MS_REPO = "FunAudioLLM/Fun-ASR-Nano-2512"
FUNASR_HF_REPO = "FunAudioLLM/Fun-ASR-Nano-2512"

HF_MIRROR = "https://hf-mirror.com"
HF_MAIN = "https://huggingface.co"


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def info(msg: str) -> None:
    print(f"  [i]  {msg}")


def fail(msg: str) -> None:
    print(f"  [X]  {msg}")


def reachable(url: str, timeout: float = 5.0) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        urllib.request.urlopen(req, timeout=timeout)
        return True
    except Exception:
        return False


def hf_snapshot(repo_id: str, local_dir: Path, endpoint: str = HF_MAIN) -> None:
    os.environ.setdefault("HF_ENDPOINT", endpoint)
    os.environ["HF_ENDPOINT"] = endpoint
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=repo_id,
        local_dir=str(local_dir),
        endpoint=endpoint,
        max_workers=4,
    )


def ms_snapshot(repo_id: str, local_dir: Path) -> None:
    from modelscope import snapshot_download

    snapshot_download(model_id=repo_id, local_dir=str(local_dir))


def download_direct(url: str, dest: Path, min_bytes: int = 500 * 1024 * 1024) -> None:
    """Stream download with progress and resume support."""
    import urllib.error

    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    offset = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={offset}-"} if offset else {}

    def fmt(n: float) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.1f}{unit}"
            n /= 1024
        return f"{n:.1f}TB"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp, open(part, "ab" if offset else "wb") as f:
        total = resp.headers.get("Content-Length")
        total = int(total) + offset if total else None
        done = offset
        last_pct = -1
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total:
                pct = int(done * 100 / total)
                if pct != last_pct and pct % 5 == 0:
                    print(f"\r  downloading {fmt(done)} / {fmt(total)} ({pct}%)", end="", flush=True)
                    last_pct = pct
    print()
    if part.stat().st_size < min_bytes:
        part.unlink(missing_ok=True)
        raise RuntimeError(f"downloaded file too small: {part}")
    shutil.move(str(part), str(dest))


def download_faster_whisper(source: str) -> Path:
    dest = MODELS_ROOT / "faster-whisper" / FW_MODEL
    if (dest / "model.bin").exists() and (dest / "config.json").exists():
        ok(f"faster-whisper {FW_MODEL} 已存在，跳过: {dest}")
        return dest
    print(f"[1] 下载 faster-whisper {FW_MODEL}（约 3GB，默认转录引擎）")

    errors: list[str] = []
    order: list[str] = []
    if source == "auto":
        order = ["huggingface" if reachable(HF_MAIN) else "modelscope", "modelscope", "hf-mirror"]
    else:
        order = [source]

    for src in order:
        try:
            if src == "modelscope":
                for repo in FW_MS_REPOS:
                    try:
                        info(f"尝试 ModelScope 仓库: {repo}")
                        ms_snapshot(repo, dest)
                        ok(f"faster-whisper 下载完成: {dest}")
                        return dest
                    except Exception as e:  # repo missing or network error
                        errors.append(f"modelscope:{repo}: {e}")
                        if dest.exists():
                            shutil.rmtree(dest, ignore_errors=True)
                continue
            if src in ("huggingface", "hf-mirror"):
                endpoint = HF_MIRROR if src == "hf-mirror" else HF_MAIN
                if src == "huggingface" and not reachable(endpoint):
                    errors.append(f"{src}: endpoint unreachable")
                    continue
                info(f"从 {endpoint} 下载 {FW_HF_REPO}")
                hf_snapshot(FW_HF_REPO, dest, endpoint=endpoint)
                ok(f"faster-whisper 下载完成: {dest}")
                return dest
        except Exception as e:
            errors.append(f"{src}: {e}")
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)

    fail("faster-whisper 模型下载失败。已尝试: " + "; ".join(errors))
    print("      手动方案：浏览器打开 https://hf-mirror.com/Systran/faster-whisper-large-v3")
    print(f"      下载全部文件后放入: {dest}")
    raise SystemExit(1)


def download_whisper(source: str) -> Path:
    dest = MODELS_ROOT / "whisper" / f"{WHISPER_MODEL}.pt"
    if dest.exists() and dest.stat().st_size > 1024 * 1024 * 1024:
        ok(f"whisper {WHISPER_MODEL} 已存在，跳过: {dest}")
        return dest
    print(f"[2] 下载 openai-whisper {WHISPER_MODEL}（约 2.9GB，备选引擎 --engine whisper）")

    try:
        import whisper

        url = whisper._MODELS.get(WHISPER_MODEL)
    except Exception as e:
        fail(f"openai-whisper 包不可用（先运行 uv sync）: {e}")
        raise SystemExit(1)
    if not url:
        fail(f"whisper 内置模型列表中没有 {WHISPER_MODEL}")
        raise SystemExit(1)

    try:
        download_direct(url, dest, min_bytes=1024 * 1024 * 1024)
        ok(f"whisper 下载完成: {dest}")
    except Exception as e:
        fail(f"whisper 下载失败: {e}")
        print("      该文件来自 OpenAI 官方 CDN（azureedge），国内一般可直连；")
        print("      失败时可用浏览器/下载工具重试该 URL:")
        print(f"      {url}")
        raise SystemExit(1)
    return dest


def download_funasr(source: str) -> Path:
    dest = MODELS_ROOT / "funasr" / FUNASR_MODEL.replace("/", os.sep)
    if (dest / "model.pt").exists() or any(dest.glob("*.pt")):
        ok(f"Fun-ASR 已存在，跳过: {dest}")
        return dest
    print(f"[3] 下载 Fun-ASR（legacy，约 2GB；使用前需 uv sync --extra funasr）")

    if source in ("modelscope", "auto"):
        try:
            ms_snapshot(FUNASR_MS_REPO, dest)
            ok(f"Fun-ASR 下载完成: {dest}")
            return dest
        except Exception as e:
            info(f"ModelScope 下载失败: {e}；尝试 HuggingFace")
    try:
        endpoint = HF_MIRROR if not reachable(HF_MAIN) else HF_MAIN
        hf_snapshot(FUNASR_HF_REPO, dest, endpoint=endpoint)
        ok(f"Fun-ASR 下载完成: {dest}")
        return dest
    except Exception as e:
        fail(f"Fun-ASR 下载失败: {e}")
        raise SystemExit(1)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Download local transcription models into <skill>/models/"
    )
    ap.add_argument(
        "--source",
        choices=["auto", "modelscope", "huggingface", "direct"],
        default="auto",
        help="Download source: auto detect / modelscope (CN) / huggingface (overseas) / direct",
    )
    ap.add_argument(
        "--include",
        action="append",
        choices=["whisper", "funasr"],
        default=[],
        help="Optional extra models: whisper (openai-whisper .pt) / funasr (legacy)",
    )
    ap.add_argument(
        "--list",
        action="store_true",
        help="List model status only, download nothing",
    )
    args = ap.parse_args()

    MODELS_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"模型目录: {MODELS_ROOT}")

    if args.list:
        fw = MODELS_ROOT / "faster-whisper" / FW_MODEL
        wh = MODELS_ROOT / "whisper" / f"{WHISPER_MODEL}.pt"
        fa = MODELS_ROOT / "funasr" / FUNASR_MODEL.replace("/", os.sep)
        print(f"  faster-whisper {FW_MODEL}: {'已下载' if (fw / 'model.bin').exists() else '未下载（默认引擎，建议下载）'}")
        print(f"  whisper {WHISPER_MODEL}:   {'已下载' if wh.exists() else '未下载（备选引擎，可选）'}")
        print(f"  funasr:                {'已下载' if fa.exists() else '未下载（legacy，可选）'}")
        return

    download_faster_whisper(args.source)

    if "whisper" in args.include:
        download_whisper(args.source)
    else:
        info("跳过 openai-whisper 模型（需要时加 --include whisper）")

    if "funasr" in args.include:
        download_funasr(args.source)
    else:
        info("跳过 Fun-ASR 模型（legacy；需要时加 --include funasr）")

    print()
    print("模型就绪。转录默认使用 faster-whisper（Windows 友好）。")
    print("切换备选引擎: transcribe.py --engine whisper")


if __name__ == "__main__":
    main()
