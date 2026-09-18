#!/usr/bin/env bash
#
# oracle-bone / uninstall.sh
#
# Removes the root router plus symlinks for the 26 current sub-skills and
# legacy entries (aliases and retired skills) from ~/.claude/skills/.
# Copied directories are reported
# but never deleted automatically, because they may contain user edits.
#
# Does NOT touch any content project's data (.oracle-state.json, predictions/,
# rubric_notes.md, user-profile.md, content-plan.md, candidates.md, etc.) — those
# live in your content directories and uninstalling the skill leaves your work intact.
#
# To re-install: bash install.sh

set -euo pipefail

SOURCE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

SKILLS=(
  oracle-init
  oracle-study
  oracle-learn-from
  oracle-apprentice
  oracle-migrate
  oracle-trends
  oracle-recommend
  oracle-seed
  oracle-voice
  oracle-score
  oracle-title
  oracle-description
  oracle-cover
  oracle-cover-analyze
  oracle-no-ai-slop
  oracle-who-for
  oracle-open-source
  oracle-simulate-audience
  oracle-compliance
  oracle-predict
  oracle-shoot
  oracle-edit-plan
  oracle-publish
  oracle-pinned-comment
  oracle-derivative
  oracle-retro
  oracle-compass-retro
  oracle-bump
  oracle-status
  oracle-feishu
)

echo ""
echo "Removing oracle-bone from ~/.claude/skills/"
echo ""

REMOVED=0
for s in "${SKILLS[@]}"; do
  TARGET="$HOME/.claude/skills/$s"
  if [[ -L "$TARGET" ]]; then
    LINK_TARGET=$(readlink "$TARGET")
    if [[ "$LINK_TARGET" == "$SOURCE_ROOT/skills/$s" ]]; then
      rm "$TARGET"
      echo "  ✓ removed symlink:   $s"
      REMOVED=$((REMOVED + 1))
    else
      echo "  · skipped foreign symlink: $s -> $LINK_TARGET"
    fi
  elif [[ -d "$TARGET" ]]; then
    echo "  · skipped directory:  $s (manual review required; not deleted)"
  else
    echo "  · not found:         $s (skipped)"
  fi
done

# Remove the root workflow router only when it points at this checkout.
ROOT_TARGET="$HOME/.claude/skills/oracle-bone"
if [[ -L "$ROOT_TARGET" ]]; then
  ROOT_LINK_TARGET=$(readlink "$ROOT_TARGET")
  if [[ "$ROOT_LINK_TARGET" == "$SOURCE_ROOT" ]]; then
    rm "$ROOT_TARGET"
    echo "  ✓ removed symlink:   oracle-bone"
    REMOVED=$((REMOVED + 1))
  else
    echo "  · skipped foreign symlink: oracle-bone -> $ROOT_LINK_TARGET"
  fi
elif [[ -d "$ROOT_TARGET" ]]; then
  echo "  · skipped directory:  oracle-bone (manual review required; not deleted)"
else
  echo "  · not found:         oracle-bone (skipped)"
fi

echo ""
if [[ $REMOVED -gt 0 ]]; then
  echo "✅ Uninstalled $REMOVED skill(s)."
else
  echo "ℹ️  Nothing to uninstall."
fi
echo ""
echo "Note: your content projects' data (predictions/, rubric_notes.md, .oracle-state.json,"
echo "      .oracle-hooks/, user-profile.md, content-plan.md, audience-profiles.md, candidates.md,"
echo "      etc.) are NOT touched. They live in each content project directory."
echo "      To clean a specific content project, delete those files manually."
echo ""
echo "To re-install: bash install.sh (from oracle-bone source root)"
echo ""
