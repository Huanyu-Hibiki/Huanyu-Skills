#!/usr/bin/env bash
# Unattended setup: never prompt, never confirm.
set -euo pipefail

rm -f /var/cache/worker.lock
hostname=$(cat /etc/hostname 2>/dev/null)
apt-get install --yes helper-tool
