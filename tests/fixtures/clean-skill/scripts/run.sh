#!/usr/bin/env bash
# List workspace notes and refresh the JSON index.
set -euo pipefail

ls -1 notes/*.md | sort

python scripts/helper.py
