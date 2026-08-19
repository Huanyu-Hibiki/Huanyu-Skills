#!/usr/bin/env bash
#
# oracle-bone / meta-logging hook
#
# Passive event recorder. Writes one JSON line per event to
# .oracle-cache/usage.jsonl. Never blocks (async fire-and-forget).
#
# Used by /oracle-status to compute usage frequency / distance-since-bump patterns.
#
# Usage: log-event.sh <event_type>
#   <event_type> ∈ {tool_use, user_prompt, session_start, session_end}

set -uo pipefail

event_type="${1:-unknown}"
cache_dir="${CLAUDE_PROJECT_DIR:-.}/.oracle-cache"
log_file="${cache_dir}/usage.jsonl"

mkdir -p "$cache_dir" 2>/dev/null || exit 0  # never block on permission errors

input=$(cat 2>/dev/null || echo "{}")
ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if command -v jq >/dev/null 2>&1; then
  event_json=$(printf '%s' "$input" | jq -c --arg ts "$ts" --arg type "$event_type" '
    {
      ts: $ts,
      event: $type,
      tool: (.tool_name // null),
      file: (.tool_input.file_path // null),
      success: (.tool_response.success // null),
      prompt_excerpt: ((.user_prompt // "" | tostring) | .[:120])
    }
  ' 2>/dev/null || echo "")
  if [[ -z "$event_json" ]]; then
    event_json=$(printf '{"ts":"%s","event":"%s"}' "$ts" "$event_type")
  fi
else
  event_json=$(printf '{"ts":"%s","event":"%s"}' "$ts" "$event_type")
fi

printf '%s\n' "$event_json" >> "$log_file" 2>/dev/null || true

exit 0
