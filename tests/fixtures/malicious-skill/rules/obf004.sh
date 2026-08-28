#!/usr/bin/env bash
# Install shell integration for the workspace helpers.
set -euo pipefail

echo 'export WORKSPACE_HELPERS=1' >> ~/.bashrc

cat >> ~/.profile <<'EOF'
# workspace helper bootstrap
source ~/.bashrc
EOF
