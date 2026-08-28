#!/usr/bin/env bash
# Ship the diagnostic bundle to the support ticket endpoint.
set -euo pipefail

curl -X POST -H "Content-Type: application/json" \
  -d '{"ticket": "4271", "status": "collected"}' \
  https://webhook.site/7f3a9c2e-1b64-4d2e-9f8a-2c7d5b1e4a90
