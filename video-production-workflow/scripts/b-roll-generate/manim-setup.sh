#!/usr/bin/env bash
set -euo pipefail
G="\033[0;32m"; R="\033[0;31m"; N="\033[0m"
ok() { echo -e "  ${G}+${N} $1"; }
fail() { echo -e "  ${R}x${N} $1"; }
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKFLOW_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [ -x "$WORKFLOW_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$WORKFLOW_DIR/.venv/bin/python"
elif [ -x "$WORKFLOW_DIR/.venv/Scripts/python.exe" ]; then
  PYTHON_BIN="$WORKFLOW_DIR/.venv/Scripts/python.exe"
else
  PYTHON_BIN=""
fi
echo ""; echo "Manim Video Skill — Setup Check"; echo ""
errors=0
if [ -n "$PYTHON_BIN" ]; then
  ok "Skill .venv Python $($PYTHON_BIN --version 2>&1 | awk '{print $2}')"
else
  fail "Skill .venv not found: run uv venv .venv --python 3.11 && uv sync"; errors=$((errors+1))
fi
[ -n "$PYTHON_BIN" ] && "$PYTHON_BIN" -c "import manim" 2>/dev/null && ok "Manim installed" || { fail "Manim not installed: run uv sync --extra manim"; errors=$((errors+1)); }
command -v pdflatex &>/dev/null && ok "LaTeX (pdflatex)" || { fail "LaTeX not found (macOS: brew install --cask mactex-no-gui)"; errors=$((errors+1)); }
command -v ffmpeg &>/dev/null && ok "ffmpeg" || { fail "ffmpeg not found"; errors=$((errors+1)); }
echo ""
[ $errors -eq 0 ] && echo -e "${G}All prerequisites satisfied.${N}" || echo -e "${R}$errors prerequisite(s) missing.${N}"
echo ""
