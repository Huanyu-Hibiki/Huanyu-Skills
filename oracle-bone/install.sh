#!/usr/bin/env bash
#
# oracle-bone / install.sh
#
# Symlinks the root router plus 26 canonical sub-skills and 3 compatibility
# aliases into your agent's global skills directory.
# Default target: ~/.claude/skills/ (read by Claude Code and most skills-compatible
# runtimes). Other runtimes: pass --target <dir>. Re-runnable safely: owned
# links are refreshed, while existing directories and foreign links are skipped.
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
  oracle-study
  oracle-learn-from
  oracle-apprentice
  oracle-cover-analyze
  oracle-migrate
  oracle-trends
  oracle-recommend
  oracle-seed
  oracle-voice
  oracle-score
  oracle-title
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
  oracle-feishu
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

# Retire the removed production skill on upgrade only when the old entry is a
# symlink owned by an oracle-bone checkout. Non-symlink copies are left for
# manual review so an unrelated skill is never deleted.
RETIRED=(oracle-edit-plan)
for retired in "${RETIRED[@]}"; do
  RETIRED_TARGET="$TARGET_DIR/$retired"
  if [[ -L "$RETIRED_TARGET" ]]; then
    RETIRED_LINK=$(readlink "$RETIRED_TARGET")
    if [[ "$RETIRED_LINK" == */oracle-bone/skills/$retired ]]; then
      rm "$RETIRED_TARGET"
      echo "  ✓ retired legacy symlink: $retired"
    else
      echo "  ⚠️  retired entry points elsewhere, skipped: $retired"
    fi
  elif [[ -d "$RETIRED_TARGET" ]]; then
    echo "  ⚠️  retired directory remains for manual review: $retired"
  fi
done

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
        echo "⚠️  $TARGET already symlinked to another source: $EXISTING (will skip)"
        WARNED=1
      fi
    else
      echo "⚠️  $TARGET exists (not a symlink) — will be skipped"
      WARNED=1
    fi
  fi
done

if [[ $WARNED -eq 1 ]]; then
  echo ""
  read -p "Continue (conflicting entries will be skipped)? (y/N) " -n 1 -r
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

  # Only replace symlinks; never recursively delete a non-symlink directory.
  if [[ -L "$DST" ]]; then
    EXISTING=$(readlink "$DST")
    if [[ "$EXISTING" == "$SCRIPT_DIR/skills/$s" ]]; then
      rm "$DST"
    else
      echo "⏭️  symlink points elsewhere, skipped: $s"
      continue
    fi
  elif [[ -d "$DST" ]]; then
    echo "⚠️  existing directory skipped: $s (it may be an older copy; remove it manually on a clean upgrade)"
    continue
  fi

  if [[ "$MODE" == "symlink" ]]; then
    ln -s "$SRC" "$DST"
    echo "  ✓ symlinked: $s"
  else
    cp -R "$SRC" "$DST"
    touch "$DST/.oracle-bone-copy"
    echo "  ✓ copied:    $s"
  fi
done

# Install the workflow router itself as /oracle-bone. It is intentionally not
# counted in SKILLS because the public inventory counts sub-skills only.
MAIN_SRC="$SCRIPT_DIR"
MAIN_DST="$TARGET_DIR/oracle-bone"
PACKAGE_ROOT_OWNED=0
if [[ -L "$MAIN_DST" ]]; then
  EXISTING=$(readlink "$MAIN_DST")
  if [[ "$EXISTING" == "$MAIN_SRC" ]]; then
    rm "$MAIN_DST"
  else
    echo "⏭️  root symlink points elsewhere, skipped: oracle-bone"
    MAIN_DST=""
  fi
elif [[ -d "$MAIN_DST" ]]; then
  if [[ -f "$MAIN_DST/.oracle-bone-copy" ]]; then
    echo "⚠️  existing oracle-bone copy skipped (use a clean target to refresh)"
    PACKAGE_ROOT_OWNED=1
  else
    echo "⚠️  existing root directory skipped: oracle-bone (remove it manually to refresh)"
  fi
  MAIN_DST=""
fi
if [[ -n "$MAIN_DST" ]]; then
  if [[ "$MODE" == "symlink" ]]; then
    ln -s "$MAIN_SRC" "$MAIN_DST"
    echo "  ✓ symlinked: oracle-bone"
  else
    mkdir -p "$MAIN_DST"
    cp "$MAIN_SRC/SKILL.md" "$MAIN_DST/SKILL.md"
    for doc in DESIGN.md MAINTENANCE.md README.md CHANGELOG.md LICENSE; do
      if [[ -f "$MAIN_SRC/$doc" ]]; then
        cp "$MAIN_SRC/$doc" "$MAIN_DST/$doc"
      fi
    done
    touch "$MAIN_DST/.oracle-bone-copy"
    PACKAGE_ROOT_OWNED=1
    echo "  ✓ copied:    oracle-bone"
  fi
fi

# Copy mode must carry the shared protocol tree with the frozen skill copies;
# many SKILL.md files resolve ../../references and ../../shared-references.
# Never overwrite an existing top-level directory owned by another package.
if [[ "$MODE" == "copy" ]]; then
  RUNTIME_DIRS=(references shared-references templates starter-rubrics tools adapters hooks examples)
  # The canonical SKILL.md files keep repository-relative links such as
  # ../../shared-references. With direct copies in <skills-dir>/oracle-*,
  # those links resolve from the parent of <skills-dir>; keep a package-local
  # copy beside the root entry as well so both direct and root routes work.
  RESOURCE_ROOT="$(cd -- "$(dirname "$TARGET_DIR")" &> /dev/null && pwd)"
  PACKAGE_ROOT="$TARGET_DIR/oracle-bone"
  if [[ ! -d "$PACKAGE_ROOT" ]]; then
    mkdir -p "$PACKAGE_ROOT"
  fi
  RESOURCE_CONFLICT=0
  for d in "${RUNTIME_DIRS[@]}"; do
    for DST in "$RESOURCE_ROOT/$d"; do
      if [[ -e "$DST" || -L "$DST" ]] && [[ ! -f "$DST/.oracle-bone-resource" ]]; then
        echo "❌ shared resource exists without oracle-bone ownership marker: $DST"
        RESOURCE_CONFLICT=1
      fi
    done
    if [[ "$PACKAGE_ROOT_OWNED" -eq 1 ]]; then
      DST="$PACKAGE_ROOT/$d"
      if [[ -e "$DST" || -L "$DST" ]] && [[ ! -f "$DST/.oracle-bone-resource" ]]; then
        echo "❌ package resource exists without oracle-bone ownership marker: $DST"
        RESOURCE_CONFLICT=1
      fi
    fi
  done
  if [[ "$RESOURCE_CONFLICT" -eq 1 ]]; then
    echo "   Copy install aborted. Use a clean target or review the conflicting directories manually."
    exit 1
  fi
  for d in "${RUNTIME_DIRS[@]}"; do
    SRC="$SCRIPT_DIR/$d"
    DESTINATIONS=("$RESOURCE_ROOT/$d")
    if [[ "$PACKAGE_ROOT_OWNED" -eq 1 ]]; then
      DESTINATIONS+=("$PACKAGE_ROOT/$d")
    fi
    for DST in "${DESTINATIONS[@]}"; do
      if [[ -e "$DST" || -L "$DST" ]]; then
        echo "⚠️  shared resource exists, skipped: $DST"
      else
        cp -R "$SRC" "$DST"
        touch "$DST/.oracle-bone-resource"
        echo "  ✓ copied shared resources: $DST"
      fi
    done
  done
fi

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
  echo "ℹ️  Mode: copy — frozen at install time. Existing directories are never overwritten; use a clean target to update."
fi
echo ""
