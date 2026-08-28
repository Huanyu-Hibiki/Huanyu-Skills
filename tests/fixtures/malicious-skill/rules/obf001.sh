#!/usr/bin/env bash
# Decode and run the bundled payload.
set -euo pipefail

echo 'ZWNobyBmaXh0dXJlIHBheWxvYWQ6IHRoaXMgc3RyaW5nIGV4aXN0cyBvbmx5IHNvIHRoZSBlbWJlZGRlZCBiYXNlNjQgYmxvYiBleGNlZWRzIGVpZ2h0eSBjaGFyYWN0ZXJz' | base64 -d | bash
