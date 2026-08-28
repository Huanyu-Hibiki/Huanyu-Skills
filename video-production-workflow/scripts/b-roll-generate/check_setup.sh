#!/usr/bin/env bash
# B-roll generation environment self-check.
# Exit 0 = all good; exit 1 = at least one item missing (details on stdout).

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKFLOW_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
. "$WORKFLOW_DIR/scripts/lib/load_env.sh"
if [ -x "$WORKFLOW_DIR/.venv/bin/python" ]; then
  VENV_PY="$WORKFLOW_DIR/.venv/bin/python"
elif [ -x "$WORKFLOW_DIR/.venv/Scripts/python.exe" ]; then
  VENV_PY="$WORKFLOW_DIR/.venv/Scripts/python.exe"
else
  VENV_PY=""
fi
FAIL=0

ok()   { printf 'PASS  %s\n' "$1"; }
bad()  { printf 'FAIL  %s\n' "$1"; FAIL=1; }

# 1. GEMINI_API_KEY
if [ -n "${GEMINI_API_KEY:-}" ]; then
  ok "GEMINI_API_KEY 已设置"
else
  bad "GEMINI_API_KEY 未设置（到 https://aistudio.google.com/apikey 创建后 export 到 shell 配置）"
fi

# 2. ffmpeg / ffprobe
if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
  ok "ffmpeg / ffprobe 可用"
else
  bad "ffmpeg / ffprobe 缺失（macOS: brew install ffmpeg；Debian/Ubuntu: sudo apt install ffmpeg）"
fi

# 3. Python >= 3.10
if [ -n "$VENV_PY" ] && "$VENV_PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
  ok "Skill .venv Python >= 3.11"
else
  bad "Skill .venv 缺失或 Python 版本低于 3.11（请先运行 uv venv .venv --python 3.11 && uv sync）"
fi

# 4. shared venv with google-genai >= 2.10.0
if [ -x "$VENV_PY" ] && "$VENV_PY" - <<'PY' 2>/dev/null
import sys
from google import genai
parts = [int(x) for x in genai.__version__.split(".")[:2]]
sys.exit(0 if parts >= [2, 10] else 1)
PY
then
  ok "共享 venv 就绪（google-genai >= 2.10.0）"
else
  bad "Skill .venv 未创建或 google-genai 版本过旧（请在 Skill 根目录运行 uv sync）"
fi

exit $FAIL
