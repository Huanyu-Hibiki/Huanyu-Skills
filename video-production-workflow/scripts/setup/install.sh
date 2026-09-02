#!/usr/bin/env bash
# ============================================================================
# video-production-workflow 一键依赖安装脚本（macOS / Linux）
# 用法：
#   bash scripts/setup/install.sh
# 可选参数：
#   -mirror        使用国内镜像（清华 PyPI）加速下载
#   -skip-models   只装依赖，不下载 AI 模型
#   -model-source  模型下载源：auto / modelscope / huggingface
# 示例：
#   bash scripts/setup/install.sh -mirror -model-source modelscope
# ============================================================================
set -e

MIRROR=0
SKIP_MODELS=0
MODEL_SOURCE="auto"
while [[ $# -gt 0 ]]; do
  case "$1" in
    -mirror) MIRROR=1; shift ;;
    -skip-models) SKIP_MODELS=1; shift ;;
    -model-source) MODEL_SOURCE="$2"; shift 2 ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

SKILL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$SKILL_ROOT"

step()  { printf "\n\033[36m==> %s\033[0m\n" "$1"; }
okmsg() { printf "    [OK] %s\n" "$1"; }
warn()  { printf "    [!]  %s\n" "$1"; }
fail()  { printf "    [X]  %s\n" "$1"; }

printf "============================================================\n"
printf "  video-production-workflow 依赖一键安装 (macOS/Linux)\n"
printf "  安装目录: %s\n" "$SKILL_ROOT"
printf "============================================================\n"

# ---------------------------------------------------------------------------
# 1. uv
# ---------------------------------------------------------------------------
step "检查 uv（Python 包管理器）"
if command -v uv >/dev/null 2>&1; then
  okmsg "uv 已安装: $(uv --version)"
else
  warn "未检测到 uv，开始自动安装（约 20 秒）..."
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    command -v uv >/dev/null 2>&1 && okmsg "uv 安装成功: $(uv --version)" || {
      fail "uv 安装失败，请手动执行: curl -LsSf https://astral.sh/uv/install.sh | sh"
      exit 1
    }
  else
    fail "没有 curl，请先安装 uv: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
  fi
fi

if [[ "$MIRROR" == "1" ]]; then
  export UV_DEFAULT_INDEX="https://pypi.tuna.tsinghua.edu.cn/simple"
  okmsg "已启用清华 PyPI 镜像"
fi

# ---------------------------------------------------------------------------
# 2. FFmpeg
# ---------------------------------------------------------------------------
step "检查 FFmpeg"
if command -v ffmpeg >/dev/null 2>&1; then
  okmsg "FFmpeg 已安装: $(ffmpeg -version | head -1)"
else
  warn "未检测到 FFmpeg。安装方式："
  warn "  macOS:  brew install ffmpeg   （无 Homebrew 先见 brew.sh）"
  warn "  Ubuntu/Debian: sudo apt install ffmpeg"
  warn "安装后重新运行本脚本确认"
fi

# ---------------------------------------------------------------------------
# 3. Node.js 18+
# ---------------------------------------------------------------------------
step "检查 Node.js（Remotion / HyperFrames 需要，18 以上版本）"
if command -v node >/dev/null 2>&1; then
  okmsg "Node.js 已安装: $(node --version)"
else
  warn "未检测到 Node.js。安装方式："
  warn "  macOS:  brew install node@22"
  warn "  Ubuntu/Debian: 参考 https://github.com/nodesource/distributions"
  warn "不做 Remotion 动效可以暂时不装"
fi

# ---------------------------------------------------------------------------
# 4. Python 虚拟环境
# ---------------------------------------------------------------------------
step "创建 Python 虚拟环境并安装依赖（首次约 5-15 分钟，含 PyTorch GPU 版约 3GB）"
uv venv .venv --python 3.11
uv sync
okmsg "Python 环境就绪: .venv"

# ---------------------------------------------------------------------------
# 5. 自检
# ---------------------------------------------------------------------------
step "环境自检"
uv run python -c "import torch; print('    torch', torch.__version__, '| CUDA 可用:', torch.cuda.is_available())"
okmsg "依赖安装完成"

# ---------------------------------------------------------------------------
# 6. AI 模型下载
# ---------------------------------------------------------------------------
if [[ "$SKIP_MODELS" == "1" ]]; then
  step "按参数跳过模型下载。稍后可随时运行："
  printf "    uv run python scripts/setup/download_models.py --source auto\n"
else
  step "下载 AI 转录模型 faster-whisper large-v3（约 3GB，默认引擎）"
  printf  "    国内网络自动使用魔搭 ModelScope，国外自动使用 HuggingFace\n"
  read -r -p "    现在下载吗？(y/n) " answer
  if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
    uv run python scripts/setup/download_models.py --source "$MODEL_SOURCE" || {
      warn "模型下载未完成。可稍后手动重试："
      printf "    uv run python scripts/setup/download_models.py --source modelscope\n"
      printf "    uv run python scripts/setup/download_models.py --source huggingface\n"
    }
  else
    warn "跳过模型下载。粗剪前需要先运行："
    printf "    uv run python scripts/setup/download_models.py --source auto\n"
  fi
fi

printf "\n============================================================\n"
printf "  安装流程结束\n"
printf "============================================================\n"
printf "下一步：\n"
printf "  1. 复制 .env.example 为 .env，按需填写 API Key（本地转录不需要任何 Key）\n"
printf "  2. 在 Agent（Claude Code / OpenCode 等）中对该视频项目说：初始化视频制作管线\n"
printf "  详细教程见 README.md「第一次使用」章节\n"
