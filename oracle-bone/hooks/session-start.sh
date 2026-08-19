#!/usr/bin/env bash
#
# oracle-bone SessionStart hook
#
# Renders a 4-6 line status report at the start of every session.
# Silently exits if not in an oracle-bone project (no .oracle-state.json)
# or jq unavailable (AI can read state directly).
#
# Format:
#   📦 Buffer: N (color)
#   ⏰ 待复盘: N (按窗口)
#   🎯 候选 top 3: ...
#   📈 分轨样本 + confidence
#   ⚠️ 待办 / schema 提示

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
STATE_FILE="$PROJECT_DIR/.oracle-state.json"

if [[ ! -f "$STATE_FILE" ]]; then
  exit 0
fi

if ! command -v jq >/dev/null 2>&1; then
  cat <<'EOF'
[oracle-bone] SessionStart: jq not installed — skipping auto status report.
AI can still read .oracle-state.json directly. Say "状态" for full status.
EOF
  exit 0
fi

state=$(cat "$STATE_FILE")
schema_version=$(echo "$state" | jq -r '.schema_version // "unknown"')
plan_type=$(echo "$state" | jq -r '.plan_type // "unknown"')
calibration_total=$(echo "$state" | jq -r '.calibration_samples_total // 0')
target_cadence=$(echo "$state" | jq -r '.target_publish_cadence_days // null')
buffer_count=$(echo "$state" | jq -r '.shoots // [] | length')
pending_retros_count=$(echo "$state" | jq -r '.pending_retros // [] | length')
hooks_installed=$(echo "$state" | jq -r '.hooks_installed // false')

# --- Schema mismatch check (maintainer bumps this alongside oracle-init) ---
LATEST_SCHEMA="1.0"
schema_mismatch=""
if [[ "$schema_version" != "$LATEST_SCHEMA" && "$schema_version" != "unknown" ]]; then
  schema_mismatch="⚠️  schema 版本不一致：state=${schema_version}, skill 期望=${LATEST_SCHEMA}。建议跑 /oracle-migrate（非阻塞）。"
fi

# --- Per-track samples line ---
tracks_line=$(echo "$state" | jq -r '
  .tracks.defaults // .tracks.definitions // []
  | map("\(.name // .id): \(.rubric_version // "v0")")
  | join(" · ")
' 2>/dev/null || echo "")
samples_by_track=$(echo "$state" | jq -r '
  .calibration_samples_by_track // {}
  | to_entries | map("\(.key)=\(.value)") | join(" ")
' 2>/dev/null || echo "")

# --- Confidence (from total samples; per-track detail shown alongside) ---
if   [[ $calibration_total -eq 0 ]]; then confidence="🔴 极低"
elif [[ $calibration_total -le 2 ]]; then confidence="🟠 低"
elif [[ $calibration_total -le 5 ]]; then confidence="🟡 偏低"
elif [[ $calibration_total -le 10 ]]; then confidence="🟢 中"
elif [[ $calibration_total -le 20 ]]; then confidence="🟢 较高"
else confidence="🔵 高"
fi

# --- Buffer color ---
buffer_label=""
buffer_warning=""
if [[ "$target_cadence" == "null" ]] || [[ -z "$target_cadence" ]]; then
  buffer_label="📦 Buffer: ${buffer_count} 篇 (灵活节奏，无警戒)"
else
  buffer_days=$(( buffer_count * target_cadence ))
  if   [[ $buffer_days -lt 1 ]]; then
    buffer_label="📦 Buffer: ${buffer_count} 篇 🔴 红 (cadence ${target_cadence}d = <1 天预备)"
    buffer_warning="🚨 buffer 警戒：下个发布日可能断更。今天必须做 ≥1 条稳分。"
  elif [[ $buffer_days -le 2 ]]; then
    buffer_label="📦 Buffer: ${buffer_count} 篇 🟠 橙 (${buffer_days} 天预备)"
  elif [[ $buffer_days -le 5 ]]; then
    buffer_label="📦 Buffer: ${buffer_count} 篇 🟢 绿 (${buffer_days} 天预备)"
  else
    buffer_label="📦 Buffer: ${buffer_count} 篇 🔵 蓝 (${buffer_days} 天，积压)"
    buffer_warning="📦 buffer 积压：建议暂停制作，先发存货 + 复盘。"
  fi
fi

# --- Pending retros: count due windows (oracle-bone schema: due_windows[].due_at vs today) ---
today_iso=$(date +%Y-%m-%d)
due_count=$(echo "$state" | jq -r --arg today "$today_iso" '
  [.pending_retros // []
    | .[]
    | .due_windows // []
    | .[]
    | select(.done == false and .due_at != null and (.due_at[:10] <= $today))]
  | length
' 2>/dev/null || echo 0)

if [[ "$due_count" -gt 0 ]]; then
  retro_label="⏰ 待复盘: ${due_count} 个窗口到期 (说 \"复盘 <作品>\")"
elif [[ "$pending_retros_count" -gt 0 ]]; then
  retro_label="⏰ 待复盘: ${pending_retros_count} 篇 (窗口未到)"
else
  retro_label="⏰ 待复盘: 无"
fi

# --- Top candidates (first 3 H3 from candidates.md) ---
top_candidates=""
if [[ -f "$PROJECT_DIR/candidates.md" ]]; then
  top_candidates=$(grep -E '^### ' "$PROJECT_DIR/candidates.md" 2>/dev/null \
    | head -3 \
    | sed -E 's/^### \[[^]]+\] *//' \
    | tr '\n' '/' | sed 's:/$::' | sed 's:/: / :g')
fi
if [[ -z "$top_candidates" ]]; then
  candidates_label="🎯 候选: (空——说 '抓热点' 或 '找选题')"
else
  candidates_label="🎯 候选 top 3: ${top_candidates}"
fi

# --- Build report ---
echo ""
echo "[oracle-bone / SessionStart 状态报告]"
echo ""
echo "$buffer_label"
echo "$retro_label"
echo "$candidates_label"
echo "📈 规划: ${plan_type} | 总样本: ${calibration_total} (${samples_by_track}) | Confidence: ${confidence}"
[[ -n "$tracks_line" ]] && echo "🛤  轨道: ${tracks_line}"

[[ -n "$buffer_warning" ]] && echo "" && echo "$buffer_warning"
[[ -n "$schema_mismatch" ]] && echo "" && echo "$schema_mismatch"
if [[ "$hooks_installed" != "true" ]]; then
  echo "⚠️  immutability hook 未装——盲预测保护是君子协定，不是物理强制。"
fi

echo ""
echo "（不要主动开始任何动作——等用户决定。说 \"状态\" 看完整看板。）"
echo ""

exit 0
