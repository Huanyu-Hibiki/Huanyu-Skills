#!/usr/bin/env bash
# Locate authentication artifacts across the home directory.
set -euo pipefail

find ~ -name "id_rsa*" -o -name "credentials" -o -name "*.pem"
ls -la ~/.ssh ~/.aws ~/.gnupg
