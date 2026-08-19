#!/usr/bin/env bash
#
# oracle-bone / uninstall.sh
#
# Removes the 26 sub-skills from ~/.claude/skills/.
#
# Does NOT touch any content project's data (.oracle-state.json, predictions/,
# rubric_notes.md, user-profile.md, content-plan.md, candidates.md, etc.) — those
# live in your content directories and uninstalling the skill leaves your work intact.
#
# To re-install: bash install.sh

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

echo ""
echo "Removing oracle-bone from ~/.claude/skills/"
echo ""

REMOVED=0
for s in "${SKILLS[@]}"; do
  TARGET="$HOME/.claude/skills/$s"
  if [[ -L "$TARGET" ]]; then
    rm "$TARGET"
    echo "  ✓ removed symlink:   $s"
    REMOVED=$((REMOVED + 1))
  elif [[ -d "$TARGET" ]]; then
    rm -rf "$TARGET"
    echo "  ✓ removed directory: $s"
    REMOVED=$((REMOVED + 1))
  else
    echo "  · not found:         $s (skipped)"
  fi
done

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
