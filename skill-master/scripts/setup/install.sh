#!/usr/bin/env bash
# skill-master 一键安装脚本（macOS / Linux）
set -euo pipefail

SKILL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MIRROR=false

for arg in "$@"; do
    case "$arg" in
        -mirror|--mirror) MIRROR=true ;;
    esac
done

echo ""
echo "========================================"
echo "  skill-master 一键安装"
echo "========================================"
echo ""

# ---------- Step 1: 检查/安装 uv ----------
echo "[1/3] 检查 uv..."

if ! command -v uv &>/dev/null; then
    echo "  uv 未安装，正在安装..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

UV_VERSION=$(uv --version 2>/dev/null || echo "unknown")
echo "  uv 已就绪：$UV_VERSION"

# ---------- Step 2: 创建环境并装依赖 ----------
echo "[2/3] 创建虚拟环境并安装依赖..."

cd "$SKILL_ROOT"

if [ ! -d ".venv" ]; then
    uv venv .venv --python 3.12
fi

SYNC_ARGS=("sync")
if [ "$MIRROR" = true ]; then
    SYNC_ARGS+=("--extra-index-url" "https://pypi.tuna.tsinghua.edu.cn/simple")
fi

uv "${SYNC_ARGS[@]}"
echo "  依赖安装完成"

# ---------- Step 3: 健康检查 ----------
echo "[3/3] 运行健康检查..."

cd "$SKILL_ROOT"

if uv run python -c "import json; print('Python OK')" 2>/dev/null | grep -q "Python OK"; then
    echo "  Python 环境正常"
else
    echo "  Python 环境异常"
fi

for script in scanner.py inventory.py report.py; do
    if uv run python "scripts/$script" --help &>/dev/null; then
        echo "  $script 可用"
    else
        echo "  $script 异常"
    fi
done

echo ""
echo "========================================"
echo "  安装完成！"
echo "========================================"
echo ""
echo "重启 Agent 会话后即可使用。"
echo "对 Agent 说「盘点我装了哪些 skill」开始体验。"
echo ""
