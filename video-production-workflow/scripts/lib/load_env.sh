#!/usr/bin/env bash
# 从 Skill 根目录加载 .env；已有 shell 环境变量优先。

_env_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_env_skill_root="$(cd "$_env_script_dir/../.." && pwd)"
_env_file="$_env_skill_root/.env"

if [ -f "$_env_file" ]; then
  while IFS= read -r _env_line || [ -n "$_env_line" ]; do
    case "$_env_line" in
      ''|[[:space:]]*|\#*) continue ;;
    esac
    _env_key="${_env_line%%=*}"
    _env_value="${_env_line#*=}"
    _env_key="$(printf '%s' "$_env_key" | tr -d '[:space:]')"
    case "$_env_value" in
      \"*\") _env_value="${_env_value:1:${#_env_value}-2}" ;;
      \'*\') _env_value="${_env_value:1:${#_env_value}-2}" ;;
    esac
    [ -n "$_env_key" ] || continue
    if [ -z "${!_env_key+x}" ]; then
      export "$_env_key=$_env_value"
    fi
  done < "$_env_file"
fi

unset _env_script_dir _env_skill_root _env_file _env_line _env_key _env_value
