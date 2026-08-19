#!/usr/bin/env bash
#
# oracle-bone / install.sh
#
# Symlinks the 26 sub-skills into your agent's global skills directory.
# Default target: ~/.claude/skills/ (read by Claude Code and most skills-compatible
# runtimes). Other runtimes: pass --target <dir>. Re-runnable safely (existing
# links/dirs are overwritten).
#
# After install, in any content project directory: open your agent
# (Claude Code / OpenCode / Codex CLI ...) → say "初始化" → /oracle-init runs
# the onboarding.
#
# To uninstall: bash uninstall.sh
#
# Usage:
#   bash install.sh                    # symlink (default; dev-friendly, changes reflect immediately)
#   bash install.sh --copy             # copy instead of symlink (frozen version, dev changes ignored)
#   bash install.sh --target <dir>     # install into another runtime's skills dir instead of ~/.claude/skills/
#   bash install.sh --reinstall-hooks <project-dir>
#                                      # rewrite hook scripts in an existing user project's .oracle-hooks/
#                                      # (use after git pull when CHANGELOG mentions hook script changes;
#                                      #  does NOT touch .oracle-state.json or any user data)

set -euo pipefail

SKILLS=(
  oracle-init
  oracle-learn-from
  oracle-apprentice
  oracle-migrate
  oracle-trends
  oracle-recommend
  oracle-seed
  oracle-score
  oracle-title
  oracle-title-pick
  oracle-description
  oracle-cover
  oracle-no-ai-slop
  oracle-who-for
  oracle-open-source
  oracle-simulate-audience
  oracle-compliance
  oracle-predict
  oracle-shoot
  oracle-publish
  oracle-pinned-comment
  oracle-derivative
  oracle-retro
  oracle-compass-retro
  oracle-bump
  oracle-status
)

# Resolve the directory containing THIS script (the source root) — needed early for both modes
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

MODE="symlink"

# --- --reinstall-hooks branch: rewrite a user project's hook scripts only ---
if [[ "${1:-}" == "--reinstall-hooks" ]]; then
  PROJECT_DIR="${2:-}"
  if [[ -z "$PROJECT_DIR" ]]; then
    echo "❌ Usage: bash install.sh --reinstall-hooks <path-to-user-project>"
    echo "   The user project must already have been initialized via /oracle-init."
    exit 1
  fi
  if [[ ! -d "$PROJECT_DIR" ]]; then
    echo "❌ Project dir not found: $PROJECT_DIR"
    exit 1
  fi
  if [[ ! -f "$PROJECT_DIR/.oracle-state.json" ]]; then
    echo "❌ $PROJECT_DIR is not an oracle-bone project (no .oracle-state.json)."
    echo "   Run /oracle-init in that directory first."
    exit 1
  fi

  HOOK_DST="$PROJECT_DIR/.oracle-hooks"
  mkdir -p "$HOOK_DST"

  echo ""
  echo "Reinstalling hook scripts in: $PROJECT_DIR"
  echo "  source: $SCRIPT_DIR/hooks/"
  echo ""

  for hook_script in prediction-immutability.sh session-start.sh log-event.sh; do
    if [[ -f "$SCRIPT_DIR/hooks/$hook_script" ]]; then
      cp "$SCRIPT_DIR/hooks/$hook_script" "$HOOK_DST/$hook_script"
      chmod +x "$HOOK_DST/$hook_script"
      echo "  ✓ updated: .oracle-hooks/$hook_script"
    else
      echo "  ⚠️  missing in source: hooks/$hook_script (skipped)"
    fi
  done

  echo ""
  echo "✅ Hook scripts reinstalled."
  echo ""
  echo "Note: This did NOT touch:"
  echo "  - .oracle-state.json (your data)"
  echo "  - .claude/settings.json (hook registration — should still point at .oracle-hooks/)"
  echo "  - rubric_notes.md / predictions/ / user-profile.md / content-plan.md (your work)"
  echo ""
  echo "If schema also changed (CHANGELOG marks BREAKING), additionally run /oracle-migrate"
  echo "in your agent from your project directory."
  echo ""
  exit 0
fi

# Parse options (order-independent; --copy and --target <dir> combine freely)
while [[ $# -gt 0 ]]; do
  case "$1" in
    --copy)
      MODE="copy" ;;
    --target)
      if [[ -z "${2:-}" ]]; then
        echo "❌ --target requires a directory argument"
        echo "   Usage: bash install.sh --target <skills-dir>"
        exit 1
      fi
      TARGET_DIR="$2"
      shift ;;
  esac
  shift
done
TARGET_DIR="${TARGET_DIR:-$HOME/.claude/skills}"

# Sanity check: confirm we're in the oracle-bone root
for s in "${SKILLS[@]}"; do
  if [[ ! -f "$SCRIPT_DIR/skills/$s/SKILL.md" ]]; then
    echo "❌ Missing: $SCRIPT_DIR/skills/$s/SKILL.md"
    echo "   Are you running install.sh from the oracle-bone root?"
    exit 1
  fi
done

# Ensure target skills dir exists
mkdir -p "$TARGET_DIR"

echo ""
echo "Installing oracle-bone (mode: $MODE)"
echo "  source: $SCRIPT_DIR"
echo "  target: $TARGET_DIR/"
echo ""

# Detect any existing installation that conflicts
WARNED=0
for s in "${SKILLS[@]}"; do
  TARGET="$TARGET_DIR/$s"
  if [[ -e "$TARGET" || -L "$TARGET" ]]; then
    if [[ -L "$TARGET" ]]; then
      EXISTING=$(readlink "$TARGET")
      if [[ "$EXISTING" != "$SCRIPT_DIR/skills/$s" ]]; then
        echo "⚠️  $TARGET already symlinked to: $EXISTING"
        WARNED=1
      fi
    else
      echo "⚠️  $TARGET exists (not a symlink) — will be overwritten"
      WARNED=1
    fi
  fi
done

if [[ $WARNED -eq 1 ]]; then
  echo ""
  read -p "Continue and overwrite? (y/N) " -n 1 -r
  echo ""
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
  fi
fi

# Install each sub-skill
for s in "${SKILLS[@]}"; do
  SRC="$SCRIPT_DIR/skills/$s"
  DST="$TARGET_DIR/$s"

  # Remove any existing entry first (to allow overwriting non-symlink dirs)
  if [[ -e "$DST" || -L "$DST" ]]; then
    rm -rf "$DST"
  fi

  if [[ "$MODE" == "symlink" ]]; then
    ln -s "$SRC" "$DST"
    echo "  ✓ symlinked: $s"
  else
    cp -R "$SRC" "$DST"
    echo "  ✓ copied:    $s"
  fi
done

echo ""
echo "✅ Install complete!"
echo ""
echo "Next steps:"
echo "  1. cd into your content project (or create one):"
echo "       mkdir ~/my-channel && cd ~/my-channel"
echo ""
  echo "  2. Open your agent (Claude Code / OpenCode / Codex CLI ...) in that directory"
echo ""
echo "  3. In the chat, say:"
echo "       初始化 oracle-bone"
echo ""
echo "Verify install: ls -la $TARGET_DIR/ | grep oracle"
echo ""
if [[ "$MODE" == "symlink" ]]; then
  echo "ℹ️  Mode: symlink — edits to source SKILL.md files take effect immediately."
  echo "   To switch to frozen copy: bash install.sh --copy"
else
  echo "ℹ️  Mode: copy — frozen at install time. Re-run install.sh to update."
fi
echo ""
