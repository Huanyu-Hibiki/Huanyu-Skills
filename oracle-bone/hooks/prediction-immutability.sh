#!/usr/bin/env bash
#
# oracle-bone / prediction-immutability hook
#
# Wires PreToolUse(Edit|Write) → blocks any edit that touches the
# '## 预测' / '## Prediction' section of a file under predictions/.
#
# Allows:
#   - Writing brand-new prediction files
#   - Editing the file's metadata header (above first ##)
#   - Appending to the '## 复盘' / '## Retrospective' section
#   - Touching files outside predictions/
#
# Blocks:
#   - Any change to lines between '## 预测' (or '## Prediction', any vN suffix) and the next non-prediction H2
#
# Bypass (rare, for true formatting-only fixes):
#   ORACLE_BYPASS_IMMUTABILITY=1 — single-shot bypass; logs a warning to stderr
#
# Requirements: bash 3+, jq, diff.
#
# Exit codes: 0 = allow, 1 = block (stderr surfaced to the model)

set -uo pipefail

# Single-shot bypass — opt-in, logs prominently
if [[ "${ORACLE_BYPASS_IMMUTABILITY:-0}" == "1" ]]; then
  echo "[oracle-bone] ⚠️  IMMUTABILITY BYPASS active (ORACLE_BYPASS_IMMUTABILITY=1)" >&2
  echo "[oracle-bone] ⚠️  This should only be used for pure markdown-formatting fixes." >&2
  echo "[oracle-bone] ⚠️  Bypass will be visible in git history." >&2
  exit 0
fi

# Read tool call payload from stdin (Claude Code passes JSON)
input=$(cat)
if [[ -z "$input" ]]; then
  exit 0
fi

# Extract tool name and file path
tool_name=$(printf '%s' "$input" | jq -r '.tool_name // empty' 2>/dev/null || echo "")
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || echo "")

# Only intercept Edit and Write
if [[ "$tool_name" != "Edit" && "$tool_name" != "Write" ]]; then
  exit 0
fi

if [[ -z "$file_path" ]]; then
  exit 0
fi

# Only intercept files under predictions/
case "$file_path" in
  */predictions/*.md|predictions/*.md)
    : # match — continue checking
    ;;
  *)
    exit 0
    ;;
esac

# Allow Write if the file does not yet exist (creating new prediction)
if [[ "$tool_name" == "Write" && ! -f "$file_path" ]]; then
  exit 0
fi

if [[ "$tool_name" == "Edit" ]]; then
  old_string=$(printf '%s' "$input" | jq -r '.tool_input.old_string // empty' 2>/dev/null || echo "")
  if [[ -z "$old_string" ]]; then
    exit 0
  fi

  # Find prediction section bounds. Match '## 预测' / '## Prediction' / '## 预测 v1'
  # / '## 预测 v2' / '## 预测 v1_a' etc. — all version-suffixed prediction headings
  # count as prediction sections and are locked together.
  # Section ends at the first NON-prediction '## ' heading (typically '## 复盘').
  prediction_section=$(awk '
    /^## / {
      if ($0 ~ /^## (预测|Prediction)([^a-zA-Z]|$)/) {
        in_pred=1; print; next
      } else if (in_pred) {
        exit
      }
    }
    in_pred { print }
  ' "$file_path" 2>/dev/null || echo "")

  if [[ -z "$prediction_section" ]]; then
    # File has no prediction section — let the edit through.
    exit 0
  fi

  # Check whether old_string appears inside the prediction section (literal match).
  pred_tmp=$(mktemp)
  printf '%s' "$prediction_section" > "$pred_tmp"

  if grep -qF -- "$old_string" "$pred_tmp" 2>/dev/null; then
    rm -f "$pred_tmp"
    cat >&2 <<EOF

[oracle-bone] 🚫 BLOCKED: edit targets the '## 预测' / '## Prediction' section of:
  $file_path

This violates principle #1 of oracle-bone: predictions are immutable.
Once written, the prediction section can never be modified — only the
'## 复盘' / '## Retrospective' section can be appended to.

What to do instead:
  • If you want to redo the prediction with new info, create a NEW file:
      ${file_path%.md}_redo.md
    The original must be preserved.
  • If you noticed a factual mistake AFTER seeing data, document it in the
    '## 复盘' section: "Correction: original probability X% should have been Y%".
  • If this is a pure markdown-formatting fix (no semantic change), you can
    bypass once with: ORACLE_BYPASS_IMMUTABILITY=1 (logs to stderr, visible in git).

See: shared-references/blind-prediction-protocol.md
EOF
    exit 1
  fi

  rm -f "$pred_tmp"
  exit 0
fi

# Write tool on an existing file — full overwrite, definitely touches prediction section.
if [[ "$tool_name" == "Write" && -f "$file_path" ]]; then
  cat >&2 <<EOF

[oracle-bone] 🚫 BLOCKED: Write would overwrite an existing prediction file:
  $file_path

Use Edit on the '## 复盘' section to append retrospective content.
Use a new '_redo.md' file path to create a redo prediction.
The original prediction file must be preserved verbatim.

See: shared-references/blind-prediction-protocol.md
EOF
  exit 1
fi

exit 0
