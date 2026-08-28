#!/usr/bin/env bash
# Silent elevated cleanup.
set -euo pipefail

sudo -n rm /var/cache/stale.lock
sudo -n systemctl restart worker
